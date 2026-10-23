import json

import numpy as np
import pandas as pd
import pytest

from gridshift.forecasting import (
    ModelSpec, _capture_state, _config_dict, _eligible_window, _fill_short_gaps,
    _inverse_distribution, _vectorized_state_forecasts, candidate_catalogue,
    fit_model, load_bundle, rolling_forecasts, save_bundle,
)


def fixture_series():
    rng = np.random.default_rng(1729)
    values = 100 + 12 * np.sin(np.arange(400) * 2 * np.pi / 48) + rng.normal(0, 3, 400)
    return pd.Series(values, index=pd.date_range("2023-01-01", periods=400, freq="30min", tz="UTC"))


@pytest.mark.parametrize("order,seasonal", [
    ((2, 0, 0), (0, 0, 0, 0)), ((0, 0, 2), (0, 0, 0, 0)),
    ((1, 0, 1), (0, 0, 0, 0)), ((1, 1, 0), (0, 0, 0, 0)),
    ((1, 0, 0), (1, 0, 0, 48)),
])
def test_forward_states_equal_statsmodels(order, seasonal):
    spec = ModelSpec("fixture", "SARIMA" if seasonal[0] else "ARIMA", order, seasonal)
    fitted = fit_model(fixture_series(), spec, {"maxiter": 30, "loglikelihood_burn": 48})
    state, cov = _capture_state(fitted.result)
    mean, variance = _vectorized_state_forecasts(fitted.result, state[None], cov[None], 49)
    reference = fitted.result.get_forecast(49)
    np.testing.assert_allclose(mean[0], reference.predicted_mean, atol=1e-7)
    np.testing.assert_allclose(variance[0], reference.var_pred_mean, atol=1e-7)


def test_inverse_log_mean_is_not_median():
    expected, std, median, lo80, hi80, lo95, hi95 = _inverse_distribution(
        np.array([2.0]), np.array([0.2]), "log1p"
    )
    assert expected[0] == pytest.approx(np.exp(2.1) - 1)
    assert expected[0] > median[0]
    assert lo95[0] < lo80[0] < median[0] < hi80[0] < hi95[0]


def test_missing_and_eligibility_preserve_future_boundary():
    data = fixture_series()
    data.iloc[150] = np.nan
    data.iloc[180:184] = np.nan
    filled, mask = _fill_short_gaps(data)
    assert mask[150]
    assert not mask[180:184].any()
    assert filled.iloc[150] == data.iloc[102]
    origin = data.index[200]
    before, _, cutoff = _eligible_window(data, origin, _config_dict(None))
    changed = data.copy()
    changed.loc[changed.index > cutoff] = 9999
    after, _, _ = _eligible_window(changed, origin, _config_dict(None))
    pd.testing.assert_series_equal(before, after)


def test_bundle_integrity_and_reload(tmp_path):
    fitted = fit_model(fixture_series(), ModelSpec("AR1", "AR", (1, 0, 0), (0, 0, 0, 0)))
    path, arrays = save_bundle(fitted, tmp_path / "model.json")
    restored = load_bundle(path)
    np.testing.assert_allclose(
        fitted.result.get_forecast(48).predicted_mean,
        restored.result.get_forecast(48).predicted_mean, atol=1e-8,
    )
    manifest = json.loads(path.read_text())
    manifest["libraries"]["statsmodels"] = "0.invalid"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="versions"):
        load_bundle(path)
    arrays.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="hash"):
        load_bundle(path)


def test_delayed_origin_alignment_and_future_mutation(tmp_path):
    data = fixture_series()
    origin = data.index[300]
    spec = ModelSpec("AR1", "AR", (1, 0, 0), (0, 0, 0, 0))
    config = {"training_window_days": 5, "loglikelihood_burn": 48}
    first = rolling_forecasts(data, spec, origin, origin + pd.Timedelta(days=1), tmp_path / "one", config)
    mutated = data.copy()
    mutated.loc[mutated.index >= origin - pd.Timedelta(minutes=30)] = 5000
    second = rolling_forecasts(mutated, spec, origin, origin + pd.Timedelta(days=1), tmp_path / "two", config)
    with np.load(first.forecasts) as a, np.load(second.forecasts) as b:
        assert a["mean"].shape == (1, 48)
        assert a["origins_ns"][0] == origin.value
        np.testing.assert_array_equal(a["mean"], b["mean"])


def test_catalogue_effective_models_unique():
    specs = candidate_catalogue({"d_values": (0, 1), "transforms": ("identity", "log1p")})
    assert {spec.family for spec in specs} == {"AR", "MA", "ARMA", "ARIMA", "SARIMA"}
    assert len(specs) == len({spec.effective_key for spec in specs})


def test_cumulative_paths_use_complete_prefixes_and_common_mask():
    from gridshift.forecasting import cumulative_path_metrics
    truth = pd.Series([10., 20., np.nan, 40.], index=pd.date_range("2024-01-01", periods=4, freq="30min", tz="UTC"))
    origins = truth.index[:2]
    predictions = np.array([[12., 18.], [21., 30.]])
    table = cumulative_path_metrics(truth, origins, predictions, [1, 2])
    assert table.n_complete_paths.tolist() == [2, 1]
    assert table.path_mae.tolist() == pytest.approx([1.5, 2.])
    assert table.prefix_mean_mae.tolist() == pytest.approx([1.5, 0.])
    masked = cumulative_path_metrics(truth, origins, predictions, [1], [True, False])
    assert masked.iloc[0].path_mae == pytest.approx(2.)
    with pytest.raises(ValueError, match="horizon"):
        cumulative_path_metrics(truth, origins, predictions, [3])


def test_joint_paths_reproduce_known_constant_cost():
    from gridshift.domain import Job, SLOT
    from gridshift.live import joint_job_costs
    data = fixture_series() * 0 + 100
    fitted = fit_model(data, ModelSpec("constant", "AR", (1, 0, 0), (0, 0, 0, 0)))
    origin = data.index[-1] + 2 * SLOT
    job = Job("joint", origin, 2, origin + pd.Timedelta(hours=12))
    costs = joint_job_costs(fitted, job, origin, simulations=200)
    assert costs["median_grams"] == pytest.approx(job.energy_kwh.sum() * 100, abs=.1)
    assert costs["lower95"] <= costs["median_grams"] <= costs["upper95"]
