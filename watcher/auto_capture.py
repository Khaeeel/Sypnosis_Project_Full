import pyautogui
import psutil
from PIL import Image
import imagehash
import time
import os
import sys
import subprocess
import numpy as np
from datetime import datetime

# ==========================================
# PATH SETUP
# ==========================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

BASE_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data/raw_screenshots")
os.makedirs(BASE_OUTPUT_DIR, exist_ok=True)

print(f"📂 Saving screenshots to: {BASE_OUTPUT_DIR}")

# ==========================================
# CONFIGURATION
# ==========================================
TARGET_WINDOW_NAME = "Rakuten Viber" 
ROI = (383, 183, 936, 531)  

SCREEN_CAPTURE_INTERVAL = 0.5
STABILIZATION_DELAY = 2
DEBOUNCE_SECONDS = 2

HAMMING_THRESHOLD = 5
PIXEL_CHANGE_THRESHOLD = 5

# REMOVED: CAPTURE_START_TIME is no longer needed

# ==========================================
# HELPERS
# ==========================================
def get_today_folder():
    today = datetime.now().strftime("%m-%d-%y")
    folder = os.path.join(BASE_OUTPUT_DIR, today)
    os.makedirs(folder, exist_ok=True)
    return folder

def log_event(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_path = os.path.join(BASE_OUTPUT_DIR, "capture_log.txt")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"[{timestamp}] {message}")

def get_active_window_title_linux():
    """Returns the title of the currently active window on Linux."""
    try:
        window_id = subprocess.check_output(
            ["xdotool", "getactivewindow"], 
            stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()
        
        window_name = subprocess.check_output(
            ["xdotool", "getwindowname", window_id], 
            stderr=subprocess.DEVNULL
        ).decode("utf-8").strip()
        
        return window_name
    except Exception:
        return None
    
# ==========================================
# INIT
# ==========================================
current_day = datetime.now().date()
output_dir = get_today_folder()

screenshots_today = 0
last_img = None
last_hash = None
last_capture_time = 0
target_active_last_state = None  

log_event(f"--- WATCHING FOR WINDOW: '{TARGET_WINDOW_NAME}' (24/7 MODE) ---")

# ==========================================
# MAIN LOOP
# ==========================================
while True:
    now = datetime.now()

    # --- New Day Reset ---
    if now.date() != current_day:
        log_event(f"End of Day Report: Captured {screenshots_today} images.")
        current_day = now.date()
        output_dir = get_today_folder()
        screenshots_today = 0
        last_img = None
        last_hash = None
        log_event(f"New Day Detected. Switched folder to {output_dir}")

    try:
        # --- 1. DETECT ACTIVE WINDOW ---
        active_title = get_active_window_title_linux()
        is_target_active = active_title and TARGET_WINDOW_NAME.lower() in active_title.lower()

        # --- 2. LOG CONTEXT SWITCHING ---
        if is_target_active != target_active_last_state:
            if is_target_active:
                log_event(f"✅ Target Active: {active_title}")
            else:
                log_event(f"⏸️ Target Lost. Current: {active_title}")
            target_active_last_state = is_target_active

        # --- 3. SKIP IF NOT TARGET ---
        # The script now runs 24/7, but only does work if Viber is on top
        if not is_target_active:
            time.sleep(1)
            continue

        # --- 4. CAPTURE LOGIC ---
        current_img = pyautogui.screenshot(region=ROI)
        current_hash = imagehash.phash(current_img)

        if last_img is None:
            last_img = current_img
            last_hash = current_hash
            time.sleep(SCREEN_CAPTURE_INTERVAL)
            continue

        if time.time() - last_capture_time < DEBOUNCE_SECONDS:
            time.sleep(SCREEN_CAPTURE_INTERVAL)
            continue

        hamming_distance = last_hash - current_hash
        
        current_arr = np.array(current_img)
        last_arr = np.array(last_img)
        diff_pixels = np.sum(np.abs(current_arr - last_arr) > 30)
        percent_change = (diff_pixels / current_arr.size) * 100

        if hamming_distance > HAMMING_THRESHOLD or percent_change > PIXEL_CHANGE_THRESHOLD:
            time.sleep(STABILIZATION_DELAY)

            timestamp = datetime.now().strftime("%H-%M-%S")
            filename = f"cap_{timestamp}.png"
            output_path = os.path.join(output_dir, filename)

            img_to_save = pyautogui.screenshot(region=ROI)
            img_to_save.save(output_path)

            screenshots_today += 1
            log_event(f"📸 Captured: {filename} (Diff: {percent_change:.2f}%)")

            last_img = img_to_save
            last_hash = imagehash.phash(img_to_save)
            last_capture_time = time.time()

        time.sleep(SCREEN_CAPTURE_INTERVAL)

    except KeyboardInterrupt:
        print("\nStopping...")
        sys.exit(0)
    except Exception as e:
        log_event(f"Error: {e}")
        time.sleep(5)