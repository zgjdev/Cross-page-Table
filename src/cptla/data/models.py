from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class BBox(StrictModel):
    x0: float = Field(ge=0.0, le=1.0)
    y0: float = Field(ge=0.0, le=1.0)
    x1: float = Field(ge=0.0, le=1.0)
    y1: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_order(self) -> BBox:
        if self.x0 >= self.x1 or self.y0 >= self.y1:
            raise ValueError("bbox coordinates must be ordered")
        return self


class Word(StrictModel):
    page: int = Field(ge=0)
    text: str = Field(min_length=1)
    bbox: BBox


class Cell(StrictModel):
    cell_id: str = Field(min_length=1)
    row: int = Field(ge=0)
    column: int = Field(ge=0)
    row_span: int = Field(default=1, ge=1)
    column_span: int = Field(default=1, ge=1)
    text: str
    is_header: bool = False
    word_indices: tuple[int, ...] = ()


class TableFragment(StrictModel):
    fragment_id: str = Field(min_length=1)
    table_id: str = Field(min_length=1)
    page: int = Field(ge=0)
    bbox: BBox


class LogicalTable(StrictModel):
    table_id: str = Field(min_length=1)
    cells: list[Cell]
    fragments: list[TableFragment]


class DocumentRecord(StrictModel):
    document_id: str = Field(min_length=1)
    source_split: Literal["train", "validation", "test", "hidden_test"]
    journal_id: str | None = None
    page_count: int = Field(ge=1)
    words: list[Word]
    tables: list[LogicalTable]
