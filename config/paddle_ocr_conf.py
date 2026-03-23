import os
import sys

# Tell Python to explicitly look in the folder where this script lives
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# MUST set these BEFORE importing paddle
os.environ['PADDLE_DISABLE_ALLOCATOR_STRATEGY'] = '1'
os.environ['FLAGS_use_mkldnn'] = '0'
os.environ['PADDLE_MKLDNN_ENABLED'] = '0'
os.environ['CPU_NUM'] = '4'

import json
import cv2
import re
import numpy as np
from datetime import datetime
from difflib import SequenceMatcher, get_close_matches
import torch

from paddleocr import PaddleOCR

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT)
sys.path.append(os.path.join(ROOT, "core/ocr"))

# --- IMPORT SHARED UTILS (Leaving the brain untouched) ---
from ocr_utils import resolve_sender, is_timestamp, clean_message_text, is_noise, detect_dynamic_header


# ----------------------------
# CONFIGURATION
# ----------------------------
INPUT_FOLDER = os.path.join(ROOT, "data", "raw_screenshots") 
BASE_OUTPUT_FOLDER = os.path.join(ROOT, "output")

CONFIDENCE_THRESHOLD = 0.2
GAP_THRESHOLD = 150 

PADDLE_OUT_DIR = os.path.join(BASE_OUTPUT_FOLDER, "paddle")
os.makedirs(PADDLE_OUT_DIR, exist_ok=True)

# ---- ROCm/GPU Detection ----
rocm_available = False
if hasattr(torch.version, 'hip') and torch.version.hip is not None:
    rocm_available = True
if not rocm_available and os.environ.get("HIP_VISIBLE_DEVICES"):
    rocm_available = True

cuda_available = torch.cuda.is_available() or rocm_available

# Note: PaddleOCR is not fully compatible with AMD ROCm yet, so we use CPU mode
print(f"--- Initializing PaddleOCR (CPU Mode - ROCm incompatible) ---")
print(f"    Note: EasyOCR uses GPU, but PaddleOCR uses CPU for compatibility")
print(f"    CUDA Available: {torch.cuda.is_available()}")
print(f"    ROCm Available: {rocm_available}")

if cuda_available:
    try:
        device_name = torch.cuda.get_device_name(0)
        mem_total = torch.cuda.mem_get_info()[1] / 1e9
        print(f"    GPU Device (for EasyOCR): {device_name}")
        print(f"    GPU Memory: {mem_total:.2f}GB total")
    except Exception as e:
        print(f"    (Could not get GPU info: {e})")

ocr = PaddleOCR(
    lang='en', 
    use_angle_cls=True,
    use_gpu=False,
    show_log=False
)

# ----------------------------
# UTILS (Moved to ocr_utils.py)
# ----------------------------
def get_ocr_results(img):
    try:
        result = ocr.ocr(img, cls=True)
        if result and result[0]: return result
    except Exception as e:
        print(f"⚠️ OCR Error on ocr: {e}")
        return []
    
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        enhanced = cv2.fastNlMeansDenoising(enhanced, None, 10, 7, 21)
        
        result = ocr.ocr(enhanced, cls=True)
        return result if result else []
    except Exception as e:
        print(f"⚠️ OCR Error on enhanced ocr: {e}")
        return []

