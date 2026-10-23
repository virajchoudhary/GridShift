"""Historical evaluation for isolated, deadline-constrained jobs."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from gridshift.domain import Decision, ForecastPath, Job, SLOT, grid_time, utc

from .scheduling import _candidate_windows, candidates, earliest_minimum


_HORIZONS = (1, 4, 12, 24, 48)
_PARQUET_FILES = ("primary_decisions.parquet", "primary_pairs.parquet")


@dataclass(frozen=True)
class _ForecastFile:
    model_id: str
    origins_ns: np.ndarray
    mean: np.ndarray
    std: np.ndarray | None
    fallback: np.ndarray
    row_by_origin: dict[int, int]
    publication_delay_slots: int = 1
    artifact_hash: str = ""


def forecast_metrics(
    actual,
    predicted,
    mase_scale=None,
    std=None,
) -> dict[str, float | int]:
    """Compute point and Gaussian interval metrics on one common finite mask."""
    observed = np.asarray(actual, dtype=float).reshape(-1)
    forecast = np.asarray(predicted, dtype=float).reshape(-1)
    if observed.shape != forecast.shape:
        raise ValueError("actual and predicted arrays must have equal shape")
    mask = np.isfinite(observed) & np.isfinite(forecast)
    errors = forecast[mask] - observed[mask]
    count = int(mask.sum())
    mae = float(np.mean(np.abs(errors))) if count else np.nan
    rmse = float(np.sqrt(np.mean(errors**2))) if count else np.nan
    bias = float(np.mean(errors)) if count else np.nan

    if mase_scale is None:
        mase = np.nan
    else:
        scales = np.asarray(mase_scale, dtype=float)
        if scales.ndim == 0:
            mase = mae / float(scales) if count and np.isfinite(scales) and scales > 0 else np.nan
        else:
            if scales.size != observed.size:
                raise ValueError("mase_scale must be scalar or match the input arrays")
            valid_scale = mask & np.isfinite(scales.reshape(-1)) & (scales.reshape(-1) > 0)
            mase = (
                float(np.mean(np.abs(forecast[valid_scale] - observed[valid_scale]) / scales.reshape(-1)[valid_scale]))
                if valid_scale.any()
                else np.nan
            )

    coverage: dict[str, float | int] = {
        "interval_n": 0,
        "interval_coverage80": np.nan,
        "interval_coverage95": np.nan,
    }
    if std is not None:
        deviations = np.asarray(std, dtype=float).reshape(-1)
        if deviations.size != observed.size:
            raise ValueError("std must match the input arrays")
        interval_mask = mask & np.isfinite(deviations) & (deviations >= 0)
        interval_count = int(interval_mask.sum())
        coverage = {
            "interval_n": interval_count,
            "interval_coverage80": (
                float(np.mean(np.abs(errors_for_interval := (forecast - observed)[interval_mask]) <= 1.2815515655446004 * deviations[interval_mask]))
                if interval_count
                else np.nan
            ),
            "interval_coverage95": (
                float(np.mean(np.abs(errors_for_interval := (forecast - observed)[interval_mask]) <= 1.959963984540054 * deviations[interval_mask]))
                if interval_count
                else np.nan
            ),
        }

    return {
        "n": count,
        "mae": mae,
        "rmse": rmse,
        "bias": bias,
        "mase": float(mase),
        **coverage,
    }


def paired_moving_block_bootstrap(
    pairs: pd.DataFrame,
    start,
    end,
    *,
    block_days: Sequence[int] = (7,),
    n_resamples: int = 2000,
    seed: int = 1729,
) -> pd.DataFrame:
    """Resample paired daily totals in moving calendar blocks, never individual jobs."""
    required = {"release", "baseline_grams", "policy_grams"}
    if not required.issubset(pairs.columns):
        raise ValueError(f"pairs must include {sorted(required)}")
    if n_resamples < 1:
        raise ValueError("n_resamples must be positive")

    start_utc = grid_time(start)
    end_utc = grid_time(end)
    if end_utc <= start_utc:
        raise ValueError("end must follow start")

    rows: list[dict[str, object]] = []
    if pairs.empty:
        for days in block_days:
            rows.append(
                {
                    "block_days": int(days),
                    "n_resamples": n_resamples,
                    "paired_job_count": 0,
                    "calendar_days": int((end_utc - start_utc).days),
                    "estimate_savings_grams": np.nan,
                    "estimate_savings_pct": np.nan,
                    "ci95_savings_grams_per_job_low": np.nan,
                    "ci95_savings_grams_per_job_high": np.nan,
                    "ci95_savings_pct_low": np.nan,
                    "ci95_savings_pct_high": np.nan,
                    "valid_resamples": 0,
                }
            )
        return pd.DataFrame(rows)

    release = pd.DatetimeIndex(pd.to_datetime(pairs["release"]))
    if release.tz is None:
        raise ValueError("Pair release timestamps must be timezone-aware")
    release = release.tz_convert("UTC")
    baseline = pd.to_numeric(pairs["baseline_grams"], errors="raise").to_numpy(dtype=float)
    policy = pd.to_numeric(pairs["policy_grams"], errors="raise").to_numpy(dtype=float)
    valid = np.isfinite(baseline) & np.isfinite(policy)
    release = release[valid]
    baseline = baseline[valid]
    policy = policy[valid]

    first_day = start_utc.floor("D")
    last_day = (end_utc - pd.Timedelta(nanoseconds=1)).floor("D")
    days = pd.date_range(first_day, last_day, freq="D")
    daily = pd.DataFrame(
        {
            "baseline": baseline,
            "policy": policy,
            "count": np.ones(len(baseline), dtype=np.int64),
        },
        index=release.floor("D"),
    ).groupby(level=0).sum().reindex(days, fill_value=0)
    base_values = daily["baseline"].to_numpy(dtype=float)
    savings_values = base_values - daily["policy"].to_numpy(dtype=float)
    count_values = daily["count"].to_numpy(dtype=float)
    day_count = len(days)

    for block in block_days:
        requested_block = int(block)
        if requested_block < 1:
            raise ValueError("block_days values must be positive")
        block = min(requested_block, max(day_count, 1))
        estimate_baseline = float(np.sum(base_values))
        estimate_savings = float(np.sum(savings_values))
        estimate_jobs = float(np.sum(count_values))
        estimate_pct = (
            100.0 * estimate_savings / estimate_baseline if estimate_baseline > 0 else np.nan
        )
        block_rng = np.random.default_rng(np.random.SeedSequence([int(seed), requested_block]))
        block_count = int(math.ceil(day_count / block)) if day_count else 0
        gram_samples: list[float] = []
        percent_samples: list[float] = []
        if day_count:
            max_start = day_count - block
            for _ in range(n_resamples):
                starts = block_rng.integers(0, max_start + 1, size=block_count)
                sample_indices = np.concatenate(
                    [np.arange(index, index + block) for index in starts]
                )[:day_count]
                sample_base = float(base_values[sample_indices].sum())
                sample_savings = float(savings_values[sample_indices].sum())
                sample_jobs = float(count_values[sample_indices].sum())
                if sample_jobs > 0:
                    gram_samples.append(sample_savings / sample_jobs)
                if sample_base > 0:
                    percent_samples.append(100.0 * sample_savings / sample_base)

        gram_interval = np.quantile(gram_samples, [0.025, 0.975]) if gram_samples else (np.nan, np.nan)
        percent_interval = (
            np.quantile(percent_samples, [0.025, 0.975])
            if percent_samples
            else (np.nan, np.nan)
        )
        rows.append(
            {
                "block_days": requested_block,
                "effective_block_days": block,
                "n_resamples": n_resamples,
                "paired_job_count": int(estimate_jobs),
                "calendar_days": day_count,
                "estimate_savings_grams": estimate_savings,
                "estimate_savings_grams_per_job": (
                    estimate_savings / estimate_jobs if estimate_jobs > 0 else np.nan
                ),
                "estimate_savings_pct": estimate_pct,
                "ci95_savings_grams_per_job_low": float(gram_interval[0]),
                "ci95_savings_grams_per_job_high": float(gram_interval[1]),
                "ci95_savings_pct_low": float(percent_interval[0]),
                "ci95_savings_pct_high": float(percent_interval[1]),
                "valid_resamples": len(percent_samples),
            }
        )
    return pd.DataFrame(rows)


def _config_section(config: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = config.get(key, {})
    return value if isinstance(value, Mapping) else {}


def _config_value(config: Mapping[str, object], section: str, key: str, default):
    return _config_section(config, section).get(key, default)


def _hours(values, name: str, *, allow_zero: bool) -> tuple[float, ...]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise ValueError(f"{name} must be a sequence of hour values")
    converted = tuple(float(value) for value in values)
    if not converted or not all(np.isfinite(value) for value in converted):
        raise ValueError(f"{name} must contain finite hour values")
    lower_ok = (lambda value: value >= 0) if allow_zero else (lambda value: value > 0)
    if not all(lower_ok(value) for value in converted):
        raise ValueError(f"{name} contains an out-of-range value")
    return tuple(sorted(set(converted)))


def _scenarios(config: Mapping[str, object]) -> tuple[list[dict[str, object]], float, float]:
    scheduling = _config_section(config, "scheduling")
    durations = _hours(scheduling.get("duration_hours", (0.5, 1, 2, 4)), "duration_hours", allow_zero=False)
    slacks = _hours(scheduling.get("slack_hours", (0, 2, 6, 12, 20)), "slack_hours", allow_zero=True)
    default_duration = float(scheduling.get("default_duration_hours", 2))
    default_slack = float(scheduling.get("default_slack_hours", 10))
    if not np.isfinite(default_duration) or default_duration <= 0:
        raise ValueError("default_duration_hours must be positive and finite")
    if not np.isfinite(default_slack) or default_slack < 0:
        raise ValueError("default_slack_hours must be nonnegative and finite")

    pairs = set((duration, slack) for duration in durations for slack in slacks)
    pairs.add((default_duration, default_slack))
    scenarios: list[dict[str, object]] = []
    for duration, slack in sorted(pairs):
        if duration + slack > 24:
            raise ValueError("Every feasible job window must fit within the 48-slot forecast path")
        scenario_id = f"duration_{duration:g}h_slack_{slack:g}h"
        scenarios.append(
            {
                "scenario_id": scenario_id,
                "duration_hours": duration,
                "slack_hours": slack,
                "is_default": duration == default_duration and slack == default_slack,
            }
        )
    return scenarios, default_duration, default_slack


def _canonical_truth(truth: pd.Series) -> pd.Series:
    if not isinstance(truth, pd.Series):
        raise TypeError("truth must be a pandas Series")
    if not isinstance(truth.index, pd.DatetimeIndex) or truth.index.tz is None:
        raise ValueError("truth must have an explicitly timezone-aware DatetimeIndex")
    index = truth.index.tz_convert("UTC")
    if index.has_duplicates:
        raise ValueError("truth contains duplicate interval starts")
    if np.any(index.asi8 % SLOT.value):
        raise ValueError("truth timestamps must lie on the half-hour grid")
    try:
        values = pd.to_numeric(truth, errors="raise").to_numpy(dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("truth values must be numeric") from exc
    if np.isinf(values).any() or np.any(values[np.isfinite(values)] < 0):
        raise ValueError("truth cannot contain infinite or negative intensity values")
    return pd.Series(values, index=index, name=truth.name).sort_index()


def _range_boundary(value, name: str) -> pd.Timestamp:
    try:
        return grid_time(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a timezone-aware half-hour boundary") from exc


def _origins(start: pd.Timestamp, end: pd.Timestamp) -> pd.DatetimeIndex:
    if end <= start:
        return pd.DatetimeIndex([], tz="UTC")
    return pd.date_range(start, end, freq=pd.Timedelta(hours=3), inclusive="left")


def _load_forecast_files(forecast_files: Mapping[str, Path], *, require_metadata=False, default_delay_slots=1) -> dict[str, _ForecastFile]:
    stores: dict[str, _ForecastFile] = {}
    for model_id, filename in sorted(forecast_files.items()):
        filename = Path(filename)
        artifact_hash = hashlib.sha256(filename.read_bytes()).hexdigest()
        metadata_path = filename.with_suffix(".json")
        metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {}
        if require_metadata and not metadata:
            raise ValueError("Official backtests require checksummed forecast metadata")
        if metadata and metadata.get("forecast_sha256") != artifact_hash:
            raise ValueError("Forecast checksum differs from stored metadata")
        recorded_model = metadata.get("model_id", metadata.get("model_spec", {}).get("name"))
        if require_metadata and recorded_model is None:
            raise ValueError("Official forecast metadata requires model identity")
        if recorded_model is not None and recorded_model != model_id:
            raise ValueError("Forecast model ID differs from stored metadata")
        if require_metadata and int(metadata.get("publication_delay_slots", default_delay_slots)) != default_delay_slots:
            raise ValueError("Forecast publication delay differs from configured information cutoff")
        with np.load(Path(filename), allow_pickle=False) as archive:
            if not {"origins_ns", "mean"}.issubset(archive.files):
                raise ValueError(f"{filename} must contain origins_ns and mean")
            origins_ns = np.asarray(archive["origins_ns"])
            mean = np.asarray(archive["mean"])
            if origins_ns.dtype != np.dtype("int64") or origins_ns.ndim != 1:
                raise ValueError(f"{filename} origins_ns must be a one-dimensional int64 array")
            if mean.ndim != 2 or mean.shape != (len(origins_ns), 48) or mean.dtype.kind != "f":
                raise ValueError(f"{filename} mean must be a floating [n, 48] array")
            if np.any(origins_ns % SLOT.value):
                raise ValueError(f"{filename} has a forecast origin off the half-hour grid")
            if len(np.unique(origins_ns)) != len(origins_ns):
                raise ValueError(f"{filename} has duplicate forecast origins")
            std = np.asarray(archive["std"]) if "std" in archive.files else None
            if std is not None and (std.shape != mean.shape or std.dtype.kind != "f"):
                raise ValueError(f"{filename} std must be a floating array matching mean")
            fallback = (
                np.asarray(archive["fallback"])
                if "fallback" in archive.files
                else np.zeros(len(origins_ns), dtype=bool)
            )
            if fallback.dtype != np.dtype("bool") or fallback.shape != (len(origins_ns),):
                raise ValueError(f"{filename} fallback must be a boolean [n] array")
        stores[str(model_id)] = _ForecastFile(
            model_id=str(model_id),
            origins_ns=origins_ns,
            mean=mean,
            std=std,
            fallback=fallback,
            row_by_origin={int(value): index for index, value in enumerate(origins_ns)},
            publication_delay_slots=int(metadata.get("publication_delay_slots", default_delay_slots)),
            artifact_hash=artifact_hash,
        )
    return stores


def _forecast_path(
    store: _ForecastFile,
    origin: pd.Timestamp,
) -> tuple[ForecastPath | None, str, bool, np.ndarray | None]:
    row = store.row_by_origin.get(origin.value)
    if row is None:
        return None, "Forecast is missing at this origin", False, None
    fallback = bool(store.fallback[row])
    mean = np.asarray(store.mean[row], dtype=float)
    if not np.all(np.isfinite(mean)):
        return None, "Forecast path contains non-finite values", fallback, None

    std = None
    if store.std is not None:
        candidate_std = np.asarray(store.std[row], dtype=float)
        if np.all(np.isfinite(candidate_std)) and np.all(candidate_std >= 0):
            std = candidate_std
    status = "fallback" if fallback else "ok"
    return (
        ForecastPath(
            origin=origin,
            mean=mean,
            model_id=store.model_id,
            training_cutoff=origin - (1 + store.publication_delay_slots) * SLOT,
            std=std,
            status=status,
        ),
        "",
        fallback,
        std,
    )


def _truth_window(truth: pd.Series, release: pd.Timestamp, deadline: pd.Timestamp) -> tuple[np.ndarray, int]:
    duration_ns = deadline.value - release.value
    slot_count = int(math.ceil(duration_ns / SLOT.value))
    index = release + np.arange(slot_count, dtype=np.int64) * SLOT
    values = truth.reindex(index).to_numpy(dtype=float)
    missing = int((~np.isfinite(values)).sum())
    return values, missing


def _candidate_truth_costs(job: Job, window_values: np.ndarray, candidate_count: int) -> np.ndarray:
    energy = job.energy_kwh
    windows = np.lib.stride_tricks.sliding_window_view(window_values, job.slots)
    return np.asarray(windows[:candidate_count] @ energy, dtype=float)


def _batch_recommend(
    job: Job,
    path: ForecastPath,
    windows: Sequence[tuple[pd.Timestamp, pd.Timestamp]],
) -> tuple[Decision, np.ndarray]:
    """Evaluate all unreserved starts at once for the backtest's inner loop."""
    model_id = path.model_id
    if path.status not in {"ok", "fallback"}:
        return (
            Decision(job.id, "unavailable", None, None, None, f"Forecast path status is {path.status!r}", model_id),
            np.asarray([], dtype=float),
        )
    if path.origin != job.release:
        return (
            Decision(job.id, "unavailable", None, None, None, "Forecast origin does not match the job release", model_id),
            np.asarray([], dtype=float),
        )
    starts = len(windows)
    if not starts:
        return (
            Decision(job.id, "infeasible", None, None, None, "No half-hour start meets the deadline", model_id),
            np.asarray([], dtype=float),
        )

    values = np.maximum(np.asarray(path.mean, dtype=float), 0.0)
    needed = starts - 1 + job.slots
    if needed > len(values):
        return (
            Decision(
                job.id,
                "unavailable",
                None,
                None,
                None,
                "Forecast path does not cover every feasible candidate window",
                model_id,
            ),
            np.asarray([], dtype=float),
        )
    costs = np.correlate(values, job.energy_kwh, mode="valid")[:starts]
    if len(costs) != starts or not np.all(np.isfinite(costs)):
        return (
            Decision(job.id, "unavailable", None, None, None, "Forecast candidate costs are invalid", model_id),
            np.asarray(costs, dtype=float),
        )
    chosen_index = earliest_minimum(costs)
    start, finish = windows[chosen_index]
    reason = "Minimum integrated forecast cost; exact ties favor the earliest start"
    if path.status == "fallback":
        reason += "; fallback forecast"
    decision = Decision(
        job_id=job.id,
        status="scheduled",
        start=start,
        finish=finish,
        predicted_grams=float(costs[chosen_index]),
        reason=reason,
        model_id=model_id,
    )
    return decision, np.asarray(costs, dtype=float)


