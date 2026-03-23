import os
import sys
import json
import requests
import chromadb
from chromadb.utils import embedding_functions

# =========================
# CONFIGURATION
# =========================
BASE_DIR = os.getcwd()
DB_PATH = os.path.join(BASE_DIR, "chroma_storage")
OLLAMA_GENERATE_API = "http://localhost:11434/api/generate"
CHAT_MODEL = "qwen3:8b" # The Talker

# 1. Connect to ChromaDB
if not os.path.exists(DB_PATH):
    print("❌ Error: Database not found. Please run build_database.py first.")
    sys.exit(1)

client = chromadb.PersistentClient(path=DB_PATH)

# 2. Set up the Embedding Function
try:
    ollama_ef = embedding_functions.OllamaEmbeddingFunction(
        url="http://localhost:11434/api/embeddings",
        model_name="mxbai-embed-large",
    )
    collection = client.get_collection(name="team_chat_history", embedding_function=ollama_ef)
except Exception as e:
    print(f"❌ Error connecting to ChromaDB or Ollama: {e}")
    sys.exit(1)

print("=========================================")
print("🤖 TEAM CHAT ARCHIVE AI INITIALIZED")
print("Type 'exit' or 'quit' to stop.")
print("=========================================\n")

# =========================
# CHAT LOOP
# =========================
while True:
    user_query = input("\n👤 You: ")
    
    if user_query.lower() in ['exit', 'quit']:
        print("Goodbye! 👋")
        break
    if not user_query.strip():
        continue

    print("🔍 Searching memory...")

    # 1. Search ChromaDB for the top 15 most relevant messages
    # 1. Search ChromaDB for a LARGER set to get past the noise
    results = collection.query(
        query_texts=[user_query],
        n_results=50 
    )

    raw_docs = results.get('documents', [[]])[0]
    raw_metas = results.get('metadatas', [[]])[0]

    # 2. De-duplicate and Clean (Only keep unique content)
    seen_content = set()
    unique_context = []

    for doc, meta in zip(raw_docs, raw_metas):
        # We clean the doc to check for duplicates regardless of timestamp
        clean_content = doc.split("]: ", 1)[-1] if "]: " in doc else doc
        
        if clean_content not in seen_content:
            seen_content.add(clean_content)
            unique_context.append(f"[Date: {meta.get('date')}] {doc}")

    # 3. Limit the AI to the top 15 UNIQUE/DIVERSE results
    context_text = "\n".join(unique_context[:15])

    documents = results.get('documents', [[]])[0]
    metadatas = results.get('metadatas', [[]])[0]
    
    if not documents:
        print("🤖 Qwen: I couldn't find anything in the chat logs about that.")
        continue

    # 2. Build highly structured context using ChromaDB's hidden metadata
    # 2. Build highly structured context using ChromaDB's expanded metadata
    context_lines = []
    
    # Use a dictionary to de-duplicate messages (vector search often returns duplicates)
    seen_messages = set()

    for doc, meta in zip(documents, metadatas):
        # Create a unique key to skip exact duplicate messages
        message_key = f"{meta.get('sender')}_{doc}"
        if message_key in seen_messages:
            continue
        seen_messages.add(message_key)

        # Extract enriched metadata
        sender = meta.get("sender", "Unknown")
        date = meta.get("date", "Unknown Date")
        time = meta.get("timestamp", "N/A")
        
        # Note: 'doc' already contains "[Time] Sender: Message (Reply Context)" 
        # from your new build_database.py script.
        context_lines.append(f"LOG ENTRY: [Date: {date}] {doc}")

    context_text = "\n".join(context_lines)

    # 3. Build the strict RAG Prompt
    prompt = f"""### ROLE
You are a High-Precision Data Retrieval Agent. Your task is to analyze team chat logs to provide factual answers. You must account for conversational threads (replies) and chronological order.

### SOURCE DATA (CHAT LOGS):
{context_text}

### CRITICAL INSTRUCTIONS:
1. **Thread Awareness:** If a message is a reply, use the "Replying to" context to understand the subject. (e.g., If Dominic says "wala pang viber yun," identify that "yun" refers to the "2nd new pc" mentioned by Bharon).
2. **Identity Integrity:** Only attribute statements to the "SENDER." Do not confuse the person being replied to with the person speaking.
3. **Task Status Tracking:** - Identify what is "Complete" (e.g., OCRs, Qwen Model).
    - Identify what is "Pending" (e.g., Viber installation, UI suggestions).
    - Identify "Future Actions" (e.g., Monday tasks, meeting with Sir Jun).
4. **No Hallucinations:** If the user asks about something not in the text (e.g., "What is the password?"), you must state: "The chat logs do not contain that information."

### CRITICAL INSTRUCTIONS:
1. **Transactional Agency:** Distinguish between a "Seller" (the person providing the goods/owning the inventory) and an "Endorser/Middleman" (someone suggesting where to buy or helping coordinate). 
    - Look for phrases like "kanila" (them), "benta namin" (our sale), or "support local" to identify the actual source.
    - If a sender says "buy from them," do not label that sender as the primary seller.
2. **Thread Awareness:** If a message is a reply, use the "Replying to" context to understand the subject.
3. **Identity Integrity:** Only attribute statements to the "SENDER." Ensure you do not confuse the person being replied to with the person speaking.
4. **No Hallucinations:** If the chat logs do not explicitly confirm a specific detail (like the "original" owner), state that the logs are "inconclusive" or "suggest [Name] but don't confirm it."

### RESPONSE FORMAT:
- **Summary:** A 1-sentence direct answer.
- **Evidence:** Bullet points citing the SENDER and the exact TIMESTAMP.
- **Context (Optional):** Mention if the information was part of a reply thread.

### USER QUESTION:
{user_query}

### FACTUAL RESPONSE:
"""

    # 4. Send to Qwen
    payload = {
        "model": CHAT_MODEL,
        "prompt": prompt,
        "stream": True,
        "options": {
            "temperature": 0.1 # Lowered temperature to make it even more strictly factual
        }
    }

    print("\n🤖 Qwen: ", end="", flush=True)

    try:
        response = requests.post(OLLAMA_GENERATE_API, json=payload, stream=True)
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                chunk = json.loads(line)
                word = chunk.get("response", "")
                print(word, end="", flush=True)
                
                if chunk.get("done"):
                    print() 
                    
    except requests.exceptions.RequestException as e:
        print(f"\n❌ API Error communicating with Qwen: {e}")