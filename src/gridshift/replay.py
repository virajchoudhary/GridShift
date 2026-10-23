"""Online immutable one-GPU reservations, with truth joined only afterward."""

import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

from . import baselines
from .artifacts import require_freeze, write_json, digest
from .data import load
from .domain import Decision, ForecastPath, Job, SLOT, grid_time
from .evaluation import paired_moving_block_bootstrap
from .forecasting import ModelSpec, rolling_forecasts
from .scheduling import candidates, integrated_cost, recommend
from .study import forecast_config, run_dir


def arrivals(start, end, load_level, seed, slack_hours, config):
    queue = config["queue"]
    warm = grid_time(start) - pd.Timedelta(hours=queue["warmup_hours"])
    stop = grid_time(end) - pd.Timedelta(hours=queue["drain_hours"])
    durations = np.asarray(queue["durations_hours"], dtype=float)
    probabilities = np.asarray(queue["probabilities"], dtype=float)
    if not np.isclose(probabilities.sum(), 1) or np.any(probabilities < 0):
        raise ValueError("Duration probabilities must sum to one")
    expected_duration = float(durations @ probabilities)
    if not 0 < load_level < 1:
        raise ValueError("Offered load must lie between zero and one")
    rng = np.random.default_rng(seed)
    current = warm
    jobs = []
    while True:
        current += pd.Timedelta(hours=float(rng.exponential(expected_duration / load_level)))
        if current >= stop:
            break
        release = current.ceil("30min")
        duration = float(rng.choice(durations, p=probabilities))
        jobs.append(Job(f"load_{load_level}_seed_{seed}_job_{len(jobs):05d}",
                        release, duration, release + pd.Timedelta(hours=duration + slack_hours),
                        config["scheduling"]["power_kw"], config["scheduling"]["pue"]))
    return jobs


def simulate(jobs, path_provider, policy):
    reservations = []
    rows = []
    previous_release = None
    for job in jobs:
        if previous_release is not None and job.release < previous_release:
            raise ValueError("Arrivals must be ordered chronologically")
        previous_release = job.release
        reservations = [interval for interval in reservations if interval[1] > job.release]
        fallback = False
        if policy == "earliest":
            path = ForecastPath(job.release, np.ones(48), "earliest", job.release - SLOT)
        else:
            path = path_provider(job.release)
            fallback = path is None or path.status == "unavailable"
            if fallback:
                path = ForecastPath(job.release, np.ones(48), "earliest_fallback", job.release - SLOT, status="fallback")
        decision = recommend(job, path, reservations)
        if decision.status == "scheduled":
            reservations.append((decision.start, decision.finish))
        if policy == "earliest" or fallback:
            predicted = None
        else:
            predicted = decision.predicted_grams
        rows.append({
            "job_id": job.id, "release": job.release, "deadline": job.deadline,
            "duration_hours": job.duration_hours, "energy_kwh": float(job.energy_kwh.sum()),
            "policy": policy, "status": decision.status, "start": decision.start,
            "finish": decision.finish, "predicted_grams": predicted, "reason": decision.reason,
            "fallback": fallback or path.status == "fallback", "model_id": path.model_id,
            "training_cutoff": path.training_cutoff,
        })
    return pd.DataFrame(rows)


def _provider(files, model_id):
    stores = {}
    for file in files:
        file = Path(file)
        metadata = json.loads(file.with_suffix(".json").read_text())
        if metadata.get("forecast_sha256") != digest(file.read_bytes()):
            raise ValueError("Queue forecast checksum differs from stored metadata")
        actual_model = metadata.get("model_id", metadata.get("model_spec", {}).get("name"))
        if actual_model != model_id:
            raise ValueError("Queue forecast model differs from declared policy")
        with np.load(file, allow_pickle=False) as arrays:
            stores.update({int(t): (arrays["mean"][i].copy(), bool(arrays["fallback"][i]))
                           for i, t in enumerate(arrays["origins_ns"])})
    def provider(origin):
        item = stores.get(origin.value)
        if item is None:
            return None
        mean, fallback = item
        return ForecastPath(origin, mean, model_id, origin - 2 * SLOT,
                            status="fallback" if fallback else "ok")
    return provider


