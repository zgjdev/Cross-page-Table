import pytest
from pydantic import ValidationError

from cptla.data.models import BBox, Cell, DocumentRecord, LogicalTable, TableFragment, Word


def test_document_round_trip() -> None:
    record = DocumentRecord(
        document_id="doc-1",
        source_split="train",
        journal_id="journal-a",
        page_count=2,
        words=[Word(page=0, text="Age", bbox=BBox(x0=0.1, y0=0.1, x1=0.2, y1=0.2))],
        tables=[
            LogicalTable(
                table_id="table-1",
                cells=[Cell(cell_id="c1", row=0, column=0, text="Age")],
                fragments=[
                    TableFragment(
                        fragment_id="f1",
                        table_id="table-1",
                        page=0,
                        bbox=BBox(x0=0.05, y0=0.1, x1=0.95, y1=0.95),
                    )
                ],
            )
        ],
    )

    assert DocumentRecord.model_validate_json(record.model_dump_json()) == record


def test_bbox_rejects_inverted_coordinates() -> None:
    with pytest.raises(ValidationError):
        BBox(x0=0.8, y0=0.1, x1=0.2, y1=0.5)
