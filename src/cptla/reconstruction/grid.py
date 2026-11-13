"""独立规范网格 v1；半开区间，原样保留文本，不修补预测缺格。

仅接受完整的单个 table，可有完整 html/body 纯包装。td/th 可在下一 cell 或 tr 结束时省略闭合；
其他结构须显式闭合。thead 的 td 也标记 header。行组本身不进入网格。
仅保留内联元素的文本，br 为换行；不支持的标签明确报错。
"""

from dataclasses import dataclass
from html import escape
from html.parser import HTMLParser

GRID_VERSION = "cptla-grid-v1"
MAX_HTML_CHARS = 2_000_000
MAX_ROWS = 10_000
MAX_COLS = 1_024
MAX_POSITIONS = 100_000


def _check_limits(rows, cols):
    if rows > MAX_ROWS or cols > MAX_COLS or rows * cols > MAX_POSITIONS:
        raise GridError("grid resource limit exceeded")


class GridError(ValueError):
    """输入不满足规范网格契约。"""


@dataclass(frozen=True)
class Cell:
    row_start: int
    row_end: int
    col_start: int
    col_end: int
    text: str
    header: bool = False


@dataclass(frozen=True)
class Grid:
    n_rows: int
    n_cols: int
    cells: tuple[Cell, ...]
    version: str = GRID_VERSION

    def __post_init__(self):
        if self.version != GRID_VERSION:
            raise GridError("unsupported grid version")
        if any(type(v) is not int or v <= 0 for v in (self.n_rows, self.n_cols)):
            raise GridError("grid dimensions must be positive integers")
        _check_limits(self.n_rows, self.n_cols)
        occupied = set()
        for c in self.cells:
            if not isinstance(c, Cell) or any(
                type(v) is not int for v in (c.row_start, c.row_end, c.col_start, c.col_end)
            ):
                raise GridError("invalid cell coordinates")
            if not (
                0 <= c.row_start < c.row_end <= self.n_rows
                and 0 <= c.col_start < c.col_end <= self.n_cols
            ):
                raise GridError("cell outside grid")
            if not isinstance(c.text, str) or type(c.header) is not bool:
                raise GridError("invalid text/header")
            for r in range(c.row_start, c.row_end):
                for col in range(c.col_start, c.col_end):
                    if (r, col) in occupied:
                        raise GridError("overlapping cells")
                    occupied.add((r, col))
        if len(occupied) != self.n_rows * self.n_cols:
            raise GridError("uncovered grid positions")
        object.__setattr__(
            self, "cells", tuple(sorted(self.cells, key=lambda c: (c.row_start, c.col_start)))
        )


