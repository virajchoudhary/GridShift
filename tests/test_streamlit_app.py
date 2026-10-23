from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pandas as pd
import pytest
import requests
import streamlit as st
import yaml
from streamlit.testing.v1 import AppTest


LANE_ROOT = Path(__file__).resolve().parents[1]
APP_FILE = LANE_ROOT / "app" / "streamlit_app.py"
PACKAGE_ROOT = LANE_ROOT
sys.path.insert(0, str(PACKAGE_ROOT / "src"))


def _app_test(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AppTest:
    st.cache_data.clear()
    shutil.copytree(
        PACKAGE_ROOT / "configs",
        tmp_path / "configs",
    )
    monkeypatch.setenv("GRIDSHIFT_ROOT", str(tmp_path))
    app = AppTest.from_file(str(APP_FILE), default_timeout=20)
    app.session_state["gridshift_research_mode"] = True
    return app


def _simple_app_test(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AppTest:
    app = _app_test(tmp_path, monkeypatch)
    app.session_state["gridshift_research_mode"] = False
    return app


def _write_fake_frozen_results(root: Path) -> tuple[dict, Path]:
    from gridshift.study import run_dir

    config = yaml.safe_load((root / "configs" / "study.yaml").read_text(encoding="utf-8"))
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "manifest.json").write_text(
        json.dumps({"normalized_hash": "fixture-data-hash"}),
        encoding="utf-8",
    )

    test_run = run_dir(root, config, "test")
    test_run.mkdir(parents=True, exist_ok=True)
    (test_run / "forecast_store.json").write_text(
        json.dumps({"fixture-model": "artifacts/fake/fixture-model.npz"}),
        encoding="utf-8",
    )

    protocol = {
        "study_id": "fixture-study",
        "software_hash": "fixture-software-hash",
        "forecast_champion": "fixture-model",
        "best_classical": "fixture-model",
        "strongest_simple": "calendar_mean",
        "deployment_model": "fixture-model",
    }
    freeze = {
        "data_hash": "fixture-data-hash",
        "protocol_hash": "fixture-protocol-hash",
        "protocol": protocol,
    }
    result = {
        "schema_version": 1,
        "experimental_status": "EXECUTED_FROZEN_2025",
        "study_id": protocol["study_id"],
        "data_hash": freeze["data_hash"],
        "protocol_hash": freeze["protocol_hash"],
        "software_hash": protocol["software_hash"],
        "forecast_champion": protocol["forecast_champion"],
        "best_classical": protocol["best_classical"],
        "strongest_simple": protocol["strongest_simple"],
        "deployment_model": protocol["deployment_model"],
        "validation_metrics": [{"model_id": "fixture-model", "horizon": 1, "mae": 10.0}],
        "test_metrics": [{"model_id": "fixture-test-record", "horizon": 1, "mae": 11.0}],
        "primary_summary": [
            {"duration_hours": 2, "slack_hours": 6, "month": "2025-01", "policy": "fixture"},
            {"duration_hours": 4, "slack_hours": 12, "month": "2025-02", "policy": "fixture"},
        ],
        "primary_bootstrap": [{"block_days": 7, "estimate_savings_pct": 0.0}],
        "queue_summary": [{"scenario": "fixture", "status": "scheduled"}],
        "limitations": ["Fixture-only AppTest evidence."],
    }
    result_path = root / "artifacts" / "results.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result), encoding="utf-8")
    return freeze, test_run


def _alert_text(elements: list) -> str:
    return "\n".join(str(element.value) for element in elements)


def test_default_schedule_has_bounded_utc_controls_and_missing_artifact_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gridshift import live

    calls: list[pd.Timestamp] = []
    monkeypatch.setattr(live, "fetch_recent", lambda origin: calls.append(origin))
    app = _app_test(tmp_path, monkeypatch).run()

    assert not app.exception
    assert app.title[0].value == "GridShift"
    assert any(widget.label == "Origin date (UTC)" for widget in app.date_input)
    assert any(widget.label == "Origin time (UTC)" for widget in app.time_input)
    assert any(widget.label == "Duration (hours)" for widget in app.number_input)
    assert any(widget.label == "Slack after duration (hours)" for widget in app.number_input)
    assert any(widget.label == "IT power (kW)" for widget in app.number_input)
    assert any(widget.label == "PUE" for widget in app.number_input)
    assert any(widget.label == "Forecast model" for widget in app.selectbox)
    assert any("earliest feasible fallback" in item.value.casefold() for item in app.warning)
    assert "2025 test forecast is hidden" in _alert_text(app.warning)
    assert calls == []


def test_workload_controls_update_energy_and_explicit_deadline_can_be_infeasible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app_test(tmp_path, monkeypatch).run()
    duration = next(widget for widget in app.number_input if widget.label == "Duration (hours)")
    duration.set_value(1.0)
    app = app.run()
    energy = next(metric for metric in app.metric if metric.label == "Facility energy")
    assert energy.value == "0.480 kWh"

    override = next(widget for widget in app.checkbox if widget.label == "Set a hard deadline offset")
    override.set_value(True)
    app = app.run()
    deadline = next(
        widget
        for widget in app.number_input
        if widget.label == "Hard deadline after release (hours)"
    )
    deadline.set_value(0.5)
    app = app.run()

    assert not app.exception
    assert "Job is infeasible" in _alert_text(app.error)
    assert "No forecast is scored" in _alert_text(app.caption)


def test_live_mode_does_not_fetch_on_rerun_and_reports_provider_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gridshift import live

    calls: list[pd.Timestamp] = []

    def unavailable(origin: pd.Timestamp) -> pd.Series:
        calls.append(origin)
        raise requests.ConnectionError("offline test fixture")

    monkeypatch.setattr(live, "fetch_recent", unavailable)
    app = _app_test(tmp_path, monkeypatch).run()
    mode = next(widget for widget in app.radio if widget.label == "Data mode")
    mode.set_value("Live")
    app = app.run()

    assert not app.exception
    assert calls == []
    assert "have not been fetched" in _alert_text(app.info)

    refresh = next(button for button in app.button if button.label == "Fetch / refresh observations")
    refresh.click()
    app = app.run()
    assert len(calls) == 1
    assert "Live API refresh failed" in _alert_text(app.warning)
    assert not app.exception


def test_stale_live_observations_disable_carbon_ranking(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gridshift import live

    def stale_series(origin: pd.Timestamp) -> pd.Series:
        index = pd.DatetimeIndex([origin - pd.to_timedelta(5, unit="h")])
        return pd.Series([120.0], index=index, name="actual")

    monkeypatch.setattr(live, "fetch_recent", stale_series)
    app = _app_test(tmp_path, monkeypatch).run()
    next(widget for widget in app.radio if widget.label == "Data mode").set_value("Live")
    app = app.run()
    next(button for button in app.button if button.label == "Fetch / refresh observations").click()
    app = app.run()

    assert not app.exception
    assert "Observation state: stale" in _alert_text(app.warning)
    assert "Carbon recommendation is disabled" in _alert_text(app.warning)
    assert any("Earliest feasible fallback" in item.value for item in app.warning)


def test_failed_refresh_disables_ranking_even_when_an_old_snapshot_is_retained(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gridshift import live

    calls: list[pd.Timestamp] = []

    def fail_after_first_success(origin: pd.Timestamp) -> pd.Series:
        calls.append(origin)
        if len(calls) == 1:
            index = pd.DatetimeIndex([origin - pd.to_timedelta(1.5, unit="h")])
            return pd.Series([120.0], index=index, name="actual")
        raise requests.ConnectionError("offline test fixture")

    monkeypatch.setattr(live, "fetch_recent", fail_after_first_success)
    app = _app_test(tmp_path, monkeypatch).run()
    next(widget for widget in app.radio if widget.label == "Data mode").set_value("Live")
    app = app.run()
    next(button for button in app.button if button.label == "Fetch / refresh observations").click()
    app = app.run()
    assert len(calls) == 1

    next(widget for widget in app.checkbox if widget.label == "Bypass the 15-minute response cache").set_value(True)
    app = app.run()
    next(button for button in app.button if button.label == "Fetch / refresh observations").click()
    app = app.run()

    assert len(calls) == 2
    assert not app.exception
    assert "Carbon recommendation is disabled until a successful refresh" in _alert_text(app.warning)
    assert any("Earliest feasible fallback" in item.value for item in app.warning)
    assert "Forecast-ranked start" not in _alert_text(app.info)


def test_verified_fixture_results_unlock_test_paths_metrics_and_backtest_filters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gridshift import artifacts, live

    app = _app_test(tmp_path, monkeypatch)
    freeze, _ = _write_fake_frozen_results(tmp_path)
    monkeypatch.setattr(artifacts, "require_freeze", lambda root, config: freeze)
    calls: list[tuple[str, str]] = []

    def fake_historical_path(root, config, origin, model_id, stage="test"):
        calls.append((stage, model_id))
        return None, {}

    monkeypatch.setattr(live, "historical_path", fake_historical_path)
    app.run()

    assert not app.exception
    assert calls == [("test", "fixture-model")]
    assert "Earliest feasible fallback" in _alert_text(app.warning)

    next(widget for widget in app.radio if widget.label == "View").set_value("Model comparison")
    app.run()
    assert not app.exception
    assert any("fixture-test-record" in str(table.value) for table in app.dataframe)

    next(widget for widget in app.radio if widget.label == "View").set_value("Backtests")
    app.run()
    assert not app.exception
    assert any(widget.label == "Duration filter" for widget in app.multiselect)
    assert any(widget.label == "Slack filter" for widget in app.multiselect)
    assert any(widget.label == "Month filter" for widget in app.multiselect)


def test_hash_mismatched_results_hide_test_forecasts_metrics_and_backtests(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gridshift import artifacts, live

    app = _app_test(tmp_path, monkeypatch)
    freeze, _ = _write_fake_frozen_results(tmp_path)
    results_path = tmp_path / "artifacts" / "results.json"
    results = json.loads(results_path.read_text(encoding="utf-8"))
    results["data_hash"] = "tampered-data-hash"
    results_path.write_text(json.dumps(results), encoding="utf-8")
    monkeypatch.setattr(artifacts, "require_freeze", lambda root, config: freeze)
    path_calls: list[str] = []
    monkeypatch.setattr(
        live,
        "historical_path",
        lambda root, config, origin, model_id, stage="test": path_calls.append(stage),
    )

    app.run()
    assert not app.exception
    assert path_calls == []
    assert "does not match the verified protocol freeze" in _alert_text(app.warning)
    model_selector = next(widget for widget in app.selectbox if widget.label == "Forecast model")
    assert "fixture-model" not in model_selector.options

    next(widget for widget in app.radio if widget.label == "View").set_value("Model comparison")
    app.run()
    assert not app.exception
    assert "fixture-test-record" not in "\n".join(str(table.value) for table in app.dataframe)
    assert "2025 test artifacts are hidden" in _alert_text(app.warning)

    next(widget for widget in app.radio if widget.label == "View").set_value("Backtests")
    app.run()
    assert not app.exception
    assert "fixture" not in "\n".join(str(table.value) for table in app.dataframe)
    assert "was not accepted" in _alert_text(app.warning)
    assert path_calls == []


def test_data_evidence_summarizes_only_the_fake_source_missingness_ledger(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _app_test(tmp_path, monkeypatch).run()
    ledger_path = tmp_path / "artifacts" / "data" / "source_missingness.csv"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "interval_start_utc": [
                "2024-01-01T00:00:00Z",
                "2024-01-01T00:30:00Z",
                "2024-01-01T01:00:00Z",
            ],
            "reason": ["absent_interval", "absent_interval", "explicit_null_actual"],
        }
    ).to_csv(ledger_path, index=False)

    next(widget for widget in app.radio if widget.label == "View").set_value("Data and evidence")
    app.run()

    assert not app.exception
    summaries = [
        table.value
        for table in app.dataframe
        if isinstance(table.value, pd.DataFrame) and "intervals" in table.value.columns
    ]
    assert len(summaries) == 1
    summary = summaries[0].set_index("reason")["intervals"].to_dict()
    assert summary == {"absent_interval": 2, "explicit_null_actual": 1}


def test_model_comparison_labels_joint_examples_without_claiming_calibration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gridshift.study import run_dir

    app = _app_test(tmp_path, monkeypatch)
    config = yaml.safe_load((tmp_path / "configs/study.yaml").read_text())
    (tmp_path / "data").mkdir()
    (tmp_path / "data/manifest.json").write_text(
        json.dumps({"normalized_hash": "fixture-data-hash"}), encoding="utf-8",
    )
    residuals = run_dir(tmp_path, config, "validation") / "residuals"
    residuals.mkdir(parents=True)
    (residuals.parent / "validation_choices.json").write_text(
        json.dumps({"family_finalists": []}), encoding="utf-8",
    )
    (residuals / "model_00_job_uncertainty.json").write_text(json.dumps({
        "model_id": "fixture-only", "origin": "2024-12-01T00:00:00Z",
        "chosen_start": "2024-12-01T00:00:00Z", "duration_hours": 2,
        "energy_kwh": 0.96, "mean_grams": 100, "lower80": 60, "upper80": 140,
        "lower95": 40, "upper95": 160, "simulations": 1000,
    }), encoding="utf-8")
    app.run()
    next(widget for widget in app.radio if widget.label == "View").set_value("Model comparison")
    app.run()
    assert not app.exception
    assert any("fixture-only" in str(table.value) for table in app.dataframe)
    assert "not calibrated intervals for the workload" in _alert_text(app.caption)


@pytest.mark.parametrize("view", ["Forecasts", "Model comparison", "Backtests", "Data and evidence"])
def test_non_schedule_views_remain_usable_without_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    view: str,
) -> None:
    app = _app_test(tmp_path, monkeypatch).run()
    next(widget for widget in app.radio if widget.label == "View").set_value(view)
    app = app.run()

    assert not app.exception
    assert app.title[0].value == "GridShift"
    if view == "Backtests":
        assert "not been produced" in _alert_text(app.warning)


def test_simple_mode_waits_for_the_run_button_and_hides_the_research_views(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gridshift import live

    calls: list[pd.Timestamp] = []
    monkeypatch.setattr(live, "fetch_recent", lambda origin: calls.append(origin))
    app = _simple_app_test(tmp_path, monkeypatch).run()

    assert not app.exception
    assert app.title[0].value == "GridShift"
    assert [widget.label for widget in app.selectbox] == ["Fitted model"]
    assert [widget.label for widget in app.button] == ["Run forecast"]
    assert not any(widget.label == "View" for widget in app.radio)
    assert "Press Run forecast" in _alert_text(app.info)
    assert calls == []


def test_simple_mode_run_button_scores_windows_without_a_forecast_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _simple_app_test(tmp_path, monkeypatch).run()
    next(widget for widget in app.button if widget.label == "Run forecast").click()
    app = app.run()

    assert not app.exception
    assert "Press Run forecast" not in _alert_text(app.info)
    assert "Forecast unavailable" in _alert_text(app.warning)
