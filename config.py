import os

# Agent loop
MAX_RETRIES = 5
MAX_MEMORY_TOKENS = 2000

# Model
# Gemini API id (REST / google-genai SDK). Alias: gemini-flash-latest -> current Flash.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
GEMMA4_MODEL = "gemma4:latest"
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen/qwen-2.5-72b-instruct")
MINIMAX_MODEL = "MiniMaxAI/MiniMax-M2.5"

# Paths
DATASET_ROOT = os.path.join(os.path.dirname(__file__), "dataset")
CASES_DIR = os.path.join(DATASET_ROOT, "cases")
FEW_SHOT_DIR = os.path.join(DATASET_ROOT, "few_shot")
LOG_PATH = os.path.join(os.path.dirname(__file__), "logs", "run.jsonl")
