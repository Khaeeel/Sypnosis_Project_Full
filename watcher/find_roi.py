import pyautogui
import time

def wait_for_click(button='left'):
    print(f"Waiting for {button}-click...")
    while True:
        if pyautogui.mouseDown(button=button):
            # Wait for release
            while pyautogui.mouseDown(button=button):
                time.sleep(0.01)
            return pyautogui.position()
        time.sleep(0.01)

print("Move your mouse to the TOP-LEFT corner of the Viber chat area and click...")
top_left = wait_for_click()
print("Top-left recorded:", top_left)

print("Move your mouse to the BOTTOM-RIGHT corner of the Viber chat area and click...")
bottom_right = wait_for_click()
print("Bottom-right recorded:", bottom_right)

# Calculate ROI
x1, y1 = top_left
x2, y2 = bottom_right
roi = (x1, y1, x2 - x1, y2 - y1)
print("ROI coordinates (x, y, width, height):", roi)
