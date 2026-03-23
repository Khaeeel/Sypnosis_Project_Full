import json
import os
from sqlalchemy import text
from shared_config import engine, TASK_JSON_PATH

def sync_master_tasks():
    if not os.path.exists(TASK_JSON_PATH):
        print(f"❌ Error: {TASK_JSON_PATH} not found.")
        return

    print(f"--- Loading Tasks from {TASK_JSON_PATH} ---")
    with open(TASK_JSON_PATH, 'r', encoding='utf-8') as f:
        tasks_data = json.load(f)

    with engine.begin() as conn:
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
                
    print("✅ Tasks synced to Database successfully.")

if __name__ == "__main__":
    sync_master_tasks()