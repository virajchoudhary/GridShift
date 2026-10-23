"""Atomic, content-addressed research artifacts."""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def json_bytes(value) -> bytes:
    return json.dumps(value, indent=2, sort_keys=True, default=str, allow_nan=False).encode()


def software_digest(root):
    source = Path(root) / "src/gridshift"
    scientific_modules = {
        "artifacts.py", "data.py", "domain.py", "forecasting.py", "baselines.py",
        "scheduling.py", "evaluation.py", "replay.py", "study.py", "cli.py",
        "sensitivities.py", "results.py", "analysis.py", "live.py",
    }
    payload = b"".join(p.name.encode() + p.read_bytes() for p in sorted(source.glob("*.py"))
                       if p.name in scientific_modules)
    runner = Path(root) / "scripts/run_research.py"
    if runner.exists():
        payload += b"scripts/run_research.py" + runner.read_bytes()
    return digest(payload)


def atomic_bytes(path, payload: bytes):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def write_json(path, value):
    atomic_bytes(path, json_bytes(value))


def log(root, phase, decision, why, evidence, result):
    cells = [datetime.now(timezone.utc).isoformat(), phase, decision, why, str(evidence), result]
    cells = [str(cell).replace("\t", " ").replace("\n", " ") for cell in cells]
    cells = ["'" + cell if cell.startswith(("=", "+", "-", "@")) else cell for cell in cells]
    path = Path(root) / "decisions.tsv"
    if not path.exists():
        path.write_text("ts\tphase\tdecision\twhy\tevidence\tresult\n", encoding="utf-8")
    with path.open("a", encoding="utf-8") as stream:
        stream.write("\t".join(cells) + "\n")


def freeze_protocol(root, protocol):
    root = Path(root)
    manifest = json.loads((root / "data/manifest.json").read_text())
    document = {
        "schema_version": 1,
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_hash": manifest["normalized_hash"],
        "protocol": protocol,
        "test_period": ["2025-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        "provider_historical_forecast_used": False,
    }
    document["protocol_hash"] = digest(json_bytes(document["protocol"]))
    path = root / "artifacts/protocol_freeze.json"
    if path.exists():
        existing = json.loads(path.read_text())
        if existing["data_hash"] != document["data_hash"] or existing["protocol_hash"] != document["protocol_hash"]:
            raise ValueError("A frozen protocol already exists with different inputs")
        return existing
    write_json(path, document)
    log(root, "freeze", "Seal validation-selected protocol before test execution",
        "Prevent test-driven model or policy choices", path, "FROZEN")
    return document


def require_freeze(root, config=None):
    root = Path(root)
    path = root / "artifacts/protocol_freeze.json"
    if not path.exists():
        raise ValueError("The 2025 test is locked until validation is frozen")
    document = json.loads(path.read_text())
    manifest = json.loads((root / "data/manifest.json").read_text())
    if document["data_hash"] != manifest["normalized_hash"]:
        raise ValueError("Dataset changed after protocol freeze")
    normalized = root / "data/normalized/carbon.parquet"
    if not normalized.exists() or digest(normalized.read_bytes()) != document["data_hash"]:
        raise ValueError("Dataset bytes changed after protocol freeze")
    if document["protocol_hash"] != digest(json_bytes(document["protocol"])):
        raise ValueError("Frozen protocol was modified")
    if document["protocol"].get("software_hash") != software_digest(root):
        raise ValueError("Software changed after protocol freeze")
    if config is not None and document["protocol"].get("config") != config:
        raise ValueError("Configuration differs from frozen protocol")
    amendments_hash = document["protocol"].get("protocol_amendments_hash")
    if amendments_hash is not None and digest((root / "PROTOCOL_AMENDMENTS.md").read_bytes()) != amendments_hash:
        raise ValueError("Protocol amendments changed after freeze")
    for filename, expected in document["protocol"].get("validation_artifact_hashes", {}).items():
        path = (root / filename).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file() or digest(path.read_bytes()) != expected:
            raise ValueError("Validation artifact changed after protocol freeze")
    return document


def authorize_period(series, start, end, *, experiment_root=None, synthetic=False):
    from .domain import utc
    start, end = utc(start), utc(end)
    if synthetic:
        if series.attrs.get("gridshift_source") == "NESO":
            raise ValueError("Official data cannot be marked as a synthetic fixture")
        return None
    if start < utc("2026-01-01T00:00Z") and end > utc("2025-01-01T00:00Z"):
        if experiment_root is None:
            raise ValueError("The 2025 test is locked; a compatible frozen project is required")
        frozen = require_freeze(experiment_root)
        import numpy as np
        import pandas as pd
        expected = pd.read_parquet(Path(experiment_root) / "data/normalized/carbon.parquet").actual
        if (
            not series.index.equals(expected.index)
            or not np.array_equal(series.to_numpy(dtype=float),
                                  expected.reindex(series.index).to_numpy(dtype=float), equal_nan=True)
        ):
            raise ValueError("Submitted test series differs from frozen source values")
        return frozen
    return None
