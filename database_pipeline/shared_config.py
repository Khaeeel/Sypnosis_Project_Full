import os
from sqlalchemy import create_engine

# Database Configuration
DB_URL = "mysql+mysqlconnector://root:comfac%40123@127.0.0.1:3306/sypnosis"
engine = create_engine(DB_URL)

# 1. Find the current folder (database_pipeline)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. Go UP one level to the main project root (sintosis-engine 1)
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

# 3. Point directly to where your actual OCR output goes
SUMMARY_INPUT_DIR = os.path.join(PROJECT_ROOT, "output", "final")

# 4. Point to your master tasks JSON in the root folder
TASK_JSON_PATH = os.path.join(PROJECT_ROOT, "master_tasks.json")

# Ensure the final output directory exists just in case
if not os.path.exists(SUMMARY_INPUT_DIR):
    os.makedirs(SUMMARY_INPUT_DIR)