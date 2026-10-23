"""Prespecified bounded validation sensitivities, never test-driven tuning."""

import copy
import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import baselines
from .artifacts import write_json
from .data import load
from .domain import Job, SLOT, ForecastPath
from .evaluation import primary_backtest
from .forecasting import ModelSpec, rolling_forecasts
from .study import forecast_config, run_dir
from .scheduling import candidates, integrated_cost, recommend


def run(root, config):
    root = Path(root)
    choices = json.loads((run_dir(root, config, "validation") / "validation_choices.json").read_text())
    model_id = choices["best_classical"]
    spec = next(ModelSpec.from_dict(v) for v in choices["family_finalists"] if v["name"] == model_id)
    destination = root / "artifacts/sensitivities"
    destination.mkdir(parents=True, exist_ok=True)
    truth = load(root).actual
    variants = {
        "default": {}, "delay_0min": {"publication_delay_slots": 0},
        "delay_60min": {"publication_delay_slots": 2},
        "window_90days": {"training_window_days": 90},
        "window_365days": {"training_window_days": 365},
        "native_missing": {"missing_policy": "native"},
    }
    rows = []
    for month in (1, 4, 7, 10):
        start = pd.Timestamp(f"2024-{month:02d}-01T00:00Z")
        end = start + pd.Timedelta(days=3)
        for label, changes in variants.items():
            out = destination / f"month_{month:02d}" / label
            out.mkdir(parents=True, exist_ok=True)
            cfg = {**forecast_config(config), **changes}
            file = out / "forecast.npz"
            if not file.with_suffix(".json").exists():
                rolling_forecasts(truth, spec, start, end, file, cfg)
            if not (out / "primary_summary.csv").exists():
                evaluation = copy.deepcopy(config)
                evaluation["scheduling"].update(duration_hours=[2], slack_hours=[10],
                    selected_model_id=model_id, selection_metadata={"selection_basis": "frozen validation finalist; descriptive sensitivity"})
                evaluation["study"]["bootstrap_resamples"] = 2000
                evaluation["study"]["publication_delay_slots"] = cfg["publication_delay_slots"]
                primary_backtest(truth, {model_id: file}, start, end, out, evaluation)
            table = pd.read_csv(out / "primary_summary.csv")
            row = table.loc[(table.result_type == "scheduling") & (table.policy == "forecast")].iloc[0].to_dict()
            rows.append({"month": month, "variant": label, "model_id": model_id, **row})
            print(f"SENSITIVITY month={month} {label}", flush=True)
    pd.DataFrame(rows).to_csv(destination / "sensitivity_summary.csv", index=False)
    _energy_profiles(truth, destination, model_id, config)
    write_json(destination / "completion.json", {
        "completed": True, "year": 2024, "months": [1, 4, 7, 10], "episode_days": 3,
        "forecast_origins_per_episode": 97, "variants": variants, "model": model_id,
        "scope": "Descriptive validation episodes. No full-year robustness or test selection claim.",
        "power_pue_sensitivity": "Absolute costs scale with power times PUE for constant fixed energy; percentage and ranking invariance tested.",
        "nonconstant_profile": {"multipliers": [.5, 1.5, .5, 1.5], "duration_hours": 2},
    })


def _energy_profiles(truth, destination, model_id, config):
    rows = []
    outages = []
    from .live import operational_state
    for month in (1, 4, 7, 10):
        source = destination / f"month_{month:02d}/default/forecast.npz"
        with np.load(source, allow_pickle=False) as arrays:
            for index in range(0, len(arrays["origins_ns"]), 6):
                origin = pd.Timestamp(int(arrays["origins_ns"][index]), tz="UTC")
                path = ForecastPath(origin, arrays["mean"][index], model_id, origin - 2 * SLOT)
                deadline = origin + pd.Timedelta(hours=12)
                if truth.reindex(pd.date_range(origin, deadline, freq=SLOT, inclusive="left")).isna().any():
                    continue
                for label, profile in (("constant", None), ("nonconstant", (.5, 1.5, .5, 1.5))):
                    job = Job(f"{label}_{origin.value}", origin, 2, deadline, profile=profile)
                    decision = recommend(job, path)
                    table = candidates(job, path)
                    oracle_costs = [integrated_cost(job, start, truth) for start in table.start]
                    rows.append({
                        "month": month, "origin": str(origin), "profile": label,
                        "energy_kwh": float(job.energy_kwh.sum()), "chosen_start": str(decision.start),
                        "earliest_grams": integrated_cost(job, origin, truth),
                        "selected_grams": integrated_cost(job, decision.start, truth),
                        "oracle_grams": min(oracle_costs),
                        "predicted_grams": decision.predicted_grams,
                        "scope": "Descriptive quarterly validation episodes",
                    })
                    if label == "constant":
                        for power in (.2, .8):
                            for pue in (1., 1.5):
                                scaled = Job("scaled", origin, 2, deadline, power, pue)
                                choice = recommend(scaled, path)
                                if choice.start != decision.start:
                                    raise ValueError("Constant power/PUE unexpectedly changed placement ranking")
                if index == 0:
                    cutoff = origin - 2 * SLOT
                    snapshot = truth.loc[(truth.index > cutoff - pd.Timedelta(days=7)) & (truth.index <= cutoff)].copy()
                    snapshot.loc[snapshot.index > origin - pd.Timedelta(hours=6)] = np.nan
                    state = operational_state(snapshot, origin)
                    if state["recommendation_enabled"]:
                        raise ValueError("Six-hour outage did not disable carbon recommendation")
                    outages.append({
                        "origin": str(origin), **state, "injected_outage_hours": 6,
                        "fallback_start": str(origin), "fallback_finish": str(origin + pd.Timedelta(hours=2)),
                        "deadline": str(deadline), "carbon_estimate": None,
                        "scope": "Operational state replay using only eligible validation history",
                    })
    pd.DataFrame(rows).to_csv(destination / "energy_profile_sensitivity.csv", index=False)
    pd.DataFrame(outages).to_csv(destination / "outage_state_replay.csv", index=False)
