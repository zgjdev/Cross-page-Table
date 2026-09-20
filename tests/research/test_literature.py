from pathlib import Path


def test_rejects_missing_evidence_fields(tmp_path: Path) -> None:
    from cptla.research.literature import validate_literature_csv

    csv_path = tmp_path / "papers.csv"
    csv_path.write_text("paper_id,title,year\np1,Example,2026\n", encoding="utf-8")

    errors = validate_literature_csv(csv_path)

    assert "missing columns" in errors[0]


def test_accepts_complete_seed_row(tmp_path: Path) -> None:
    from cptla.research.literature import validate_literature_csv

    csv_path = tmp_path / "papers.csv"
    csv_path.write_text(
        "paper_id,title,year,venue,url,task,data,context,modality,method,metrics,code,status,notes\n"
        "smock2026pubtablesv2,PubTables-v2,2026,arXiv,"
        "https://arxiv.org/abs/2512.10888,table extraction,PubTables-v2,document,"
        "vision+text,VLM and classifiers,GriTS+TEDS,"
        "https://huggingface.co/datasets/kensho/PubTables-v2,read,primary dataset\n",
        encoding="utf-8",
    )

    assert validate_literature_csv(csv_path) == []
