import importlib.util
import json
import re
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


from gridshift import verification


def test_independent_cost_uses_partial_slot_power_and_pue():
    start = pd.Timestamp("2030-01-01T00:00:00Z")
    actuals = pd.Series(
        [100.0, 200.0],
        index=pd.date_range(start, periods=2, freq="30min"),
    )

    grams = verification._independent_cost(actuals, start, 0.75, 2.0, 1.5)

    assert grams == pytest.approx(300.0)


def test_independent_cost_rejects_missing_realized_actuals():
    start = pd.Timestamp("2030-01-01T00:00:00Z")
    actuals = pd.Series([100.0], index=pd.DatetimeIndex([start]))

    with pytest.raises(ValueError, match="missing or invalid"):
        verification._independent_cost(actuals, start, 1.0, 0.4, 1.2)


def test_reservation_check_accepts_adjacent_jobs():
    start = pd.Timestamp("2030-01-01T00:00:00Z")
    decisions = pd.DataFrame(
        [
            {
                "job_id": "a",
                "status": "scheduled",
                "release": start,
                "deadline": start + timedelta(hours=2),
                "start": start,
                "finish": start + timedelta(hours=1),
                "duration_hours": 1.0,
            },
            {
                "job_id": "b",
                "status": "scheduled",
                "release": start,
                "deadline": start + timedelta(hours=2),
                "start": start + timedelta(hours=1),
                "finish": start + timedelta(hours=2),
                "duration_hours": 1.0,
            },
        ]
    )

    assert verification._reservations(decisions) == 2


def test_reservation_check_rejects_overlapping_jobs():
    start = pd.Timestamp("2030-01-01T00:00:00Z")
    decisions = pd.DataFrame(
        [
            {
                "job_id": "a",
                "status": "scheduled",
                "release": start,
                "deadline": start + timedelta(hours=2),
                "start": start,
                "finish": start + timedelta(hours=1),
                "duration_hours": 1.0,
            },
            {
                "job_id": "b",
                "status": "scheduled",
                "release": start,
                "deadline": start + timedelta(hours=2),
                "start": start + timedelta(minutes=30),
                "finish": start + timedelta(hours=1, minutes=30),
                "duration_hours": 1.0,
            },
        ]
    )

    with pytest.raises(ValueError, match="(?i)overlap"):
        verification._reservations(decisions)


