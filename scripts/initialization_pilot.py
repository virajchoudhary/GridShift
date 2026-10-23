"""Interleaved training-only initialization feasibility and likelihood audit."""

import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import time
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX
from gridshift.data import load
from gridshift.artifacts import write_json


def main():
    root = Path(__file__).resolve().parents[1]
    series = load(root).actual
    cutoff = pd.Timestamp("2023-12-31T23:00Z")
    series = series.loc[(series.index > cutoff-pd.Timedelta(days=180)) & (series.index <= cutoff)]
    if len(series) != 8640:
        raise ValueError("Unexpected training pilot grid")
    rows = []
    for repeat in range(5):
        for initialization in ("stationary", "approximate_diffuse"):
            began = time.perf_counter()
            with warnings.catch_warnings(record=True) as captured:
                model = SARIMAX(series, order=(1,0,0),seasonal_order=(1,0,0,48),trend="c",
                                initialization=initialization,loglikelihood_burn=96,
                                enforce_stationarity=True,enforce_invertibility=True)
                fitted = model.fit(disp=False,maxiter=80,low_memory=True,cov_type="none")
            row = {"repeat":repeat,"initialization":initialization,
                   "seconds":time.perf_counter()-began,"converged":bool(fitted.mle_retvals["converged"]),
                   "parameters":fitted.params.tolist(),"aic":float(fitted.aic),
                   "n_effective":len(series)-96,"burn":96,"warnings":[str(w.message) for w in captured]}
            rows.append(row)
            print(row,flush=True)
            write_json(root/"artifacts/pilot/initialization_pilot.json",{
                "scope":"Training2023 only;5interleaved runs; sharedburn96; BLAS1thread",
                "training_start":str(series.index[0]),"training_end":str(series.index[-1]),"runs":rows})


if __name__ == "__main__":
    main()
