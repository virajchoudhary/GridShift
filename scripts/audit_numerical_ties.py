"""Recompute every isolated minimum against the current numerical tie contract."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from gridshift.artifacts import digest, software_digest, write_json
from gridshift.data import load
from gridshift.scheduling import earliest_minimum
from gridshift.study import run_dir


def main():
    root = Path(".").resolve()
    config = yaml.safe_load((root / "configs/study.yaml").read_text())
    run = run_dir(root, config, "validation")
    truth = load(root).actual
    decisions = pd.read_parquet(run / "single_job/primary_decisions.parquet")
    mapping = json.loads((run / "forecast_store.json").read_text())
    stores = {}
    for name, relative in mapping.items():
        with np.load(root / relative) as data:
            stores[name] = (data["origins_ns"].copy(), data["mean"].copy())
    mismatches = []
    inspected = 0
    for row in decisions.loc[(decisions.policy == "oracle") | (decisions.policy == "forecast")].itertuples():
        slots = int(np.ceil(row.duration_hours * 2))
        starts = int((row.deadline - row.release).total_seconds() / 1800) - slots + 1
        energy = np.minimum(.5, np.maximum(0, row.duration_hours - np.arange(slots) * .5)) * row.power_kw * row.pue
        if row.policy == "oracle":
            values = truth.reindex(pd.date_range(row.release, row.deadline, freq="30min", inclusive="left")).to_numpy(float)
        else:
            origins, paths = stores[row.model_id]
            index = np.searchsorted(origins, row.release.value)
            if index == len(origins) or origins[index] != row.release.value:
                continue
            values = np.maximum(paths[index].astype(float), 0)
        costs = np.correlate(values, energy, mode="valid")[:starts]
        expected = earliest_minimum(costs)
        actual = int((row.start - row.release).total_seconds() / 1800)
        inspected += 1
        if actual != expected:
            mismatches.append({"job_id": row.job_id, "model_id": row.model_id,
                               "saved_offset": actual, "expected_offset": expected})
    receipt = {
        "passed": not mismatches, "inspected_minimum_decisions": inspected,
        "mismatches": mismatches[:20], "mismatch_count": len(mismatches),
        "software_hash": software_digest(root),
        "decision_sha256": digest((run / "single_job/primary_decisions.parquet").read_bytes()),
        "scope": "All saved validation oracle and forecast starts recomputed with the current shared tie rule",
    }
    write_json(root / "artifacts/tests/numerical_ties.json", receipt)
    print(receipt)
    if mismatches:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
