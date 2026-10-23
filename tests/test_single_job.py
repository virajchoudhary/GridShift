from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from gridshift.domain import ForecastPath, Job, SLOT

from gridshift.evaluation import (
    _batch_recommend,
    forecast_metrics,
    paired_moving_block_bootstrap,
    primary_backtest,
)
from gridshift.scheduling import candidates, integrated_cost, recommend


ORIGIN = pd.Timestamp("2025-01-01T00:00:00Z")


def test_negative_forecasts_cannot_create_negative_predicted_emissions():
    job = Job("negative", ORIGIN, 1, ORIGIN + pd.Timedelta(hours=2))
    path = ForecastPath(ORIGIN, np.full(48, -10.), "fixture", ORIGIN - SLOT)
    decision = recommend(job, path)
    assert decision.predicted_grams == 0.
    assert decision.start == ORIGIN


def make_job(
    *,
    duration=1,
    slack=2,
    power_kw=0.4,
    pue=1.2,
    release=ORIGIN,
):
    release = pd.Timestamp(release)
    return Job(
        id="job",
        release=release,
        duration_hours=duration,
        deadline=release + pd.Timedelta(hours=duration + slack),
        power_kw=power_kw,
        pue=pue,
    )


def make_path(values, *, origin=ORIGIN, model_id="forecast", status="ok"):
    values = np.asarray(values, dtype=float)
    return ForecastPath(
        origin=origin,
        mean=values,
        model_id=model_id,
        training_cutoff=origin,
        status=status,
    )


def intensity_series(values, start=ORIGIN):
    index = pd.date_range(start, periods=len(values), freq=SLOT)
    return pd.Series(values, index=index, dtype=float)


def test_integrated_cost_matches_energy_times_intensity():
    job = make_job(duration=1, slack=0)
    grams = integrated_cost(job, ORIGIN, intensity_series([100, 100]))
    assert grams == pytest.approx(0.4 * 1.2 * 1 * 100)


def test_power_scaling_is_linear_and_pue_is_applied_once():
    low_power = make_job(duration=1, slack=0, power_kw=0.4, pue=1.2)
    high_power = make_job(duration=1, slack=0, power_kw=0.8, pue=1.2)
    values = intensity_series([100, 100])
    low = integrated_cost(low_power, ORIGIN, values)
    high = integrated_cost(high_power, ORIGIN, values)
    assert high == pytest.approx(2 * low)
    assert low == pytest.approx(48)


def test_partial_last_slot_uses_only_the_overlap_energy():
    job = make_job(duration=0.75, slack=0)
    assert job.energy_kwh.tolist() == pytest.approx([0.24, 0.12])
    assert integrated_cost(job, ORIGIN, intensity_series([100, 200])) == pytest.approx(48)


def test_schedule_integrates_the_full_window_not_the_single_lowest_slot():
    job = make_job(duration=1, slack=1)
    path = make_path([300, 0, 500, 500])
    decision = recommend(job, path)
    assert decision.status == "scheduled"
    assert decision.start == ORIGIN
    assert decision.predicted_grams == pytest.approx(72)
    candidates_frame = candidates(job, path)
    windows = list(zip(candidates_frame["start"], candidates_frame["finish"], strict=True))
    batch_decision, batch_costs = _batch_recommend(job, path, windows)
    assert batch_decision == decision
    assert batch_costs.tolist() == pytest.approx(candidates_frame["predicted_grams"].tolist())


def test_reservations_use_half_open_overlap_and_preserve_deadline():
    job = make_job(duration=1, slack=0.5)
    path = make_path([100, 0, 100, 100])
    decision = recommend(job, path, [(ORIGIN, ORIGIN + SLOT)])
    assert decision.status == "scheduled"
    assert decision.start == ORIGIN + SLOT
    assert decision.finish == job.deadline

    blocked = recommend(job, path, [(ORIGIN, job.deadline)])
    assert blocked.status == "infeasible"
    assert "reservations" in blocked.reason.lower()


def test_no_slack_requires_release_start_even_when_later_forecast_is_lower():
    job = make_job(duration=1, slack=0)
    decision = recommend(job, make_path([500, 500, 0, 0]))
    assert decision.status == "scheduled"
    assert decision.start == ORIGIN


def test_flat_carbon_exact_tie_favors_earliest_start():
    job = make_job(duration=1, slack=2)
    decision = recommend(job, make_path(np.full(8, 100.0)))
    assert decision.status == "scheduled"
    assert decision.start == ORIGIN


def test_missing_or_short_forecast_is_explicitly_unavailable():
    job = make_job(duration=1, slack=2)
    assert recommend(job, None).status == "unavailable"
    short = recommend(job, make_path([100, 100]))
    assert short.status == "unavailable"
    assert "cover" in short.reason.lower()


def test_invalid_truth_coverage_in_integrator_is_not_silently_zero_filled():
    job = make_job(duration=1, slack=0)
    with pytest.raises(ValueError, match="does not cover"):
        integrated_cost(job, ORIGIN, intensity_series([100]))


