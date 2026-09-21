import pytest

from cptla.evaluation.dotsocr import extract_table_html, parse_layout


def test_parse_layout_accepts_direct_json_list() -> None:
    assert parse_layout('[{"category":"Text","text":"hello"}]') == [
        {"category": "Text", "text": "hello"}
    ]


def test_parse_layout_accepts_fenced_wrapped_object() -> None:
    raw = '```json\n{"layouts":[{"category":"Table","text":"<table></table>"}]}\n```'

    assert parse_layout(raw) == [{"category": "Table", "text": "<table></table>"}]


def test_parse_layout_repairs_common_json_damage() -> None:
    raw = "{'elements': [{'category': 'Text', 'text': 'hello',}],}"

    assert parse_layout(raw) == [{"category": "Text", "text": "hello"}]


def test_parse_layout_rejects_scalar() -> None:
    with pytest.raises(ValueError, match="object or a list"):
        parse_layout('"not a layout"')


def test_extract_table_html_returns_only_valid_table_elements() -> None:
    raw = (
        '[{"category":"Text","text":"ignore"},'
        '{"category":"Table","text":"<table><tr><td>A</td></tr></table>"}]'
    )

    tables, warnings = extract_table_html(raw)

    assert tables == ["<table><tr><td>A</td></tr></table>"]
    assert warnings == []


def test_extract_table_html_reports_invalid_table_html() -> None:
    raw = '[{"category":"Table","text":"<table><tr><td>A"}]'

    tables, warnings = extract_table_html(raw)

    assert tables == []
    assert warnings == ["invalid_table_html:0"]
