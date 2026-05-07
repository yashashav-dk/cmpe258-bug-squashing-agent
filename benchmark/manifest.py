import hashlib
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


ALLOWED_SOURCE_TYPES = {"historical", "synthetic"}
ALLOWED_DIFFICULTY = {"easy", "medium", "hard"}


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    source_type: str
    repo_url: str
    repo_name: str
    base_commit: str
    python_version: str
    install: List[str]
    test_command: str
    regression_test_command: Optional[str]
    allowed_paths: List[str]
    target_file: str
    injection_patch: str
    expected_failures: List[str]
    tags: List[str]
    difficulty: str
    seed: int
    metadata: Dict[str, Any]

    def content_hash(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def benchmark_case_schema() -> Dict[str, Any]:
    return {
        "required": {
            "case_id": str,
            "source_type": str,
            "repo_url": str,
            "repo_name": str,
            "base_commit": str,
            "python_version": str,
            "install": list,
            "test_command": str,
            "allowed_paths": list,
            "target_file": str,
            "injection_patch": str,
            "expected_failures": list,
            "tags": list,
            "difficulty": str,
            "seed": int,
            "metadata": dict,
        },
        "optional": {"regression_test_command": (str, type(None))},
    }


def _validate_non_empty_string(value: Any, key: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key!r} must be a non-empty string")


def _validate_string_list(value: Any, key: str) -> None:
    if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
        raise ValueError(f"{key!r} must be a list of non-empty strings")


def validate_case_payload(payload: Dict[str, Any]) -> None:
    schema = benchmark_case_schema()
    required = schema["required"]
    optional = schema["optional"]

    for key, expected_type in required.items():
        if key not in payload:
            raise ValueError(f"Missing required key: {key}")
        if not isinstance(payload[key], expected_type):
            raise ValueError(f"Invalid type for {key!r}: expected {expected_type}, got {type(payload[key])}")

    for key, expected_type in optional.items():
        if key in payload and not isinstance(payload[key], expected_type):
            raise ValueError(f"Invalid type for optional {key!r}: expected {expected_type}, got {type(payload[key])}")

    _validate_non_empty_string(payload["case_id"], "case_id")
    _validate_non_empty_string(payload["repo_url"], "repo_url")
    _validate_non_empty_string(payload["repo_name"], "repo_name")
    _validate_non_empty_string(payload["base_commit"], "base_commit")
    _validate_non_empty_string(payload["test_command"], "test_command")
    _validate_non_empty_string(payload["target_file"], "target_file")
    _validate_non_empty_string(payload["injection_patch"], "injection_patch")
    _validate_string_list(payload["install"], "install")
    _validate_string_list(payload["allowed_paths"], "allowed_paths")
    _validate_string_list(payload["expected_failures"], "expected_failures")
    _validate_string_list(payload["tags"], "tags")

    source_type = payload["source_type"]
    if source_type not in ALLOWED_SOURCE_TYPES:
        raise ValueError(f"source_type must be one of {sorted(ALLOWED_SOURCE_TYPES)}")

    difficulty = payload["difficulty"]
    if difficulty not in ALLOWED_DIFFICULTY:
        raise ValueError(f"difficulty must be one of {sorted(ALLOWED_DIFFICULTY)}")

    seed = payload["seed"]
    if seed < 0:
        raise ValueError("seed must be >= 0")


def case_from_payload(payload: Dict[str, Any]) -> BenchmarkCase:
    validate_case_payload(payload)
    return BenchmarkCase(
        case_id=payload["case_id"],
        source_type=payload["source_type"],
        repo_url=payload["repo_url"],
        repo_name=payload["repo_name"],
        base_commit=payload["base_commit"],
        python_version=payload["python_version"],
        install=payload["install"],
        test_command=payload["test_command"],
        regression_test_command=payload.get("regression_test_command"),
        allowed_paths=payload["allowed_paths"],
        target_file=payload["target_file"],
        injection_patch=payload["injection_patch"],
        expected_failures=payload["expected_failures"],
        tags=payload["tags"],
        difficulty=payload["difficulty"],
        seed=payload["seed"],
        metadata=payload["metadata"],
    )


def load_manifest(path: str) -> List[BenchmarkCase]:
    records: List[BenchmarkCase] = []
    manifest_path = Path(path)
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest file not found: {path}")

    with manifest_path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
                records.append(case_from_payload(payload))
            except Exception as exc:
                raise ValueError(f"Manifest parse error at line {line_no}: {exc}") from exc
    return records


def write_manifest(path: str, cases: Iterable[BenchmarkCase]) -> None:
    manifest_path = Path(path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8") as handle:
        for case in cases:
            handle.write(json.dumps(asdict(case), sort_keys=True) + "\n")