def test_future_truth_mutation_cannot_change_forecast_decision():
    job = make_job(duration=1, slack=1)
    path = make_path([300, 0, 500, 500])
    future_truth = intensity_series([900, 900, 0, 0])
    before = recommend(job, path)
    future_truth.iloc[2:] = -999
    after = recommend(job, path)
    assert before == after


def test_oracle_matches_exhaustive_candidate_enumeration(tmp_path):
    index = pd.date_range(ORIGIN, periods=96, freq=SLOT)
    values = np.full(96, 200.0)
    values[4:8] = 5
    truth = pd.Series(values, index=index)
    origins = pd.date_range(ORIGIN, ORIGIN + pd.Timedelta(days=3), freq="3h", inclusive="left")
    means = np.full((len(origins), 48), 150, dtype=np.float32)
    np.savez(tmp_path / "model.npz", origins_ns=origins.asi8, mean=means)
    config = {
        "study": {
            "validation_start": ORIGIN.isoformat(),
            "validation_end": (ORIGIN + pd.Timedelta(days=1)).isoformat(),
            "seed": 1729,
            "bootstrap_resamples": 20,
        },
        "scheduling": {
            "duration_hours": [1],
            "slack_hours": [2],
            "default_duration_hours": 1,
            "default_slack_hours": 2,
        },
    }
    result = primary_backtest(
        truth,
        {"model": tmp_path / "model.npz"},
        ORIGIN,
        ORIGIN + pd.Timedelta(days=3),
        tmp_path / "out",
        config,
        synthetic=True,
    )
    row = result["decisions"].query("policy == 'oracle'").iloc[0]
    job = make_job(duration=1, slack=2, release=row["release"])
    truth_window = truth.reindex(pd.date_range(job.release, periods=6, freq=SLOT)).to_numpy()
    energy = job.energy_kwh
    exhaustive = []
    starts = pd.date_range(job.release, periods=5, freq=SLOT)
    for start in starts:
        offset = int((start - job.release) / SLOT)
        exhaustive.append(float(np.dot(energy, truth_window[offset : offset + job.slots])))
    expected_start = starts[int(np.argmin(exhaustive))]
    assert row["start"] == expected_start


def test_backtest_persists_paired_identical_job_sets(tmp_path):
    start = ORIGIN
    end = start + pd.Timedelta(days=4)
    truth_index = pd.date_range(start - pd.Timedelta(days=4), end, freq=SLOT, inclusive="left")
    truth = pd.Series(100 + (np.arange(len(truth_index)) % 12), index=truth_index, dtype=float)
    origins = pd.date_range(start - pd.Timedelta(days=2), end, freq="3h", inclusive="left")
    mean_a = np.tile(np.full(48, 100, dtype=np.float32), (len(origins), 1))
    mean_b = np.tile(np.full(48, 90, dtype=np.float32), (len(origins), 1))
    mean_b[np.flatnonzero(origins == start)[0], :] = np.nan
    np.savez(tmp_path / "a.npz", origins_ns=origins.asi8, mean=mean_a)
    np.savez(tmp_path / "b.npz", origins_ns=origins.asi8, mean=mean_b)
    config = {
        "study": {
            "validation_start": (start - pd.Timedelta(days=2)).isoformat(),
            "validation_end": start.isoformat(),
            "seed": 1729,
            "bootstrap_resamples": 40,
            "bootstrap_block_days": [3, 7, 14],
        },
        "scheduling": {
            "duration_hours": [0.5, 1],
            "slack_hours": [0, 2],
            "default_duration_hours": 1,
            "default_slack_hours": 1,
        },
    }
    result = primary_backtest(
        truth,
        {"model_a": tmp_path / "a.npz", "model_b": tmp_path / "b.npz"},
        start,
        end,
        tmp_path / "out",
        config,
        synthetic=True,
    )

    pairs = result["pairs"]
    assert not pairs.empty
    for _, group in pairs.groupby(["scenario_id", "policy", "model_id"], dropna=False):
        assert group["job_id"].is_unique
        earliest = result["decisions"].query(
            "scenario_id == @group.iloc[0]['scenario_id'] and policy == 'earliest'"
        )
        assert set(group["job_id"]) == set(earliest["job_id"])
    for filename in (
        "primary_decisions.parquet",
        "primary_summary.csv",
        "primary_pairs.parquet",
        "primary_bootstrap.csv",
        "primary_monthly.csv",
        "primary_exclusions.csv",
        "primary_candidates.parquet",
    ):
        assert (tmp_path / "out" / filename).exists()
    assert set(result["bootstrap"]["block_days"]) == {3, 7, 14}
    forecast_rows = result["decisions"].query("policy == 'forecast'")
    assert forecast_rows["status"].eq("scheduled").all()
    assert forecast_rows["forecast_status"].eq("fallback_earliest").any()
    assert forecast_rows["fallback"].any()
    assert (result["decisions"]["origin"] + pd.Timedelta(hours=24) <= end).all()


