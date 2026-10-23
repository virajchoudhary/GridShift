"""Training-only fit feasibility pilot, not a comparative speed benchmark."""

import gzip
import json
import os
import platform
import time
import warnings
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np
import pandas as pd
import psutil
import statsmodels
from statsmodels.tsa.statespace.sarimax import SARIMAX

from gridshift.artifacts import write_json
from gridshift.data import normalize

ROOT = Path(__file__).resolve().parents[1]


def main():
    frames = []
    for path in sorted((ROOT / "data/raw").glob("2023-*.json.gz")):
        left, right = path.name.split(".")[0].split("_")
        records = json.loads(gzip.decompress(path.read_bytes()))["data"]
        frames.append(normalize(records, left+"T00:00Z", right+"T00:00Z"))
    series = pd.concat(frames).actual.sort_index().asfreq("30min")
    cutoff = pd.Timestamp("2023-12-31T23:00Z")
    series = series.loc[(series.index > cutoff-pd.Timedelta(days=180)) & (series.index <= cutoff)]
    if len(series) != 8640 or series.index[-1] != cutoff:
        raise ValueError("The training-only pilot needs a complete canonical 180-day grid")
    specs = [
        ("AR", (2,0,0),(0,0,0,0)),
        ("MA", (0,0,2),(0,0,0,0)),
        ("ARMA", (1,0,1),(0,0,0,0)),
        ("ARIMA", (1,1,1),(0,0,0,0)),
        ("SARIMA_AR", (1,0,0),(1,0,0,48)),
        ("SARIMA_MA", (0,0,1),(0,0,1,48)),
    ]
    rows = []
    process = psutil.Process()
    for name, order, seasonal in specs:
        began = time.perf_counter()
        with warnings.catch_warnings(record=True) as captured:
            fitted = SARIMAX(series, order=order, seasonal_order=seasonal,
                             trend="c" if order[1] == 0 else "n",
                             enforce_stationarity=True, enforce_invertibility=True).fit(
                                 disp=False, maxiter=80, low_memory=True, cov_type="none")
        elapsed = time.perf_counter()-began
        row = {
            "model": name, "order": order, "seasonal_order": seasonal,
            "elapsed_seconds": elapsed, "iterations": fitted.mle_retvals.get("iterations"),
            "converged": bool(fitted.mle_retvals.get("converged")),
            "finite_parameters": bool(np.all(np.isfinite(fitted.params))),
            "rss_after_fit_mb": process.memory_info().rss / 1024**2,
            "aic": float(fitted.aic), "k_states": fitted.model.k_states,
            "warnings": [str(item.message) for item in captured],
        }
        rows.append(row)
        print(json.dumps(row), flush=True)
        write_json(ROOT/"artifacts/pilot/fit_pilot.json", {
            "purpose": "single-run training-only feasibility, not comparative speedup",
            "training_start": str(series.index[0]), "training_end": str(series.index[-1]),
            "slots": len(series), "missing": int(series.isna().sum()), "maxiter":80,
            "cpu_count":os.cpu_count(), "platform":platform.platform(),
            "cpu_percent_snapshot":psutil.cpu_percent(), "statsmodels":statsmodels.__version__,
            "rss_is_not_peak_memory":True, "fits":rows,
        })


if __name__ == "__main__":
    main()
