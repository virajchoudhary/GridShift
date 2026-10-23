import numpy as np
import pandas as pd

from gridshift.sensitivities import _energy_profiles


def test_energy_profile_and_outage_replay_use_real_artifact_shapes(tmp_path):
    truth = pd.Series(100., index=pd.date_range("2023-12-01", "2024-10-04", freq="30min", tz="UTC"))
    for month in (1, 4, 7, 10):
        start = pd.Timestamp(f"2024-{month:02d}-01T00:00Z")
        origins = pd.date_range(start, periods=7, freq="30min")
        directory = tmp_path / f"month_{month:02d}/default"
        directory.mkdir(parents=True)
        np.savez(directory / "forecast.npz", origins_ns=origins.asi8,
                 mean=np.tile(np.linspace(100, 50, 48), (len(origins), 1)))
    _energy_profiles(truth, tmp_path, "fixture", {})
    energy = pd.read_csv(tmp_path / "energy_profile_sensitivity.csv")
    assert len(energy) == 16
    assert set(energy.profile) == {"constant", "nonconstant"}
    np.testing.assert_allclose(energy.energy_kwh, .96)
    np.testing.assert_allclose(energy.selected_grams, 96.)
    outages = pd.read_csv(tmp_path / "outage_state_replay.csv")
    assert len(outages) == 4
    assert not outages.recommendation_enabled.any()
    assert outages.carbon_estimate.isna().all()
    assert (pd.to_datetime(outages.fallback_finish) <= pd.to_datetime(outages.deadline)).all()
