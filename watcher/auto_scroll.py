import subprocess
import pyautogui
import time

# --- CONFIG ---
# This looks for the name you saw in wmctrl
TARGET_NAME = "Viber"  
SCROLL_AMOUNT = -5
SCROLL_INTERVAL = 5    

print(f"🚀 Scroller active. Targeting windows containing: '{TARGET_NAME}'")

try:
    while True:
        try:
            # Get the name of the window you are currently clicked on
            active_name = subprocess.check_output(
                ["xdotool", "getactivewindow", "getwindowname"]
            ).decode("utf-8").strip()
            
            # Logic: If the target name is inside the active window name
            if TARGET_NAME.lower() in active_name.lower():
                pyautogui.scroll(SCROLL_AMOUNT)
                print(f"✅ Active: [{active_name}] - SCROLLING", end="\r")
            else:
                print(f"⏸️ Active: [{active_name[:20]}] - PAUSED   ", end="\r")
                
        except Exception:
            # This happens if you are clicking between windows or on the desktop
            pass

        time.sleep(SCROLL_INTERVAL)

except KeyboardInterrupt:
    print("\n👋 Stopped by user.")