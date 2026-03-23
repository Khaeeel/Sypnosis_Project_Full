import subprocess
import os
import sys
from datetime import datetime

# --- PATHING CONFIGURATION ---
# Get the directory where auto_run.py is
CURRENT_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Reverted back to your original working path!
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_SCRIPT_DIR, "../"))

# CRITICAL: Change the working directory to the project root
os.chdir(PROJECT_ROOT)


# --- SCRIPT PATHS (Relative to PROJECT_ROOT) ---
PADDLE_SCRIPT = "config/paddle_ocr_conf.py"
EASY_SCRIPT = "config/easy_ocr_conf.py"
MERGE_SCRIPT = "core/database/hybrid_merge.py" 
TRACKER_SCRIPT = "core/automation/task_tracker.py"
BUILD_DB_SCRIPT = "core/database/build_database.py"
QWEN_SCRIPT = "core/llm/qwen_run.py"
CLEANUP_SCRIPT = "core/automation/cleanup_manager.py"

LOG_FILE = os.path.join(PROJECT_ROOT, "logs/cron_log.txt")

def log(message):
    """Writes to the central logs/cron_log.txt folder."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {message}"
    print(formatted)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(formatted + "\n")

# --- CHANGED: Now fetches Today's date instead of Yesterday's ---
def get_todays_folder():
    today = datetime.now()
    return today.strftime("%m-%d-%y")

def run_command(script_name, target_folder=None):
    """Runs a python script and logs the result."""
    log(f"🚀 Starting {script_name}...")
    
    # We build the absolute path to ensure the shell finds it
    script_full_path = os.path.join(PROJECT_ROOT, script_name)
    
    cmd = [sys.executable, script_full_path]
    if target_folder:
        cmd.append(target_folder) 

    try:
        # Use PROJECT_ROOT as the cwd so child scripts find their folders
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)
        
        if result.returncode == 0:
            log(f"✅ {script_name} Success.")
            return True
        else:
            # logs the actual error from the sub-script
            log(f"⚠️ {script_name} Failed/Warning:\n{result.stderr}")
            return False
            
    except Exception as e:
        log(f"❌ Critical Error running {script_name}: {e}")
        return False

def main():
    # --- CHANGED: Target date is now Today ---
    target_date = get_todays_folder()
    
    log("========================================")
    log(f"   AUTOMATION PIPELINE STARTED")
    log(f"   Target Data: {target_date}")
    log("========================================")
    
    # Run the OCR Engines (Passing today's date)
    run_command(PADDLE_SCRIPT, target_date)
    run_command(EASY_SCRIPT, target_date)

    # Run Hybrid Merge
    if run_command(MERGE_SCRIPT, target_date):
        log("✅ Merge complete.")
        
        log("🔄 Updating Task Ledger...")
        if run_command(TRACKER_SCRIPT, target_date):
            
            log("🧠 Updating AI Vector Database...")
            run_command(BUILD_DB_SCRIPT, target_date)

            log("📝 Generating Forensic Report...")
            run_command(QWEN_SCRIPT, target_date)
            
            log("🧹 Running Storage Cleanup...")
            run_command(CLEANUP_SCRIPT)
        else:
            log("⛔ Task Tracker failed. Skipping downstream tasks.")
    else:
        log("⛔ Merge failed. Pipeline stopped.")

    log("=== PIPELINE FINISHED ===\n")

if __name__ == "__main__":
    main()