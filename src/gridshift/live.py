"""Trusted local inference and explicit operational failure states."""

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from . import baselines
from .artifacts import digest, require_freeze, write_json
from .data import normalize, as_of, load, SOURCE, retry_seconds
from .domain import ForecastPath, SLOT, grid_time
from .forecasting import (
    ModelSpec, _eligible_window, _capture_state, _vectorized_state_forecasts,
    _inverse_distribution, fit_model, load_bundle, save_bundle,
)
from .study import forecast_config, run_dir


def historical_path(root, config, origin, model_id, stage="test"):
    root = Path(root)
    origin = grid_time(origin)
    out = run_dir(root, config, stage)
    mapping = json.loads((out / "forecast_store.json").read_text())
    filename = (root / mapping[model_id]).resolve()
    if not filename.is_relative_to(root.resolve()):
        raise ValueError("Forecast artifact is outside trusted project")
    metadata = json.loads(filename.with_suffix(".json").read_text())
    if metadata.get("forecast_sha256") != digest(filename.read_bytes()):
        raise ValueError("Forecast artifact checksum mismatch")
    with np.load(filename, allow_pickle=False) as arrays:
        position = np.searchsorted(arrays["origins_ns"], origin.value)
        if position >= len(arrays["origins_ns"]) or arrays["origins_ns"][position] != origin.value:
            raise ValueError("No issued forecast at requested origin")
        cutoff = origin - (1 + config["study"]["publication_delay_slots"]) * SLOT
        path = ForecastPath(origin, arrays["mean"][position], model_id, cutoff,
                            arrays["std"][position],
                            "fallback" if arrays["fallback"][position] else "ok")
        bounds = {k: arrays[k][position].copy() for k in ("lower80", "upper80", "lower95", "upper95")}
    return path, bounds


def build_deployment(root, config):
    root = Path(root)
    frozen = require_freeze(root, config)
    name = frozen["protocol"]["deployment_model"]
    cutoff_origin = pd.Timestamp(config["study"]["test_end"])
    cfg = forecast_config(config)
    series = load(root).actual
    history, start, cutoff = _eligible_window(series, cutoff_origin, cfg)
    dest = root / "artifacts/deployment"
    dest.mkdir(parents=True, exist_ok=True)
    manifest = {"schema_version": 1, "model_id": name, "protocol_hash": frozen["protocol_hash"],
                "data_hash": frozen["data_hash"], "origin": str(cutoff_origin), "training_cutoff": str(cutoff),
                "library_versions": {"numpy": np.__version__, "pandas": pd.__version__}}
    if name in baselines.BASELINES:
        history.to_frame("actual").to_parquet(dest / "baseline_history.parquet")
        manifest["kind"] = "baseline"
        manifest["file"] = "baseline_history.parquet"
    else:
        spec = next(ModelSpec.from_dict(v) for v in frozen["protocol"]["family_finalists"] if v["name"] == name)
        fitted = fit_model(history, spec, cfg, training_start=start, training_cutoff=cutoff)
        if not fitted.result.mle_retvals["converged"]:
            raise ValueError("Deployment refit failed convergence")
        save_bundle(fitted, dest / "model.json")
        manifest["kind"] = "classical"
        manifest["file"] = "model.json"
        expected = fitted.result.get_forecast(49).predicted_mean
        restored = load_bundle(dest / "model.json")
        np.testing.assert_allclose(expected, restored.result.get_forecast(49).predicted_mean, atol=1e-7)
    manifest["file_hash"] = digest((dest / manifest["file"]).read_bytes())
    write_json(dest / "deployment.json", manifest)
    path, state = predict_live(root, config, history, cutoff_origin)
    write_json(dest / "prediction_fixture.json", {
        "origin": str(cutoff_origin), "mean": path.mean.tolist(),
        "std": path.std.tolist(), "state": state,
        "scope": "2026-01-01 conditional prediction fixture, not a scored test result",
    })
    manifest["fixture_hash"] = digest((dest / "prediction_fixture.json").read_bytes())
    write_json(dest / "deployment.json", manifest)
    return manifest


