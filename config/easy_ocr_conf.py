import os
import sys

# --- MANDATORY ROCm / 7900 XT FIXES ---
os.environ["HIP_VISIBLE_DEVICES"] = "0"
os.environ["HSA_OVERRIDE_GFX_VERSION"] = "11.0.0"
os.environ["PYTORCH_ROCM_ARCH"] = "gfx1100"
os.environ["ROC_ENABLE_PRE_VEGA"] = "0" 
os.environ["MIOPEN_DEBUG_DISABLE_CONV_ALGO_SEARCH"] = "1"

import json
import cv2
import numpy as np
from datetime import datetime
import easyocr
import torch 

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT)
sys.path.append(os.path.join(ROOT, "core/ocr"))

# --- IMPORT SHARED UTILS ---
from ocr_utils import resolve_sender, is_timestamp, clean_message_text, is_noise, detect_dynamic_header

if torch.cuda.is_available():
    print("🔥 Pre-warming ROCm kernels...")
    _ = torch.randn(1024, 1024, device="cuda") @ torch.randn(1024, 1024, device="cuda")
    torch.cuda.synchronize()

# ----------------------------
# CONFIGURATION
# ----------------------------
INPUT_FOLDER = os.path.join(ROOT, "data", "raw_screenshots") 
BASE_OUTPUT_FOLDER = os.path.join(ROOT, "output")

CONFIDENCE_THRESHOLD = 0.2
GAP_THRESHOLD = 150 

EASY_OUT_DIR = os.path.join(BASE_OUTPUT_FOLDER, "easyocr")
os.makedirs(EASY_OUT_DIR, exist_ok=True)

reader = None
def initialize_reader(use_gpu=True):
    global reader
    try:
        cuda_available = torch.cuda.is_available() or bool(os.environ.get("HIP_VISIBLE_DEVICES"))
        mode = "GPU" if (use_gpu and cuda_available) else "CPU"
        print(f"--- Initializing EasyOCR ({mode} Mode) ---")
        reader = easyocr.Reader(['en'], gpu=(use_gpu and cuda_available))
        return True
    except Exception as e:
        if use_gpu: return initialize_reader(use_gpu=False)
        return False

if not initialize_reader(use_gpu=True): sys.exit(1)

if reader and torch.cuda.is_available():
    try: reader.detector.to("cuda")
    except: pass
    try:
        if hasattr(reader.recognizer, 'model'): reader.recognizer.model.to("cuda")
        elif hasattr(reader.recognizer, 'module'): reader.recognizer.module.to("cuda")
    except: pass

def get_ocr_results(img):
    global reader
    try:
        if torch.cuda.is_available(): torch.cuda.empty_cache()
        with torch.no_grad(): result = reader.readtext(img)
        if not result:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            enhanced = cv2.fastNlMeansDenoising(cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray), None, 10, 7, 21)
            with torch.no_grad(): result = reader.readtext(enhanced)
        return [[item[0], [item[1], item[2]]] for item in result]
    except Exception as e:
        return []