def _earliest_fallback(job: Job, model_id: str, reason: str) -> Decision:
    earliest = job.release
    finish = earliest + pd.Timedelta(hours=job.duration_hours)
    return Decision(
        job_id=job.id,
        status="scheduled",
        start=earliest,
        finish=finish,
        predicted_grams=None,
        reason=f"Forecast failure ({reason}); executed earliest feasible fallback",
        model_id=model_id,
    )


def _seeded_random_index(seed: int, job_id: str, candidate_count: int) -> int:
    digest = hashlib.blake2b(job_id.encode("utf-8"), digest_size=8).digest()
    stable_job_seed = int.from_bytes(digest, "little")
    rng = np.random.default_rng(
        np.random.SeedSequence([int(seed), stable_job_seed & 0xFFFFFFFF, stable_job_seed >> 32])
    )
    return int(rng.integers(0, candidate_count))


def _decision_row(
    job: Job,
    scenario: Mapping[str, object],
    policy: str,
    model_id: str | None,
    decision: Decision,
    realized_grams: float | None,
    *,
    fallback: bool = False,
    forecast_status: str | None = None,
    selected_model: str | None = None,
) -> dict[str, object]:
    waiting = (
        (decision.start - job.release).total_seconds() / 3600
        if decision.start is not None
        else np.nan
    )
    return {
        "scenario_id": scenario["scenario_id"],
        "is_default_scenario": bool(scenario["is_default"]),
        "job_id": job.id,
        "origin": job.release,
        "release": job.release,
        "deadline": job.deadline,
        "duration_hours": job.duration_hours,
        "slack_hours": float(scenario["slack_hours"]),
        "power_kw": job.power_kw,
        "pue": job.pue,
        "policy": policy,
        "model_id": model_id,
        "status": decision.status,
        "start": decision.start,
        "finish": decision.finish,
        "waiting_hours": waiting,
        "predicted_grams": decision.predicted_grams,
        "realized_grams": realized_grams,
        "fallback": fallback,
        "forecast_status": forecast_status,
        "reason": decision.reason,
        "validation_selected_model": selected_model,
    }


