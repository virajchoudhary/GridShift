import numpy as np
import pandas as pd
import pytest

from gridshift.data import as_of, normalize, audit
from gridshift.domain import ForecastPath, Job, utc
from gridshift.artifacts import require_freeze


def records(start, count):
    times = pd.date_range(start, periods=count, freq="30min")
    return [{"from": str(t), "to": str(t+pd.Timedelta(minutes=30)),
             "intensity": {"actual": 0, "forecast": 100, "index": "low"}} for t in times]


def test_preceding_slot_and_overlapping_chunks():
    rows = records("2024-03-30T23:30Z", 49)
    frame = normalize(rows, "2024-03-31T00:00Z", "2024-04-01T00:00Z")
    assert len(frame) == 48
    assert frame.actual.eq(0).all()
    assert frame.index[0] == pd.Timestamp("2024-03-31T00:00Z")


def test_collector_writes_portable_manifest_paths(tmp_path, monkeypatch):
    import json
    from types import SimpleNamespace
    from gridshift.data import collect
    import gridshift.data as module
    payload = json.dumps({"data": records("2030-01-01T00:00Z", 48)}).encode()
    response = SimpleNamespace(content=payload, status_code=200, headers={},
                               raise_for_status=lambda: None)
    monkeypatch.setattr(module.requests.Session, "get", lambda *args, **kwargs: response)
    monkeypatch.setattr(module.time, "sleep", lambda _: None)
    collect(tmp_path, "2030-01-01T00:00Z", "2030-01-02T00:00Z")
    manifest = json.loads((tmp_path / "data/manifest.json").read_text())
    assert manifest["chunks"][0]["path"] == "data/raw/2030-01-01_2030-01-02.json.gz"


@pytest.mark.parametrize("start,count", [("2024-03-31T00:00Z",46), ("2024-10-26T23:00Z",50)])
def test_dst_civil_days_do_not_create_missing_utc_intervals(start,count):
    rows = records(start,count)
    end = pd.Timestamp(start)+pd.Timedelta(minutes=30*count)
    frame = normalize(rows,start,end)
    assert len(frame) == count
    assert frame.index.is_unique
    assert frame.actual.notna().all()


def test_null_actual_does_not_use_provider_forecast():
    rows = records("2024-01-01T00:00Z",2)
    rows[0]["intensity"]["actual"] = None
    frame = normalize(rows,"2024-01-01T00:00Z","2024-01-01T01:00Z")
    assert np.isnan(frame.actual.iloc[0])
    assert frame.provider_forecast.iloc[0] == 100


def test_conflicting_duplicates_rejected():
    rows = records("2024-01-01T00:00Z",1)
    rows += [{**rows[0], "intensity":{"actual":1,"forecast":100,"index":"low"}}]
    with pytest.raises(ValueError,match="Conflicting"):
        normalize(rows,"2024-01-01T00:00Z","2024-01-01T01:00Z")


def test_availability_delay_and_future_mutation():
    series = pd.Series(range(10),index=pd.date_range("2024-01-01T00:00Z",periods=10,freq="30min"))
    origin = pd.Timestamp("2024-01-01T03:00Z")
    before = as_of(series,origin)
    series.loc[series.index > before.index[-1]] = -1000
    pd.testing.assert_series_equal(before,as_of(series,origin))
    assert before.index[-1] == origin-pd.Timedelta(hours=1)


def test_naive_time_invalid_job_and_forecast_rejected():
    with pytest.raises(ValueError):
        utc("2024-01-01")
    with pytest.raises(ValueError):
        Job("x","2024-01-01T00:00Z",2,"2024-01-01T01:00Z")
    with pytest.raises(ValueError):
        ForecastPath("2024-01-01T00:00Z",np.array([1,np.nan]),"x","2023-12-31T00:00Z")


def test_test_set_requires_freeze(tmp_path):
    with pytest.raises(ValueError,match="locked"):
        require_freeze(tmp_path)


def test_monthly_gate_applies_to_locked_test_not_development(tmp_path):
    index = pd.date_range("2022-01-01T00:00Z","2026-01-01T00:00Z",freq="30min",inclusive="left")
    frame = pd.DataFrame({"actual":100.0},index=index)
    positions = np.flatnonzero(index.strftime("%Y-%m") == "2023-10")
    frame.iloc[positions[:100],0] = np.nan
    quality = audit(tmp_path,frame)
    assert quality["minimum_monthly_coverage"] < .95
    assert quality["minimum_test_monthly_coverage"] == 1
    assert quality["data_gate_pass"]
    frame.loc["2025-10-01":"2025-10-04","actual"] = np.nan
    assert not audit(tmp_path,frame)["data_gate_pass"]
