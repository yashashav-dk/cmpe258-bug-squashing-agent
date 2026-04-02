import json
import os
from datetime import datetime, timezone


class Logger:
    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def log(self, event: str, case_id: str, data: dict) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "case_id": case_id,
            "data": data,
        }
        with open(self.path, "a") as f:
            f.write(json.dumps(record) + "\n")
