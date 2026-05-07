import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

from benchmark.adapters.base import SourceAdapter
from benchmark.manifest import BenchmarkCase


@dataclass(frozen=True)
class MutationOperator:
    name: str
    old: str
    new: str
    difficulty: str
    tags: List[str]


DEFAULT_MUTATIONS = [
    MutationOperator(
        name="flip_comparator_gt_to_lt",
        old=" > ",
        new=" < ",
        difficulty="medium",
        tags=["logic", "comparator"],
    ),
    MutationOperator(
        name="flip_comparator_lt_to_gt",
        old=" < ",
        new=" > ",
        difficulty="medium",
        tags=["logic", "comparator"],
    ),
    MutationOperator(
        name="off_by_one_minus",
        old=" + 1",
        new=" - 1",
        difficulty="easy",
        tags=["boundary", "indexing"],
    ),
]


class SyntheticMutationAdapter(SourceAdapter):
    """
    Deterministic synthetic case generator.

    Source file is JSONL with one base template per line:
      {
        "template_id": "...",
        "repo_url": "...",
        "repo_name": "...",
        "base_commit": "...",
        "python_version": "3.11",
        "install": ["pip install -e ."],
        "test_command": "pytest tests/test_x.py -q",
        "regression_test_command": "pytest tests/test_x.py tests/test_y.py -q",
        "allowed_paths": ["src/"],
        "target_file": "src/mod.py",
        "baseline_content": "def ...",
        "expected_failures": ["tests/test_x.py::test_case"],
        "seed": 1
      }
    """

    def __init__(self, source_path: str, ratio: float = 1.0):
        self.source_path = Path(source_path)
        self.ratio = ratio

    def _load_templates(self) -> List[Dict]:
        if not self.source_path.exists():
            raise FileNotFoundError(f"Synthetic source not found: {self.source_path}")
        rows: List[Dict] = []
        with self.source_path.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    rows.append(json.loads(stripped))
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSON in {self.source_path} at line {line_no}: {exc}"
                    ) from exc
        return rows

    def _pick_operator(self, code: str, seed: int) -> MutationOperator:
        rng = random.Random(seed)
        candidates = [op for op in DEFAULT_MUTATIONS if op.old in code]
        if not candidates:
            raise ValueError("No supported mutation operator matches template baseline_content")
        return rng.choice(candidates)

    def _build_patch(self, old_content: str, new_content: str) -> str:
        if old_content == new_content:
            raise ValueError("Mutation made no change")
        return "\n".join(
            [
                "--- a/target_file",
                "+++ b/target_file",
                "@@",
                f"-{old_content}",
                f"+{new_content}",
            ]
        )

    def build_cases(self) -> List[BenchmarkCase]:
        templates = self._load_templates()
        if not templates:
            return []

        limit = max(1, int(round(len(templates) * self.ratio)))
        selected = templates[:limit]
        cases: List[BenchmarkCase] = []

        for idx, template in enumerate(selected, start=1):
            baseline = template.get("baseline_content", "")
            seed = int(template.get("seed", idx))
            op: MutationOperator
            old_content: str
            new_content: str
            mutation = template.get("mutation")
            if mutation:
                old_content = mutation["old_content"]
                new_content = mutation["new_content"]
                op = MutationOperator(
                    name=mutation.get("name", "template_declared_mutation"),
                    old=old_content,
                    new=new_content,
                    difficulty=template.get("difficulty", "medium"),
                    tags=mutation.get("tags", []),
                )
            else:
                op = self._pick_operator(baseline, seed)
                old_content = baseline
                new_content = baseline.replace(op.old, op.new, 1)
                if new_content == old_content:
                    raise ValueError(f"Mutation {op.name} made no change")
            case = BenchmarkCase(
                case_id=f"synthetic_{template['template_id']}",
                source_type="synthetic",
                repo_url=template["repo_url"],
                repo_name=template["repo_name"],
                base_commit=template["base_commit"],
                python_version=template.get("python_version", "3.11"),
                install=template["install"],
                test_command=template["test_command"],
                regression_test_command=template.get("regression_test_command"),
                allowed_paths=template["allowed_paths"],
                target_file=template["target_file"],
                injection_patch=self._build_patch(old_content, new_content),
                expected_failures=template["expected_failures"],
                tags=sorted(set(template.get("tags", []) + op.tags)),
                difficulty=template.get("difficulty", op.difficulty),
                seed=seed,
                metadata={
                    "template_id": template["template_id"],
                    "operator": op.name,
                    "workspace_dir": template.get("workspace_dir", ""),
                    "objective": template.get("objective", ""),
                },
            )
            cases.append(case)
        return cases
