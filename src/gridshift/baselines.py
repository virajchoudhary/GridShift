"""Past-only simple forecast controls in the same compact artifact format."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

from .domain import SLOT, grid_time
from .artifacts import digest
from .forecasting import _config_dict, _eligible_window, _forecast_metrics, _write_json

BASELINES = ("persistence", "daily_naive", "weekly_naive", "calendar_mean")


def path(series, origin, model_id, config=None):
    cfg = _config_dict(config)
    history, _, cutoff = _eligible_window(series, grid_time(origin), cfg)
    observed = history.dropna()
    if observed.empty:
        raise ValueError("No eligible observed history")
    latest = float(observed.iloc[-1])
    result = np.empty(48)
    fallback = False
    calendar = observed.groupby([observed.index.weekday, observed.index.hour * 2 + observed.index.minute // 30]).mean()
    for i in range(48):
        target = origin + i * SLOT
        if model_id == "persistence":
            result[i] = latest
        elif model_id == "calendar_mean":
            key = (target.weekday(), target.hour * 2 + target.minute // 30)
            result[i] = calendar.get(key, latest)
        elif model_id in ("daily_naive", "weekly_naive"):
            period = 48 if model_id == "daily_naive" else 336
            donor = target - period * SLOT
            while donor > cutoff:
                donor -= period * SLOT
            value = history.get(donor, np.nan)
            result[i] = value if np.isfinite(value) else latest
            fallback |= not np.isfinite(value)
        else:
            raise ValueError("Unknown baseline")
    raw = history.to_numpy(float)
    error = raw[48:] - raw[:-48]
    finite = error[np.isfinite(error)]
    scale = float(np.sqrt(np.mean(finite**2))) if len(finite) else 0.
    return result, np.full(48, scale), fallback


def rolling(series, start, end, outdir, config=None, *, experiment_root=None, synthetic=False):
    cfg = _config_dict(config)
    from .artifacts import authorize_period
    frozen = authorize_period(series, start, end, experiment_root=experiment_root, synthetic=synthetic)
    if frozen is not None:
        from .study import forecast_config
        if cfg != _config_dict(forecast_config(frozen["protocol"]["config"])):
            raise ValueError("Baseline settings differ from frozen protocol")
    origins = pd.date_range(grid_time(start), grid_time(end) - 48 * SLOT, freq=SLOT)
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    files = {}
    grid = series.asfreq(SLOT)
    raw = grid.to_numpy(float)
    origin_pos = grid.index.get_indexer(origins)
    cutoff_pos = origin_pos - 1 - cfg["publication_delay_slots"]
    last_positions = np.maximum.accumulate(np.where(np.isfinite(raw), np.arange(len(raw)), -1))
    latest = raw[last_positions[cutoff_pos]]
    target_pos = origin_pos[:, None] + np.arange(48)
    error2 = np.zeros(len(raw))
    count = np.zeros(len(raw), dtype=int)
    valid = np.isfinite(raw[48:]) & np.isfinite(raw[:-48])
    error2[48:] = np.where(valid, (raw[48:] - raw[:-48])**2, 0)
    count[48:] = valid
    sp, cp = np.r_[0., error2.cumsum()], np.r_[0, count.cumsum()]
    lower = np.maximum(0, origin_pos - cfg["training_window_days"] * 48 + 48)
    upper = cutoff_pos + 1
    n = cp[upper] - cp[lower]
    scale = np.sqrt(np.divide(sp[upper] - sp[lower], n, out=np.zeros(len(n)), where=n > 0))
    std = np.broadcast_to(scale[:, None], target_pos.shape).copy()
    calendar_mean = np.broadcast_to(latest[:, None], target_pos.shape).copy()
    calendar_keys = np.asarray(grid.index.weekday * 48 + grid.index.hour * 2 + grid.index.minute // 30)
    target_keys = (calendar_keys[origin_pos, None] + np.arange(48)) % 336
    for key in range(336):
        positions = np.flatnonzero((calendar_keys == key) & np.isfinite(raw))
        sums = np.r_[0., np.cumsum(raw[positions])]
        a = np.searchsorted(positions, origin_pos - cfg["training_window_days"] * 48)
        b = np.searchsorted(positions, cutoff_pos, side="right")
        counts = b - a
        average = np.divide(sums[b] - sums[a], counts, out=latest.copy(), where=counts > 0)
        row, col = np.where(target_keys == key)
        calendar_mean[row, col] = average[row]
    for model_id in BASELINES:
        fallbacks = np.zeros(len(origins), dtype=bool)
        if model_id == "calendar_mean":
            mean = calendar_mean
        elif model_id == "persistence":
            mean = np.broadcast_to(latest[:, None], target_pos.shape).copy()
        else:
            period = 48 if model_id == "daily_naive" else 336
            donor = target_pos - period
            donor -= np.maximum(0, np.ceil((donor - cutoff_pos[:, None]) / period)).astype(int) * period
            donor_values = raw[donor]
            finite = np.isfinite(donor_values)
            mean = np.where(finite, donor_values, latest[:, None])
            fallbacks = ~finite.all(axis=1)
        bounds = [mean + norm.ppf(q) * std for q in (.1, .9, .025, .975)]
        filename = out / (model_id + ".npz")
        np.savez_compressed(filename, origins_ns=origins.asi8, mean=mean.astype("float32"),
                            std=std.astype("float32"), fallback=fallbacks,
                            **dict(zip(("lower80", "upper80", "lower95", "upper95"), bounds)))
        with np.load(filename, allow_pickle=False) as saved:
            metrics = _forecast_metrics(series, origins, saved["mean"], saved["std"],
                *(saved[k] for k in ("lower80", "upper80", "lower95", "upper95")), saved["fallback"], cfg)
        metrics.to_csv(filename.with_suffix(".metrics.csv"), index=False)
        _write_json(filename.with_suffix(".json"), {
            "model_id": model_id, "origin_count": len(origins), "fallback_count": int(fallbacks.sum()),
            "forecast_sha256": digest(filename.read_bytes()),
            "interval_note": "Diagnostic Gaussian bounds using eligible daily-difference RMS; not calibrated guarantees",
        })
        print(f"BASELINE {model_id} origins={len(origins)}", flush=True)
        files[model_id] = filename
    return files
