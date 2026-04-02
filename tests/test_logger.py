import json
import os
import tempfile
from logger import Logger


def test_logger_writes_jsonlines():
    with tempfile.NamedTemporaryFile(mode="r", suffix=".jsonl", delete=False) as f:
        log_path = f.name

    try:
        logger = Logger(log_path)
        logger.log(event="test_event", case_id="case_001", data={"key": "value"})

        with open(log_path) as f:
            line = f.readline()
        record = json.loads(line)

        assert record["event"] == "test_event"
        assert record["case_id"] == "case_001"
        assert record["data"] == {"key": "value"}
        assert "timestamp" in record
    finally:
        os.unlink(log_path)


def test_logger_appends_multiple_lines():
    with tempfile.NamedTemporaryFile(mode="r", suffix=".jsonl", delete=False) as f:
        log_path = f.name

    try:
        logger = Logger(log_path)
        logger.log(event="e1", case_id="c1", data={})
        logger.log(event="e2", case_id="c1", data={})

        with open(log_path) as f:
            lines = f.readlines()

        assert len(lines) == 2
        assert json.loads(lines[0])["event"] == "e1"
        assert json.loads(lines[1])["event"] == "e2"
    finally:
        os.unlink(log_path)