def extract_chat():
    # --- CHANGED: Now defaults to TODAY instead of Yesterday ---
    target_date = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%m-%d-%y")
    
    input_folder = os.path.join(INPUT_FOLDER, target_date)
    output_path = os.path.join(EASY_OUT_DIR, f"easyocr_{target_date}.json")
    
    if not os.path.exists(input_folder): return
    image_files = sorted([f for f in os.listdir(input_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    if not image_files: return
        
    print(f"📂 Processing images from {input_folder} -> {output_path}")
    final_data = []; current_sender = None; current_sender_side = None; participants = set()
    
    for img_file in image_files:
        print(f"Processing {img_file}...")
        img = cv2.imread(os.path.join(input_folder, img_file))
        if img is None: continue
        
        lines_raw = get_ocr_results(img)
        if not lines_raw: continue
        lines = sorted([line for line in lines_raw if line[1][1] > CONFIDENCE_THRESHOLD], key=lambda x: min([p[1] for p in x[0]]))
        
        header_cut_y = detect_dynamic_header(lines)
        last_y_bottom = 0 
        
        i = 0
        while i < len(lines):
            line_data = lines[i]
            bbox = line_data[0]; text = line_data[1][0].strip(); confidence = line_data[1][1]
            y_top = min([p[1] for p in bbox]); y_bottom = max([p[1] for p in bbox]); x_left = min([p[0] for p in bbox])
            
            # Apply dynamic header cut
            if y_bottom <= header_cut_y: i += 1; continue
            
            bubble_center = x_left + (max([p[0] for p in bbox]) - x_left) / 2
            bubble_side = "left" if bubble_center < img.shape[1] / 2 else "right"

            if is_noise(text): i += 1; continue

            reference_y = last_y_bottom if last_y_bottom > 0 else 0
            if current_sender and reference_y > 0 and (y_top - reference_y) > GAP_THRESHOLD:
                final_data.append({"sender": current_sender, "message": "[PHOTO MESSAGE]", "timestamp": None, "is_reply": False, "reply_to": None, "confidence_score": 1.0})

            if "photo message" in text.lower():
                final_data.append({"sender": current_sender if current_sender else "Unknown", "message": "[PHOTO MESSAGE]", "timestamp": None, "is_reply": False, "reply_to": None, "confidence_score": float(confidence)})
                last_y_bottom = y_bottom; i += 1; continue

            cleaned = clean_message_text(text)
            if cleaned == "" and len(text.strip()) <= 5: cleaned = text.strip()
            if cleaned == "" and text != "": i += 1; continue
            last_y_bottom = y_bottom
            name1 = resolve_sender(cleaned)
            name2 = resolve_sender(clean_message_text(lines[i + 1][1][0].strip())) if i + 1 < len(lines) else None

            if name1 and name2 and name1 != name2:
                current_sender = name1; target_sender = name2
                indent_threshold = (x_left + min([p[0] for p in lines[i + 1][0]])) / 2
                quote_parts = []; reply_parts = []; scores = [confidence, lines[i + 1][1][1]]
                k = i + 2
                while k < len(lines):
                    next_line = lines[k]
                    next_text = clean_message_text(next_line[1][0].strip())
                    next_x = min([p[0] for p in next_line[0]])
                    if max([p[1] for p in next_line[0]]) <= header_cut_y or is_noise(next_line[1][0]): k += 1; continue
                    if is_timestamp(next_text): 
                        if next_x > indent_threshold: k += 1; continue 
                        else: k += 1; break 
                    if resolve_sender(next_text): break
                    scores.append(next_line[1][1])
                    if next_x > indent_threshold: quote_parts.append(next_text)
                    else: reply_parts.append(next_text)
                    last_y_bottom = max([p[1] for p in next_line[0]]); k += 1
                
                full_reply = " ".join(reply_parts)
                if not full_reply and "[PHOTO MESSAGE]" in str(final_data[-1] if final_data else ""): full_reply = "[PHOTO MESSAGE]"
                final_data.append({
                    "sender": current_sender, "message": full_reply, "timestamp": None, "is_reply": True,
                    "reply_to": {"original_sender": target_sender, "original_message": " ".join(quote_parts) if quote_parts else "[MEDIA]"},
                    "confidence_score": round(sum(scores) / len(scores) if scores else 0.0, 4)
                })
                i = k; continue
            elif name1:
                current_sender = name1; current_sender_side = bubble_side; participants.add(name1); i += 1; continue
            elif is_timestamp(cleaned):
                if final_data: final_data[-1]["timestamp"] = cleaned
                i += 1; continue
            else:
                if not name1 and current_sender_side and bubble_side != current_sender_side:
                    if len(participants) == 2:
                        other = [p for p in participants if p != current_sender]
                        if other: current_sender = other[0]; current_sender_side = bubble_side
                    else: current_sender_side = bubble_side

                if current_sender and cleaned:
                    last_msg = final_data[-1] if final_data else None
                    if last_msg and last_msg["sender"] == current_sender:
                        if last_msg["message"] == "[PHOTO MESSAGE]": final_data.append({"sender": current_sender, "message": cleaned, "timestamp": None, "is_reply": False, "reply_to": None, "confidence_score": float(confidence)})
                        else: last_msg["message"] += f" {cleaned}"; last_msg["confidence_score"] = round((last_msg.get("confidence_score", 0.0) + confidence) / 2, 4)
                    else: final_data.append({"sender": current_sender, "message": cleaned, "timestamp": None, "is_reply": False, "reply_to": None, "confidence_score": float(confidence)})
                i += 1

    cleaned_data = [d for d in final_data if d['message'].strip() != "" and d['message'] != "Pinned on"]
    with open(output_path, "w", encoding="utf-8") as f: json.dump(cleaned_data, f, indent=2, ensure_ascii=False)
    print(f"✅ Extraction complete. Saved to {output_path}")

if __name__ == "__main__": extract_chat()