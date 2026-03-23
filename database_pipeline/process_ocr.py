import os
import json
from sqlalchemy import text
from shared_config import engine, SUMMARY_INPUT_DIR

def upload_raw_ocr_json():
    # Find all json files, but ignore the master_tasks file if it accidentally ends up here
    files = [f for f in os.listdir(SUMMARY_INPUT_DIR) if f.endswith('.json') and 'master' not in f.lower()]
    
    if not files:
        print("No OCR .json files found.")
        return

    print(f"--- Processing {len(files)} OCR JSON results ---")
    
    # engine.begin() auto-commits and prevents the red-line error
    with engine.begin() as conn:
        for file_name in files:
            file_path = os.path.join(SUMMARY_INPUT_DIR, file_name)
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    if not data:
                        print(f"⚠️ Skipping {file_name}: File is empty.")
                        continue
                        
                    query = text("""
                        INSERT INTO ocr_results (file_name, raw_json_data)
                        VALUES (:file_name, :json_data)
                        ON DUPLICATE KEY UPDATE 
                        raw_json_data = VALUES(raw_json_data),
                        processed_at = CURRENT_TIMESTAMP
                    """)
                    
                    conn.execute(query, {"file_name": file_name, "json_data": json.dumps(data)})
                    print(f"✅ OCR Result Saved: {file_name}")
                except Exception as e:
                    print(f"❌ Error processing {file_name}: {e}")

if __name__ == "__main__":
    upload_raw_ocr_json()