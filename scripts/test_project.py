"""Run offline tests and bind the passing receipt to the tested source bytes."""

import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

from gridshift.artifacts import digest, software_digest, write_json


def main():
    root = Path(__file__).resolve().parents[1]
    before = software_digest(root)
    xml = root / "artifacts/tests/core.xml"
    xml.parent.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment.update(OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", OMP_NUM_THREADS="1")
    result = subprocess.run(
        [sys.executable, "-W", "ignore::DeprecationWarning", "-m", "pytest",
         "tests", "-q", f"--junitxml={xml}"],
        cwd=root, env=environment,
    )
    after = software_digest(root)
    if result.returncode or before != after:
        raise SystemExit("Tests failed or scientific source changed during the test run")
    suites = ET.parse(xml).getroot().findall(".//testsuite")
    write_json(root / "artifacts/tests/core_receipt.json", {
        "passed": True, "software_hash": after, "junit_sha256": digest(xml.read_bytes()),
        "tests": sum(int(s.get("tests", 0)) for s in suites),
        "failures": sum(int(s.get("failures", 0)) for s in suites),
        "errors": sum(int(s.get("errors", 0)) for s in suites),
    })


if __name__ == "__main__":
    main()
