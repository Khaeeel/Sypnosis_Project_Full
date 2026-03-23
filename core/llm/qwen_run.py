import os
import sys
import json
import requests
import markdown
import re
import chromadb
from chromadb.utils import embedding_functions
from datetime import datetime
from sqlalchemy import create_engine, text

# =========================================================
# 1. PATHING FIX & IMPORTS
# =========================================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../"))

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
    sys.path.insert(0, os.path.join(ROOT, "core", "ocr"))

try:
    from ocr_utils import OFFICIAL_ORGANIZATION
except ImportError:
    OFFICIAL_ORGANIZATION = {"Miscellaneous": ["Unknown"]}

# =========================
# 2. EMBEDDED PROMPT (No more dictionary_prompt.py!)
# =========================
FORENSIC_PROMPT_TPL = """
You are an Advanced Forensic Linguistic Analyzer. 
Analyze the provided chat log for the date: {LOG_DATE}

### INPUT DATA:
- Participants: {participant_count} ({participant_list_str})
- Org Structure: {org_structure_str}
- Dialect Context: {dialect_context}
- Raw Messages: {conversation_json_str}

### INSTRUCTIONS:
1. Summarize the key technical discussions.
2. Identify sentiment and potential blockers.
3. **UNRECOGNIZED LINGUISTIC DATA**: 
   - List any Tagalog/English slang or dialect terms not found in the provided context.
   - Format: **Unknown/Dialect Terms:** [term1, term2]
   - Format: **Contextual Gap:** Explain why these were hard to analyze.

### OUTPUT FORMAT:
Return a professional forensic report in Markdown.
"""

# =========================
# 3. CONFIGURATION & DATABASE
# =========================
OLLAMA_API = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen3.5:9b" 
BASE_DIR = ROOT
DB_PATH = os.path.join(BASE_DIR, "chroma_storage")

# MySQL Connection (Matches your task_tracker.py)
DB_URL = "mysql+mysqlconnector://root:comfac%40123@127.0.0.1:3306/sypnosis"
engine = create_engine(DB_URL)

# =========================
# 4. CHROMA / RAG SETUP
# =========================
client = chromadb.PersistentClient(path=DB_PATH)
ollama_ef = embedding_functions.OllamaEmbeddingFunction(
    url="http://localhost:11434/api/embeddings",
    model_name="bge-m3"
)
dict_collection = client.get_collection(name="filipino_dialect_lookup", embedding_function=ollama_ef)

def get_dialect_context(chat_data, top_k=12): 
    all_text = " ".join([item.get("message", "") for item in chat_data])
    try:
        results = dict_collection.query(
            query_texts=[all_text], 
            n_results=top_k,
            where={"type": "dictionary_entry"} 
        )
        if results['documents'] and len(results['documents'][0]) > 0:
            unique_entries = list(set(results['documents'][0]))
            return "\n".join([f"- {entry}" for entry in unique_entries])
        return "No matching dialect terms found in dictionary for this specific vocabulary."
    except Exception as e:
        return f"Note: Dictionary RAG lookup skipped. ({e})"

# =========================
# 5. PATH SETUP & DATA PREP
# =========================
FINAL_JSON_DIR = os.path.join(BASE_DIR, "output", "final")
OUTPUT_DIR = os.path.join(BASE_DIR, "summary")
HTML_DIR = os.path.join(OUTPUT_DIR, "html")
os.makedirs(HTML_DIR, exist_ok=True)

def get_target_json():
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        target = os.path.join(FINAL_JSON_DIR, arg if arg.endswith('.json') else f"merged_{arg}.json")
        if os.path.exists(target): return target
    files = [os.path.join(FINAL_JSON_DIR, f) for f in os.listdir(FINAL_JSON_DIR) if f.endswith('.json')]
    return max(files, key=os.path.getmtime) if files else None

DATA_FILE = get_target_json()
if not DATA_FILE:
    print(f"❌ Error: No JSON files found in {FINAL_JSON_DIR}"); sys.exit(1)

# Extract Date
file_name = os.path.basename(DATA_FILE)
date_match = re.search(r'(\d{2}-\d{2}-\d{2})', file_name)
LOG_DATE = datetime.strptime(date_match.group(1), "%m-%d-%y").strftime("%Y-%m-%d") if date_match else datetime.now().strftime("%Y-%m-%d")

# =========================
# 6. FETCH TASKS FROM MYSQL
# =========================
master_tasks_html = ""
print("🔄 Fetching pending/recent tasks from MySQL for the HTML report...")
try:
    with engine.connect() as conn:
        # Fetch tasks that were created today OR are still pending
        query = text("""
            SELECT task_description, department_name, status, date_created 
            FROM tasks 
            WHERE date_created = :log_date OR status = 'Pending'
        """)
        result = conn.execute(query, {"log_date": LOG_DATE})
        
        rows = []
        for row in result:
            desc = row[0]
            dept = row[1]
            stat = row[2]
            date_c = str(row[3]) if row[3] else ""
            rows.append(f"<tr><td>{desc}</td><td>{dept}</td><td><strong>{stat}</strong></td><td>{date_c}</td></tr>")
            
        if rows:
            master_tasks_html = f"<hr><h2>Action Items & Tasks (Ledger)</h2><table><thead><tr><th>Task</th><th>Dept</th><th>Status</th><th>Created</th></tr></thead><tbody>{''.join(rows)}</tbody></table><br>"