def trusted_manifest(root):
    root = Path(root)
    freeze = require_freeze(root)
    dest = root / "artifacts/deployment"
    manifest = json.loads((dest / "deployment.json").read_text())
    if manifest["schema_version"] != 1 or manifest["protocol_hash"] != freeze["protocol_hash"] or manifest["data_hash"] != freeze["data_hash"]:
        raise ValueError("Incompatible deployment bundle")
    study = freeze["protocol"]["config"]["study"]
    expected_origin = grid_time(study["test_end"])
    expected_cutoff = expected_origin - (1 + study["publication_delay_slots"]) * SLOT
    if (
        grid_time(manifest["origin"]) != expected_origin
        or grid_time(manifest["training_cutoff"]) != expected_cutoff
        or manifest["model_id"] != freeze["protocol"]["deployment_model"]
    ):
        raise ValueError("Deployment training period or model differs from frozen protocol")
    path = (dest / manifest["file"]).resolve()
    if not path.is_relative_to(dest.resolve()) or digest(path.read_bytes()) != manifest["file_hash"]:
        raise ValueError("Deployment bundle integrity failed")
    if manifest["library_versions"] != {"numpy": np.__version__, "pandas": pd.__version__}:
        raise ValueError("Incompatible deployment library versions")
    if "fixture_hash" in manifest and digest((dest / "prediction_fixture.json").read_bytes()) != manifest["fixture_hash"]:
        raise ValueError("Deployment prediction fixture integrity failed")
    return manifest


def verify_deployment_fixture(root, config):
    manifest = trusted_manifest(root)
    fixture = json.loads((Path(root) / "artifacts/deployment/prediction_fixture.json").read_text())
    origin = grid_time(fixture["origin"])
    observations = load(root).actual
    path, state = predict_live(root, config, observations, origin)
    np.testing.assert_allclose(path.mean, fixture["mean"], rtol=1e-8, atol=1e-7)
    np.testing.assert_allclose(path.std, fixture["std"], rtol=1e-8, atol=1e-7)
    return {"verified": True, "model_id": manifest["model_id"], "origin": str(origin),
            "max_mean_absolute_difference": float(np.max(np.abs(path.mean - fixture["mean"]))),
            "observation_state": state["status"], "realized_result": "not scored"}


def fetch_recent(origin, session=None):
    origin = grid_time(origin)
    start = origin - pd.Timedelta(days=7)
    url = f"{SOURCE}/intensity/{start:%Y-%m-%dT%H:%MZ}/{origin:%Y-%m-%dT%H:%MZ}"
    client = session or requests
    for attempt in range(3):
        try:
            response = client.get(url, timeout=(5, 20))
            if response.status_code == 429 or response.status_code >= 500:
                response.raise_for_status()
            break
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status is not None and status != 429 and status < 500:
                raise
            if attempt == 2:
                raise
            pause = retry_seconds(getattr(getattr(exc, "response", None), "headers", {}).get("Retry-After"), attempt)
            if pause > 10:
                raise ValueError("API retry exceeds the interactive wait budget; refresh later") from exc
            time.sleep(pause)
    response.raise_for_status()
    content = response.json()
    if not isinstance(content.get("data"), list):
        raise ValueError("API response has no observation array")
    return normalize(content["data"], start, origin).actual


def operational_state(series, origin, delay_slots=1):
    origin = grid_time(origin)
    history = as_of(series, origin, delay_slots).dropna()
    if history.empty:
        return {"status": "missing", "recommendation_enabled": False, "last_observation": None}
    latest = history.index[-1]
    age = (origin - (latest + SLOT)).total_seconds() / 3600
    return {"status": "stale" if age > 2 else "fresh", "recommendation_enabled": age <= 2,
            "last_observation": str(latest), "age_hours": age}