def _job_for(release: pd.Timestamp, scenario: Mapping[str, object], power_kw: float, pue: float) -> Job:
    scenario_id = str(scenario["scenario_id"])
    duration = float(scenario["duration_hours"])
    slack = float(scenario["slack_hours"])
    job_id = f"{scenario_id}@{release.isoformat()}"
    return Job(
        id=job_id,
        release=release,
        duration_hours=duration,
        deadline=release + pd.Timedelta(hours=duration + slack),
        power_kw=power_kw,
        pue=pue,
    )


def _mase_scale_for_origin(
    truth: pd.Series,
    origin: pd.Timestamp,
    publication_delay_slots: int,
    training_window_days: int,
) -> float:
    available_through = origin - (publication_delay_slots + 1) * SLOT
    window_start = origin - pd.Timedelta(days=training_window_days)
    past = truth.loc[(truth.index >= window_start) & (truth.index <= available_through)]
    if past.empty:
        return np.nan
    lag_index = past.index - pd.Timedelta(hours=24)
    lagged = truth.reindex(lag_index).to_numpy(dtype=float)
    current = past.to_numpy(dtype=float)
    valid = (lag_index >= window_start) & np.isfinite(current) & np.isfinite(lagged)
    return float(np.mean(np.abs(current[valid] - lagged[valid]))) if valid.any() else np.nan


