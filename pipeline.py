import os
import pandas as pd
import chromadb
import json
import uuid
from thefuzz import process
from sqlalchemy import create_engine, text

# ==========================================
# CONFIGURATION & SETUP
# ==========================================
# MySQL connection string
DB_URL = "mysql+mysqlconnector://root:comfac%40123@127.0.0.1:3306/sypnosis"
engine = create_engine(DB_URL)

# Initialize ChromaDB (Local persistent storage)
chroma_client = chromadb.PersistentClient(path="./chroma_db")
jargon_collection = chroma_client.get_or_create_collection(name="jargon_embeddings")

# Folders for Input
SUMMARY_INPUT_DIR = "./summaries_input"
TASK_JSON_PATH = "master_tasks.json" # The JSON file you provided

# Ensure the folder exists
if not os.path.exists(SUMMARY_INPUT_DIR):
    os.makedirs(SUMMARY_INPUT_DIR)

# ==========================================
# COMPONENT A: OCR ALIAS NORMALIZATION
# ==========================================
class AliasNormalizer:
    def __init__(self, db_engine):
        self.engine = db_engine
        self._load_aliases()

    def _load_aliases(self):
        """Loads all aliases into memory for fast fuzzy matching."""
        query = """
            SELECT s.alias, s.canonical_name, d.name as department
            FROM sender_aliases s
            LEFT JOIN departments d ON s.department_id = d.id
        """
        with self.engine.connect() as conn:
            self.alias_df = pd.read_sql(query, conn)
        self.alias_list = self.alias_df['alias'].tolist()

    def normalize(self, ocr_input: str, threshold: int = 85):
        clean_input = str(ocr_input).strip().lower()
        
        # 1. Exact Match
        exact_match = self.alias_df[self.alias_df['alias'] == clean_input]
        if not exact_match.empty:
            row = exact_match.iloc[0]
            return {"canonical_name": row['canonical_name'], "department": row['department'], "confidence": 100}

        # 2. Fuzzy Match
        if self.alias_list:
            best_match, score = process.extractOne(clean_input, self.alias_list)
            if score >= threshold:
                row = self.alias_df[self.alias_df['alias'] == best_match].iloc[0]
                return {"canonical_name": row['canonical_name'], "department": row['department'], "confidence": score}

        return {"canonical_name": "Unknown", "department": "Miscellaneous", "confidence": 0}

# ==========================================
# COMPONENT B: JARGON CSV TO CHROMADB
# ==========================================
class JargonPipeline:
    def __init__(self, db_engine, vector_collection):
        self.engine = db_engine
        self.collection = vector_collection

    def process_csv(self, file_path: str):
        print(f"--- Component B: Loading Dictionary {file_path} ---")
        df = pd.read_csv(file_path)
        
        # Data Cleaning
        df['word'] = df['word'].astype(str).str.strip().str.lower()
        df['dialect'] = df['dialect'].astype(str).str.strip()
        df['definition'] = df['definition'].astype(str).str.strip()
        df['letter'] = df['letter'].astype(str).str.strip().str.upper()

        # Insert into MySQL
        with self.engine.connect() as conn:
            print("Inserting into MySQL...")
            for _, row in df.iterrows():
                try:
                    query = text("""
                        INSERT IGNORE INTO jargons (letter, word, definition, dialect)
                        VALUES (:letter, :word, :definition, :dialect)
                    """)
                    conn.execute(query, {
                        "letter": row['letter'][:2], "word": row['word'],
                        "definition": row['definition'], "dialect": row['dialect']
                    })
                except Exception: pass
            conn.commit()

        # ChromaDB Batch Ingestion
        documents, metadatas, ids = [], [], []
        for _, row in df.iterrows():
            documents.append(f"{row['word']}: {row['definition']} ({row['dialect']})")
            metadatas.append({"word": row['word'], "dialect": row['dialect'], "letter": row['letter']})
            ids.append(str(uuid.uuid4()))

        batch_size = 5000
        for i in range(0, len(documents), batch_size):
            print(f"-> Chroma batch {(i//batch_size)+1}...")
            self.collection.upsert(
                documents=documents[i:i+batch_size],
                metadatas=metadatas[i:i+batch_size],
                ids=ids[i:i+batch_size]
            )
        print("✅ Jargon Ingestion Complete!")

