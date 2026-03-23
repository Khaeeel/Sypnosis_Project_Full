import pandas as pd
import chromadb
import uuid
from sqlalchemy import text
from shared_config import engine

def ingest_jargon_dictionary(file_path):
    print(f"--- Loading Dictionary: {file_path} ---")
    
    # Initialize ChromaDB locally ONLY when this script runs
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    collection = chroma_client.get_or_create_collection(name="jargon_embeddings")
    
    df = pd.read_csv(file_path)
    
    # Data Cleaning
    df['word'] = df['word'].astype(str).str.strip().str.lower()
    df['dialect'] = df['dialect'].astype(str).str.strip()
    df['definition'] = df['definition'].astype(str).str.strip()
    df['letter'] = df['letter'].astype(str).str.strip().str.upper()

    print("Inserting into MySQL...")
    with engine.begin() as conn:
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

    print("Generating Embeddings for ChromaDB...")
    documents, metadatas, ids = [], [], []
    for _, row in df.iterrows():
        documents.append(f"{row['word']}: {row['definition']} ({row['dialect']})")
        metadatas.append({"word": row['word'], "dialect": row['dialect'], "letter": row['letter']})
        ids.append(str(uuid.uuid4()))

    batch_size = 5000
    for i in range(0, len(documents), batch_size):
        print(f"-> Processing Chroma batch {(i//batch_size)+1}...")
        collection.upsert(
            documents=documents[i:i+batch_size],
            metadatas=metadatas[i:i+batch_size],
            ids=ids[i:i+batch_size]
        )
    print("✅ Jargon Ingestion Complete! (GPU Memory will now be released)")

if __name__ == "__main__":
    ingest_jargon_dictionary("FilipinoWordsDictionary - Sheet.csv")