import json
from pathlib import Path
from typing import Any, Dict, List

from benchmark.adapters.base import SourceAdapter
from benchmark.manifest import BenchmarkCase, case_from_payload


class HistoricalBugAdapter(SourceAdapter):
    """
    Converts curated historical bug metadata into normalized benchmark cases.

    Input format is JSONL where each row includes at minimum the fields required
    by `case_from_payload(...)`. This keeps historical ingestion deterministic and
    easy to audit.
    """

    def __init__(self, source_path: str):
        self.source_path = Path(source_path)

    def _load_rows(self) -> List[Dict[str, Any]]:
        if not self.source_path.exists():
            raise FileNotFoundError(f"Historical source not found: {self.source_path}")
        rows: List[Dict[str, Any]] = []
        with self.source_path.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    row = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSON in {self.source_path} at line {line_no}: {exc}"
                    ) from exc
                rows.append(row)
        return rows

    def build_cases(self) -> List[BenchmarkCase]:
        return [case_from_payload(row) for row in self._load_rows()]