def _forecast_metric_rows(
    stores: Mapping[str, _ForecastFile],
    truth: pd.Series,
    origins: pd.DatetimeIndex,
    start: pd.Timestamp,
    end: pd.Timestamp,
    path_cache: dict[tuple[str, int], tuple[ForecastPath | None, str, bool, np.ndarray | None]],
    publication_delay_slots: int,
    training_window_days: int,
) -> list[dict[str, object]]:
    metrics: dict[tuple[str, int, str], dict[str, list[float]]] = defaultdict(
        lambda: {"actual": [], "predicted": [], "std": [], "scale": []}
    )
    from .forecasting import mase_scales
    scales = dict(zip(origins.asi8, mase_scales(truth, origins, {
        "training_window_days": training_window_days,
        "publication_delay_slots": publication_delay_slots,
    }), strict=True))
    for model_id, store in stores.items():
        for origin in origins:
            cache_key = (model_id, origin.value)
            if cache_key not in path_cache:
                path_cache[cache_key] = _forecast_path(store, origin)
            path, _, _, std = path_cache[cache_key]
            if path is None:
                continue
            target_index = origin + np.arange(48, dtype=np.int64) * SLOT
            actual = truth.reindex(target_index).to_numpy(dtype=float)
            evaluation_mask = (target_index >= start) & (target_index < end) & np.isfinite(actual)
            scale = scales[origin.value]
            mean = path.mean

            for horizon in _HORIZONS:
                endpoint_mask = evaluation_mask[horizon - 1]
                if endpoint_mask:
                    key = (model_id, horizon, "endpoint")
                    metrics[key]["actual"].append(float(actual[horizon - 1]))
                    metrics[key]["predicted"].append(float(mean[horizon - 1]))
                    metrics[key]["std"].append(float(std[horizon - 1]) if std is not None else np.nan)
                    metrics[key]["scale"].append(scale)

                cumulative = evaluation_mask[:horizon]
                if cumulative.any():
                    key = (model_id, horizon, "cumulative")
                    metrics[key]["actual"].extend(actual[:horizon][cumulative].tolist())
                    metrics[key]["predicted"].extend(mean[:horizon][cumulative].tolist())
                    metrics[key]["std"].extend(
                        std[:horizon][cumulative].tolist()
                        if std is not None
                        else [np.nan] * int(cumulative.sum())
                    )
                    metrics[key]["scale"].extend([scale] * int(cumulative.sum()))

    rows: list[dict[str, object]] = []
    for (model_id, horizon, scope), values in sorted(metrics.items()):
        result = forecast_metrics(
            values["actual"],
            values["predicted"],
            mase_scale=values["scale"],
            std=values["std"],
        )
        rows.append(
            {
                "result_type": "forecast",
                "scenario_id": None,
                "duration_hours": np.nan,
                "slack_hours": np.nan,
                "policy": "forecast",
                "model_id": model_id,
                "metric_scope": scope,
                "interval_method": (
                    "normal_approximation_from_std" if result["interval_n"] else None
                ),
                "lead_slots": horizon,
                "n_eligible_jobs": np.nan,
                "n_scheduled": np.nan,
                "n_unavailable": np.nan,
                "n_infeasible": np.nan,
                "fallback_rate": np.nan,
                "mean_realized_grams": np.nan,
                "total_realized_grams": np.nan,
                "paired_n": np.nan,
                "paired_savings_grams": np.nan,
                "paired_savings_pct": np.nan,
                "oracle_regret_grams": np.nan,
                "mae": result["mae"],
                "rmse": result["rmse"],
                "bias": result["bias"],
                "mase": result["mase"],
                "interval_n": result["interval_n"],
                "interval_coverage80": result["interval_coverage80"],
                "interval_coverage95": result["interval_coverage95"],
                "window_cost_mae_grams": np.nan,
                "window_cost_n": np.nan,
                "candidate_rank_spearman": np.nan,
                "candidate_rank_n": np.nan,
            }
        )
    return rows


def _paired_rows(decisions: pd.DataFrame) -> pd.DataFrame:
    columns = (
        "scenario_id",
        "job_id",
        "origin",
        "release",
        "duration_hours",
        "slack_hours",
        "policy",
        "model_id",
        "baseline_grams",
        "policy_grams",
        "savings_grams",
        "savings_pct",
    )
    if decisions.empty:
        return pd.DataFrame(columns=columns)

    rows: list[dict[str, object]] = []
    for scenario_id, scenario_frame in decisions.groupby("scenario_id", sort=False):
        baseline = scenario_frame.loc[scenario_frame["policy"] == "earliest"].set_index("job_id")
        for (policy, model_id), frame in scenario_frame.loc[
            scenario_frame["policy"] != "earliest"
        ].groupby(["policy", "model_id"], dropna=False, sort=False):
            compared = frame.set_index("job_id").join(
                baseline[["status", "realized_grams"]].rename(
                    columns={"status": "baseline_status", "realized_grams": "baseline_grams"}
                ),
                how="inner",
            )
            compared = compared.loc[
                (compared["status"] == "scheduled")
                & (compared["baseline_status"] == "scheduled")
                & np.isfinite(compared["realized_grams"].to_numpy(dtype=float))
                & np.isfinite(compared["baseline_grams"].to_numpy(dtype=float))
            ]
            for job_id, record in compared.iterrows():
                baseline_grams = float(record["baseline_grams"])
                policy_grams = float(record["realized_grams"])
                saving = baseline_grams - policy_grams
                rows.append(
                    {
                        "scenario_id": scenario_id,
                        "job_id": job_id,
                        "origin": record["origin"],
                        "release": record["release"],
                        "duration_hours": record["duration_hours"],
                        "slack_hours": record["slack_hours"],
                        "policy": policy,
                        "model_id": None if pd.isna(model_id) else model_id,
                        "baseline_grams": baseline_grams,
                        "policy_grams": policy_grams,
                        "savings_grams": saving,
                        "savings_pct": (
                            100.0 * saving / baseline_grams if baseline_grams > 0 else np.nan
                        ),
                    }
                )
    return pd.DataFrame(rows, columns=columns)


