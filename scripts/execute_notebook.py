"""Re-execute a copy with this interpreter, preserving published academic files."""

import shutil
import tempfile
from pathlib import Path

from gridshift.exports import _execute_notebook


def main():
    root = Path(__file__).resolve().parents[1]
    source = root / "notebooks/01_gridshift_study.ipynb"
    if not source.is_file():
        raise FileNotFoundError("Generate the verified academic exports first")
    directory = root / "tmp"
    directory.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="gridshift-notebook-rerun-", dir=directory) as name:
        work = Path(name)
        notebook = work / source.name
        shutil.copy2(source, notebook)
        html = _execute_notebook(root, notebook, work)
        destination = directory / "notebook_reexecuted"
        destination.mkdir(exist_ok=True)
        for file in (notebook, html):
            shutil.copy2(file, destination / file.name)
        print(destination)


if __name__ == "__main__":
    main()
