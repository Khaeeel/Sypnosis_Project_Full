# SYPNOSIS ENGINE 1

An automated Viber chat monitoring, multi-engine OCR processing, AI-powered forensic analysis, and project management system for extracting, analyzing, and archiving team communications.

## Overview

SYPNOSIS ENGINE 1 is a comprehensive automation framework that:
- Continuously monitors and captures screenshots of a Viber chat window (24/7)
- Applies multiple OCR engines (EasyOCR, PaddleOCR) for robust text recognition
- Merges OCR results using intelligent confidence-based hybrid algorithms
- Automatically maintains a project task ledger using LLM-powered analysis (MySQL-backed)
- Syncs OCR results, summaries, and jargon data to MySQL via a unified pipeline
- Embeds processed chat logs and tasks into a ChromaDB vector database
- Generates RAG-augmented forensic HTML and text reports using Qwen LLM
- Provides an interactive CLI for querying the full chat archive via semantic search
- Self-builds a growing slang/dialect dictionary from unrecognized linguistic data
- Automatically purges files older than 7 days to manage disk usage

---

## Project Structure

```
SYPNOSIS_ENGINE_1/
├── config/                          # OCR engine configs & AI prompt templates
│   ├── easy_ocr_conf.py             # EasyOCR processing + chat parsing logic
│   ├── paddle_ocr_conf.py           # PaddleOCR processing + chat parsing logic
│   ├── prompt_template.py           # Base forensic analyst prompt (no RAG)
│   └── dictionary_prompt.py         # Forensic analyst prompt with dialect RAG
├── core/
│   ├── automation/
│   │   ├── task_tracker.py          # LLM-powered project task ledger manager (MySQL)
│   │   └── cleanup_manager.py       # Rolling 7-day file retention manager
│   ├── database/
│   │   ├── build_database.py        # Embeds chat + tasks into ChromaDB
│   │   ├── hybrid_merge.py          # Merges EasyOCR + PaddleOCR JSON outputs
│   │   └── filipinodictionarychroma.py  # Loads Filipino dictionary into ChromaDB
│   ├── llm/
│   │   ├── qwen_run.py              # Production forensic report generator
│   │   └── qwen_dictionary_engine.py  # Defines unrecognized slang via Qwen LLM
│   └── ocr/
│       └── ocr_utils.py             # Shared OCR utility library (canonical)
├── database_pipeline/               # MySQL sync pipeline components
│   ├── shared_config.py             # MySQL/SQLAlchemy configuration
│   ├── manage_tasks.py              # Sync tasks from master_tasks.json to MySQL
│   ├── generate_summary.py          # Record AI summaries to MySQL
│   ├── process_ocr.py               # Upload raw OCR JSON results to MySQL
│   └── ingest_jargon.py             # Ingest jargon CSV to MySQL + ChromaDB
├── watcher/
│   ├── auto_run.py                  # Daily pipeline orchestrator (cron entry point)
│   ├── auto_capture.py              # 24/7 Viber window screenshot watcher
│   ├── auto_scroll.py               # Auto-scrolls Viber chat window
│   ├── find_roi.py                  # Interactive ROI coordinate tool
│   └── visual_call_blocker.py       # Visual bot to auto-reject incoming calls
├── scripts/
│   └── chat.py                      # Interactive RAG chat CLI against ChromaDB
├── data/
│   ├── raw_screenshots/             # Daily capture folders (MM-DD-YY format)
│   └── dictionary/
│       └── FilipinoWordsDictionary.csv  # 210,000+ Filipino/dialect word definitions
├── output/
│   ├── easyocr/                     # Per-day EasyOCR JSON results
│   ├── paddle/                      # Per-day PaddleOCR JSON results
│   ├── final/                       # Merged hybrid JSON results
│   ├── linguistic_data/             # Unrecognized slang/OCR noise records
│   └── automated_dictionary.json   # Self-growing slang dictionary
├── summary/
│   ├── html/                        # Styled forensic HTML reports
│   └── txt/                         # Raw markdown forensic reports
├── chroma_storage/                  # ChromaDB vector database (persistent)
│   └── chroma.sqlite3               # ChromaDB index metadata (SQLite)
├── logs/
│   ├── cron_log.txt                 # Pipeline execution log
│   ├── automation_log.txt           # Legacy automation log
│   ├── capture_log.txt              # Screenshot event log
│   └── cron_sys_log.txt             # System-level cron log
├── master_tasks.json                # Project task ledger (JSON, synced to MySQL)
├── synology_schema.sql              # MySQL schema with full table definitions
├── database_dump.sql                # Legacy MySQL dump (departments + jargons)
├── pipeline.py                      # Unified orchestration (MySQL + ChromaDB sync)
├── cron_log.txt                     # Root-level cron execution log
├── ocr_utils.py                     # Root-level legacy copy of core/ocr/ocr_utils.py
├── docker-compose.yaml              # Docker deployment config with ROCm pass-through
├── entrypoint.sh                    # Docker entry point (runs pipeline every 24h)
├── master_viber_bot.sh              # Launches all 3 watcher bots simultaneously
└── requirements.txt                 # Python dependencies
```