# ----------------------------
# MAIN LOGIC
# ----------------------------
def extract_chat():
    target_date = None
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
        print(f"🎯 Target Date Provided by Controller: {target_date}")
    else:
        # --- CHANGED: Default fallback is now TODAY ---
        today = datetime.now()
        target_date = today.strftime("%m-%d-%y")
        print(f"⚠️ No date arg provided. Defaulting to TODAY: {target_date}")

    input_folder = os.path.join(INPUT_FOLDER, target_date)
    
    if not os.path.exists(input_folder):
        print(f"❌ Folder '{input_folder}' not found.")
        if os.path.exists(INPUT_FOLDER):
             folders = sorted([f for f in os.listdir(INPUT_FOLDER) if os.path.isdir(os.path.join(INPUT_FOLDER, f))])
             if folders:
                 target_date = folders[-1]
                 input_folder = os.path.join(INPUT_FOLDER, target_date)
                 print(f"🔄 Fallback: Switching to latest available folder -> {target_date}")
             else:
                 print("❌ No folders found in raw_screenshots.")
                 return
        else:
            return

    image_files = sorted([f for f in os.listdir(input_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    
    if not image_files:
        print(f"❌ No images found in {input_folder}.")
        return

    output_filename = f"paddle_{target_date}.json"
    output_path = os.path.join(PADDLE_OUT_DIR, output_filename)
    
    print(f"📂 Processing Batch: {target_date} -> {output_path}")
    final_data = []
    current_sender = None 
    
    for img_file in image_files:
        print(f"Processing {img_file}...")
        img = cv2.imread(os.path.join(input_folder, img_file))
        if img is None: continue

        result = get_ocr_results(img)
        if not result or not result[0]: continue

        valid_lines = []
        if isinstance(result[0], list):
            for line in result[0]:
                if isinstance(line, list) and len(line) >= 2:
                    content = line[1]
                    if isinstance(content, (list, tuple)) and len(content) >= 2:
                         if content[1] > CONFIDENCE_THRESHOLD:
                             valid_lines.append(line)
        
        lines = sorted(valid_lines, key=lambda x: x[0][0][1])
        
        header_cut_y = detect_dynamic_header(lines)
        last_y_bottom = 0 
        
        i = 0
        while i < len(lines):
            line_data = lines[i]
            text = line_data[1][0].strip()
            confidence = line_data[1][1] 
            y_top = line_data[0][0][1]
            y_bottom = line_data[0][2][1]
            x_left = line_data[0][0][0]

            if y_bottom <= header_cut_y: i += 1; continue
            if is_noise(text): i += 1; continue

            reference_y = last_y_bottom if last_y_bottom > 0 else header_cut_y
            if current_sender and reference_y > 0 and (y_top - reference_y) > GAP_THRESHOLD:
                final_data.append({"sender": current_sender, "message": "[PHOTO MESSAGE]", "timestamp": None, "is_reply": False, "reply_to": None, "confidence_score": 1.0})

            if "photo message" in text.lower():
                final_data.append({"sender": current_sender if current_sender else "Unknown", "message": "[PHOTO MESSAGE]", "timestamp": None, "is_reply": False, "reply_to": None, "confidence_score": float(confidence)})
                last_y_bottom = y_bottom; i += 1; continue

            cleaned = clean_message_text(text)
            if cleaned == "" and text != "": i += 1; continue
            last_y_bottom = y_bottom
            name1 = resolve_sender(cleaned)
            name2 = resolve_sender(clean_message_text(lines[i+1][1][0].strip())) if i + 1 < len(lines) else None

            if name1 and name2 and name1 != name2:
                current_sender = name1
                target_sender = name2
                sender_x = x_left
                target_x = lines[i+1][0][0][0]
                indent_threshold = (sender_x + target_x) / 2
                quote_parts = []; reply_parts = []; scores = [confidence, lines[i+1][1][1]]
                k = i + 2
                while k < len(lines):
                    next_line = lines[k]
                    next_text = clean_message_text(next_line[1][0].strip())
                    next_x = next_line[0][0][0]
                    next_y_top = next_line[0][0][1]
                    if next_y_top <= header_cut_y or is_noise(next_line[1][0]): k+=1; continue
                    if is_timestamp(next_text): 
                        if next_x > indent_threshold: k += 1; continue 
                        else: k += 1; break 
                    if resolve_sender(next_text): break
                    scores.append(next_line[1][1])
                    if next_x > indent_threshold: quote_parts.append(next_text)
                    else: reply_parts.append(next_text)
                    last_y_bottom = next_line[0][2][1]; k += 1
                
                full_reply = " ".join(reply_parts)
                if not full_reply and "[PHOTO MESSAGE]" in str(final_data[-1]): full_reply = "[PHOTO MESSAGE]"
                final_data.append({
                    "sender": current_sender, "message": full_reply, "timestamp": None, "is_reply": True,
                    "reply_to": {"original_sender": target_sender, "original_message": " ".join(quote_parts) if quote_parts else "[MEDIA]"},
                    "confidence_score": round(sum(scores) / len(scores) if scores else 0.0, 4)
                })
                i = k; continue
            elif name1:
                current_sender = name1; i += 1; continue
            elif is_timestamp(cleaned):
                if final_data: final_data[-1]["timestamp"] = cleaned
                i += 1; continue
            else:
                if current_sender and cleaned:
                    last_msg = final_data[-1] if final_data else None
                    if last_msg and last_msg["sender"] == current_sender and not is_timestamp(last_msg.get("timestamp", "")):
                        if last_msg["message"] == "[PHOTO MESSAGE]":
                             final_data.append({"sender": current_sender, "message": cleaned, "timestamp": None, "is_reply": False, "reply_to": None, "confidence_score": float(confidence)})
                        else:
                            last_msg["message"] += f" {cleaned}"
                            last_msg["confidence_score"] = round((last_msg.get("confidence_score", 0.0) + confidence) / 2, 4)
                    else:
                        final_data.append({"sender": current_sender, "message": cleaned, "timestamp": None, "is_reply": False, "reply_to": None, "confidence_score": float(confidence)})
                i += 1

    cleaned_data = [d for d in final_data if d['message'].strip() != "" and d['message'] != "Pinned on"]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cleaned_data, f, indent=2, ensure_ascii=False)
    print(f"✅ Extraction complete. Saved to {output_path}")

if __name__ == "__main__":
    extract_chat()