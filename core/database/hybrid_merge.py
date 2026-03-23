import json
import os
import re
import sys
from difflib import SequenceMatcher

# ----------------------------
# CONFIGURATION
# ----------------------------
BASE_OUTPUT_FOLDER = "output"
PADDLE_DIR = os.path.join(BASE_OUTPUT_FOLDER, "paddle")
EASY_DIR = os.path.join(BASE_OUTPUT_FOLDER, "easyocr")
FINAL_DIR = os.path.join(BASE_OUTPUT_FOLDER, "final")

os.makedirs(FINAL_DIR, exist_ok=True)

def load_json(filepath):
    if not os.path.exists(filepath): return []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content: return []
            data = json.loads(content)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"Warning: Error reading {filepath} ({e})")
        return []

def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

def is_better_timestamp(ts1, ts2):
    if not ts1: return False
    if not ts2: return True
    return (':' in ts1) and not (':' in ts2)

def merge_datasets(paddle_data, easy_data):
    merged_results = []
    used_easy_indices = set()

    if not paddle_data and easy_data: return easy_data
    if paddle_data and not easy_data: return paddle_data

    for p_msg in paddle_data:
        best_match_idx = -1; best_match_score = 0.0
        for i, e_msg in enumerate(easy_data):
            if i in used_easy_indices: continue
            if p_msg.get('sender') != e_msg.get('sender'): continue
            sim = similarity(p_msg['message'], e_msg['message'])
            if len(p_msg['message']) < 5 and sim < 0.9: continue
            if sim > 0.5 and sim > best_match_score:
                best_match_score = sim; best_match_idx = i

        final_entry = p_msg.copy()
        if best_match_idx != -1:
            e_msg = easy_data[best_match_idx]; used_easy_indices.add(best_match_idx)
            p_conf = p_msg.get('confidence_score', 0); e_conf = e_msg.get('confidence_score', 0)
            if e_conf > p_conf:
                final_entry['message'] = e_msg['message']; final_entry['confidence_score'] = e_conf
                if e_msg.get('is_reply') and not p_msg.get('is_reply'):
                    final_entry['is_reply'] = True; final_entry['reply_to'] = e_msg['reply_to']
            if is_better_timestamp(e_msg.get('timestamp'), p_msg.get('timestamp')):
                final_entry['timestamp'] = e_msg.get('timestamp')
        merged_results.append(final_entry)

    for i, e_msg in enumerate(easy_data):
        if i not in used_easy_indices:
            merged_results.append(e_msg)
    return merged_results

def get_dates_to_process():
    # 1. Check for command line argument first
    if len(sys.argv) > 1:
        return [sys.argv[1]]

    # 2. Fallback: Scan all files
    dates = set()
    if os.path.exists(PADDLE_DIR):
        for f in os.listdir(PADDLE_DIR):
            m = re.search(r'paddle_(\d{2}-\d{2}-\d{2})\.json', f)
            if m: dates.add(m.group(1))
    if os.path.exists(EASY_DIR):
        for f in os.listdir(EASY_DIR):
            m = re.search(r'easyocr_(\d{2}-\d{2}-\d{2})\.json', f)
            if m: dates.add(m.group(1))
    return sorted(list(dates))

def main():
    dates = get_dates_to_process()
    if not dates:
        print("❌ No JSON files or date arguments provided.")
        return

    print(f"📊 Merging datasets for: {dates}")
    
    for date in dates:
        print(f"--- Merging Date: {date} ---")
        p_file = os.path.join(PADDLE_DIR, f"paddle_{date}.json")
        e_file = os.path.join(EASY_DIR, f"easyocr_{date}.json")
        out_file = os.path.join(FINAL_DIR, f"merged_{date}.json")

        paddle_data = load_json(p_file)
        easy_data = load_json(e_file)
        
        final_data = merge_datasets(paddle_data, easy_data)
        
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved merged log to: {out_file}")

if __name__ == "__main__":
    main()