class _Parser(HTMLParser):
    inline = {"b", "i", "em", "strong", "span", "sup", "sub", "u", "s", "a", "code"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.cells = []
        self.current = None
        self.parts = []
        self.rows = 0
        self.seen = False
        self.finished = False
        self.max_right = 0
        self.max_bottom = 0
        self.wrappers = set()

    def finish_cell(self):
        if self.current is not None:
            if self.stack[-1] not in ("td", "th"):
                raise GridError("unclosed inline element")
            self.stack.pop()
            r, end, col, right, header = self.current
            self.cells.append(Cell(r, end, col, right, "".join(self.parts), header))
            self.current = None
            self.parts = []

    def handle_starttag(self, tag, attrs):
        parent = self.stack[-1] if self.stack else None
        if tag in ("html", "body"):
            valid_parent = parent is None if tag == "html" else parent in (None, "html")
            if self.seen or tag in self.wrappers or not valid_parent:
                raise GridError("invalid document wrapper")
            self.wrappers.add(tag)
        elif tag == "table":
            if self.seen or parent not in (None, "html", "body"):
                raise GridError("multiple or nested tables")
            self.seen = True
        elif tag in ("thead", "tbody", "tfoot"):
            if parent != "table":
                raise GridError("invalid row group")
        elif tag == "tr":
            if parent not in ("table", "thead", "tbody", "tfoot"):
                raise GridError("invalid row")
            self.rows += 1
            _check_limits(self.rows, self.max_right)
        elif tag in ("td", "th"):
            self.finish_cell()
            if not self.stack or self.stack[-1] != "tr":
                raise GridError("cell outside row")
            spans = {"rowspan": 1, "colspan": 1}
            seen = set()
            for key, value in attrs:
                if key in spans:
                    if key in seen or value is None or not value.isascii() or not value.isdigit():
                        raise GridError("invalid span")
                    digits = value.lstrip("0")
                    if len(digits) > 5:
                        raise GridError("span resource limit exceeded")
                    spans[key] = int(digits or "0")
                    if spans[key] <= 0:
                        raise GridError("invalid span")
                    seen.add(key)
            row = self.rows - 1
            _check_limits(row + spans["rowspan"], spans["colspan"])
            col = 0
            while any(
                c.row_start <= row < c.row_end and c.col_start <= col < c.col_end
                for c in self.cells
            ):
                col += 1
                _check_limits(row + spans["rowspan"], col + spans["colspan"])
            self.max_right = max(self.max_right, col + spans["colspan"])
            self.max_bottom = max(self.max_bottom, row + spans["rowspan"])
            _check_limits(self.max_bottom, self.max_right)
            self.current = (
                row,
                row + spans["rowspan"],
                col,
                col + spans["colspan"],
                tag == "th" or "thead" in self.stack,
            )
        elif tag == "br":
            if self.current is None:
                raise GridError("br outside cell")
            self.parts.append("\n")
            return
        elif tag in self.inline:
            if self.current is None:
                raise GridError("inline outside cell")
        else:
            raise GridError(f"unsupported tag: {tag}")
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in ("html", "body") and not self.finished:
            raise GridError("document wrapper must contain complete table")
        if tag == "tr":
            self.finish_cell()
        if tag in ("td", "th"):
            if not self.stack or self.stack[-1] != tag:
                raise GridError("mismatched cell closure")
            self.finish_cell()
            return
        if not self.stack or self.stack[-1] != tag:
            raise GridError(f"mismatched closure: {tag}")
        self.stack.pop()
        if tag == "table":
            self.finished = True

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag != "br":
            self.handle_endtag(tag)

    def handle_data(self, data):
        if self.current is not None:
            self.parts.append(data)
        elif data.strip():
            raise GridError("text outside cell")

    def handle_decl(self, decl):
        raise GridError("unsupported declaration")

    def handle_pi(self, data):
        raise GridError("unsupported processing instruction")


def html_to_grid(html: str) -> Grid:
    """解析完整单表 HTML；所有失败显式抛出 GridError。"""
    if not isinstance(html, str):
        raise GridError("HTML must be a string")
    if len(html) > MAX_HTML_CHARS:
        raise GridError("HTML resource limit exceeded")
    parser = _Parser()
    parser.feed(html)
    parser.close()
    if not parser.finished or parser.stack or not parser.cells:
        raise GridError("incomplete or empty table")
    return Grid(parser.rows, max(c.col_end for c in parser.cells), tuple(parser.cells))


def grid_to_html(grid: Grid) -> str:
    """序列化规范网格；header 写为 th，换行写为 br。"""
    parts = ["<table>"]
    for row in range(grid.n_rows):
        parts.append("<tr>")
        for c in grid.cells:
            if c.row_start != row:
                continue
            tag = "th" if c.header else "td"
            parts.append(
                f'<{tag} rowspan="{c.row_end - c.row_start}" colspan="{c.col_end - c.col_start}">'
            )
            parts.append(escape(c.text).replace("\n", "<br>"))
            parts.append(f"</{tag}>")
        parts.append("</tr>")
    parts.append("</table>")
    return "".join(parts)