---

## Databases

The system uses three distinct data stores:

### 1. MySQL Database (`synology_schema.sql`)

A MySQL database named `sypnosis` serving as the primary relational data store. Schema defined in `synology_schema.sql`.

**Table: `departments`** (7 rows)

| id | name |
|----|------|
| 1  | Project Manager |
| 2  | System Administration and Maintenance |
| 3  | Artificial Intelligence |
| 4  | Web Development |
| 5  | Computer Engineering |
| 6  | Accounting |
| 7  | Miscellaneous |

**Table: `jargons`** (~210,877 rows)

| Column | Type | Description |
|--------|------|-------------|
| id | INT AUTO_INCREMENT PK | Primary key |
| letter | VARCHAR(10) | Alphabetic group (A, B, C...) |
| word | VARCHAR(255) | The term |
| definition | TEXT | Full definition with grammar tags |
| dialect | VARCHAR(100) | Language: tagalog, cebuano, hiligaynon, ilocano |

**Table: `sender_aliases`** (maps OCR-prone name variants to canonical names)

| Column | Type | Description |
|--------|------|-------------|
| id | INT AUTO_INCREMENT PK | Primary key |
| alias | VARCHAR(255) | OCR-prone variant/nickname |
| canonical_name | VARCHAR(255) | Resolved full name |
| department_id | INT FK | Reference to `departments.id` |

Managed by `core/ocr/ocr_utils.py` via `resolve_sender()` and synced from `SENDER_ALIASES` dict. `AliasNormalizer` in `database_pipeline/generate_summary.py` provides fuzzy matching against this table.

**Table: `users`** (user accounts)

| Column | Type | Description |
|--------|------|-------------|
| id | INT PK | Primary key |
| username | VARCHAR(100) | Login username |
| password | VARCHAR(255) | Hashed password |
| role | ENUM | super_admin / admin / user |
| created_at | DATETIME | Account creation timestamp |

**Table: `summaries`** (AI-generated forensic reports)

| Column | Type | Description |
|--------|------|-------------|
| id | INT AUTO_INCREMENT PK | Primary key |
| date | DATE | Summary date |
| raw_text | TEXT | Raw markdown report |
| html_content | TEXT | Rendered HTML |
| created_by | INT FK | Reference to `users.id` |
| created_at | DATETIME | Creation timestamp |

**Table: `tasks`** (project task ledger — primary source of truth)

| Column | Type | Description |
|--------|------|-------------|
| id | INT AUTO_INCREMENT PK | Primary key |
| task_id | VARCHAR(50) UNIQUE | TSK-YYYYMMDD-NNN format |
| task_description | TEXT | Task description |
| department_id | INT FK | Reference to `departments.id` |
| status | ENUM | Pending / In Progress / Completed / Blocked |
| date_created | DATE | Creation date |
| possible_assignees | TEXT | JSON array of names |
| assigned_name | VARCHAR(255) | Assigned person |
| completed_by | VARCHAR(255) | Person who completed it |
| notes | TEXT | Additional notes |

Managed by `core/automation/task_tracker.py` which reads from MySQL and writes back using `INSERT ... ON DUPLICATE KEY UPDATE`. Synced from/to `master_tasks.json` via `database_pipeline/manage_tasks.py`.

**Table: `ocr_results`** (raw OCR JSON data)

| Column | Type | Description |
|--------|------|-------------|
| id | INT AUTO_INCREMENT PK | Primary key |
| date | DATE | Capture date |
| engine | VARCHAR(50) | easyocr or paddle |
| json_data | JSON | Full OCR output JSON |
| summary_id | INT FK | Reference to `summaries.id` |
| created_at | DATETIME | Upload timestamp |

Ingested via `database_pipeline/process_ocr.py`.

---

### 2. ChromaDB Vector Database (`chroma_storage/`)

