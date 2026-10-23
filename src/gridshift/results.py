"""Result certification and traceable report input from completed frozen runs."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .artifacts import require_freeze, write_json
from .data import load
from .evaluation import paired_moving_block_bootstrap
from .study import run_dir
from .baselines import BASELINES

LIMITATIONS = [
    "Retrospective NESO estimated actuals have no verified historical publication vintages.",
    "Thirty-minute publication delay is an assumed replay policy.",
    "Power, PUE, known durations, and arrivals are synthetic. No GPU energy was measured.",
    "Costs are modeled intensity-weighted operational CO2, not actual avoided grid emissions.",
    "National GB intensity is a proxy for a hypothetical GB-powered workload.",
    "Predictive intervals condition on fitted parameters and may be poorly calibrated.",
    "Queue completion intersections are descriptive when policies accept different jobs.",
    "Net computing overhead, marginal emissions, and embodied emissions are unmeasured.",
    "The untouched test covers 2025 only. No post-test model promotion is justified.",
    "Local packaging and runtime verification do not establish public deployment.",
]


def _records(frame):
    return json.loads(frame.to_json(orient="records", date_format="iso"))


def certify(root, config):
    root = Path(root)
    frozen = require_freeze(root, config)
    val, test = run_dir(root, config, "validation"), run_dir(root, config, "test")
    for stage in (val, test):
        for path in ("single_job/completion.json", "queue/completion.json"):
            if not (stage / path).exists():
                raise ValueError("Forecast and both scheduling experiments must complete first")
    choices = frozen["protocol"]
    metrics = pd.read_csv(test / "forecast_common_metrics.csv")
    primary = pd.read_csv(test / "single_job/primary_summary.csv")
    queue = pd.read_csv(test / "queue/queue_summary.csv")
    bootstrap = pd.read_csv(test / "single_job/primary_bootstrap.csv")
    decisions = pd.read_parquet(test / "single_job/primary_decisions.parquet")
    default = decisions.loc[(decisions.duration_hours == 2) & (decisions.slack_hours == 10)]
    deploy = choices["deployment_model"]
    simple = choices["strongest_simple"]
    a = default.loc[(default.policy == "forecast") & (default.model_id == simple),
                    ["job_id", "release", "realized_grams"]]
    b = default.loc[(default.policy == "forecast") & (default.model_id == deploy),
                    ["job_id", "realized_grams"]]
    pairs = a.merge(b, on="job_id", suffixes=("_baseline", "_policy")).rename(
        columns={"realized_grams_baseline": "baseline_grams", "realized_grams_policy": "policy_grams"})
    added_value = paired_moving_block_bootstrap(
        pairs, config["study"]["test_start"], config["study"]["test_end"],
        block_days=config["study"]["bootstrap_block_days"],
        n_resamples=config["study"]["bootstrap_resamples"], seed=config["study"]["seed"],
    )
    added_value.to_csv(test / "single_job/versus_simple_bootstrap.csv", index=False)
    selected = default.loc[(default.policy == "forecast") & (default.model_id == deploy)]
    if (selected.finish > selected.deadline).any() or (selected.status != "scheduled").any():
        raise ValueError("Primary selected policy violates fixed-work or deadline contract")
    row = bootstrap.loc[bootstrap.block_days == 7].iloc[0]
    h3 = added_value.loc[added_value.block_days == 7].iloc[0]
    effect = float(row.estimate_savings_pct)
    positive = float(row.ci95_savings_pct_low) > 0
    practical = {str(threshold): effect >= threshold for threshold in (2, 5, 10)}
    mapping = json.loads((test / "forecast_store.json").read_text())
    forecast_loss = _forecast_inference(root, config, mapping, choices["best_classical"], simple)
    forecast_loss.to_csv(test / "forecast_loss_bootstrap.csv", index=False)
    observed = load(root).actual
    origins = pd.date_range(config["study"]["test_start"], config["study"]["test_end"], freq="3h", inclusive="left")
    offered_months = pd.Series(origins.month).value_counts().sort_index()
    eligible_months = selected.release.dt.month.value_counts().sort_index().reindex(offered_months.index, fill_value=0)
    coverage = eligible_months / offered_months
    quality = json.loads((root / "artifacts/data/quality.json").read_text())
    result = {
        "schema_version": 1, "study_id": choices["study_id"],
        "data_hash": frozen["data_hash"], "protocol_hash": frozen["protocol_hash"],
        "software_hash": choices["software_hash"],
        "forecast_champion": choices["forecast_champion"], "best_classical": choices["best_classical"],
        "strongest_simple": simple, "deployment_model": deploy,
        "validation_metrics": _records(pd.read_csv(val / "forecast_metrics.csv")),
        "test_metrics": _records(pd.read_csv(test / "forecast_metrics.csv")),
        "validation_common_metrics": _records(pd.read_csv(val / "forecast_common_metrics.csv")),
        "test_common_metrics": _records(metrics),
        "primary_summary": _records(primary), "primary_bootstrap": _records(bootstrap),
        "versus_simple_bootstrap": _records(added_value),
        "forecast_loss_bootstrap": _records(forecast_loss),
        "queue_summary": _records(queue), "limitations": LIMITATIONS,
        "primary_jobs": len(selected),
        "primary_deadline_misses": int((selected.finish > selected.deadline).sum()),
        "primary_monthly_release_coverage": {str(month): float(value) for month, value in coverage.items()},
        "complete_year_scheduling_gate_pass": bool(quality["data_gate_pass"] and (coverage >= .8).all()),
        "h2_modeled_benefit_supported": positive,
        "selected_vs_forecast_selected_simple_supported_descriptively": float(h3.ci95_savings_pct_low) > 0,
        "deployment_is_classical": deploy not in BASELINES,
        "h3_added_value_supported_descriptively": deploy not in BASELINES and float(h3.ci95_savings_pct_low) > 0,
        "h3_interpretation": ("Selected classical policy improves on the forecast-selected simple comparator descriptively"
                              if deploy not in BASELINES else
                              "No classical deployment was selected; selected-policy improvement is simple timing value, not classical added value"),
        "practical_thresholds_met": practical,
        "primary_savings_pct": effect,
        "primary_ci95_pct": [float(row.ci95_savings_pct_low), float(row.ci95_savings_pct_high)],
        "headline": ("Modeled isolated-job benefit under declared assumptions" if positive
                     else "Inconclusive or negative modeled isolated-job benefit"),
        "experimental_status": "EXECUTED_FROZEN_2025",
        "external_deployment": "NOT_PERFORMED",
        "overhead_break_even_kwh_at_100g_per_kwh": float(row.estimate_savings_grams) / 100.,
        "overhead_break_even_kwh_per_isolated_case": float(row.estimate_savings_grams) / max(1, len(selected)) / 100.,
        "overhead_break_even_basis": "Illustrative 100 gCO2/kWh computing supply; overhead unmeasured. Aggregate sums correlated isolated counterfactuals, not an executable annual GPU trace.",
        "test_estimated_actual_slots": int(observed.loc[observed.index.year == 2025].notna().sum()),
        "evidence_paths": {"validation": val.relative_to(root).as_posix(), "test": test.relative_to(root).as_posix(),
                           "data": "data/manifest.json", "freeze": "artifacts/protocol_freeze.json"},
    }
    write_json(root / "artifacts/results.json", result)
    return result


def _forecast_inference(root, config, mapping, classical, simple):
    arrays = {}
    common = None
    for name, filename in mapping.items():
        with np.load(Path(root) / filename) as file:
            mask = ~file["fallback"]
            common = mask if common is None else common & mask
            if name in (classical, simple):
                arrays[name] = (file["origins_ns"].copy(), file["mean"].copy())
    origins = pd.to_datetime(arrays[simple][0], utc=True)
    slots = np.asarray(config["study"]["reported_horizons"]) - 1
    targets = origins.asi8[:, None] + slots * pd.Timedelta(minutes=30).value
    truth = load(root).actual
    actual = truth.reindex(pd.to_datetime(targets.ravel(), utc=True)).to_numpy().reshape(targets.shape)
    valid = common & np.isfinite(actual).all(axis=1)
    base_loss = np.mean(np.abs(arrays[simple][1][:, slots] - actual), axis=1)
    policy_loss = np.mean(np.abs(arrays[classical][1][:, slots] - actual), axis=1)
    pairs = pd.DataFrame({"release": origins[valid], "baseline_grams": base_loss[valid], "policy_grams": policy_loss[valid]})
    table = paired_moving_block_bootstrap(pairs, config["study"]["test_start"], config["study"]["test_end"],
        block_days=config["study"]["bootstrap_block_days"], n_resamples=config["study"]["bootstrap_resamples"],
        seed=config["study"]["seed"])
    table.columns = [c.replace("savings", "loss_reduction").replace("grams", "gco2_per_kwh").replace("job", "origin")
                     for c in table.columns]
    table["classical"], table["baseline"] = classical, simple
    table["interpretation"] = "Secondary descriptive paired equal-horizon MAE contrast"
    return table