except Exception as e:
    print(f"⚠️ Could not fetch tasks from DB for HTML report: {e}")

# Load the raw chat log
with open(DATA_FILE, "r", encoding="utf-8") as f:
    raw_data = json.load(f)

# =========================
# 7. CHAT PREPARATION
# =========================
chat_json_payload = []
seen_sigs = set()
detected_names = set()

for item in raw_data:
    sender, msg = item.get("sender", "Unknown").strip(), item.get("message", "").strip()
    if not msg or len(msg) < 2: continue
    sig = f"{sender}:{msg[:20]}"
    if sig in seen_sigs: continue
    seen_sigs.add(sig); detected_names.add(sender)
    chat_json_payload.append(item)

print(f"🔍 Searching Dialect Dictionary for context...")
dialect_context = get_dialect_context(chat_json_payload)

org_structure_str = ""
for dept, names in OFFICIAL_ORGANIZATION.items():
    org_structure_str += f"- {dept}: {', '.join(names)}\n"

# =========================
# 8. AI ANALYSIS
# =========================
prompt = FORENSIC_PROMPT_TPL.format(
    participant_count=len(detected_names),
    participant_list_str=", ".join(sorted(detected_names)),
    LOG_DATE=LOG_DATE,
    org_structure_str=org_structure_str,
    dialect_context=dialect_context,
    conversation_json_str=json.dumps(chat_json_payload, indent=2)
)

print(f"🧠 Analyzing: {file_name} with {MODEL_NAME}")
payload = {"model": MODEL_NAME, "prompt": prompt, "stream": False, "options": {"num_ctx": 40000, "temperature": 0.0}}

try:
    response = requests.post(OLLAMA_API, json=payload, timeout=1200)
    raw_ai_response = response.json()['response']
except Exception as e:
    print(f"❌ API Error: {e}"); sys.exit(1)
    
# =========================
# 9. LINGUISTIC DATA EXTRACTION
# =========================
LINGUISTIC_DIR = os.path.join(BASE_DIR, "output", "linguistic_data")
os.makedirs(LINGUISTIC_DIR, exist_ok=True)

def save_unrecognized_data(ai_text, source_file):
    terms_match = re.search(r"\*\*Unknown/Dialect Terms:\*\*\s*\[?(.*?)\]?\n", ai_text)
    gap_match = re.search(r"\*\*Contextual Gap:\*\*\s*(.*)", ai_text)
    
    raw_terms_str = terms_match.group(1).strip() if terms_match else ""
    gap = gap_match.group(1).strip() if gap_match else "None"

    if raw_terms_str and raw_terms_str.lower() != "none":
        original_phrases = [t.strip().strip('"').strip("'").strip(']') for t in raw_terms_str.split(",")]
        all_individual_tokens = []
        for phrase in original_phrases:
            tokens = re.findall(r'\b\w+\b', phrase.lower())
            all_individual_tokens.extend(tokens)
        
        unique_tokens = list(dict.fromkeys(all_individual_tokens))

        entry = {
            "source_log": source_file,
            "detected_at": datetime.now().isoformat(),
            "context_phrases": original_phrases,
            "atomic_word_index": unique_tokens, 
            "reasoning": gap
        }
        
        output_json_path = os.path.join(LINGUISTIC_DIR, f"unrecognized_{os.path.basename(source_file)}")
        with open(output_json_path, "w", encoding="utf-8") as jf:
            json.dump(entry, jf, indent=4)
        print(f"📥 Atomic word-level JSON saved to: {output_json_path}")

save_unrecognized_data(raw_ai_response, DATA_FILE)

# =========================
# 10. HTML CONSTRUCTION
# =========================
markdown_body = markdown.markdown(raw_ai_response, extensions=['tables'])
findings_header = "<h2>FORENSIC FINDINGS</h2>"

if findings_header in markdown_body:
    parts = markdown_body.split(findings_header)
    final_content = parts[0] + master_tasks_html + findings_header + parts[1]
else:
    final_content = markdown_body + master_tasks_html

styled_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; background: #f0f2f5; padding: 40px; color: #1a1a1a; }}
        .report-container {{ max-width: 1000px; margin: auto; background: #fff; padding: 50px; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
        .meta {{ font-family: monospace; font-size: 11px; color: #7f8c8d; text-align: right; border-bottom: 2px solid #3498db; margin-bottom: 30px; }}
        h2 {{ color: #2c3e50; background: #ecf0f1; padding: 10px; border-left: 5px solid #3498db; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th {{ background: #34495e; color: white; padding: 10px; text-align: left; }}
        td {{ padding: 10px; border: 1px solid #ddd; }}
    </style>
</head>
<body>
    <div class="report-container">
        <div class="meta">REF: {datetime.now().strftime("%Y%m%d")}-FRNSC | SOURCE: {file_name}</div>
        {final_content}
    </div>
</body>
</html>
"""

output_path = os.path.join(HTML_DIR, file_name.replace(".json", ".html"))
with open(output_path, "w", encoding="utf-8") as f:
    f.write(styled_html)

print(f"✅ Report Complete: {output_path}")