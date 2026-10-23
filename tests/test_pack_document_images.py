import pymupdf as fitz
import pytest

from scripts.pack_pubtables_document_images import pack_documents


def image(path, color):
    with fitz.open() as pdf:
        page = pdf.new_page(width=80, height=120)
        fill = (1, 0, 0) if color == "red" else (0, 0, 1)
        page.draw_rect(page.rect, fill=fill)
        path.write_bytes(page.get_pixmap().tobytes("jpeg"))


def test_complete_document_image_only_pdf_and_mapping(tmp_path):
    source = tmp_path / "images"
    source.mkdir()
    image(source / "PMC1_page_1.jpg", "blue")
    image(source / "PMC1_page_0.jpg", "red")
    result = pack_documents(source, ["PMC1"], tmp_path / "new")
    assert [p["page_number"] for p in result["pages"]] == [0, 1]
    with fitz.open(tmp_path / "new/PMC1.pdf") as pdf:
        assert len(pdf) == 2
        for page in pdf:
            assert not page.get_text()
            rendered = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            assert (rendered.width, rendered.height) == (80, 120)
    assert all(p["image_sha256"] for p in result["pages"])


def test_missing_page_is_rejected_before_output(tmp_path):
    image(tmp_path / "PMC1_page_0.jpg", "red")
    image(tmp_path / "PMC1_page_2.jpg", "red")
    with pytest.raises(ValueError, match="contiguous"):
        pack_documents(tmp_path, ["PMC1"], tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_existing_outputs_are_preserved(tmp_path):
    image(tmp_path / "PMC1_page_0.jpg", "red")
    out = tmp_path / "out"
    out.mkdir()
    marker = out / "marker"
    marker.write_bytes(b"keep")
    with pytest.raises(FileExistsError):
        pack_documents(tmp_path, ["PMC1"], out)
    assert marker.read_bytes() == b"keep"
