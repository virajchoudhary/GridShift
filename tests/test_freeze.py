import pytest

from gridshift.artifacts import freeze_protocol, require_freeze, software_digest, write_json, digest


def test_missing_freeze_blocks_test(tmp_path):
    with pytest.raises(ValueError, match="locked"):
        require_freeze(tmp_path)


def test_freeze_binds_config_software_and_data(tmp_path):
    src = tmp_path / "src/gridshift"
    src.mkdir(parents=True)
    source = src / "data.py"
    source.write_text("VERSION = 1")
    dataset = tmp_path / "data/normalized/carbon.parquet"
    dataset.parent.mkdir(parents=True)
    dataset.write_bytes(b"synthetic fixture bytes")
    write_json(tmp_path / "data/manifest.json", {"normalized_hash": digest(dataset.read_bytes())})
    config = {"study": {"test_start": "2025-01-01T00:00Z"}}
    evidence = tmp_path / "validation.csv"
    evidence.write_text("verified")
    freeze_protocol(tmp_path, {"config": config, "software_hash": software_digest(tmp_path),
                              "validation_artifact_hashes": {"validation.csv": digest(evidence.read_bytes())}})
    assert require_freeze(tmp_path, config)["schema_version"] == 1
    with pytest.raises(ValueError, match="Configuration"):
        require_freeze(tmp_path, {"changed": True})
    evidence.write_text("altered")
    with pytest.raises(ValueError, match="Validation artifact"):
        require_freeze(tmp_path, config)
    evidence.write_text("verified")
    source.write_text("VERSION = 2")
    with pytest.raises(ValueError, match="Software"):
        require_freeze(tmp_path, config)
    source.write_text("VERSION = 1")
    dataset.write_bytes(b"altered bytes")
    with pytest.raises(ValueError, match="Dataset bytes"):
        require_freeze(tmp_path, config)
    dataset.write_bytes(b"synthetic fixture bytes")
    write_json(tmp_path / "data/manifest.json", {"normalized_hash": "changed_data"})
    with pytest.raises(ValueError, match="Dataset"):
        require_freeze(tmp_path, config)


def test_lower_level_experiments_cannot_bypass_2025_lock(tmp_path):
    import pandas as pd
    from gridshift.forecasting import ModelSpec, rolling_forecasts
    from gridshift.evaluation import primary_backtest
    from gridshift.baselines import rolling
    series = pd.Series(100., index=pd.date_range("2024-01-01", periods=100, freq="30min", tz="UTC"))
    start, end = "2025-01-01T00:00Z", "2025-01-03T00:00Z"
    spec = ModelSpec("AR1", "AR", (1, 0, 0), (0, 0, 0, 0))
    with pytest.raises(ValueError, match="locked"):
        rolling_forecasts(series, spec, start, end, tmp_path / "forecast")
    with pytest.raises(ValueError, match="locked"):
        primary_backtest(series, {}, start, end, tmp_path / "backtest", {})
    with pytest.raises(ValueError, match="locked"):
        rolling(series, start, end, tmp_path / "baseline")
    assert not any(tmp_path.iterdir())


def test_official_series_cannot_use_synthetic_escape():
    import pandas as pd
    from gridshift.artifacts import authorize_period
    series = pd.Series([100.])
    series.attrs["gridshift_source"] = "NESO"
    with pytest.raises(ValueError, match="Official"):
        authorize_period(series, "2025-01-01T00:00Z", "2025-01-03T00:00Z", synthetic=True)


@pytest.mark.parametrize("change", ["random_seed", "selection_metadata"])
def test_backtest_rejects_unfrozen_overrides_before_forecast_loading(monkeypatch, tmp_path, change):
    import copy
    import pandas as pd
    from gridshift import artifacts, evaluation
    from gridshift.baselines import BASELINES
    expected = {
        "study": {"seed": 1729, "test_start": "2025-01-01T00:00Z", "test_end": "2025-01-03T00:00Z"},
        "scheduling": {"power_kw": .4, "pue": 1.2},
    }
    frozen = {"protocol": {
        "config": expected, "family_finalists": [],
        "deployment_model": "daily_naive",
        "scheduling_selection": {"validation_common_jobs": 25, "selection_basis": "validation"},
    }}
    config = copy.deepcopy(expected)
    config["scheduling"].update(
        model_complexity={}, simple_model_ids=list(BASELINES),
        selected_model_id="daily_naive",
        selection_metadata=copy.deepcopy(frozen["protocol"]["scheduling_selection"]),
    )
    monkeypatch.setattr(artifacts, "authorize_period", lambda *args, **kwargs: frozen)
    def stop_at_loader(*args, **kwargs):
        raise AssertionError("forecast loader reached")
    monkeypatch.setattr(evaluation, "_load_forecast_files", stop_at_loader)
    truth = pd.Series(100., index=pd.date_range("2024-01-01", periods=4, freq="30min", tz="UTC"))
    start, end = "2025-01-01T00:00Z", "2025-01-03T00:00Z"
    with pytest.raises(AssertionError, match="loader reached"):
        evaluation.primary_backtest(truth, {}, start, end, tmp_path, config)
    if change == "random_seed":
        config["scheduling"]["random_seed"] = 7
    else:
        config["scheduling"]["selection_metadata"]["validation_common_jobs"] = 1
    with pytest.raises(ValueError, match="settings differ"):
        evaluation.primary_backtest(truth, {}, start, end, tmp_path, config)
    assert not any(tmp_path.iterdir())


def test_test_series_must_match_frozen_source_values(monkeypatch, tmp_path):
    import pandas as pd
    from gridshift.artifacts import authorize_period
    index = pd.date_range("2025-01-01", periods=4, freq="30min", tz="UTC")
    series = pd.Series(100., index=index, name="actual")
    target = tmp_path / "data/normalized/carbon.parquet"
    target.parent.mkdir(parents=True)
    series.to_frame().to_parquet(target)
    monkeypatch.setattr("gridshift.artifacts.require_freeze", lambda root: {"fixture": True})
    assert authorize_period(series, index[0], index[-1], experiment_root=tmp_path)["fixture"]
    altered = series.copy()
    altered.iloc[-1] = 1.
    with pytest.raises(ValueError, match="series differs"):
        authorize_period(altered, index[0], index[-1], experiment_root=tmp_path)
    with pytest.raises(ValueError, match="series differs"):
        authorize_period(series.iloc[:2], index[0], index[-1], experiment_root=tmp_path)
