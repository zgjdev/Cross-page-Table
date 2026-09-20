from pathlib import Path


def test_data_ignore_rule_is_anchored_to_repository_root() -> None:
    rules = Path(".gitignore").read_text(encoding="utf-8").splitlines()

    assert "/data/" in rules
    assert "data/" not in rules