A persistent local vector database backed by SQLite (`chroma_storage/chroma.sqlite3`). Contains two collections:

**Collection: `team_chat_history`**
- Embedding model: `mxbai-embed-large` (via Ollama)
- Two document types stored under `metadata.type`:
  - `"chat_message"` — Full message string: `[timestamp] Sender: message (Replying to...)`. Metadata: `{type, sender, date, timestamp}`
  - `"official_task"` — Full task record string from MySQL `tasks` table. Metadata: `{type, task_id, department, status, date_created}`
- Used by `scripts/chat.py` for natural-language question answering over the full chat archive

**Collection: `filipino_dialect_lookup`**
- Embedding model: `bge-m3` (via Ollama, multilingual)
- Document format: `"Term: {word} | Dialect: {dialect} | Meaning: {definition}"`
- Metadata: `{type: "dictionary_entry", dialect, word, letter}`
- Used by `qwen_run.py` for RAG dialect context injection during report generation
- Populated by `core/database/filipinodictionarychroma.py` from the MySQL CSV export

**Collection: `jargon_embeddings`** (Filipino jargon ChromaDB collection)
- Embedding model: `bge-m3` (via Ollama, multilingual)
- Document format: `"Term: {word} | Dialect: {dialect} | Meaning: {definition}"`
- Populated by `database_pipeline/ingest_jargon.py` directly from MySQL `jargons` table

---

### 3. `master_tasks.json` — Project Task Ledger (JSON)

A flat JSON array maintained in sync with the MySQL `tasks` table. The `task_tracker.py` reads existing tasks from MySQL for context, then writes updates back to both MySQL and this JSON file. The JSON serves as a portable/exportable snapshot. Task schema:

```json
{
  "task_id": "TSK-YYYYMMDD-NNN",
  "task_description": "...",
  "department": "one of 7 enum values",
  "status": "Pending | In Progress | Completed | Blocked",
  "date_created": "YYYY-MM-DD",
  "possible_assignees": ["Name"],
  "assigned_name": "Name",
  "completed_by": null,
  "notes": "..."
}
```

Valid department enum values: `Project Manager`, `System Administration and Maintenance`, `Artificial Intelligence`, `Web Development`, `Computer Engineering`, `Accounting`, `Miscellaneous`

Valid status enum values: `Pending`, `In Progress`, `Completed`, `Blocked`

---

### 4. `output/automated_dictionary.json` — Self-Growing Slang Dictionary

A flat key-value JSON map of `word → pipe-delimited definition string`, built and updated by `core/llm/qwen_dictionary_engine.py`. Covers Filipino slang, Jejemon spellings, internet abbreviations, and OCR-distorted terms.

---

## Data Flow / Pipeline

```
Phase 1: CAPTURE (Continuous, 24/7)
─────────────────────────────────────────────────────────────
  master_viber_bot.sh
  ├─ auto_scroll.py          → Scrolls Viber window every 5s
  ├─ auto_capture.py         → Detects screen changes via pHash + pixel diff,
  │                             saves PNGs to data/raw_screenshots/MM-DD-YY/
  └─ visual_call_blocker.py  → Pixel-scans screen at 10Hz, auto-rejects calls

Phase 2: DAILY PROCESSING (Nightly via cron → watcher/auto_run.py)
─────────────────────────────────────────────────────────────
  Target: yesterday's date folder

  Step 1: paddle_ocr_conf.py
    Input:  data/raw_screenshots/MM-DD-YY/*.png
    Output: output/paddle/paddle_MM-DD-YY.json

  Step 2: easy_ocr_conf.py
    Input:  data/raw_screenshots/MM-DD-YY/*.png
    Output: output/easyocr/easyocr_MM-DD-YY.json

  Step 3: hybrid_merge.py
    Input:  output/paddle/ + output/easyocr/
    Output: output/final/merged_MM-DD-YY.json
    Action: Confidence-based merge, best-text selection

  Step 4: task_tracker.py
    Input:  output/final/merged_MM-DD-YY.json + MySQL tasks table
    Output: MySQL tasks table (upserted) + master_tasks.json (synced)
    Action: qwen3.5:9b analyzes chat, writes to MySQL, syncs JSON

  Step 5: build_database.py
    Input:  output/final/merged_MM-DD-YY.json + MySQL tasks table
    Output: chroma_storage/ (upserted vectors)
    Action: Embeds messages + tasks into ChromaDB team_chat_history

  Step 6: qwen_run.py
    Input:  output/final/merged_MM-DD-YY.json + ChromaDB dialect RAG
    Output: summary/txt/merged_MM-DD-YY.txt
            summary/html/merged_MM-DD-YY.html
            output/linguistic_data/unrecognized_merged_MM-DD-YY.json
    Action: RAG-augmented forensic report with embedded task ledger table
            Saves unrecognized linguistic data for dictionary enrichment

  Step 7: cleanup_manager.py
    Action: Deletes raw screenshots + output files older than 7 days

Phase 3: DATABASE SYNC (part of or standalone from auto_run.py)
─────────────────────────────────────────────────────────────
  database_pipeline/manage_tasks.py
    Action: Sync master_tasks.json → MySQL tasks table

  database_pipeline/process_ocr.py
    Action: Upload OCR JSON files to MySQL ocr_results table

  database_pipeline/generate_summary.py
    Action: Record AI summary to MySQL summaries table
            Uses AliasNormalizer for fuzzy sender matching

  database_pipeline/ingest_jargon.py
    Action: Ingest jargon CSV to MySQL jargons table + ChromaDB jargon_embeddings

  pipeline.py (unified orchestrator)
    Action: Runs all 4 database pipeline components in sequence

Phase 4: INTERACTIVE QUERY (On-demand)
─────────────────────────────────────────────────────────────
  scripts/chat.py
    Input:  Terminal user query
    Action: Semantic search ChromaDB → RAG prompt → qwen3:8b streaming
    Output: Answer with evidence from the chat archive

  core/llm/qwen_dictionary_engine.py
    Input:  output/linguistic_data/*.json (unrecognized words)
    Action: qwen3:8b defines slang terms, updates automated_dictionary.json
```

