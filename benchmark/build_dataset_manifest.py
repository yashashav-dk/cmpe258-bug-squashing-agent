"""
Emit a benchmark JSONL manifest covering dataset/cases/case_* local fixtures.

Each row uses injection_mode=replace with metadata.old/new set to golden.py vs
buggy.py so run_matrix reset (golden overlay) plus injection restores the repo’s
committed broken state semantics.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import List


def _case_dirs(cases_root: Path) -> List[Path]:
    rows: List[tuple[int, Path]] = []
    for p in sorted(cases_root.glob("case_*")):
        if not p.is_dir():
            continue
        m = re.fullmatch(r"case_(\d+)", p.name)
        if not m:
            continue
        rows.append((int(m.group(1)), p))
    return [path for _, path in sorted(rows, key=lambda t: t[0])]


def _collect_pytest_funcs(test_py: Path) -> List[str]:
    text = test_py.read_text(encoding="utf-8")
    return sorted(set(re.findall(r"^def (test_\w+)\b", text, flags=re.MULTILINE)))


def build_rows(cases_root: Path) -> List[dict]:
    cases_root = cases_root.resolve()
    out: List[dict] = []
    for case_dir in _case_dirs(cases_root):
        golden = case_dir / "golden.py"
        buggy = case_dir / "buggy.py"
        test_py = case_dir / "test_buggy.py"
        if not (golden.exists() and buggy.exists() and test_py.exists()):
            raise FileNotFoundError(
                f"case {case_dir.name}: require golden.py, buggy.py, test_buggy.py"
            )
        g_text = golden.read_text(encoding="utf-8")
        b_text = buggy.read_text(encoding="utf-8")
        if g_text == b_text:
            raise ValueError(f"case {case_dir.name}: golden.py equals buggy.py (no bug corpus)")

        case_num_m = re.fullmatch(r"case_(\d+)", case_dir.name)
        nstr = case_num_m.group(1) if case_num_m else str(idx + 1)
        case_id = f"synthetic_dataset_case_{int(nstr):03d}"
        ws_rel = f"./dataset/cases/{case_dir.name}"

        tests = _collect_pytest_funcs(test_py)
        expected_failures = [f"test_buggy.py::{fn}" for fn in tests]

        # Heuristic difficulty from relative change mass
        gl, bl = len(g_text.splitlines()), len(b_text.splitlines())
        diff_lines = abs(gl - bl) + sum(1 for a, b in zip(g_text.splitlines(), b_text.splitlines()) if a != b)
        if diff_lines <= 4:
            difficulty = "easy"
        elif diff_lines <= 18:
            difficulty = "medium"
        else:
            difficulty = "hard"

        multifile_hint = (
            len(b_text.splitlines()) <= 8
            and b_text.strip().startswith("from ")
            and "\n\n" not in b_text[:200]
        )
        tags = ["local_fixture", "synthetic", "dataset_scan"]
        if multifile_hint:
            tags.extend(["multifile", "facade"])

        row = {
            "allowed_paths": ["."],
            "base_commit": "dataset-fixture-v1",
            "case_id": case_id,
            "difficulty": difficulty,
            "expected_failures": expected_failures,
            "install": ["python -m pip install -q pytest"],
            "injection_patch": "--- a/target_file\n+++ b/target_file\n@@\n-replace-mode\n+replace-mode",
            "metadata": {
                "injection_mode": "replace",
                "new_content": b_text,
                "objective": f"Repair regression in dataset case {case_dir.name}: make tests green.",
                "old_content": g_text,
                "workspace_dir": ws_rel,
            },
            "python_version": "3.11",
            "regression_test_command": "python -m pytest test_buggy.py -q",
            "repo_name": "local_dataset",
            "repo_url": "local://dataset/cases",
            "seed": 5000 + int(nstr),
            "source_type": "synthetic",
            "tags": tags,
            "target_file": "buggy.py",
            "test_command": "python -m pytest test_buggy.py -q",
        }
        out.append(row)
    return out


def write_manifest(rows: List[dict], dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Build manifest from dataset/cases")
    parser.add_argument(
        "--cases-root",
        default=str(root / "dataset" / "cases"),
        help="Directory containing case_NNN folders",
    )
    parser.add_argument(
        "--output",
        default=str(root / "benchmark" / "manifests" / "dataset_full_52.jsonl"),
        help="Output JSONL path",
    )
    args = parser.parse_args()

    rows = build_rows(Path(args.cases_root))
    dest = Path(args.output).resolve()
    write_manifest(rows, dest)
    from benchmark.manifest import load_manifest

    load_manifest(str(dest))

    print(f"[build_dataset_manifest] wrote {len(rows)} rows to {dest}")


if __name__ == "__main__":
    main()
