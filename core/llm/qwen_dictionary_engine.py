import os
import json
import requests
import re

# =========================
# CONFIGURATION
# =========================
OLLAMA_API = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen3:8b"
BASE_DIR = os.getcwd()

LINGUISTIC_DIR = os.path.join(BASE_DIR, "output", "linguistic_data")
MASTER_DICT_JSON = os.path.join(BASE_DIR, "output", "automated_dictionary.json")

# =========================
# LEXICOGRAPHER PROMPT
# =========================
LEXICON_PROMPT_TPL = """You are a computational linguist specializing in Filipino informal language.

Your task is to analyze UNRECOGNIZED LINGUISTIC DATA extracted from real conversations and produce accurate dictionary definitions.

These words may include:
• Filipino slang
• Taglish
• Internet abbreviations
• Jejemon spellings
• OCR distortions
• Phonetic spellings
• Typographical errors

=====================
STRICT LINGUISTIC RULES
=====================

1. Do not invent meanings.
2. Do not guess if uncertain.
3. If meaning cannot be determined → mark as UNKNOWN.
4. Prefer real conversational meaning over formal dictionary meaning.
5. If the word is distorted, first infer its most probable normalized form.
6. If the word is an abbreviation, expand it before defining.
7. If multiple meanings exist, choose the most probable conversational usage.
8. Maintain linguistic neutrality. Do not assume meaning without evidence.
9. If the word appears to be noise or OCR error → classify as UNKNOWN.
10. Definitions must be factual, not interpretive.

=====================
ANALYSIS PROCESS (INTERNAL)
=====================

For each word:
1 Normalize spelling if needed
2 Detect language origin (Filipino, English, Taglish, slang)
3 Determine part of speech
4 Produce a concise definition
5 If uncertain mark UNKNOWN

=====================
OUTPUT FORMAT (STRICT)
=====================

word | normalized_form | part_of_speech | definition | confidence_score

confidence_score must be:
HIGH → common slang or known word
MEDIUM → probable meaning
LOW → uncertain meaning
UNKNOWN → cannot determine meaning

=====================
FORMAT RULES
=====================

• One entry per line
• No explanations
• No numbering
• No commentary
• No markdown
• No extra text
• No examples
• No reasoning output

=====================
WORDS TO DEFINE:
{word_list}

Return only the formatted entries.
"""

def define_and_archive_words():
    if not os.path.exists(LINGUISTIC_DIR):
        print("❌ Linguistic data directory not found."); return

    source_json_files = [f for f in os.listdir(LINGUISTIC_DIR) if f.endswith('.json')]
    if not source_json_files:
        print("✅ No new linguistic data to process."); return

    master_dict = {}
    if os.path.exists(MASTER_DICT_JSON):
        with open(MASTER_DICT_JSON, "r", encoding="utf-8") as f:
            master_dict = json.load(f)

    for filename in source_json_files:
        file_path = os.path.join(LINGUISTIC_DIR, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        words_in_this_file = data.get("atomic_word_index", [])
        words_to_define = [w for w in words_in_this_file if w.lower() not in master_dict]

        if not words_to_define:
            print(f"✅ Words in {filename} already defined in master dictionary.")
            continue

        print(f"🧠 Defining {len(words_to_define)} terms from {filename}...")
        
        prompt = LEXICON_PROMPT_TPL.format(word_list=", ".join(words_to_define))
        payload = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.0, "num_ctx": 4096}
        }

        try:
            response = requests.post(OLLAMA_API, json=payload, timeout=600)
            raw_response = response.json().get('response', '')
            lines = raw_response.strip().split('\n')
            
            new_definitions_found = 0

            for line in lines:
                # 1. CLEANING: Remove AI artifacts (bullets, bolding, colons)
                clean_line = line.strip()
                if not clean_line or len(clean_line) < 3: continue
                
                # Remove common prefixes like "1. ", "- ", "* "
                clean_line = re.sub(r'^(\d+\.|\*|-)\s+', '', clean_line)
                # Remove bolding if AI ignores instructions
                clean_line = clean_line.replace('**', '')

                # 2. EXTRACTION: Split by first space to isolate the word
                # Structure: [word] [pos. definition]
                parts = clean_line.split(' ', 1)
                
                if len(parts) == 2:
                    word = parts[0].strip().lower().rstrip(':')
                    definition = parts[1].strip()
                    
                    # 3. STORAGE
                    master_dict[word] = definition
                    new_definitions_found += 1
                    print(f"  ✨ Saved: {word}")
                else:
                    print(f"  ⚠️ Failed to parse line: {clean_line}")

            # Update the Master JSON
            with open(MASTER_DICT_JSON, "w", encoding="utf-8") as f:
                json.dump(master_dict, f, indent=4)
                
            print(f"✅ Done with {filename}. Added {new_definitions_found} entries.")

        except Exception as e:
            print(f"❌ API/Processing Error: {e}")

if __name__ == "__main__":
    define_and_archive_words()