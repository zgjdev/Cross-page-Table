import pytest

from cptla.reconstruction.grid import GridError, html_to_grid
from cptla.reconstruction.grid_sequence import html_to_sequence, sequence_to_grid, sequence_to_html


def test_roundtrip_text_span_role():
    html = '<table><tr><th colspan="2">A&amp;B</th></tr><tr><td>x<br>y</td><td></td></tr></table>'
    text = html_to_sequence(html)
    assert sequence_to_grid(text) == html_to_grid(html)
    assert html_to_grid(sequence_to_html(text)) == html_to_grid(html)
    assert html_to_sequence(sequence_to_html(text)) == text


@pytest.mark.parametrize(
    "value",
    [
        '{"x":1,"x":2}',
        '{"x":NaN}',
        "```json\n{}\n```",
        '{"schema_version":"global-grid-v1","num_rows":1,"num_cols":1,"cells":[]}',
        '{"schema_version":"global-grid-v1","num_rows":true,"num_cols":1,"cells":[]}',
    ],
)
def test_reject_invalid(value):
    with pytest.raises(GridError):
        sequence_to_grid(value)
