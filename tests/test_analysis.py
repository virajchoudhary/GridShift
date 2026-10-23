import numpy as np
import pandas as pd
import pytest

from gridshift.analysis import _gaps, _source_presence


def test_normalized_full_grid_preserves_source_absent_vs_null_gap_reasons():
    grid = pd.date_range("2023-01-01", periods=6, freq="30min", tz="UTC")
    ledger = pd.DataFrame({"interval_start_utc": [grid[1], grid[4]],
                           "reason": ["absent_interval", "explicit_null_actual"]})
    present = _source_presence(grid, grid, ledger)
    assert present.tolist() == [True, False, True, True, True, True]
    gaps = _gaps(grid, np.array([1., np.nan, 1., 1., np.nan, 1.]), present)
    assert gaps.reason.tolist() == ["absent_interval", "null_actual"]
    ledger.loc[0, "reason"] = "unknown"
    with pytest.raises(ValueError, match="Unknown"):
        _source_presence(grid, grid, ledger)