def score_trace(jobs, decisions, truth, start, end, *, experiment_root=None, synthetic=False):
    from .artifacts import authorize_period
    authorize_period(truth, start, end, experiment_root=experiment_root, synthetic=synthetic)
    start, end = grid_time(start), grid_time(end)
    job_map = {job.id: job for job in jobs}
    scores = decisions.copy()
    scores["scored_release"] = (scores.release >= start) & (scores.deadline <= end)
    eligible = {}
    for job in jobs:
        window = pd.date_range(job.release, job.deadline, freq=SLOT, inclusive="left")
        eligible[job.id] = bool(truth.reindex(window).notna().all())
    scores["full_window_observed"] = scores.job_id.map(eligible)
    costs = []
    for row in scores.itertuples():
        if row.status == "scheduled" and row.full_window_observed:
            costs.append(integrated_cost(job_map[row.job_id], row.start, truth))
        else:
            costs.append(np.nan)
    scores["realized_grams"] = costs
    return scores


def _trace_summary(scores, load_level, seed, slack_hours, start, end):
    rows = []
    offered = scores.loc[scores.scored_release]
    policy_names = sorted(offered.policy.unique())
    accepted = {name: set(offered.loc[(offered.policy == name) & (offered.status == "scheduled"), "job_id"])
                for name in policy_names}
    common = set.intersection(*accepted.values()) if accepted else set()
    equal_work = bool(accepted) and all(ids == accepted[policy_names[0]] for ids in accepted.values())
    comparison = offered.loc[offered.job_id.isin(common) & offered.full_window_observed]
    baseline = comparison.loc[comparison.policy == "earliest"].set_index("job_id")
    nominal = {"offered_load": load_level, "seed": seed, "slack_hours": slack_hours}
    for name in policy_names:
        data = offered.loc[offered.policy == name]
        complete = data.loc[data.status == "scheduled"]
        matched = comparison.loc[comparison.policy == name].set_index("job_id")
        waiting = (complete.start - complete.release).dt.total_seconds() / 3600
        base_grams = float(baseline.realized_grams.sum())
        matched_grams = float(matched.realized_grams.sum())
        rows.append({
            **nominal, "policy": name, "offered_jobs": len(data), "completed_jobs": len(complete),
            "rejected_jobs": int((data.status != "scheduled").sum()),
            "rejection_rate": float((data.status != "scheduled").mean()),
            "deadline_misses": int((complete.finish > complete.deadline).sum()),
            "total_completed_energy_kwh": float(complete.energy_kwh.sum()),
            "observed_completed_jobs": int(complete.realized_grams.notna().sum()),
            "observed_completed_grams": float(complete.realized_grams.sum()),
            "unknown_actual_jobs": int(complete.realized_grams.isna().sum()),
            "common_completed_observed_jobs": len(matched),
            "matched_grams": matched_grams,
            "matched_baseline_grams": base_grams,
            "matched_savings_pct": 100 * (base_grams - matched_grams) / base_grams if base_grams > 0 else np.nan,
            "matched_savings_grams": base_grams - matched_grams,
            "unmatched_completed_jobs": len(complete) - len(matched),
            "fixed_work_comparison": equal_work,
            "whole_offered_trace_completed": len(complete) == len(data),
            "interpretation": "fixed accepted work" if equal_work else "descriptive completion intersection; service differs",
            "waiting_median_hours": float(waiting.median()),
            "waiting_p95_hours": float(waiting.quantile(.95)),
            "fallback_rate": float(data.fallback.mean()),
            "actual_discretized_offered_load": float(data.duration_hours.sum()) / ((end - start).total_seconds() / 3600),
        })
    return rows, comparison