def _summary_rows(
    decisions: pd.DataFrame,
    pairs: pd.DataFrame,
    selected_model: str | None,
    *,
    month: bool = False,
    window_costs: Mapping[str, Sequence[float]] | None = None,
    rank_scores: Mapping[str, Sequence[float]] | None = None,
) -> list[dict[str, object]]:
    if decisions.empty:
        return []

    work = decisions.copy()
    pair_frame = pairs.copy()
    group_columns = ["scenario_id", "policy", "model_id"]
    if month:
        work["month_utc"] = pd.to_datetime(work["release"], utc=True).dt.strftime("%Y-%m")
        pair_frame["month_utc"] = pd.to_datetime(pair_frame["release"], utc=True).dt.strftime("%Y-%m")
        group_columns.insert(0, "month_utc")
    rows: list[dict[str, object]] = []
    for keys, frame in work.groupby(group_columns, dropna=False, sort=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        labels = dict(zip(group_columns, keys, strict=True))
        status = frame["status"]
        realized = frame.loc[status == "scheduled", "realized_grams"].to_numpy(dtype=float)
        realized = realized[np.isfinite(realized)]
        pair_mask = np.ones(len(pair_frame), dtype=bool)
        for key in ("scenario_id", "policy", "model_id"):
            value = labels[key]
            if value is None or pd.isna(value):
                pair_mask &= pair_frame[key].isna().to_numpy()
            else:
                pair_mask &= (pair_frame[key] == value).to_numpy()
        if month:
            pair_mask &= (pair_frame["month_utc"] == labels["month_utc"]).to_numpy()
        paired = pair_frame.loc[pair_mask]
        baseline_total = float(paired["baseline_grams"].sum()) if not paired.empty else 0.0
        saved_total = float(paired["savings_grams"].sum()) if not paired.empty else 0.0
        oracle_rows = work.loc[
            (work["scenario_id"] == labels["scenario_id"]) & (work["policy"] == "oracle")
        ]
        if month:
            oracle_rows = oracle_rows.loc[oracle_rows["month_utc"] == labels["month_utc"]]
        oracle_by_job = oracle_rows.set_index("job_id")[["status", "realized_grams"]].rename(
            columns={"status": "oracle_status", "realized_grams": "oracle_grams"}
        )
        oracle_comparison = frame.set_index("job_id").join(oracle_by_job, how="inner")
        oracle_comparison = oracle_comparison.loc[
            (oracle_comparison["status"] == "scheduled")
            & (oracle_comparison["oracle_status"] == "scheduled")
            & np.isfinite(oracle_comparison["realized_grams"].to_numpy(dtype=float))
            & np.isfinite(oracle_comparison["oracle_grams"].to_numpy(dtype=float))
        ]
        oracle_regrets = (
            oracle_comparison["realized_grams"].to_numpy(dtype=float)
            - oracle_comparison["oracle_grams"].to_numpy(dtype=float)
        )

        model_id = labels["model_id"]
        if pd.isna(model_id):
            model_id = None
        model_costs = list((window_costs or {}).get(str(model_id), ())) if model_id is not None else []
        model_ranks = list((rank_scores or {}).get(str(model_id), ())) if model_id is not None else []
        rows.append(
            {
                "result_type": "scheduling",
                "month_utc": labels.get("month_utc"),
                "scenario_id": labels["scenario_id"],
                "duration_hours": float(frame["duration_hours"].iloc[0]),
                "slack_hours": float(frame["slack_hours"].iloc[0]),
                "policy": labels["policy"],
                "model_id": model_id,
                "metric_scope": "scenario",
                "lead_slots": np.nan,
                "n_eligible_jobs": int(len(frame)),
                "n_scheduled": int((status == "scheduled").sum()),
                "n_unavailable": int((status == "unavailable").sum()),
                "n_infeasible": int((status == "infeasible").sum()),
                "fallback_rate": float(frame["fallback"].mean()) if len(frame) else np.nan,
                "mean_realized_grams": float(np.mean(realized)) if len(realized) else np.nan,
                "total_realized_grams": float(np.sum(realized)) if len(realized) else np.nan,
                "paired_n": int(len(paired)),
                "paired_savings_grams": saved_total,
                "paired_savings_pct": (
                    100.0 * saved_total / baseline_total if baseline_total > 0 else np.nan
                ),
                "oracle_regret_grams": (
                    float(np.mean(oracle_regrets)) if len(oracle_regrets) else np.nan
                ),
                "oracle_regret_n": int(len(oracle_regrets)),
                "mae": np.nan,
                "rmse": np.nan,
                "bias": np.nan,
                "mase": np.nan,
                "interval_n": 0,
                "interval_coverage80": np.nan,
                "interval_coverage95": np.nan,
                "window_cost_mae_grams": float(np.mean(model_costs)) if model_costs else np.nan,
                "window_cost_n": len(model_costs),
                "candidate_rank_spearman": float(np.mean(model_ranks)) if model_ranks else np.nan,
                "candidate_rank_n": len(model_ranks),
                "validation_selected_model": selected_model,
                "selected_for_deployment": (
                    labels["policy"] == "forecast" and model_id == selected_model
                ),
            }
        )
    return rows


def _selection(
    stores: Mapping[str, _ForecastFile],
    truth: pd.Series,
    config: Mapping[str, object],
    path_cache: dict[tuple[str, int], tuple[ForecastPath | None, str, bool, np.ndarray | None]],
    power_kw: float,
    pue: float,
    default_duration: float,
    default_slack: float,
) -> tuple[str | None, pd.DataFrame, int, str]:
    study = _config_section(config, "study")
    if "validation_start" not in study or "validation_end" not in study:
        return None, pd.DataFrame(), 0, "Validation bounds are not configured"
    validation_start = _range_boundary(study["validation_start"], "validation_start")
    validation_end = _range_boundary(study["validation_end"], "validation_end")
    if validation_end <= validation_start:
        raise ValueError("validation_end must follow validation_start")
    scenario = {
        "scenario_id": f"duration_{default_duration:g}h_slack_{default_slack:g}h",
        "duration_hours": default_duration,
        "slack_hours": default_slack,
        "is_default": True,
    }
    score_rows: list[dict[str, object]] = []
    job_costs: dict[str, dict[str, float]] = defaultdict(dict)
    fallback_counts: dict[str, int] = defaultdict(int)
    validation_job_ids: set[str] = set()
    for release in _origins(validation_start, validation_end):
        if release + 48 * SLOT > validation_end:
            continue
        job = _job_for(release, scenario, power_kw, pue)
        if job.deadline > validation_end:
            continue
        truth_values, missing = _truth_window(truth, release, job.deadline)
        if missing:
            continue
        windows = _candidate_windows(job)
        realized_candidates = _candidate_truth_costs(job, truth_values, len(windows))
        validation_job_ids.add(job.id)
        for model_id, store in stores.items():
            cache_key = (model_id, release.value)
            if cache_key not in path_cache:
                path_cache[cache_key] = _forecast_path(store, release)
            path, reason, _, _ = path_cache[cache_key]
            if path is None:
                decision = _earliest_fallback(job, model_id, reason)
                fallback_counts[model_id] += 1
            else:
                decision, _ = _batch_recommend(job, path, windows)
                if decision.status != "scheduled":
                    decision = _earliest_fallback(job, model_id, decision.reason)
                    fallback_counts[model_id] += 1
                elif path.status == "fallback":
                    fallback_counts[model_id] += 1
            candidate_index = int(
                round((decision.start.value - release.value) / SLOT.value)
            )
            cost = float(realized_candidates[candidate_index])
            job_costs[model_id][job.id] = cost

    common_jobs = validation_job_ids
    scores: dict[str, float] = {}
    for model_id in stores:
        vals = [job_costs[model_id][job_id] for job_id in common_jobs if job_id in job_costs[model_id]]
        if vals:
            scores[model_id] = float(np.mean(vals))
            score_rows.append(
                {
                    "model_id": model_id,
                    "validation_common_jobs": len(vals),
                    "validation_mean_realized_grams": scores[model_id],
                    "validation_fallback_rate": fallback_counts[model_id] / len(vals),
                }
            )
    if not scores:
        return None, pd.DataFrame(score_rows), len(common_jobs), "No common validation decisions"

    best = min(scores.values())
    tolerance = best * 0.01 if best > 0 else 0
    tied = [model_id for model_id, score in scores.items() if score <= best + tolerance]
    scheduling = _config_section(config, "scheduling")
    simple_models = set(scheduling.get("simple_model_ids", ()))
    complexity = scheduling.get("model_complexity", {})
    operational_cost = scheduling.get("model_operational_cost", {})
    if not isinstance(complexity, Mapping):
        complexity = {}
    if not isinstance(operational_cost, Mapping):
        operational_cost = {}

    def simple_rank(model_id: str) -> tuple[float, float, str]:
        tokens = ("mean", "naive", "baseline", "last")
        inferred_simple = any(token in model_id.lower() for token in tokens)
        complexity_rank = float(complexity.get(model_id, 0 if model_id in simple_models or inferred_simple else math.inf))
        return (complexity_rank, float(operational_cost.get(model_id, 0)), model_id)

    preferred = [
        model_id
        for model_id in tied
        if model_id in simple_models
        or any(token in model_id.lower() for token in ("mean", "naive", "baseline", "last"))
        or model_id in complexity
    ]
    if len(tied) > 1 and preferred:
        selected = min(preferred, key=simple_rank)
        basis = "validation minimum with 1% simpler-model tie rule"
    else:
        selected = min(tied, key=lambda model_id: (scores[model_id], model_id))
        basis = "lowest mean validation realized grams"
    for row in score_rows:
        row["within_1pct_of_best"] = row["model_id"] in tied
        row["selected"] = row["model_id"] == selected
        row["selection_basis"] = basis
    return selected, pd.DataFrame(score_rows), len(common_jobs), basis


def _write_table(frame: pd.DataFrame, filename: Path) -> None:
    temp_path = filename.with_name(f".{filename.name}.{os.getpid()}.tmp")
    try:
        if filename.suffix == ".parquet":
            frame.to_parquet(temp_path, index=False)
        else:
            frame.to_csv(temp_path, index=False)
        os.replace(temp_path, filename)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def primary_backtest(
    truth: pd.Series,
    forecast_files: Mapping[str, Path],
    start,
    end,
    outdir,
    config: Mapping[str, object],
    *,
    experiment_root=None,
    synthetic=False,
) -> dict[str, object]:
    """Run the isolated-job historical backtest and persist its evidence tables."""
    from .artifacts import authorize_period
    frozen = authorize_period(truth, start, end, experiment_root=experiment_root, synthetic=synthetic)
    if frozen is not None:
        expected = frozen["protocol"]["config"]
        if utc(start) != utc(expected["study"]["test_start"]) or utc(end) != utc(expected["study"]["test_end"]):
            raise ValueError("Official backtest range differs from frozen test window")
        expected_scheduling = {
            **expected["scheduling"],
            "model_complexity": {
                value["name"]: sum(value["order"][::2]) + value["seasonal_order"][0]
                + value["seasonal_order"][2] + 1
                + int(not value["order"][1] and not value["seasonal_order"][1])
                for value in frozen["protocol"]["family_finalists"]
            },
            "simple_model_ids": ["persistence", "daily_naive", "weekly_naive", "calendar_mean"],
            "selected_model_id": frozen["protocol"]["deployment_model"],
            "selection_metadata": frozen["protocol"]["scheduling_selection"],
        }
        if config["study"] != expected["study"] or config["scheduling"] != expected_scheduling:
            raise ValueError("Backtest settings differ from frozen protocol")
        if config["scheduling"].get("selected_model_id") != frozen["protocol"]["deployment_model"]:
            raise ValueError("Backtest model differs from validation selection")
    truth_series = _canonical_truth(truth)
    start_utc = _range_boundary(start, "start")
    end_utc = _range_boundary(end, "end")
    if end_utc <= start_utc:
        raise ValueError("end must follow start")
    if not isinstance(config, Mapping):
        raise TypeError("config must be a mapping")

    stores = _load_forecast_files(
        forecast_files, require_metadata=not synthetic,
        default_delay_slots=int(_config_value(config, "study", "publication_delay_slots", 1)),
    )
    scenarios, default_duration, default_slack = _scenarios(config)
    scheduling = _config_section(config, "scheduling")
    power_kw = float(scheduling.get("power_kw", 0.4))
    pue = float(scheduling.get("pue", 1.2))
    if not np.isfinite(power_kw) or power_kw <= 0 or not np.isfinite(pue) or pue < 1:
        raise ValueError("scheduling power_kw must be positive and pue must be at least one")
    seed = int(_config_value(config, "study", "seed", scheduling.get("seed", 1729)))
    publication_delay_slots = int(
        _config_value(config, "study", "publication_delay_slots", 1)
    )
    training_window_days = int(_config_value(config, "study", "window_days", 180))
    if publication_delay_slots < 0:
        raise ValueError("publication_delay_slots must be nonnegative")
    if training_window_days < 1:
        raise ValueError("window_days must be positive")

    path_cache: dict[
        tuple[str, int], tuple[ForecastPath | None, str, bool, np.ndarray | None]
    ] = {}
    frozen_metadata = scheduling.get("selection_metadata", {})
    if not isinstance(frozen_metadata, Mapping):
        raise ValueError("selection_metadata must be a mapping")
    frozen_metadata = dict(frozen_metadata)
    frozen_model = scheduling.get("selected_model_id")
    if frozen_model is not None:
        selected_model = str(frozen_model).strip()
        if not selected_model:
            raise ValueError("selected_model_id cannot be empty")
        if selected_model not in stores:
            raise ValueError(
                f"Frozen selected_model_id {selected_model!r} has no matching forecast file"
            )
        validation_n = int(
            frozen_metadata.get(
                "validation_common_jobs",
                frozen_metadata.get("n_validation_jobs", 0),
            )
        )
        selection_basis = str(
            frozen_metadata.get("selection_basis", "frozen validation-selected model")
        )
        supplied_scores = frozen_metadata.get(
            "model_scores",
            frozen_metadata.get("scores", {}),
        )
        if not isinstance(supplied_scores, Mapping):
            raise ValueError("selection_metadata.model_scores must be a mapping")
        score_rows = []
        for model_id, score in supplied_scores.items():
            details = dict(score) if isinstance(score, Mapping) else {
                "validation_mean_realized_grams": score
            }
            score_rows.append(
                {
                    "model_id": str(model_id),
                    "validation_common_jobs": validation_n,
                    **details,
                    "selected": str(model_id) == selected_model,
                    "selection_basis": selection_basis,
                }
            )
        if not score_rows:
            score_rows.append(
                {
                    "model_id": selected_model,
                    "validation_common_jobs": validation_n,
                    "selected": True,
                    "selection_basis": selection_basis,
                }
            )
        validation_scores = pd.DataFrame(score_rows)
    else:
        study = _config_section(config, "study")
        validation_start = (
            _range_boundary(study["validation_start"], "validation_start")
            if "validation_start" in study
            else None
        )
        validation_end = (
            _range_boundary(study["validation_end"], "validation_end")
            if "validation_end" in study
            else None
        )
        if start_utc == validation_start and end_utc == validation_end:
            selected_model, validation_scores, validation_n, selection_basis = _selection(
                stores,
                truth_series,
                config,
                path_cache,
                power_kw,
                pue,
                default_duration,
                default_slack,
            )
        else:
            selected_model = None
            validation_scores = pd.DataFrame()
            validation_n = 0
            selection_basis = (
                "Selection skipped outside validation window; supply frozen selected_model_id"
            )

    origins = _origins(start_utc, end_utc)
    decisions: list[dict[str, object]] = []
    exclusions: list[dict[str, object]] = []
    candidate_rows: list[dict[str, object]] = []
    window_errors: dict[str, list[float]] = defaultdict(list)
    rank_scores: dict[str, list[float]] = defaultdict(list)
    random_seed = int(scheduling.get("random_seed", seed))

    default_scenario_id = f"duration_{default_duration:g}h_slack_{default_slack:g}h"
    for release in origins:
        if release + 48 * SLOT > end_utc:
            for scenario in scenarios:
                job = _job_for(release, scenario, power_kw, pue)
                exclusions.append(
                    {
                        "job_id": job.id,
                        "scenario_id": scenario["scenario_id"],
                        "origin": release,
                        "release": release,
                        "deadline": job.deadline,
                        "duration_hours": job.duration_hours,
                        "slack_hours": scenario["slack_hours"],
                        "reason": "48-slot forecast path extends beyond evaluation end",
                        "missing_truth_slots": 0,
                    }
                )
            continue
        for scenario in scenarios:
            job = _job_for(release, scenario, power_kw, pue)
            if job.deadline > end_utc:
                exclusions.append(
                    {
                        "job_id": job.id,
                        "scenario_id": scenario["scenario_id"],
                        "origin": release,
                        "release": release,
                        "deadline": job.deadline,
                        "duration_hours": job.duration_hours,
                        "slack_hours": scenario["slack_hours"],
                        "reason": "Feasible window extends beyond evaluation end",
                        "missing_truth_slots": 0,
                    }
                )
                continue

            truth_values, missing_slots = _truth_window(truth_series, release, job.deadline)
            if missing_slots:
                exclusions.append(
                    {
                        "job_id": job.id,
                        "scenario_id": scenario["scenario_id"],
                        "origin": release,
                        "release": release,
                        "deadline": job.deadline,
                        "duration_hours": job.duration_hours,
                        "slack_hours": scenario["slack_hours"],
                        "reason": "Feasible decision window contains missing realized truth",
                        "missing_truth_slots": missing_slots,
                    }
                )
                continue

            windows = _candidate_windows(job)
            starts = [window[0] for window in windows]
            costs = _candidate_truth_costs(job, truth_values, len(windows))
            job_id = job.id
            earliest = Decision(
                job_id=job_id,
                status="scheduled",
                start=starts[0],
                finish=starts[0] + pd.Timedelta(hours=job.duration_hours),
                predicted_grams=None,
                reason="Earliest feasible start",
                model_id="earliest",
            )
            decisions.append(
                _decision_row(
                    job,
                    scenario,
                    "earliest",
                    None,
                    earliest,
                    float(costs[0]),
                    selected_model=selected_model,
                )
            )

            random_index = _seeded_random_index(random_seed, job_id, len(starts))
            random_start = starts[random_index]
            random_decision = Decision(
                job_id=job_id,
                status="scheduled",
                start=random_start,
                finish=random_start + pd.Timedelta(hours=job.duration_hours),
                predicted_grams=None,
                reason="Seeded random feasible start",
                model_id="seeded_random",
            )
            decisions.append(
                _decision_row(
                    job,
                    scenario,
                    "seeded_random",
                    None,
                    random_decision,
                    float(costs[random_index]),
                    selected_model=selected_model,
                )
            )

            oracle_index = earliest_minimum(costs)
            oracle_start = starts[oracle_index]
            oracle_decision = Decision(
                job_id=job_id,
                status="scheduled",
                start=oracle_start,
                finish=oracle_start + pd.Timedelta(hours=job.duration_hours),
                predicted_grams=None,
                reason="Hindsight carbon oracle; unattainable lower bound",
                model_id="oracle",
            )
            decisions.append(
                _decision_row(
                    job,
                    scenario,
                    "oracle",
                    "oracle",
                    oracle_decision,
                    float(costs[oracle_index]),
                    selected_model=selected_model,
                )
            )

            for model_id, store in stores.items():
                cache_key = (model_id, release.value)
                if cache_key not in path_cache:
                    path_cache[cache_key] = _forecast_path(store, release)
                path, missing_reason, fallback, _ = path_cache[cache_key]
                if path is None:
                    decision = _earliest_fallback(job, model_id, missing_reason)
                    fallback = True
                    forecast_status = "fallback_earliest"
                else:
                    decision, _ = _batch_recommend(job, path, windows)
                    if decision.status != "scheduled":
                        decision = _earliest_fallback(job, model_id, decision.reason)
                        fallback = True
                        forecast_status = "fallback_earliest"
                    else:
                        forecast_status = "fallback" if fallback else "ok"
                realized = None
                if decision.status == "scheduled" and decision.start is not None:
                    candidate_index = int(
                        round((decision.start.value - release.value) / SLOT.value)
                    )
                    realized = float(costs[candidate_index])
                decisions.append(
                    _decision_row(
                        job,
                        scenario,
                        "forecast",
                        model_id,
                        decision,
                        realized,
                        fallback=fallback,
                        forecast_status=forecast_status,
                        selected_model=selected_model,
                    )
                )

                if scenario["scenario_id"] == default_scenario_id:
                    candidate_frame = candidates(job, path)
                    predicted = candidate_frame["predicted_grams"].to_numpy(dtype=float)
                    statuses = candidate_frame["status"].to_numpy()
                    if len(predicted) == len(costs) and np.all(statuses == "feasible"):
                        window_errors[model_id].extend(np.abs(predicted - costs).tolist())
                        if len(costs) > 1 and np.ptp(predicted) > 0 and np.ptp(costs) > 0:
                            correlation = spearmanr(predicted, costs).statistic
                            if np.isfinite(correlation):
                                rank_scores[model_id].append(float(correlation))
                    for candidate in candidate_frame.to_dict("records"):
                        candidate_index = candidate["candidate_index"]
                        candidate_rows.append(
                            {
                                **candidate,
                                "scenario_id": scenario["scenario_id"],
                                "job_id": job_id,
                                "origin": release,
                                "policy": "forecast",
                                "forecast_status": forecast_status,
                                "realized_grams": (
                                    float(costs[int(candidate_index)])
                                    if candidate_index is not None
                                    else np.nan
                                ),
                                "selected": (
                                    decision.status == "scheduled"
                                    and candidate["start"] == decision.start
                                ),
                                "cost_source": "forecast_mean",
                            }
                        )

            if scenario["scenario_id"] == default_scenario_id:
                for index, (candidate_start, candidate_finish) in enumerate(
                    zip(starts, (start + pd.Timedelta(hours=job.duration_hours) for start in starts), strict=True)
                ):
                    candidate_rows.append(
                        {
                            "candidate_index": index,
                            "start": candidate_start,
                            "finish": candidate_finish,
                            "waiting_hours": (candidate_start - release).total_seconds() / 3600,
                            "predicted_grams": np.nan,
                            "status": "feasible",
                            "reason": "Hindsight carbon oracle candidate",
                            "model_id": "oracle",
                            "scenario_id": scenario["scenario_id"],
                            "job_id": job_id,
                            "origin": release,
                            "policy": "oracle",
                            "forecast_status": None,
                            "realized_grams": float(costs[index]),
                            "selected": index == oracle_index,
                            "cost_source": "observed_actual",
                        }
                    )

    decisions_frame = pd.DataFrame(decisions)
    if not decisions_frame.empty:
        delay = decisions_frame.model_id.map({name: store.publication_delay_slots for name, store in stores.items()})
        delay = delay.fillna(publication_delay_slots).astype(int)
        decisions_frame["decision_time"] = decisions_frame.origin
        decisions_frame["information_cutoff"] = decisions_frame.origin - pd.to_timedelta((delay + 1) * 30, unit="min")
        decisions_frame["forecast_id"] = [
            f"{row.model_id}@{row.origin.isoformat()}#{stores[row.model_id].artifact_hash[:12]}"
            if row.policy == "forecast" and row.model_id in stores else None
            for row in decisions_frame.itertuples()
        ]
    exclusions_frame = pd.DataFrame(exclusions)
    candidates_frame = pd.DataFrame(candidate_rows)
    pairs_frame = _paired_rows(decisions_frame)
    scheduling_rows = _summary_rows(
        decisions_frame,
        pairs_frame,
        selected_model,
        window_costs=window_errors,
        rank_scores=rank_scores,
    )
    forecast_rows = _forecast_metric_rows(
        stores,
        truth_series,
        origins,
        start_utc,
        end_utc,
        path_cache,
        publication_delay_slots,
        training_window_days,
    )
    selection_rows = [
        {
            "result_type": "model_selection",
            "scenario_id": default_scenario_id,
            "duration_hours": default_duration,
            "slack_hours": default_slack,
            "policy": "validation_selection",
            "model_id": row["model_id"],
            "metric_scope": "common_validation_jobs",
            "lead_slots": np.nan,
            "n_eligible_jobs": row.get("validation_common_jobs", validation_n),
            "validation_fallback_rate": row.get("validation_fallback_rate", np.nan),
            "validation_mean_realized_grams": row.get("validation_mean_realized_grams", np.nan),
            "selected_for_deployment": row.get("selected", False),
            "validation_selected_model": selected_model,
            "selection_basis": row.get("selection_basis", selection_basis),
            "selection_metadata": json.dumps(frozen_metadata, sort_keys=True, default=str),
        }
        for row in validation_scores.to_dict("records")
    ]
    if not selection_rows:
        selection_rows.append(
            {
                "result_type": "model_selection",
                "scenario_id": default_scenario_id,
                "duration_hours": default_duration,
                "slack_hours": default_slack,
                "policy": "validation_selection",
                "model_id": selected_model,
                "metric_scope": "frozen_or_skipped",
                "n_eligible_jobs": validation_n,
                "selected_for_deployment": False,
                "validation_selected_model": selected_model,
                "selection_basis": selection_basis,
                "selection_metadata": json.dumps(frozen_metadata, sort_keys=True, default=str),
            }
        )
    summary_frame = pd.DataFrame(scheduling_rows + forecast_rows + selection_rows)
    monthly_rows = _summary_rows(decisions_frame, pairs_frame, selected_model, month=True)
    monthly_frame = pd.DataFrame(monthly_rows)

    bootstrap_resamples = int(_config_value(config, "study", "bootstrap_resamples", 2000))
    bootstrap_blocks = tuple(
        int(value) for value in _config_value(config, "study", "bootstrap_block_days", (3, 7, 14))
    )
    if 7 not in bootstrap_blocks:
        bootstrap_blocks = (*bootstrap_blocks, 7)
    primary_pairs = pairs_frame.loc[
        (pairs_frame["scenario_id"] == default_scenario_id)
        & (pairs_frame["policy"] == "forecast")
        & (pairs_frame["model_id"] == selected_model)
    ] if selected_model is not None else pairs_frame.iloc[0:0]
    bootstrap_frame = paired_moving_block_bootstrap(
        primary_pairs,
        start_utc,
        end_utc,
        block_days=bootstrap_blocks,
        n_resamples=bootstrap_resamples,
        seed=seed,
    )
    bootstrap_frame["is_primary_block"] = bootstrap_frame["block_days"] == 7
    bootstrap_frame["scenario_id"] = default_scenario_id
    bootstrap_frame["policy"] = "forecast"
    bootstrap_frame["model_id"] = selected_model
    bootstrap_frame["validation_selected_model"] = selected_model

    output_dir = Path(outdir)
    output_dir.mkdir(parents=True, exist_ok=True)
    tables = {
        "primary_decisions.parquet": decisions_frame,
        "primary_candidates.parquet": candidates_frame,
        "primary_exclusions.csv": exclusions_frame,
        "primary_summary.csv": summary_frame,
        "primary_pairs.parquet": pairs_frame,
        "primary_bootstrap.csv": bootstrap_frame,
        "primary_monthly.csv": monthly_frame,
    }
    for name, frame in tables.items():
        _write_table(frame, output_dir / name)

    return {
        "decisions": decisions_frame,
        "candidates": candidates_frame,
        "exclusions": exclusions_frame,
        "summary": summary_frame,
        "pairs": pairs_frame,
        "bootstrap": bootstrap_frame,
        "monthly": monthly_frame,
        "selected_model": selected_model,
        "selection_basis": selection_basis,
        "selection_metadata": frozen_metadata,
        "validation_common_jobs": validation_n,
    }
