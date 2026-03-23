import os
import sys
import json
import chromadb
from chromadb.utils import embedding_functions
from datetime import datetime

# =========================
# CONFIGURATION
# =========================
BASE_DIR = os.getcwd()
FINAL_JSON_DIR = os.path.join(BASE_DIR, "output", "final") 
MASTER_JSON_PATH = os.path.join(BASE_DIR, "master_tasks.json") # NEW: Path to Task Ledger
DB_PATH = os.path.join(BASE_DIR, "chroma_storage") 

client = chromadb.PersistentClient(path=DB_PATH)

ollama_ef = embedding_functions.OllamaEmbeddingFunction(
    url="http://localhost:11434/api/embeddings",
    model_name="mxbai-embed-large", 
)

collection = client.get_or_create_collection(
    name="team_chat_history",
    embedding_function=ollama_ef
)

# =========================
# 1. PROCESS DAILY CHAT LOGS
# =========================
if len(sys.argv) > 1:
    target_date = sys.argv[1]
else:
    target_date = datetime.now().strftime("%m-%d-%y")

target_filename = f"merged_{target_date}.json"
filepath = os.path.join(FINAL_JSON_DIR, target_filename)

print(f"🔍 Looking for target chat file: {target_filename}...")

if not os.path.exists(filepath):
    print(f"⚠️ No chat file found for {target_date}. Skipping chat update.")
else:
    print(f"📄 Found target chat log! Processing into Vector Database...")
    
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            chat_data = json.load(f)
        except json.JSONDecodeError:
            print(f"❌ Error: Could not read {target_filename}.")
            chat_data = []
    
    chat_docs = []
    chat_metas = []
    chat_ids = []

    for idx, item in enumerate(chat_data):
        sender = item.get("sender", "Unknown")
        message = item.get("message", "").strip()
        timestamp = item.get("timestamp", "N/A")
        is_reply = str(item.get("is_reply", False)) 
        
        if not message:
            continue

        reply_to_ctx = ""
        if item.get("is_reply") and item.get("reply_to"):
            orig_sender = item["reply_to"].get("original_sender", "Unknown")
            orig_msg = item["reply_to"].get("original_message", "")
            reply_to_ctx = f" (Replying to {orig_sender}: {orig_msg})"

        full_text = f"[{timestamp}] {sender}: {message}{reply_to_ctx}"
        
        meta = {
            "type": "chat_message",
            "sender": sender,
            "date": target_date,
            "timestamp": timestamp
        }

        chat_docs.append(full_text)
        chat_metas.append(meta)
        
        unique_id = f"chat_{target_date}_{sender.replace(' ', '_')}_{idx}"
        chat_ids.append(unique_id)

    if chat_docs:
        BATCH_SIZE = 1000
        for i in range(0, len(chat_docs), BATCH_SIZE):
            collection.upsert(
                documents=chat_docs[i:i + BATCH_SIZE],
                metadatas=chat_metas[i:i + BATCH_SIZE],
                ids=chat_ids[i:i + BATCH_SIZE]
            )
        print(f"✅ Successfully embedded {len(chat_docs)} chat messages.")

# =========================
# 2. PROCESS MASTER TASK LEDGER
# =========================
print(f"\n🔍 Looking for Master Task Ledger...")

if not os.path.exists(MASTER_JSON_PATH):
    print(f"⚠️ No master_tasks.json found. Skipping task sync.")
else:
    print(f"📋 Found Task Ledger! Syncing updates to AI Memory...")
    
    with open(MASTER_JSON_PATH, "r", encoding="utf-8") as f:
        try:
            tasks_data = json.load(f)
        except json.JSONDecodeError:
            print(f"❌ Error: Could not read master_tasks.json.")
            tasks_data = []

    task_docs = []
    task_metas = []
    task_ids = []

    for task in tasks_data:
        t_id = task.get("task_id", "UNKNOWN_TASK")
        desc = task.get("task_description", "")
        dept = task.get("department", "Unassigned")
        status = task.get("status", "Pending")
        date_created = task.get("date_created", "Unknown Date")
        assignees = ", ".join(task.get("possible_assignees", []))
        completed_by = task.get("completed_by") or "None"
        notes = task.get("notes", "")

        # Create a highly structured string so the AI understands it's an official task
        full_text = (
            f"OFFICIAL TASK RECORD [{t_id}]: {desc}. "
            f"Department: {dept}. Status: {status}. "
            f"Date Created: {date_created}. Assigned to: {assignees}. "
            f"Completed by: {completed_by}. Notes: {notes}"
        )

        meta = {
            "type": "official_task",
            "task_id": t_id,
            "department": dept,
            "status": status,
            "date_created": date_created
        }

        task_docs.append(full_text)
        task_metas.append(meta)
        
        # CRITICAL: We use the exact task_id from your tracker!
        # This guarantees ChromaDB updates the existing task instead of duplicating it.
        task_ids.append(f"ledger_{t_id}")

    if task_docs:
        BATCH_SIZE = 1000
        for i in range(0, len(task_docs), BATCH_SIZE):
            collection.upsert(
                documents=task_docs[i:i + BATCH_SIZE],
                metadatas=task_metas[i:i + BATCH_SIZE],
                ids=task_ids[i:i + BATCH_SIZE]
            )
        print(f"✅ Successfully synced {len(task_docs)} official tasks.")

print("\n=========================================")
print(f"🎉 DATABASE UPDATE COMPLETE!")
print("=========================================")