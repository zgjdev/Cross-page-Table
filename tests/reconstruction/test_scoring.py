import pytest

from cptla.reconstruction.scoring import score_groups


def row(html="<table><tr><td>A</td><td></td></tr></table>", pages=None, group="g"):
    return {"group_id": group, "html": html, "source_pages": [0, 2] if pages is None else pages}


def test_correct_and_source_order():
    result = score_groups([row()], [row(pages=[2, 0])])
    assert result["n_targets"] == 1
    assert result["diagnostic_rates"]["source_joint_exact"] == 1


def test_wrong_source_extra_and_missing():
    result = score_groups([row(), row(group="missing")], [row(pages=[0]), row(group="extra")])
    assert result["extra_prediction_count"] == 1
    assert result["diagnostic_rates"]["con_exact"] == 0.5
    assert result["diagnostic_rates"]["source_joint_exact"] == 0
    assert result["per_group"][1]["failure_reason"] == "missing_prediction"


@pytest.mark.parametrize(
    "html",
    [
        "<table><tr><td>A",
        "<table></table>",
        '<table><tr><td colspan="999999999">A</td></tr></table>',
        "<table><tr><td>A</td></tr></table>" * 2,
    ],
)
def test_bad_prediction_fails(html):
    result = score_groups([row()], [row(html)])
    assert result["diagnostic_rates"]["joint_exact"] == 0
    assert result["per_group"][0]["failure_reason"] == "invalid_html"


def test_duplicate_predictions_never_choose_best():
    result = score_groups([row()], [row(), row()])
    assert result["diagnostic_rates"]["con_exact"] == 0
    assert result["per_group"][0]["failure_reason"] == "multiple_predictions"


def test_content_and_topology_are_separate():
    target = row('<table><tr><td colspan="2">A</td></tr></table>')
    pred = row("<table><tr><td>A</td><td>A</td></tr></table>")
    rates = score_groups([target], [pred])["diagnostic_rates"]
    assert rates["con_exact"] == 1 and rates["top_exact"] == 0
    rates = score_groups([row()], [row("<table><tr><th>B</th><td></td></tr></table>")])[
        "diagnostic_rates"
    ]
    assert rates["top_exact"] == 1 and rates["con_exact"] == 0


def test_no_whitespace_normalization():
    rates = score_groups([row()], [row("<table><tr><td> A</td><td></td></tr></table>")])[
        "diagnostic_rates"
    ]
    assert rates["con_exact"] == 0


@pytest.mark.parametrize("pages", [[0, 0], [-1], [True], [1.5], [], "0"])
def test_invalid_target_source_is_contract_error(pages):
    with pytest.raises(ValueError):
        score_groups([row(pages=pages)], [])


def test_bad_targets_are_errors():
    for targets in ([row(), row()], [row("broken")], [row(group="")]):
        with pytest.raises(ValueError):
            score_groups(targets, [])


def test_invalid_prediction_source_fails_and_empty_denominator():
    result = score_groups([row()], [row(pages=[True])])
    assert result["diagnostic_rates"]["joint_exact"] == 0
    assert result["per_group"][0]["failure_reason"] == "invalid_source_pages"
    assert score_groups([], [])["diagnostic_rates"]["con_exact"] is None
