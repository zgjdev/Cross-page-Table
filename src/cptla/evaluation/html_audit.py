"""Read-only syntax diagnostics; candidate conversions never become predictions."""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from collections import Counter
from html.parser import HTMLParser

VOID = frozenset("area base br col embed hr img input link meta param source track wbr".split())
TOKEN = re.compile(r"<!--[\s\S]*?-->|<[^>]*>|&(?:#[xX][0-9a-fA-F]+|#\d+|[A-Za-z]\w*);|&")


class _Structure(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.stack = []
        self.tags = Counter()
        self.issues = []

    def handle_starttag(self, tag, attrs):
        self.tags[tag] += 1
        if tag not in VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.tags[tag] += 1

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.issues.append(f"unexpected_close:{tag}")
        if tag in self.stack:
            while self.stack.pop() != tag:
                pass


def _lexical_candidate(value: str) -> str:
    """Probe XML spelling compatibility only; do not infer missing rows/cells."""

    def replace(match):
        token = match.group()
        if token.startswith("<"):
            name = re.match(r"<([A-Za-z]+)(?:\s|/?>)", token)
            if name and name[1].lower() in VOID and not token.endswith("/>"):
                return token[:-1] + "/>"
            return token
        if token == "&":
            return "&amp;"
        decoded = html.unescape(token)
        return html.escape(decoded, quote=False) if decoded != token else token

    return TOKEN.sub(replace, value)


def diagnose_html(value) -> dict:
    if not isinstance(value, str):
        return {"input_type": type(value).__name__, "xml_ok": False, "lexical_xml_ok": False}
    result = {"input_type": "str", "characters": len(value)}
    try:
        ET.fromstring(value)
        result.update(xml_ok=True, xml_error=None)
    except ET.ParseError as error:
        result.update(xml_ok=False, xml_error=str(error).split(": line")[0])
    structure = _Structure()
    try:
        structure.feed(value)
        structure.close()
    except (ValueError, AssertionError) as error:
        structure.issues.append(f"html_parser:{type(error).__name__}")
    result.update(
        tags=dict(structure.tags),
        table_count=structure.tags["table"],
        cell_count=structure.tags["td"] + structure.tags["th"],
        structural_issues=structure.issues + [f"unclosed:{tag}" for tag in structure.stack],
    )
    try:
        ET.fromstring(_lexical_candidate(value))
        result["lexical_xml_ok"] = True
    except ET.ParseError:
        result["lexical_xml_ok"] = False
    return result