---

## Key Features

- **Multi-Engine OCR**: Combines EasyOCR (AMD GPU) and PaddleOCR (CPU) for improved accuracy
- **Intelligent Chat Parsing**: Reconstructs threaded replies, photo messages, timestamps, and multi-sender attribution from raw OCR lines
- **Confidence-Based Merging**: Hybrid merge picks the highest-confidence text from each engine
- **LLM Task Tracker**: Qwen 3.5 automatically extracts, deduplicates, and tracks project tasks from daily conversations (MySQL-backed with JSON sync)
- **MySQL Database Sync**: Unified pipeline (`pipeline.py`) syncs tasks, OCR results, summaries, and jargon data to MySQL tables
- **ChromaDB Vector Store**: Full semantic memory of all processed chat logs and tasks; supports natural-language queries
- **Filipino Dialect RAG**: 210k+ word dictionary (Tagalog, Cebuano, Hiligaynon, Ilocano) embedded for context-aware forensic analysis
- **Self-Growing Slang Dictionary**: Unrecognized words from reports are automatically defined and added to `automated_dictionary.json`
- **Forensic HTML Reports**: Styled reports with task ledger tables embedded between sections
- **Interactive Chat CLI**: `scripts/chat.py` allows querying the archive in natural language with streaming output
- **Visual Call Blocker**: Pixel-scanning bot auto-rejects Viber calls to prevent capture interruptions
- **Automatic Scrolling**: `auto_scroll.py` ensures the full chat feed is captured
- **7-Day Rolling Cleanup**: `cleanup_manager.py` purges old files automatically to prevent disk overflow
- **Docker Deployment**: Fully containerized with AMD ROCm GPU pass-through and Xvfb virtual display

---

## Getting Started

### Prerequisites

- Python 3.12.3
- GPU: AMD Radeon with ROCm 6.0.0 (RX 7900 XT, `HSA_OVERRIDE_GFX_VERSION=11.0.0`)
- EasyOCR 1.7.2
- PaddleOCR 2.8.1 / PaddlePaddle 2.6.2
- OpenCV 4.6.0.66
- PIL/Pillow 12.1.1
- PyTorch 2.4.1 (ROCm variant)
- PyAutoGUI 0.9.54
- Ollama (with `qwen3:8b`, `qwen3.5:9b`, `mxbai-embed-large`, `bge-m3` models pulled)
- ChromaDB (persistent local store)
- MySQL 8.4 (for the `sypnosis` database)
- xdotool (for Viber window detection)
- Additional dependencies (see requirements.txt)

### Installation

1. Navigate to the project directory:
```bash
cd /home/citai/Documents/SYPNOSIS_ENGINE_1
```