def predict_live(root, config, observations, origin):
    origin = grid_time(origin)
    require_freeze(root, config)
    manifest = trusted_manifest(root)
    if origin < grid_time(manifest["origin"]):
        raise ValueError("Live origin precedes the trusted bundle training period; use stored historical forecasts")
    state = operational_state(observations, origin, config["study"]["publication_delay_slots"])
    if not state["recommendation_enabled"]:
        raise ValueError(f"Carbon recommendation disabled: {state['status']} observations")
    cfg = forecast_config(config)
    eligible = as_of(observations, origin, cfg["publication_delay_slots"])
    name = manifest["model_id"]
    if manifest["kind"] == "baseline":
        archived = pd.read_parquet(Path(root) / "artifacts/deployment/baseline_history.parquet").actual
        combined = pd.concat([archived, eligible]).sort_index()
        combined = combined[~combined.index.duplicated(keep="last")]
        mean, std, fallback = baselines.path(combined, origin, name, cfg)
    else:
        fitted = load_bundle(Path(root) / "artifacts/deployment/model.json")
        if fitted.training_cutoff != grid_time(manifest["training_cutoff"]) or fitted.training_cutoff >= origin:
            raise ValueError("Loaded model training cutoff is incompatible with live request")
        cutoff = eligible.index[-1]
        grid = pd.date_range(fitted.training_cutoff + SLOT, cutoff, freq=SLOT)
        update = eligible.reindex(grid).to_numpy(float)
        if fitted.spec.transform == "log1p":
            update = np.log1p(update)
        result = fitted.result.extend(update) if len(update) else fitted.result
        mean_state, cov = _capture_state(result)
        delay = cfg["publication_delay_slots"]
        horizon = cfg["horizon_slots"]
        mean_z, var_z = _vectorized_state_forecasts(result, mean_state[None], cov[None], horizon + delay)
        mean, std, *_ = _inverse_distribution(mean_z[0, delay:], var_z[0, delay:], fitted.spec.transform)
        fallback = False
    return ForecastPath(grid_time(origin), mean, name, eligible.index[-1], std, "fallback" if fallback else "ok"), state


def joint_job_costs(fitted, job, chosen_start, simulations=1000, seed=1729):
    if simulations < 100:
        raise ValueError("At least 100 joint paths are required")
    if chosen_start < job.release or chosen_start + pd.Timedelta(hours=job.duration_hours) > job.deadline:
        raise ValueError("Joint cost start violates job constraints")
    mean, covariance = _capture_state(fitted.result)
    from .forecasting import _forecast_system
    transition, design, intercept, obs_intercept, noise, obs_variance = _forecast_system(fitted.result)
    rng = np.random.default_rng(seed)
    states = rng.multivariate_normal(mean, covariance, size=simulations, check_valid="ignore")
    count = int((job.release - fitted.training_cutoff) / SLOT) + 48
    paths = np.empty((simulations, count))
    for i in range(count):
        states = states @ transition.T + intercept + rng.multivariate_normal(np.zeros(len(mean)), noise, size=simulations, check_valid="ignore")
        paths[:, i] = states @ design + obs_intercept + rng.normal(0, np.sqrt(obs_variance), simulations)
    if fitted.spec.transform == "log1p":
        paths = np.expm1(paths)
    first = int((chosen_start - fitted.training_cutoff) / SLOT) - 1
    costs = np.maximum(paths[:, first:first + job.slots], 0) @ job.energy_kwh
    return {"mean_grams": float(costs.mean()), "std_grams": float(costs.std()),
            "median_grams": float(np.median(costs)), "lower80": float(np.quantile(costs, .1)),
            "upper80": float(np.quantile(costs, .9)), "lower95": float(np.quantile(costs, .025)),
            "upper95": float(np.quantile(costs, .975)), "simulations": simulations,
            "method": "Joint conditional state-space paths with fixed fitted parameters"}
