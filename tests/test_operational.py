import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
import requests

from gridshift.data import collect, retry_seconds
from gridshift.live import operational_state, fetch_recent, trusted_manifest, joint_job_costs


def test_stale_missing_and_fresh_states():
    origin = pd.Timestamp("2023-01-02T00:00Z")
    series = pd.Series([50., 60.], index=pd.date_range(origin - pd.Timedelta(hours=1.5), periods=2, freq="30min"))
    assert operational_state(series, origin)["recommendation_enabled"]
    assert operational_state(series, origin + pd.Timedelta(hours=3))["status"] == "stale"
    assert operational_state(series * np.nan, origin)["status"] == "missing"


def test_retry_after_seconds_are_respected():
    assert retry_seconds("900", 0) == 900
    assert 2 <= retry_seconds("bad", 1) <= 2.5


def test_collector_retry_and_raw_cache(monkeypatch, tmp_path):
    records = [{"from": "2023-01-01T00:00Z", "to": "2023-01-01T00:30Z",
                "intensity": {"actual": 0, "forecast": 5, "index": "low"}}]
    class Response:
        def __init__(self, status, content):
            self.status_code = status
            self.content = content
            self.headers = {"Retry-After": "2", "Content-Type": "application/json"}
        def raise_for_status(self):
            if self.status_code >= 400:
                raise requests.HTTPError(str(self.status_code))
    responses = iter([Response(429, b""), Response(200, json.dumps({"data": records}).encode())])
    session = SimpleNamespace(headers={}, get=lambda *a, **kw: next(responses))
    delays = []
    monkeypatch.setattr("gridshift.data.requests.Session", lambda: session)
    monkeypatch.setattr("gridshift.data.time.sleep", delays.append)
    frame = collect(tmp_path, "2023-01-01T00:00Z", "2023-01-01T00:30Z")
    assert delays[0] == 2
    assert frame.actual.iloc[0] == 0
    cached = collect(tmp_path, "2023-01-01T00:00Z", "2023-01-01T00:30Z")
    pd.testing.assert_frame_equal(frame, cached)


@pytest.mark.parametrize("payload", [b"<html>failure</html>", b'{"wrong": []}'])
def test_malformed_response_cannot_be_saved(monkeypatch, tmp_path, payload):
    response = SimpleNamespace(status_code=200, content=payload, headers={}, raise_for_status=lambda: None)
    session = SimpleNamespace(headers={}, get=lambda *a, **kw: response)
    monkeypatch.setattr("gridshift.data.requests.Session", lambda: session)
    with pytest.raises(ValueError):
        collect(tmp_path, "2023-01-01T00:00Z", "2023-01-01T00:30Z")
    assert not (tmp_path / "data/manifest.json").exists()


def test_live_retry_is_bounded_and_never_ignores_long_retry_after(monkeypatch):
    response = requests.Response()
    response.status_code = 429
    response.headers["Retry-After"] = "900"
    calls = []
    session = SimpleNamespace(get=lambda *a, **kw: calls.append(kw) or response)
    monkeypatch.setattr("gridshift.live.time.sleep", lambda seconds: pytest.fail("Must not sleep 900 seconds"))
    with pytest.raises(ValueError, match="wait budget"):
        fetch_recent("2026-01-02T00:00Z", session)
    assert len(calls) == 1


def test_trusted_deployment_refuses_corruption_and_library_mismatch(monkeypatch, tmp_path):
    from gridshift.artifacts import digest, write_json
    root = tmp_path / "artifacts/deployment"
    root.mkdir(parents=True)
    payload = root / "baseline_history.parquet"
    payload.write_bytes(b"trusted fixture")
    manifest = {
        "schema_version": 1, "protocol_hash": "protocol", "data_hash": "data",
        "file": payload.name, "file_hash": digest(payload.read_bytes()),
        "library_versions": {"numpy": np.__version__, "pandas": pd.__version__},
        "origin": "2026-01-01T00:00Z", "training_cutoff": "2025-12-31T23:00Z",
        "model_id": "daily_naive",
    }
    monkeypatch.setattr("gridshift.live.require_freeze", lambda root: {
        "protocol_hash": "protocol", "data_hash": "data", "protocol": {
            "config": {"study": {"test_end": "2026-01-01T00:00Z", "publication_delay_slots": 1}},
            "deployment_model": "daily_naive",
        },
    })
    write_json(root / "deployment.json", manifest)
    assert trusted_manifest(tmp_path)["file"] == payload.name
    manifest["library_versions"]["numpy"] = "0.0"
    write_json(root / "deployment.json", manifest)
    with pytest.raises(ValueError, match="library"):
        trusted_manifest(tmp_path)
    payload.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="integrity"):
        trusted_manifest(tmp_path)


def test_joint_cost_simulation_matches_synthetic_ar_mean():
    from gridshift.domain import Job
    from gridshift.forecasting import ModelSpec, fit_model
    rng = np.random.default_rng(31)
    values = np.empty(600)
    values[0] = 100
    for i in range(1, len(values)):
        values[i] = 20 + .8 * values[i - 1] + rng.normal(0, 1)
    history = pd.Series(values, index=pd.date_range("2023-01-01", periods=600, freq="30min", tz="UTC"))
    cutoff = history.index[-1]
    fit = fit_model(history, ModelSpec("AR1", "AR", (1, 0, 0), (0, 0, 0, 0)), training_cutoff=cutoff)
    origin = cutoff + pd.Timedelta(hours=1)
    job = Job("joint", origin, 2, origin + pd.Timedelta(hours=12))
    result = joint_job_costs(fit, job, origin, simulations=10000, seed=41)
    expected = np.asarray(fit.result.get_forecast(5).predicted_mean)[1:] @ job.energy_kwh
    assert abs(result["mean_grams"] - expected) < 5 * result["std_grams"] / 100
    assert result["lower95"] <= result["lower80"] <= result["median_grams"] <= result["upper80"] <= result["upper95"]


def test_live_model_cannot_forecast_before_its_training_period(monkeypatch):
    from gridshift.live import predict_live
    monkeypatch.setattr("gridshift.live.require_freeze", lambda *args: {})
    monkeypatch.setattr("gridshift.live.trusted_manifest", lambda root: {"origin": "2026-01-01T00:00Z"})
    with pytest.raises(ValueError, match="precedes"):
        predict_live(".", {}, pd.Series(dtype=float), "2025-06-01T00:00Z")