def test_backtest_validation_model_choice_ignores_test_truth_changes(tmp_path, monkeypatch):
    validation_start = ORIGIN
    test_start = ORIGIN + pd.Timedelta(days=4)
    end = test_start + pd.Timedelta(days=3)
    truth_index = pd.date_range(
        validation_start - pd.Timedelta(days=2), end, freq=SLOT, inclusive="left"
    )
    truth_values = np.resize(np.asarray([400, 300, 10, 10, 10, 10], dtype=float), len(truth_index))
    truth = pd.Series(truth_values, index=truth_index)
    origins = pd.date_range(
        validation_start - pd.Timedelta(days=2), end, freq="3h", inclusive="left"
    )
    low = np.tile(np.asarray([500, 500, 0] + [0] * 45, dtype=np.float32), (len(origins), 1))
    high = np.tile(np.asarray([0, 500, 500] + [500] * 45, dtype=np.float32), (len(origins), 1))
    np.savez(tmp_path / "low.npz", origins_ns=origins.asi8, mean=low)
    np.savez(tmp_path / "high.npz", origins_ns=origins.asi8, mean=high)
    config = {
        "study": {
            "validation_start": validation_start.isoformat(),
            "validation_end": test_start.isoformat(),
            "seed": 1729,
            "bootstrap_resamples": 10,
        },
        "scheduling": {
            "duration_hours": [1],
            "slack_hours": [1],
            "default_duration_hours": 1,
            "default_slack_hours": 1,
            "selected_model_id": "low",
        },
    }
    def forbid_selection(*args, **kwargs):
        raise AssertionError("A test backtest cannot select a model")
    monkeypatch.setattr("gridshift.evaluation._selection", forbid_selection)
    files = {"low": tmp_path / "low.npz", "high": tmp_path / "high.npz"}
    first = primary_backtest(truth, files, test_start, end, tmp_path / "one", config, synthetic=True)
    changed = truth.copy()
    changed.loc[changed.index >= test_start] = 900
    second = primary_backtest(changed, files, test_start, end, tmp_path / "two", config, synthetic=True)
    assert first["selected_model"] == "low"
    assert second["selected_model"] == first["selected_model"]


def test_metrics_and_time_block_bootstrap_respect_paired_daily_rows():
    metrics = forecast_metrics([1, 2, np.nan], [2, 2, 7], mase_scale=1, std=[1, 1, 1])
    assert metrics["n"] == 2
    assert metrics["mae"] == pytest.approx(0.5)
    assert metrics["bias"] == pytest.approx(0.5)
    assert metrics["interval_n"] == 2

    pairs = pd.DataFrame(
        {
            "release": pd.date_range(ORIGIN, periods=16, freq="3h"),
            "baseline_grams": np.full(16, 10.0),
            "policy_grams": np.full(16, 8.0),
        }
    )
    bootstrap = paired_moving_block_bootstrap(
        pairs,
        ORIGIN,
        ORIGIN + pd.Timedelta(days=3),
        block_days=(3,),
        n_resamples=100,
        seed=42,
    )
    assert bootstrap.iloc[0]["paired_job_count"] == 16
    assert bootstrap.iloc[0]["estimate_savings_pct"] == pytest.approx(20)
    assert bootstrap.iloc[0]["ci95_savings_pct_low"] == pytest.approx(20)
    assert bootstrap.iloc[0]["ci95_savings_pct_high"] == pytest.approx(20)


def test_forecast_metadata_binds_checksum_model_and_information_cutoff(tmp_path):
    from gridshift.artifacts import digest, write_json
    from gridshift.evaluation import _load_forecast_files, _forecast_path
    filename = tmp_path / "fixture.npz"
    np.savez(filename, origins_ns=np.array([ORIGIN.value], dtype="int64"),
             mean=np.full((1, 48), 100., dtype=float))
    with pytest.raises(ValueError, match="metadata"):
        _load_forecast_files({"fixture": filename}, require_metadata=True)
    metadata = {"forecast_sha256": digest(filename.read_bytes()), "model_id": "fixture",
                "publication_delay_slots": 2}
    write_json(filename.with_suffix(".json"), metadata)
    store = _load_forecast_files({"fixture": filename}, require_metadata=True, default_delay_slots=2)["fixture"]
    path, _, _, _ = _forecast_path(store, ORIGIN)
    assert path.training_cutoff == ORIGIN - 3 * SLOT
    assert store.artifact_hash == metadata["forecast_sha256"]
    with pytest.raises(ValueError, match="delay"):
        _load_forecast_files({"fixture": filename}, require_metadata=True, default_delay_slots=1)
    metadata["forecast_sha256"] = "altered"
    write_json(filename.with_suffix(".json"), metadata)
    with pytest.raises(ValueError, match="checksum"):
        _load_forecast_files({"fixture": filename}, require_metadata=True)
def test_candidate_minimum_uses_earliest_numerically_equal_cost():
    from gridshift.scheduling import earliest_minimum
    import numpy as np
    assert earliest_minimum([174.24, np.nextafter(174.24, 0), 180.]) == 0
    assert earliest_minimum([174.24, 174.239, 180.]) == 1
    assert earliest_minimum([.5, .49999999999999495, .5]) == 1
    assert earliest_minimum([0., 0.]) == 0

