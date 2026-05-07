import os

# Agent loop
MAX_RETRIES = 5
MAX_MEMORY_TOKENS = 2000

# Model
GEMINI_MODEL = "gemini-2.5-flash"  # gemini-2.0-flash deprecated 404 for new users
GEMMA4_MODEL = "gemma4:latest"
QWEN_MODEL = "Qwen/Qwen2.5-72B-Instruct-Turbo"
MINIMAX_MODEL = "MiniMaxAI/MiniMax-M2.5"

# Paths
DATASET_ROOT = os.path.join(os.path.dirname(__file__), "dataset")
CASES_DIR = os.path.join(DATASET_ROOT, "cases")
FEW_SHOT_DIR = os.path.join(DATASET_ROOT, "few_shot")
LOG_PATH = os.path.join(os.path.dirname(__file__), "logs", "run.jsonl")
