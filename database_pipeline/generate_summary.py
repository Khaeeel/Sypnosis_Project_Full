import os
import pandas as pd
from thefuzz import process
from sqlalchemy import text
from shared_config import engine, SUMMARY_INPUT_DIR

# --- COMPONENT A: ALIAS NORMALIZER ---
class AliasNormalizer:
    def __init__(self, db_engine):
        self.engine = db_engine
        self._load_aliases()

    def _load_aliases(self):
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
        exact_match = self.alias_df[self.alias_df['alias'] == clean_input]
        
        if not exact_match.empty:
            row = exact_match.iloc[0]
            return {"canonical_name": row['canonical_name'], "department": row['department']}

        if self.alias_list:
            best_match, score = process.extractOne(clean_input, self.alias_list)
            if score >= threshold:
                row = self.alias_df[self.alias_df['alias'] == best_match].iloc[0]
                return {"canonical_name": row['canonical_name'], "department": row['department']}

        return {"canonical_name": "Unknown", "department": "Miscellaneous"}

# --- COMPONENT C: SUMMARY RECORDING ---
def process_txt_summaries(user_id=1):
    files = [f for f in os.listdir(SUMMARY_INPUT_DIR) if f.endswith('.txt')]
    if not files:
        print("No .txt summaries found.")
        return

    print(f"--- Processing {len(files)} AI Summaries ---")
    
    with engine.begin() as conn:
        for file_name in files:
            file_path = os.path.join(SUMMARY_INPUT_DIR, file_name)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            try:
                query = text("""
                    INSERT INTO summaries (file_name, summary_text, user_id)
                    VALUES (:file_name, :content, :uid)
                """)
                conn.execute(query, {"file_name": file_name, "content": content, "uid": user_id})
                print(f"✅ AI Summary Recorded: {file_name}")
            except Exception as e:
                print(f"❌ Error recording {file_name}: {e}")

if __name__ == "__main__":
    # Example of testing the normalizer before saving summaries
    normalizer = AliasNormalizer(engine)
    print(f"Testing normalizer on 'ryan': {normalizer.normalize('ryan')}")
    
    # Save the text summaries to the DB
    process_txt_summaries(user_id=1)