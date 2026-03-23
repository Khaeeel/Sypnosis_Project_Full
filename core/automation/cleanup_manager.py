import os
import shutil
import time
from datetime import datetime

# =========================
# CONFIGURATION
# =========================
# 1. Accurately find the Root of your Project (SYPNOSIS_ENGINE_1)
CURRENT_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Moves up two levels from core/automation to hit the main project folder
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_SCRIPT_DIR, "../../"))

# 2. Folders containing daily sub-folders (like data/raw_screenshots/03-19-26)
FOLDER_TARGETS = [
    os.path.join(PROJECT_ROOT, "data", "raw_screenshots"),
]

# 3. Folders containing individual JSON files ONLY
# --- REMOVED HTML AND TXT FOLDERS ---
FILE_TARGETS = [
    os.path.join(PROJECT_ROOT, "output", "easyocr"),
    os.path.join(PROJECT_ROOT, "output", "paddle"),
    os.path.join(PROJECT_ROOT, "output", "final")
]

RETENTION_DAYS = 7

def log_cleanup(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def run_maintenance():
    # Calculate the time threshold (Current time minus 7 days)
    now = time.time()
    cutoff_sec = now - (RETENTION_DAYS * 86400)
    
    log_cleanup(f"🧹 Starting Storage Maintenance (Policy: {RETENTION_DAYS} Days)")

    # --- PART 1: DELETE OLD FOLDERS (Screenshots) ---
    for base_path in FOLDER_TARGETS:
        if not os.path.exists(base_path): 
            log_cleanup(f"⚠️ Path not found, skipping: {base_path}")
            continue
        
        for folder_name in os.listdir(base_path):
            folder_path = os.path.join(base_path, folder_name)
            
            if os.path.isdir(folder_path):
                # Check if folder creation/modification is older than 7 days
                if os.path.getmtime(folder_path) < cutoff_sec:
                    try:
                        shutil.rmtree(folder_path)
                        log_cleanup(f"🗑️ Removed Old Folder: {folder_name}")
                    except Exception as e:
                        log_cleanup(f"❌ Error removing {folder_name}: {e}")

    # --- PART 2: DELETE OLD FILES (JSONs) ---
    for base_path in FILE_TARGETS:
        if not os.path.exists(base_path): 
            log_cleanup(f"⚠️ Path not found, skipping: {base_path}")
            continue

        for file_name in os.listdir(base_path):
            file_path = os.path.join(base_path, file_name)
            
            if os.path.isfile(file_path):
                # Don't delete your master ledger or any hidden system files!
                if "master_tasks" in file_name or file_name.startswith("."): 
                    continue
                
                if os.path.getmtime(file_path) < cutoff_sec:
                    try:
                        os.remove(file_path)
                        log_cleanup(f"🗑️ Removed Old File: {file_name}")
                    except Exception as e:
                        log_cleanup(f"❌ Error removing {file_name}: {e}")

    log_cleanup("✅ Maintenance Complete. (Summaries preserved)")

if __name__ == "__main__":
    run_maintenance()