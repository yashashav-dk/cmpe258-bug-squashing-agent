"""
conftest.py (project root)

Project-level pytest configuration.

NOTE ON DATASET CASES:
  Dataset cases (dataset/cases/case_NNN/test_buggy.py) are NOT meant to be
  run in batch from the project root via pytest, because all test files share
  the basename 'test_buggy.py' and import the companion 'buggy' module.

  Instead, run them:
    - Individually:  pytest dataset/cases/case_001/test_buggy.py
    - Via the agent: python3 main.py --case case_001 --model gemini
    - In batch:      python3 eval.py  (uses cwd=case_dir per run)

  The unit test suite (tests/) is the intended target of 'pytest' from root.
"""