def test_forecast_archive_checks_hash_origin_grid_and_finite_bounds(tmp_path):
    path = tmp_path / "model.npz"
    origins = pd.date_range("2030-01-01T00:00:00Z", periods=2, freq="3h").asi8.astype(np.int64)
    arrays = {
        "origins_ns": origins,
        "mean": np.full((2, 4), 10.0, dtype=np.float32),
        "std": np.ones((2, 4), dtype=np.float32),
        "fallback": np.zeros(2, dtype=bool),
        "lower95": np.full((2, 4), 7.0, dtype=np.float32),
        "lower80": np.full((2, 4), 8.0, dtype=np.float32),
        "upper80": np.full((2, 4), 12.0, dtype=np.float32),
        "upper95": np.full((2, 4), 13.0, dtype=np.float32),
    }
    np.savez_compressed(path, **arrays)
    sidecar = path.with_suffix(".json")
    sidecar.write_text(
        json.dumps({"forecast_sha256": verification._file_hash(path), "origin_count": 2}),
        encoding="utf-8",
    )

    result = verification._forecast_file(path, tmp_path, origins, horizon=4, delay=1)

    assert result == str(path.relative_to(tmp_path))
    with pytest.raises(ValueError, match="provenance"):
        verification._forecast_file(path, tmp_path, origins, 4, 1, require_provenance=True)
    metadata = {
        "forecast_sha256": verification._file_hash(path), "model_id": "AR(1,0,0)",
        "publication_delay_slots": 1, "refits": [{
            "refit_origin": str(pd.Timestamp(origins[0], tz="UTC")),
            "training_cutoff": str(pd.Timestamp(origins[0], tz="UTC") - pd.Timedelta(hours=1)),
            "origins": 2,
        }],
    }
    for missing_field in ("refits", "publication_delay_slots"):
        incomplete = {key: value for key, value in metadata.items() if key != missing_field}
        sidecar.write_text(json.dumps(incomplete), encoding="utf-8")
        with pytest.raises(ValueError, match="cutoff provenance"):
            verification._forecast_file(path, tmp_path, origins, 4, 1, require_provenance=True)
    sidecar.write_text(json.dumps(metadata), encoding="utf-8")
    verification._forecast_file(path, tmp_path, origins, 4, 1, require_provenance=True)
    metadata["refits"][0]["training_cutoff"] = metadata["refits"][0]["refit_origin"]
    sidecar.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(ValueError, match="cutoff"):
        verification._forecast_file(path, tmp_path, origins, 4, 1, require_provenance=True)

    arrays["mean"][0, 0] = np.nan
    np.savez_compressed(path, **arrays)
    sidecar.write_text(
        json.dumps({"forecast_sha256": verification._file_hash(path), "origin_count": 2}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="(?i)non-finite"):
        verification._forecast_file(path, tmp_path, origins, horizon=4, delay=1)


def test_verify_writes_partial_outputs_for_unfinished_synthetic_root(tmp_path):
    result = verification.verify(tmp_path, {"study": {}, "scheduling": {}, "queue": {}})

    saved = json.loads((tmp_path / "artifacts/verification.json").read_text(encoding="utf-8"))
    checklist = (tmp_path / "COMPLETION_CHECKLIST.md").read_text(encoding="utf-8")

    assert result["overall_status"] == "PARTIAL"
    assert saved["summary"]["partial"] == 23
    assert len(re.findall(r"^\| R\d{2} \|", checklist, re.MULTILINE)) == 23
    assert "| R18 | Notebook | PARTIAL |" in checklist
    assert "| R20 | Presentation | PARTIAL |" in checklist


def test_review_approvals_cannot_override_machine_failure_or_missing_evidence():
    checks = {key: {"status": "PASS", "details": "fixture"} for key in ("identity", "diagnostics", "notebook", "forecasts", "exports", "dashboard", "tests")}
    review = {"decisions": {req: "PASS" for req in verification.REVIEW_REQUIRED}, "details": "fixture reviews"}
    rows = verification._requirements(checks, {"fixture": True}, review)
    assert next(row for row in rows if row["id"] == "R19")["status"] == "PASS"
    checks["exports"]["status"] = "FAIL"
    rows = verification._requirements(checks, {"fixture": True}, review)
    assert next(row for row in rows if row["id"] == "R19")["status"] == "FAIL"
    checks["exports"]["status"] = "PARTIAL"
    rows = verification._requirements(checks, {"fixture": True}, review)
    assert next(row for row in rows if row["id"] == "R19")["status"] == "PARTIAL"
    review["decisions"]["R02"] = "FAIL"
    rows = verification._requirements(checks, {"fixture": True}, review)
    assert next(row for row in rows if row["id"] == "R02")["status"] == "FAIL"


def test_reviews_reject_stale_basis_and_duplicate_identity(tmp_path, monkeypatch):
    basis = {"basis_sha256": "basis", "identity": {"study_id": "synthetic"},
             "file_hashes": {"fixture": "hash"}}
    monkeypatch.setattr(verification, "review_basis", lambda *args: basis)
    verdicts = {req: "PASS" for req in verification.REVIEW_REQUIRED}
    for role in ("root", "independent"):
        verification.record_review(tmp_path, {}, role=role, reviewer_id=role,
                                   basis_sha256="basis", decisions=verdicts,
                                   notes="Faithful negative experimental result; no positive-benefit condition.")
    assert verification._review_evidence(tmp_path, {})["status"] == "PASS"
    path = tmp_path / "artifacts/reviews/independent.json"
    receipt = json.loads(path.read_text())
    receipt["reviewer_id"] = "root"
    path.write_text(json.dumps(receipt))
    assert verification._review_evidence(tmp_path, {})["status"] == "PARTIAL"
    receipt["reviewer_id"] = "independent"
    receipt["file_hashes"]["fixture"] = "altered"
    path.write_text(json.dumps(receipt))
    assert verification._review_evidence(tmp_path, {})["status"] == "PARTIAL"
    with pytest.raises(ValueError, match="basis changed"):
        verification.record_review(tmp_path, {}, role="root", reviewer_id="root",
                                   basis_sha256="stale", decisions=verdicts, notes="Review")


def _primary_fixture(root):
    start = pd.Timestamp("2030-01-01T00:00:00Z")
    scenario = "duration_0.5h_slack_0h"
    run = root / "artifacts/runs/synthetic/test/single_job"
    run.mkdir(parents=True)
    rows = []
    for policy, model in (("earliest", None), ("oracle", "oracle"), ("forecast", "model")):
        rows.append(
            {
                "scenario_id": scenario,
                "job_id": "job-1",
                "release": start,
                "deadline": start + timedelta(minutes=30),
                "duration_hours": 0.5,
                "slack_hours": 0.0,
                "power_kw": 0.4,
                "pue": 1.2,
                "policy": policy,
                "model_id": model,
                "status": "scheduled",
                "start": start,
                "finish": start + timedelta(minutes=30),
                "realized_grams": 24.0,
            }
        )
    pairs = [
        {
            "scenario_id": scenario,
            "job_id": "job-1",
            "policy": policy,
            "model_id": model,
            "baseline_grams": 24.0,
            "policy_grams": 24.0,
            "savings_grams": 0.0,
            "savings_pct": 0.0,
        }
        for policy, model in (("oracle", "oracle"), ("forecast", "model"))
    ]
    pd.DataFrame(rows).to_parquet(run / "primary_decisions.parquet", index=False)
    pd.DataFrame(pairs).to_parquet(run / "primary_pairs.parquet", index=False)
    data = root / "data/normalized"
    data.mkdir(parents=True)
    pd.DataFrame({"actual": [100.0]}, index=pd.DatetimeIndex([start])).to_parquet(data / "carbon.parquet")
    (root / "artifacts/results.json").write_text(json.dumps({"primary_jobs": 1}), encoding="utf-8")
    return {"run_dir": "artifacts/runs/synthetic", "deployment_model": "model"}, {
        "scheduling": {"default_duration_hours": 0.5, "default_slack_hours": 0.0}
    }


def test_primary_pairs_oracle_and_sample_recompute_match(tmp_path):
    identity, config = _primary_fixture(tmp_path)

    result = verification._primary(tmp_path, config, identity)

    assert result["jobs"] == 1
    assert result["pairs"] == 2
    assert result["sample"] == 3
    assert result["max_error_grams"] == pytest.approx(0.0)


def test_primary_oracle_cannot_exceed_actual_cost(tmp_path):
    identity, config = _primary_fixture(tmp_path)
    path = tmp_path / identity["run_dir"] / "test/single_job/primary_decisions.parquet"
    decisions = pd.read_parquet(path)
    decisions.loc[decisions.policy == "oracle", "realized_grams"] = 25.0
    decisions.to_parquet(path, index=False)
    pair_path = path.with_name("primary_pairs.parquet")
    pairs = pd.read_parquet(pair_path)
    pairs.loc[pairs.policy == "oracle", "policy_grams"] = 25.0
    pairs.loc[pairs.policy == "oracle", "savings_grams"] = -1.0
    pairs.loc[pairs.policy == "oracle", "savings_pct"] = -100.0 / 24
    pairs.to_parquet(pair_path, index=False)

    with pytest.raises(ValueError, match="Oracle exceeds"):
        verification._primary(tmp_path, config, identity)


def _queue_fixture(root):
    directory = root / "artifacts/runs/synthetic/test/queue"
    directory.mkdir(parents=True)
    loads, seeds, slacks = [0.3, 0.6, 0.85], [11, 22, 33], [6, 12]
    policies = [("earliest", 10.0), ("strongest_simple", 9.0), ("selected", 8.0)]
    summaries, bootstraps = [], []
    for load in loads:
        for seed in seeds:
            for slack in slacks:
                stem = f"load_{load}_seed_{seed}_slack_{slack}"
                release = pd.Timestamp("2030-01-01T00:00:00Z")
                arrival = pd.DataFrame([{"job_id": "job-1", "release": release, "deadline": release + timedelta(hours=2), "duration_hours": 1.0}])
                decision_rows, score_rows = [], []
                for policy, grams in policies:
                    row = {
                        "job_id": "job-1",
                        "release": release,
                        "deadline": release + timedelta(hours=2),
                        "duration_hours": 1.0,
                        "policy": policy,
                        "status": "scheduled",
                        "start": release,
                        "finish": release + timedelta(hours=1),
                        "realized_grams": grams,
                    }
                    decision_rows.append(row)
                    score_rows.append({**row, "scored_release": True, "full_window_observed": True})
                    summaries.append(
                        {
                            "offered_load": load,
                            "seed": seed,
                            "slack_hours": slack,
                            "policy": policy,
                            "interpretation": "fixed accepted work",
                            "fixed_work_comparison": True,
                            "offered_jobs": 1,
                            "completed_jobs": 1,
                            "rejected_jobs": 0,
                            "deadline_misses": 0,
                            "common_completed_observed_jobs": 1,
                            "matched_grams": grams,
                            "matched_baseline_grams": 10.0,
                            "matched_savings_grams": 10.0 - grams,
                            "matched_savings_pct": (10.0 - grams) * 10,
                        }
                    )
                arrival.to_parquet(directory / f"{stem}_arrivals.parquet", index=False)
                pd.DataFrame(decision_rows).to_parquet(directory / f"{stem}_decisions.parquet", index=False)
                pd.DataFrame(score_rows).to_parquet(directory / f"{stem}_scores.parquet", index=False)
                bootstraps.append({"offered_load": load, "seed": seed, "slack_hours": slack, "interpretation": "fixed accepted work"})
    (directory / "completion.json").write_text(json.dumps({"traces": 18, "completed": True}), encoding="utf-8")
    pd.DataFrame(summaries).to_csv(directory / "queue_summary.csv", index=False)
    pd.DataFrame(bootstraps).to_csv(directory / "queue_bootstrap.csv", index=False)
    return (
        {"run_dir": "artifacts/runs/synthetic"},
        {"queue": {"offered_loads": loads, "seeds": seeds, "slack_hours": slacks}},
        directory,
    )


def test_queue_verifies_18_traces_three_policies_and_savings_labels(tmp_path):
    identity, config, _ = _queue_fixture(tmp_path)

    result = verification._queue(tmp_path, config, identity)

    assert result["traces"] == 18
    assert result["policies_per_trace"] == 3
    assert result["reservations"] == 54


def test_queue_rejects_savings_label_that_hides_rejected_work(tmp_path):
    identity, config, directory = _queue_fixture(tmp_path)
    stem = "load_0.3_seed_11_slack_6"
    for suffix in ("decisions", "scores"):
        path = directory / f"{stem}_{suffix}.parquet"
        rows = pd.read_parquet(path)
        rejected = rows.policy == "selected"
        rows.loc[rejected, "status"] = "infeasible"
        rows.loc[rejected, "start"] = pd.NaT
        rows.loc[rejected, "finish"] = pd.NaT
        rows.loc[rejected, "realized_grams"] = np.nan
        rows.to_parquet(path, index=False)

    with pytest.raises(ValueError, match="label misstates"):
        verification._queue(tmp_path, config, identity)