# ==========================================
# COMPONENT C: SUMMARY RECORDING
# ==========================================
class SummaryPipeline:
    def __init__(self, db_engine):
        self.engine = db_engine

    def process_summaries(self, folder_path, user_id=1):
        """Reads .txt summaries and links them to a user_id."""
        files = [f for f in os.listdir(folder_path) if f.endswith('.txt')]
        if not files:
            print("No .txt summaries found.")
            return

        print(f"--- Component C: Processing {len(files)} summaries ---")
        with self.engine.connect() as conn:
            for file_name in files:
                file_path = os.path.join(folder_path, file_name)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                try:
                    query = text("""
                        INSERT INTO summaries (file_name, summary_text, user_id)
                        VALUES (:file_name, :content, :uid)
                    """)
                    conn.execute(query, {"file_name": file_name, "content": content, "uid": user_id})
                    print(f"✅ Summary Recorded: {file_name}")
                except Exception as e:
                    print(f"❌ Error recording {file_name}: {e}")
            conn.commit()

# ==========================================
# COMPONENT D: TASK CRUD PIPELINE
# ==========================================
class TaskPipeline:
    def __init__(self, db_engine):
        self.engine = db_engine

    def import_tasks_from_json(self, json_file_path):
        """Imports Master Tasks with Department-First logic."""
        if not os.path.exists(json_file_path):
            print(f"JSON file {json_file_path} not found.")
            return

        print(f"--- Component D: Loading Tasks from {json_file_path} ---")
        with open(json_file_path, 'r', encoding='utf-8') as f:
            tasks_data = json.load(f)

        with self.engine.connect() as conn:
            for item in tasks_data:
                assignees_str = ", ".join(item.get('possible_assignees', []))
                
                query = text("""
                    INSERT INTO tasks 
                    (task_id, task_description, department_name, status, date_created, possible_assignees, completed_by, notes)
                    VALUES 
                    (:tid, :desc, :dept, :stat, :date, :pos_as, :comp_by, :notes)
                    ON DUPLICATE KEY UPDATE 
                    status = VALUES(status), 
                    notes = VALUES(notes),
                    updated_at = CURRENT_TIMESTAMP
                """)
                
                try:
                    conn.execute(query, {
                        "tid": item['task_id'],
                        "desc": item['task_description'],
                        "dept": item['department'],
                        "stat": item['status'],
                        "date": item['date_created'],
                        "pos_as": assignees_str,
                        "comp_by": item['completed_by'],
                        "notes": item['notes']
                    })
                except Exception as e:
                    print(f"❌ Task Error {item.get('task_id')}: {e}")
            conn.commit()
        print("✅ Task Table Updated!")

# ==========================================
# COMPONENT E: RAW OCR DATA IMPORT
# ==========================================
class OCRPipeline:
    def __init__(self, db_engine):
        self.engine = db_engine

    def process_ocr_json(self, folder_path):
        """Reads OCR .json files and saves the raw result to MySQL."""
        import json
        
        files = [f for f in os.listdir(folder_path) if f.endswith('.json')]
        if not files:
            print("No OCR .json files found.")
            return

        print(f"--- Component E: Saving {len(files)} OCR JSON results ---")
        with self.engine.connect() as conn:
            for file_name in files:
                file_path = os.path.join(folder_path, file_name)
                with open(file_path, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                        # We convert the dict to a string for MySQL JSON column
                        json_string = json.dumps(data)
                        
                        query = text("""
                            INSERT INTO ocr_results (file_name, raw_json_data)
                            VALUES (:file_name, :json_data)
                            ON DUPLICATE KEY UPDATE 
                            raw_json_data = VALUES(raw_json_data)
                        """)
                        
                        conn.execute(query, {
                            "file_name": file_name, 
                            "json_data": json_string
                        })
                        print(f"✅ OCR Result Saved: {file_name}")
                    except Exception as e:
                        print(f"❌ Error parsing/saving {file_name}: {e}")
            conn.commit()

# ==========================================
# EXECUTION
# ==========================================
if __name__ == "__main__":
    # 1. Component A (Normalization Test)
    normalizer = AliasNormalizer(engine)
    print("\n--- Connection Test ---")
    print(f"Testing 'ryan': {normalizer.normalize('ryan')}")
    
    # 2. Component B (Jargon) - Uncomment to run 105k import
    # jargon_p = JargonPipeline(engine, jargon_collection)
    # jargon_p.process_csv("FilipinoWordsDictionary - Sheet.csv")
    
    # 3. Component C (Summaries)
    summary_p = SummaryPipeline(engine)
    summary_p.process_summaries(SUMMARY_INPUT_DIR, user_id=1)

    # 4. Component D (Tasks)
    task_p = TaskPipeline(engine)
    task_p.import_tasks_from_json(TASK_JSON_PATH)

    # 5. Component E (Raw OCR Results)
    # This will pick up your merged_03-12-26.json file
    ocr_p = OCRPipeline(engine)
    ocr_p.process_ocr_json(SUMMARY_INPUT_DIR)

    print("\n--- Sypnosis Pipeline Run Complete ---")