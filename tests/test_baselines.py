import numpy as np
import pandas as pd

from gridshift import baselines


def test_batched_baselines_equal_past_only_reference(tmp_path):
    rng = np.random.default_rng(1729)
    data = pd.Series(100 + rng.normal(size=1100), index=pd.date_range("2023-01-01", periods=1100, freq="30min", tz="UTC"))
    data.iloc[650] = np.nan
    origin = data.index[900]
    cfg = {"training_window_days": 14, "loglikelihood_burn": 48}
    files = baselines.rolling(data, origin, origin + pd.Timedelta(hours=25), tmp_path, cfg)
    for name, file in files.items():
        with np.load(file) as arrays:
            for row in range(3):
                o = pd.Timestamp(arrays["origins_ns"][row], tz="UTC")
                mean, std, fallback = baselines.path(data, o, name, cfg)
                np.testing.assert_allclose(arrays["mean"][row], mean, atol=1e-5)
                np.testing.assert_allclose(arrays["std"][row], std, atol=1e-5)
                assert arrays["fallback"][row] == fallback


def test_daily_last_slot_cannot_use_unpublished_previous_slot():
    data = pd.Series(np.arange(800.), index=pd.date_range("2023-01-01", periods=800, freq="30min", tz="UTC"))
    origin = data.index[700]
    before = baselines.path(data, origin, "daily_naive")[0]
    data.iloc[699:] = 9000
    after = baselines.path(data, origin, "daily_naive")[0]
    np.testing.assert_array_equal(before, after)
    assert before[-1] == 651