def queue_backtest(root, config, stage):
    root = Path(root).resolve()
    if not (root / "artifacts/tests/single_job_independent_review.json").exists():
        raise ValueError("Independent single-job acceptance is required")
    out = run_dir(root, config, stage)
    choices = json.loads((run_dir(root, config, "validation") / "validation_choices.json").read_text())
    if stage == "test":
        frozen = require_freeze(root, config)
        choices = frozen["protocol"]
    models = [choices["strongest_simple"], choices["deployment_model"]]
    start, end = pd.Timestamp(config["study"][stage + "_start"]), pd.Timestamp(config["study"][stage + "_end"])
    mapping = json.loads((out / "forecast_store.json").read_text())
    cfg = forecast_config(config)
    warm_start = start - pd.Timedelta(hours=config["queue"]["warmup_hours"])
    warm_end = start + pd.Timedelta(days=1)
    warm_dir = out / "warmup_forecasts"
    warm_dir.mkdir(parents=True, exist_ok=True)
    warm_files = {}
    for name in set(models):
        if name in baselines.BASELINES:
            if not (warm_dir / f"{name}.npz").exists():
                baselines.rolling(load(root).actual, warm_start, warm_end, warm_dir, cfg, experiment_root=root)
            warm_files[name] = warm_dir / f"{name}.npz"
        else:
            spec = next(ModelSpec.from_dict(v) for v in choices["family_finalists"] if v["name"] == name)
            path = warm_dir / "selected.npz"
            if not path.exists():
                rolling_forecasts(load(root).actual, spec, warm_start, warm_end, path, cfg, experiment_root=root)
            warm_files[name] = path
    providers = {name: _provider([warm_files[name], root / mapping[name]], name) for name in set(models)}
    dest = out / "queue"
    dest.mkdir(parents=True, exist_ok=True)
    summary_rows, bootstrap_rows, monthly_rows = [], [], []
    truth = load(root).actual
    for level in config["queue"]["offered_loads"]:
        for seed in config["queue"]["seeds"]:
            for slack in config["queue"]["slack_hours"]:
                jobs = arrivals(start, end, level, seed, slack, config)
                trace = pd.DataFrame([{"job_id": job.id, "release": job.release, "deadline": job.deadline,
                                       "duration_hours": job.duration_hours} for job in jobs])
                stem = f"load_{level}_seed_{seed}_slack_{slack}"
                trace.to_parquet(dest / f"{stem}_arrivals.parquet", index=False)
                policy_tables = [
                    simulate(jobs, None, "earliest"),
                    simulate(jobs, providers[models[0]], "strongest_simple"),
                    simulate(jobs, providers[models[1]], "selected"),
                ]
                decisions = pd.concat(policy_tables, ignore_index=True)
                decisions.to_parquet(dest / f"{stem}_decisions.parquet", index=False)
                scores = score_trace(jobs, decisions, truth, start, end, experiment_root=root)
                scores.to_parquet(dest / f"{stem}_scores.parquet", index=False)
                summary, common = _trace_summary(scores, level, seed, slack, start, end)
                for policy_summary in summary:
                    occupancy = np.zeros(len(truth.loc[(truth.index >= start) & (truth.index < end)]))
                    for row in decisions.loc[(decisions.policy == policy_summary["policy"]) & (decisions.status == "scheduled")].itertuples():
                        if row.finish <= start or row.start >= end:
                            continue
                        first = max(0, int((row.start - start) / SLOT))
                        last = min(len(occupancy), int((row.finish - start) / SLOT))
                        occupancy[first:last] = 1
                    actual = truth.loc[(truth.index >= start) & (truth.index < end)].to_numpy(float)
                    idle_kw = float(config["scheduling"].get("facility_idle_power_kw", .08))
                    facility_power = occupancy * config["scheduling"]["power_kw"] + (1 - occupancy) * idle_kw
                    policy_summary["facility_idle_power_kw_assumed"] = idle_kw
                    policy_summary["secondary_facility_grams"] = float(np.dot(actual, facility_power * .5 * config["scheduling"]["pue"])) if np.isfinite(actual).all() else np.nan
                    policy_summary["secondary_facility_energy_kwh"] = float((facility_power * .5 * config["scheduling"]["pue"]).sum())
                summary_rows.extend(summary)
                scored = scores.loc[scores.scored_release]
                for month, group in scored.groupby(scored.release.dt.strftime("%Y-%m")):
                    left = pd.Timestamp(month + "-01", tz="UTC")
                    right = left + pd.offsets.MonthBegin(1)
                    monthly, _ = _trace_summary(group, level, seed, slack, left, right)
                    monthly_rows.extend([{**row, "month": month} for row in monthly])
                a = common.loc[common.policy == "earliest", ["job_id", "release", "realized_grams"]]
                b = common.loc[common.policy == "selected", ["job_id", "realized_grams"]]
                pairs = a.merge(b, on="job_id", suffixes=("_baseline", "_policy")).rename(
                    columns={"realized_grams_baseline": "baseline_grams", "realized_grams_policy": "policy_grams"})
                ci = paired_moving_block_bootstrap(pairs, start, end,
                    block_days=config["study"]["bootstrap_block_days"],
                    n_resamples=config["study"]["bootstrap_resamples"], seed=seed)
                ci["offered_load"], ci["seed"], ci["slack_hours"] = level, seed, slack
                ci["interpretation"] = summary[0]["interpretation"]
                bootstrap_rows.append(ci)
                print(f"QUEUE {stage} {stem} offered={len(jobs)}", flush=True)
    pd.DataFrame(summary_rows).to_csv(dest / "queue_summary.csv", index=False)
    pd.DataFrame(monthly_rows).to_csv(dest / "queue_monthly.csv", index=False)
    pd.concat(bootstrap_rows).to_csv(dest / "queue_bootstrap.csv", index=False)
    write_json(dest / "completion.json", {"traces": 18, "completed": True, "continuous_capacity": True,
                                          "future_missingness_used_for_arrivals": False})
    return pd.DataFrame(summary_rows)
