import json

import nbformat

from gridshift.exports import _execute_notebook


def test_notebook_executes_in_a_private_kernel_prefix(tmp_path):
    notebook = nbformat.v4.new_notebook(cells=[
        nbformat.v4.new_code_cell("print('GridShift offline fixture')"),
    ])
    path = tmp_path / "fixture.ipynb"
    nbformat.write(notebook, path)
    html = _execute_notebook(tmp_path, path, tmp_path)
    executed = json.loads(path.read_text(encoding="utf-8"))
    assert executed["cells"][0]["execution_count"] == 1
    assert "GridShift offline fixture" in html.read_text(encoding="utf-8")
