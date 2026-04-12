import os

# Agent loop
MAX_RETRIES = 5
MAX_MEMORY_TOKENS = 2000

# Model
GEMINI_MODEL = "gemini-2.0-pro"  # update to current available model if needed
GEMMA4_MODEL = "gemma4:latest"

# Paths
DATASET_ROOT = os.path.join(os.path.dirname(__file__), "dataset")
CASES_DIR = os.path.join(DATASET_ROOT, "cases")
FEW_SHOT_DIR = os.path.join(DATASET_ROOT, "few_shot")
LOG_PATH = os.path.join(os.path.dirname(__file__), "logs", "run.jsonl")
