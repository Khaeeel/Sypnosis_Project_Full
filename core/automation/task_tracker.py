import os
import sys
import json
import requests
import re
from datetime import datetime
from sqlalchemy import create_engine, text

# =========================================================
# 1. PATHING & ENVIRONMENT FIX
# =========================================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../"))

# Ensure custom modules are discoverable
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
    sys.path.insert(0, os.path.join(ROOT, "core", "ocr"))

from ocr_utils import OFFICIAL_ORGANIZATION

# =========================
# 2. CONFIGURATION & DATABASE
# =========================
OLLAMA_API = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen3.5:9b" 

# Database Connection (PC #2 Configuration)
DB_URL = "mysql+mysqlconnector://root:comfac%40123@127.0.0.1:3306/sypnosis"
engine = create_engine(DB_URL)

# Dynamic Base Directory
BASE_DIR = ROOT
FINAL_JSON_DIR = os.path.join(BASE_DIR, "output", "final")

if not os.path.exists(FINAL_JSON_DIR):
    print(f"❌ Error: The directory {FINAL_JSON_DIR} does not exist.")
    sys.exit(1)

# =========================
# 3. DYNAMIC FILE SELECTION
# =========================
def get_target_json():
    # Priority 1: Command line argument
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        target = os.path.join(FINAL_JSON_DIR, arg if arg.endswith('.json') else f"merged_{arg}.json")
        if os.path.exists(target): return target
        return None

    # Priority 2: Most recent file in output/final
    files = [os.path.join(FINAL_JSON_DIR, f) for f in os.listdir(FINAL_JSON_DIR) if f.endswith('.json')]
    if not files: return None
    return max(files, key=os.path.getmtime)

TODAYS_CHAT_FILE = get_target_json()

if not TODAYS_CHAT_FILE:
    print(f"⏩ No daily JSON file found. Skipping Task Tracker.")
    sys.exit(0)

# Extract Date for ID generation
file_name = os.path.basename(TODAYS_CHAT_FILE)
date_match = re.search(r'(\d{2}-\d{2}-\d{2})', file_name)
LOG_DATE = datetime.strptime(date_match.group(1), "%m-%d-%y").strftime("%Y-%m-%d") if date_match else datetime.now().strftime("%Y-%m-%d")

# =========================
# 4. LOAD DATA (Read JSON + Read DB)
# =========================
# A. Read today's chat
with open(TODAYS_CHAT_FILE, "r", encoding="utf-8") as f:
    todays_chat = json.load(f)

# B. Fetch current tasks from MySQL to prevent duplicates/provide context
master_tasks = []
print("🔄 Fetching current tasks from MySQL Database...")
try:
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT task_id, task_description, department_name, status, 
                   date_created, possible_assignees, completed_by, notes 
            FROM tasks
        """))
        for row in result:
            # Note: result mapping handles different SQLAlchemy versions
            master_tasks.append({
                "task_id": row[0],
                "task_description": row[1],
                "department": row[2],
                "status": row[3],
                "date_created": str(row[4]) if row[4] else None,
                "possible_assignees": [x.strip() for x in row[5].split(",")] if row[5] else [],
                "completed_by": row[6],
                "notes": row[7]
            })
except Exception as e:
    print(f"⚠️ Database fetch warning (starting fresh): {e}")
    master_tasks = []

# Build Org Structure Context
org_structure_str = ""
for dept, names in OFFICIAL_ORGANIZATION.items():
    org_structure_str += f"- {dept}: {', '.join(names)}\n"

print(f"📂 Processing Chat: {TODAYS_CHAT_FILE}")
print(f"📋 Current Master Tasks: {len(master_tasks)} existing items from DB.")

# =========================
# 5. THE AI PROMPT (Strict Version)
# =========================
prompt = f"""You are an automated Project Management Database. Your ONLY job is to maintain a JSON ledger of tasks.

### REFERENCE ORGANIZATION STRUCTURE:
{org_structure_str}

### DATA INPUTS
1. CURRENT LEDGER (Existing Tasks):
{json.dumps(master_tasks, indent=2)}

2. TODAY'S CHAT LOG (Date: {LOG_DATE}):
{json.dumps(todays_chat, indent=2)}

### STRICT RULES FOR MANAGING TASKS:
1. WHAT IS A VALID BUSINESS TASK: Extract ONLY work-related, technical, or project-centric items (software, hardware, bugs, company processes).
2. WHAT IS NOT A TASK: Completely ignore food, drinks, personal errands, traffic, or casual social chatter.
3. TASK CONSOLIDATION: Group related messages into ONE single task. Do NOT create duplicates for the same topic.
4. STATUS EVALUATION: Set "Completed" ONLY if no follow-up problems exist. Otherwise, remain "Pending".
5. UPDATING: If today's chat indicates an existing task is finished, update "notes" and set "status" to "Completed".
6. NEW TASKS: Generate "task_id" as "TSK-{LOG_DATE.replace('-', '')}-XXXX".
7. DEPARTMENT ASSIGNMENT: Use ONLY: ["Project Manager", "System Administration and Maintenance", "Artificial Intelligence", "Web Development", "Computer Engineering", "Accounting", "Miscellaneous"].

### OUTPUT FORMAT
Output ONLY a valid JSON array. No markdown, no conversational text.
[
  {{
    "task_id": "...",
    "task_description": "...",
    "department": "...",
    "status": "...",
    "date_created": "YYYY-MM-DD",
    "possible_assignees": ["Name"],
    "completed_by": null,
    "notes": "..."
  }}
]
"""

# =========================
# 6. LLM EXECUTION & DB SYNC
# =========================
print(f"🧠 Updating Master Ledger with {MODEL_NAME}...")

payload = {
    "model": MODEL_NAME,
    "prompt": prompt,
    "stream": False,
    "options": {"num_ctx": 32768, "temperature": 0.0}
}

try:
    response = requests.post(OLLAMA_API, json=payload, timeout=None)
    response.raise_for_status()
    raw_ai_response = response.json().get('response', '').strip()
    
    # Clean AI output
    raw_ai_response = re.sub(r'^```json\s*|```$', '', raw_ai_response, flags=re.MULTILINE)
    updated_ledger = json.loads(raw_ai_response.strip())

    print("💾 Syncing AI Output to MySQL database...")
    with engine.begin() as conn:
        for item in updated_ledger:
            assignees_str = ", ".join(item.get('possible_assignees', []))
            query = text("""
                INSERT INTO tasks 
                (task_id, task_description, department_name, status, date_created, possible_assignees, completed_by, notes)
                VALUES 
                (:tid, :desc, :dept, :stat, :date, :pos_as, :comp_by, :notes)
                ON DUPLICATE KEY UPDATE 
                status = VALUES(status), 
                notes = VALUES(notes)
            """)
            conn.execute(query, {
                "tid": item['task_id'], "desc": item['task_description'],
                "dept": item['department'], "stat": item['status'],
                "date": item['date_created'], "pos_as": assignees_str,
                "comp_by": item['completed_by'], "notes": item['notes']
            })
                
    print(f"✅ Master Ledger Updated! Currently tracking {len(updated_ledger)} tasks in MySQL.")

except Exception as e:
    print(f"❌ Error during AI processing or DB Sync: {e}")