import json
import tempfile
from src.orchestrator_runtime import _parse_structured_suggestion


def test_valid_suggestion_parsed_and_validated():
    text = 'SUGGESTION: {"title": "Short title", "body": "Longer text", "tags": ["idea", "perf"], "severity": "medium"}'
    obj = _parse_structured_suggestion(text)
    assert obj is not None
    assert obj["title"] == "Short title"
    assert obj["body"] == "Longer text"
    assert "tags" in obj and isinstance(obj["tags"], list)
    assert obj["severity"] == "medium"


def test_invalid_suggestion_missing_fields_rejected():
    # missing title and body
    text = 'SUGGESTION: {"tags": ["misc"]}'
    obj = _parse_structured_suggestion(text)
    assert obj is None


def test_suggestion_with_bad_tags_rejected():
    text = 'SUGGESTION: {"title": "T", "body": "B", "tags": "not-a-list"}'
    obj = _parse_structured_suggestion(text)
    assert obj is None