2. Install PyTorch with ROCm support:
```bash
pip install torch==2.4.1+rocm6.0 torchaudio==2.4.1+rocm6.0 torchvision==0.19.1+rocm6.0 --index-url https://download.pytorch.org/whl/rocm6.0
```

3. Install remaining dependencies:
```bash
pip install -r requirements.txt
```

4. Import the MySQL schema:
```bash
mysql -u root -p sypnosis < synology_schema.sql
```

5. Export the Filipino dictionary CSV (if not already present):
```bash
mysql -u root -p -e "SELECT word, definition, dialect, letter FROM jargons" sypnosis > data/dictionary/FilipinoWordsDictionary.csv
```

6. Build the ChromaDB vector database:
```bash
python core/database/filipinodictionarychroma.py  # One-time: embeds Filipino dictionary
python core/database/build_database.py            # Embeds chat logs and tasks
```

7. Run the unified database sync pipeline (optional — syncs MySQL + ChromaDB):
```bash
python pipeline.py
```

### GPU Configuration (AMD ROCm 6.0)

This project is optimized for AMD Radeon GPUs using ROCm 6.0. Key notes:
- PyTorch and related packages are ROCm 6.0 compiled
- EasyOCR uses GPU acceleration; PaddleOCR runs on CPU (ROCm incompatibility)
- All NVIDIA CUDA dependencies have been removed
- Verify ROCm installation: `rocm-smi`

---

## Usage

### Run Full Daily Automation Pipeline
```bash
python watcher/auto_run.py
```

### Launch All Capture Bots (24/7 Monitoring)
```bash
bash master_viber_bot.sh
```
This starts `auto_capture.py`, `auto_scroll.py`, and `visual_call_blocker.py` as parallel background processes.

### Capture Screenshots Manually
```bash
python watcher/auto_capture.py
```

### Process with Specific OCR Engine
```bash
python config/easy_ocr_conf.py    # EasyOCR processing
python config/paddle_ocr_conf.py  # PaddleOCR processing
```

### Merge OCR Results
```bash
python core/database/hybrid_merge.py
```

### Update Task Ledger from Chat
```bash
python core/automation/task_tracker.py
```

### Build/Update ChromaDB
```bash
python core/database/build_database.py
```

### Generate Forensic Report
```bash
python core/llm/qwen_run.py
```

### Query the Chat Archive (Interactive CLI)
```bash
python scripts/chat.py
```

### Run Linguistic Data Extraction & Slang Dictionary Builder
```bash
python core/llm/qwen_dictionary_engine.py
```

### Run Unified Database Sync Pipeline
```bash
python pipeline.py
```

### Run Individual Database Pipeline Components
```bash
python database_pipeline/manage_tasks.py     # Sync tasks JSON → MySQL
python database_pipeline/process_ocr.py      # Upload OCR JSON → MySQL
python database_pipeline/generate_summary.py # Record summaries → MySQL
python database_pipeline/ingest_jargon.py    # Ingest jargons → MySQL + ChromaDB
```

### Docker Deployment
```bash
docker-compose up --build
```

---

## Output Files

| File | Description |
|------|-------------|
| `output/easyocr/easyocr_MM-DD-YY.json` | EasyOCR parsed chat messages |
| `output/paddle/paddle_MM-DD-YY.json` | PaddleOCR parsed chat messages |
| `output/final/merged_MM-DD-YY.json` | Confidence-merged final messages |
| `output/linguistic_data/unrecognized_merged_MM-DD-YY.json` | Unrecognized slang/OCR noise |
| `output/automated_dictionary.json` | Self-built slang dictionary |
| `summary/txt/merged_MM-DD-YY.txt` | Raw markdown forensic report |
| `summary/html/merged_MM-DD-YY.html` | Styled HTML forensic report |
| `master_tasks.json` | Project task ledger (JSON, synced to MySQL) |
| `chroma_storage/` | ChromaDB persistent vector store |

---

## Configuration

### ROI Configuration
Region of Interest for screenshot capture can be recalibrated using:
```bash
python watcher/find_roi.py
```

### OCR Engine Configuration
Each OCR engine has its own configuration file:
- `config/easy_ocr_conf.py` — Adjust EasyOCR parameters and sender alias map
- `config/paddle_ocr_conf.py` — Adjust PaddleOCR parameters

### Sender Alias Map
The `SENDER_ALIASES` dict in `core/ocr/ocr_utils.py` maps OCR-prone name variants and nicknames to canonical full names. Update this when new team members are added.

### Department Configuration
The `OFFICIAL_ORGANIZATION` dict in `core/ocr/ocr_utils.py` is the authority source for department-member assignments used by the LLM task tracker and forensic reports.

