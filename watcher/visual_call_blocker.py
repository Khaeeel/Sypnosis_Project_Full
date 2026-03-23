import pyautogui
import time
import subprocess
import sys

print("👁️ Visual Call Canceler: Spam-Guard Active...")

# --- EXACT COORDINATES FOR PC #2 ---
POPUP_REJECT_X, POPUP_REJECT_Y = 652, 502

# The center area between the normal call (869) and group call (857)
CHAT_BTN_X, CHAT_BTN_Y = 863, 564 

# The exact (X) button to kill the tab
TAB_CLOSE_X, TAB_CLOSE_Y = 1351, 139
SAFE_X, SAFE_Y = 700, 400

def check_for_red_popup():
    """Scans for the bright RED Reject button."""
    try:
        img = pyautogui.screenshot(region=(POPUP_REJECT_X-20, POPUP_REJECT_Y-20, 40, 40))
        for x in range(img.width):
            for y in range(img.height):
                r, g, b = img.getpixel((x, y))
                if r > 150 and g < 80 and b < 80:
                    return True
        return False
    except:
        return False

def check_for_chat_button():
    """Checks if the screen is black AND if the Chat button is visible."""
    try:
        # 🛡️ THE SPAM GUARD: Check the far right side of the screen (X: 1200, Y: 500)
        # On the black 'Call Ended' screen, this is pure pitch black (RGB near 15,15,15).
        # On a normal chat screen, this area has text, bubbles, or UI elements.
        r, g, b = pyautogui.pixel(1200, 500)
        
        # If the background is NOT dark black, we are in a normal chat. Abort!
        if r > 30 or g > 30 or b > 30:
            return False 

        # If it IS black, scan a wide 60x40 box to catch BOTH normal and group Chat buttons
        img = pyautogui.screenshot(region=(CHAT_BTN_X-30, CHAT_BTN_Y-20, 60, 40))
        for x in range(img.width):
            for y in range(img.height):
                r, g, b = img.getpixel((x, y))
                # Looking for the bright white/light gray of the Chat icon/text
                if r > 180 and g > 180 and b > 180 and abs(r-g) < 15:
                    return True
        return False
    except:
        return False

while True:
    try:
        # ==========================================
        # CONDITION 1: REGISTERED CONTACT (Red Popup)
        # ==========================================
        if check_for_red_popup():
            print(f"🚨 REGISTERED CALL DETECTED! Rejecting popup...")
            subprocess.run(["xdotool", "mousemove", str(POPUP_REJECT_X), str(POPUP_REJECT_Y), "click", "1"])
            
            time.sleep(1.5)
            
            print("🧹 Sniping the (X) to permanently destroy the tab...")
            subprocess.run([
                "xdotool", "mousemove", str(TAB_CLOSE_X), str(TAB_CLOSE_Y), 
                "click", "1", 
                "mousemove", str(SAFE_X), str(SAFE_Y)
            ])
            print("✅ Call destroyed!")
            time.sleep(4) 

        # ==========================================
        # CONDITION 2: UNKNOWN / GROUP CONTACT (Auto-Rejected Tab)
        # ==========================================
        elif check_for_chat_button():
            print(f"🚨 UNKNOWN/GROUP CALL DETECTED! Sniping the (X)...")
            
            time.sleep(0.5)
            
            # Bot SEES the Chat button, but CLICKS the (X) in the corner to kill the bug
            subprocess.run([
                "xdotool", "mousemove", str(TAB_CLOSE_X), str(TAB_CLOSE_Y), 
                "click", "1", 
                "mousemove", str(SAFE_X), str(SAFE_Y)
            ])
            print("✅ Ghost tab permanently destroyed!")
            time.sleep(4) 

    except KeyboardInterrupt:
        print("\nStopping...")
        sys.exit(0)
    except Exception as e:
        pass
        
    time.sleep(0.1)