### LLM Models
Models are served via Ollama. Update model names in the respective scripts:
- `task_tracker.py` → `qwen3.5:9b`
- `qwen_run.py` → `qwen3.5:9b`
- `qwen_dictionary_engine.py` / `scripts/chat.py` → `qwen3:8b`

### MySQL Configuration
Database connection settings are centralized in `database_pipeline/shared_config.py`. Update the `SQLALCHEMY_DATABASE_URI` to point to your MySQL instance (default: `mysql+mysqlconnector://root:password@127.0.0.1:3306/sypnosis`).

### Database Pipeline Components
The `database_pipeline/` directory contains modular MySQL sync components:
- `shared_config.py` — SQLAlchemy engine and session factory
- `manage_tasks.py` — Syncs `master_tasks.json` → MySQL `tasks` table
- `process_ocr.py` — Uploads OCR JSON → MySQL `ocr_results` table
- `generate_summary.py` — Records AI summaries → MySQL `summaries` table with `AliasNormalizer` fuzzy matching
- `ingest_jargon.py` — Ingests jargon CSV → MySQL `jargons` table AND ChromaDB `jargon_embeddings`

Use `pipeline.py` to run all components in sequence, or run them individually.

---

## Logs

| Log File | Description |
|----------|-------------|
| `cron_log.txt` | Root-level cron execution log |
| `logs/cron_log.txt` | Daily pipeline execution log |
| `logs/automation_log.txt` | Legacy automation log |
| `logs/capture_log.txt` | Screenshot capture event log |
| `logs/cron_sys_log.txt` | System-level cron log |

---

## Development

### Adding New OCR Engines
1. Create a new configuration file: `config/your_ocr_conf.py`
2. Implement the OCR processing and chat parsing logic
3. Update `core/database/hybrid_merge.py` to include the new engine output
4. Register in `watcher/auto_run.py`

### Adding New Database Pipeline Components
1. Create a new file in `database_pipeline/`
2. Import `get_engine` and `get_session` from `shared_config.py`
3. Define your SQLAlchemy model class
4. Add to `pipeline.py` to include it in the unified run

### Customizing the Task Tracker
Modify the prompt in `core/automation/task_tracker.py` to adjust how the LLM interprets and classifies tasks. The prompt governs deduplication, status evaluation, department assignment, and ID formatting. Tasks are written directly to MySQL `tasks` table and synced to `master_tasks.json`.

### Customizing Merge Logic
Modify `core/database/hybrid_merge.py` to adjust how OCR results from multiple engines are combined.

### Extending the Forensic Prompt
Two prompt templates exist:
- `config/prompt_template.py` — Base analyst prompt (no dictionary RAG)
- `config/dictionary_prompt.py` — Enhanced prompt with Filipino dialect RAG (used in production)

---

## Troubleshooting

- **No screenshots captured**: Check `watcher/find_roi.py` output and recalibrate the capture region. Verify `xdotool` can detect the "Rakuten Viber" window.
- **OCR errors or empty output**: Verify EasyOCR and PaddleOCR model files are installed. Check GPU availability with `rocm-smi`.
- **ChromaDB empty results**: Run `core/database/build_database.py` to populate the vector store. Verify Ollama is running with the correct embedding models.
- **Task tracker producing wrong results**: Check that `core/ocr/ocr_utils.py` has up-to-date `SENDER_ALIASES` and `OFFICIAL_ORGANIZATION` entries, and that the MySQL `tasks` table schema matches the expected schema in `synology_schema.sql`.
- **MySQL connection errors**: Ensure `synology_schema.sql` is imported, credentials in `database_pipeline/shared_config.py` are correct, and the `mysql-connector-python` driver is installed.
- **Database pipeline failures**: Run `pipeline.py` components individually to isolate which step is failing. Check `logs/cron_log.txt` for detailed error information.
- **Alias normalization not working**: Verify the `sender_aliases` table in MySQL is populated. The `AliasNormalizer` class in `database_pipeline/generate_summary.py` uses fuzzy matching via `thefuzz`.
- **Memory issues**: Reduce batch size in OCR configuration files, `filipinodictionarychroma.py`, or `database_pipeline/ingest_jargon.py`.
- **No output files**: Check `logs/cron_log.txt`, `cron_log.txt`, and `logs/capture_log.txt` for detailed error information.

---

## License

[Add your license information here]
"# Sypnosis_Project_Full" 
