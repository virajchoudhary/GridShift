"""Development-only EDA and classical time-series diagnostics."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import signal, stats
from statsmodels.tsa.seasonal import STL
from statsmodels.tsa.stattools import acf, adfuller, kpss, pacf

try:
    from .forecasting import _actual_series, _fill_short_gaps
except ImportError:
    from forecasting import _actual_series, _fill_short_gaps

from gridshift.domain import SLOT


_DEVELOPMENT_END = pd.Timestamp("2024-01-01T00:00:00Z")
_MAX_ADF_LAG = 48
_WEEKLY_LAG = 7 * 48
_PLOTS = (
    "series.png",
    "representative_week.png",
    "rolling_summary.png",
    "distribution.png",
    "monthly_distribution.png",
    "missingness.png",
    "weekday_local_profile.png",
    "daily_slot_heatmap.png",
    "periodogram.png",
    "acf_pacf_levels.png",
    "acf_pacf_differences.png",
    "acf_pacf_daily.png",
    "acf_pacf_weekly.png",
    "stl48.png",
)


def _finite_segment(series: pd.Series) -> pd.Series:
    values = series.to_numpy(dtype=float)
    valid = np.isfinite(values)
    edges = np.diff(np.r_[False, valid, False].astype(np.int8))
    starts = np.flatnonzero(edges == 1)
    stops = np.flatnonzero(edges == -1)
    if not len(starts):
        return series.iloc[:0]
    start, stop = max(zip(starts, stops), key=lambda pair: pair[1] - pair[0])
    return series.iloc[start:stop]


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (pd.Timestamp, np.datetime64)):
        return str(pd.Timestamp(value))
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(_json_safe(value), indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    temporary.replace(path)


def _gaps(grid: pd.DatetimeIndex, values: np.ndarray, present: np.ndarray) -> pd.DataFrame:
    missing = ~np.isfinite(values)
    edges = np.diff(np.r_[False, missing, False].astype(np.int8))
    starts = np.flatnonzero(edges == 1)
    stops = np.flatnonzero(edges == -1)
    rows = []
    for start, stop in zip(starts, stops):
        reasons = np.where(present[start:stop], "null_actual", "absent_interval")
        unique = sorted(set(reasons.tolist()))
        rows.append({
            "start_utc": grid[start],
            "end_utc_exclusive": grid[stop - 1] + SLOT,
            "slots": int(stop - start),
            "reason": unique[0] if len(unique) == 1 else "mixed",
        })
    return pd.DataFrame(rows, columns=["start_utc", "end_utc_exclusive", "slots", "reason"])


def _source_presence(grid, actual_index, source_missingness=None):
    present = grid.isin(actual_index)
    if source_missingness is not None:
        records = source_missingness.copy()
        timestamps = pd.to_datetime(records.interval_start_utc, utc=True)
        if not records.reason.isin(["absent_interval", "explicit_null_actual"]).all():
            raise ValueError("Unknown source missingness reason")
        absent = timestamps.loc[records.reason == "absent_interval"]
        present &= ~grid.isin(absent)
    return present


def _stationarity_tests(variants: dict[str, tuple[pd.Series, tuple[str, ...]]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    adf_rows = []
    kpss_rows = []
    samples = {}
    for name, (values, regressions) in variants.items():
        sample = _finite_segment(values)
        samples[name] = sample
        n = len(sample)
        if n < 128:
            for regression in regressions:
                adf_rows.append({
                    "variant": name,
                    "regression": regression,
                    "autolag": None,
                    "status": "insufficient_contiguous_observations",
                    "sample_n": n,
                    "maxlag": min(_MAX_ADF_LAG, max(0, n // 2 - 2)),
                })
            kpss_rows.append({
                "variant": name,
                "regression": "c",
                "status": "insufficient_contiguous_observations",
                "sample_n": n,
            })
            continue
        cap = min(_MAX_ADF_LAG, n // 2 - 2)
        for regression in regressions:
            for autolag in ("AIC", "BIC"):
                try:
                    result = adfuller(
                        sample.to_numpy(dtype=float),
                        maxlag=cap,
                        regression=regression,
                        autolag=autolag,
                    )
                    adf_rows.append({
                        "variant": name,
                        "regression": regression,
                        "autolag": autolag,
                        "status": "ok",
                        "sample_n": n,
                        "maxlag": cap,
                        "selected_lag": int(result[2]),
                        "test_statistic": float(result[0]),
                        "p_value": float(result[1]),
                        "used_n": int(result[3]),
                        "critical_1pct": float(result[4]["1%"]),
                        "critical_5pct": float(result[4]["5%"]),
                        "critical_10pct": float(result[4]["10%"]),
                        "ic_best": float(result[5]),
                    })
                except Exception as exc:
                    adf_rows.append({
                        "variant": name,
                        "regression": regression,
                        "autolag": autolag,
                        "status": f"failed: {type(exc).__name__}: {exc}",
                        "sample_n": n,
                        "maxlag": cap,
                    })
        try:
            with np.errstate(invalid="ignore"):
                result = kpss(sample.to_numpy(dtype=float), regression="c", nlags="auto")
            kpss_rows.append({
                "variant": name,
                "regression": "c",
                "status": "ok",
                "sample_n": n,
                "selected_lag": int(result[2]),
                "test_statistic": float(result[0]),
                "p_value": float(result[1]),
                "critical_10pct": float(result[3]["10%"]),
                "critical_5pct": float(result[3]["5%"]),
                "critical_2_5pct": float(result[3]["2.5%"]),
                "critical_1pct": float(result[3]["1%"]),
            })
        except Exception as exc:
            kpss_rows.append({
                "variant": name,
                "regression": "c",
                "status": f"failed: {type(exc).__name__}: {exc}",
                "sample_n": n,
            })
    for row in adf_rows + kpss_rows:
        sample = samples[row["variant"]]
        row["sample_start_utc"] = str(sample.index[0]) if len(sample) else None
        row["sample_end_exclusive_utc"] = str(sample.index[-1] + SLOT) if len(sample) else None
    return pd.DataFrame(adf_rows), pd.DataFrame(kpss_rows)


def _acf_pacf_table(variants: dict[str, pd.Series]) -> pd.DataFrame:
    rows = []
    for name, values in variants.items():
        sample = _finite_segment(values)
        n = len(sample)
        if n < 128:
            rows.append({
                "variant": name,
                "lag": None,
                "acf": np.nan,
                "pacf": np.nan,
                "status": "insufficient_contiguous_observations",
                "sample_n": n,
            })
            continue
        maxlag = min(2 * _WEEKLY_LAG, n // 2 - 1)
        try:
            acf_values = acf(sample.to_numpy(dtype=float), nlags=maxlag, fft=True)
            pacf_values = pacf(sample.to_numpy(dtype=float), nlags=maxlag, method="ywm")
            rows.extend({
                "variant": name,
                "lag": lag,
                "acf": float(acf_values[lag]),
                "pacf": float(pacf_values[lag]),
                "status": "ok",
                "sample_n": n,
            } for lag in range(maxlag + 1))
        except Exception as exc:
            rows.append({
                "variant": name,
                "lag": None,
                "acf": np.nan,
                "pacf": np.nan,
                "status": f"failed: {type(exc).__name__}: {exc}",
                "sample_n": n,
            })
    return pd.DataFrame(rows)


def _save_acf_figure(table: pd.DataFrame, names: list[str], path: Path, lag_bounds=None) -> None:
    fig, axes = plt.subplots(len(names), 2, figsize=(15, 3.0 * max(1, len(names))), squeeze=False)
    for row_index, name in enumerate(names):
        subset = table.loc[(table.variant == name) & table.lag.notna()]
        if lag_bounds is not None:
            subset = subset.loc[subset.lag.between(*lag_bounds)]
        if subset.empty:
            axes[row_index, 0].text(0.5, 0.5, f"{name}: insufficient contiguous data",
                                    ha="center", va="center")
            axes[row_index, 1].axis("off")
            continue
        lags = subset.lag.to_numpy(dtype=int)
        for column, metric, title in ((0, "acf", "ACF"), (1, "pacf", "PACF")):
            axis = axes[row_index, column]
            axis.axhline(0, color="black", linewidth=0.6)
            axis.axhline(1.96 / math.sqrt(int(subset.sample_n.iloc[0])),
                         color="gray", linestyle="--", linewidth=0.7)
            axis.axhline(-1.96 / math.sqrt(int(subset.sample_n.iloc[0])),
                         color="gray", linestyle="--", linewidth=0.7)
            axis.vlines(lags, 0, subset[metric].to_numpy(dtype=float), color="#287c8e", linewidth=0.55)
            axis.set_title(f"{name}: {title}")
            axis.set_xlim(*(lag_bounds or (0, max(48, int(lags[-1])))))
            axis.set_xlabel("Half-hour lag")
            if int(lags[-1]) >= _WEEKLY_LAG:
                axis.axvline(_SEASONAL_LAG := 48, color="#d95f02", linewidth=0.7)
                axis.axvline(_WEEKLY_LAG, color="#7570b3", linewidth=0.7)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def diagnose(series: pd.Series, outdir: str | Path, source_missingness=None) -> dict[str, Any]:
    """Write diagnostics using actuals through 2023-12-31 only."""
    actual = _actual_series(series)
    development = actual.loc[actual.index < _DEVELOPMENT_END]
    if development.empty:
        raise ValueError("No actual observations are available through 2023-12-31")
    start, observed_end = development.index[0], development.index[-1]
    grid = pd.date_range(start, observed_end, freq=SLOT)
    present = _source_presence(grid, actual.index, source_missingness)
    raw = actual.reindex(grid).rename("actual")
    raw_values = raw.to_numpy(dtype=float)
    short_gap_values, imputed_mask = _fill_short_gaps(raw)
    output = Path(outdir)
    output.mkdir(parents=True, exist_ok=True)
    plots_dir = output / "figures"
    plots_dir.mkdir(parents=True, exist_ok=True)

    gap_frame = _gaps(grid, raw_values, present)
    gap_frame.to_csv(output / "gaps.csv", index=False)
    local = grid.tz_convert("Europe/London")
    missing_rows = pd.DataFrame({
        "interval_start_utc": grid,
        "actual": raw_values,
        "present": present,
        "local_month": local.strftime("%Y-%m"),
        "local_year": local.year,
        "local_month_number": local.month,
        "local_season": pd.Categorical(
            np.select(
                [local.month.isin([12, 1, 2]), local.month.isin([3, 4, 5]),
                 local.month.isin([6, 7, 8])],
                ["winter", "spring", "summer"],
                default="autumn",
            ),
            categories=["winter", "spring", "summer", "autumn"],
        ),
        "local_day_of_week": local.dayofweek,
        "local_day_name": local.day_name(),
        "local_hour": local.hour,
        "local_half_hour": local.hour * 2 + (local.minute >= 30).astype(int),
    })
    missing_rows["missing_reason"] = np.where(
        missing_rows["actual"].notna(), "observed",
        np.where(missing_rows["present"], "null_actual", "absent_interval"),
    )
    monthly_coverage = missing_rows.groupby("local_month", observed=True).agg(
        expected_slots=("interval_start_utc", "size"),
        observed_slots=("actual", "count"),
        absent_intervals=("missing_reason", lambda v: int((v == "absent_interval").sum())),
        null_actuals=("missing_reason", lambda v: int((v == "null_actual").sum())),
    ).reset_index()
    monthly_coverage["coverage"] = monthly_coverage.observed_slots / monthly_coverage.expected_slots
    monthly_coverage.to_csv(output / "monthly_coverage.csv", index=False)
    missing_by_local_hour = missing_rows.groupby("local_hour", observed=True).agg(
        expected_slots=("interval_start_utc", "size"),
        observed_slots=("actual", "count"),
        missing_slots=("actual", lambda v: int(v.isna().sum())),
    ).reset_index()
    missing_by_local_hour["missing_rate"] = (
        missing_by_local_hour.missing_slots / missing_by_local_hour.expected_slots
    )
    missing_by_local_hour.to_csv(output / "missing_by_local_hour.csv", index=False)

    observed = raw.dropna()
    quantiles = observed.quantile([0.0, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 0.999, 1.0])
    q1, q3 = float(observed.quantile(0.25)), float(observed.quantile(0.75))
    iqr = q3 - q1
    distribution = pd.DataFrame({
        "statistic": [
            "count", "missing", "zeros", "mean", "std", "skew", "kurtosis",
            "iqr_lower_extreme_count", "iqr_upper_extreme_count",
        ] + [f"q{int(q * 1000):03d}" for q in quantiles.index],
        "value": [
            len(observed), int(raw.isna().sum()), int((observed == 0).sum()),
            float(observed.mean()), float(observed.std()),
            float(observed.skew()), float(observed.kurtosis()),
            int((observed < q1 - 3 * iqr).sum()),
            int((observed > q3 + 3 * iqr).sum()),
        ] + [float(value) for value in quantiles.to_numpy()],
    })
    distribution.to_csv(output / "distribution.csv", index=False)

    monthly_stats = missing_rows.groupby("local_month", observed=True).agg(
        n=("actual", "count"),
        mean=("actual", "mean"),
        median=("actual", "median"),
        std=("actual", "std"),
        q01=("actual", lambda v: v.quantile(0.01)),
        q99=("actual", lambda v: v.quantile(0.99)),
        maximum=("actual", "max"),
    ).reset_index()
    monthly_stats.to_csv(output / "monthly_distribution.csv", index=False)
    year_season = missing_rows.groupby(["local_year", "local_season"], observed=True).agg(
        n=("actual", "count"),
        mean=("actual", "mean"),
        median=("actual", "median"),
        std=("actual", "std"),
        missing=("actual", lambda v: int(v.isna().sum())),
    ).reset_index()
    year_season.to_csv(output / "year_season.csv", index=False)

    profile = missing_rows.groupby(
        ["local_day_of_week", "local_day_name", "local_half_hour"], observed=True
    ).agg(
        n=("actual", "count"),
        mean=("actual", "mean"),
        median=("actual", "median"),
    ).reset_index()
    profile.to_csv(output / "weekday_local_profile.csv", index=False)
    daily_slot = missing_rows.assign(
        local_date=local.strftime("%Y-%m-%d"),
    ).pivot_table(
        index="local_date",
        columns="local_half_hour",
        values="actual",
        aggfunc="mean",
        observed=True,
    )
    daily_slot.to_csv(output / "daily_slot_heatmap.csv")

    # Use a past-only short-gap policy for diagnostics; long outages stay missing.
    adjusted = short_gap_values
    diagnostic_segment = _finite_segment(adjusted)
    identity_segment = _finite_segment(raw)
    variants: dict[str, tuple[pd.Series, tuple[str, ...]]] = {
        "levels_identity": (identity_segment, ("c", "ct")),
        "levels_log1p": (np.log1p(identity_segment), ("c", "ct")),
    }
    if len(identity_segment):
        variants["first_difference_identity"] = (identity_segment.diff().dropna(), ("c",))
        variants["first_difference_log1p"] = (
            np.log1p(identity_segment).diff().dropna(), ("c",)
        )
        variants["seasonal_difference_48_identity"] = (
            identity_segment.diff(_SEASONAL_LAG := 48).dropna(), ("c",)
        )
        variants["seasonal_difference_48_log1p"] = (
            np.log1p(identity_segment).diff(48).dropna(), ("c",)
        )
        variants["combined_difference_teaching_identity"] = (
            identity_segment.diff(48).diff().dropna(), ("c",)
        )
        variants["combined_difference_teaching_log1p"] = (
            np.log1p(identity_segment).diff(48).diff().dropna(), ("c",)
        )
    adf, kpss_table = _stationarity_tests(variants)
    adf.to_csv(output / "adf.csv", index=False)
    kpss_table.to_csv(output / "kpss.csv", index=False)

    acf_variants = {
        "levels_identity": adjusted,
        "levels_log1p": np.log1p(adjusted),
        "first_difference_identity": adjusted.diff(),
        "first_difference_log1p": np.log1p(adjusted).diff(),
        "seasonal_difference_48_identity": adjusted.diff(48),
        "seasonal_difference_48_log1p": np.log1p(adjusted).diff(48),
    }
    acf_table = _acf_pacf_table(acf_variants)
    acf_table.to_csv(output / "acf_pacf.csv", index=False)

    finite = _finite_segment(adjusted)
    periodogram_table = pd.DataFrame(columns=["frequency_cycles_per_day", "period_days", "power"])
    periodogram_peaks: list[dict[str, float]] = []
    if len(finite) >= 96:
        frequencies, power = signal.periodogram(
            finite.to_numpy(dtype=float),
            fs=48.0,
            detrend="linear",
            scaling="spectrum",
        )
        period_days = np.divide(
            1.0, frequencies,
            out=np.full_like(frequencies, np.inf, dtype=float),
            where=frequencies > 0,
        )
        periodogram_table = pd.DataFrame({
            "frequency_cycles_per_day": frequencies,
            "period_days": period_days,
            "power": power,
        })
        periodogram_table.to_csv(output / "periodogram.csv", index=False)
        peaks, _ = signal.find_peaks(power)
        candidates = [int(i) for i in peaks if frequencies[i] > 0]
        candidates.sort(key=lambda i: power[i], reverse=True)
        periodogram_peaks = [
            {
                "frequency_cycles_per_day": float(frequencies[i]),
                "period_days": float(period_days[i]),
                "power": float(power[i]),
            }
            for i in candidates[:10]
        ]
    stl_summary: dict[str, Any] = {"status": "insufficient_contiguous_observations"}
    stl_components = None
    if len(finite) >= 2 * 48:
        try:
            decomposition = STL(
                finite.to_numpy(dtype=float),
                period=48,
                robust=True,
            ).fit()
            reconstructed = decomposition.trend + decomposition.seasonal + decomposition.resid
            residual_variance = float(np.var(decomposition.resid))
            seasonal_denominator = float(np.var(decomposition.resid + decomposition.seasonal))
            stl_summary = {
                "status": "ok",
                "period_slots": 48,
                "sample_n": int(len(finite)),
                "robust": True,
                "reconstruction_max_abs_error": float(
                    np.max(np.abs(reconstructed - finite.to_numpy(dtype=float)))
                ),
                "daily_seasonal_strength": (
                    max(0.0, 1.0 - residual_variance / seasonal_denominator)
                    if seasonal_denominator > 0 else 0.0
                ),
            }
            stl_components = pd.DataFrame({
                "actual_short_gap_adjusted": finite.to_numpy(dtype=float),
                "trend": decomposition.trend,
                "seasonal_48": decomposition.seasonal,
                "remainder": decomposition.resid,
            }, index=finite.index)
            stl_components.index.name = "interval_start_utc"
            stl_components.to_csv(output / "stl48_components.csv")
        except Exception as exc:
            stl_summary = {"status": f"failed: {type(exc).__name__}: {exc}"}

    boxcox_summary: dict[str, Any]
    if len(observed) and float(observed.min()) > 0:
        offset = 0.0
        try:
            values = observed.to_numpy(dtype=float) + offset
            lam = float(stats.boxcox_normmax(values, method="mle"))
            transformed = stats.boxcox(values, lmbda=lam)
            boxcox_summary = {
                "status": "computed_for_teaching_only",
                "training_derived_offset": offset,
                "lambda_mle": lam,
                "sample_n": int(len(values)),
                "transformed_skew": float(stats.skew(transformed)),
            }
            pd.DataFrame({"boxcox_transformed": transformed}, index=observed.index).to_csv(
                output / "boxcox_teaching.csv", index_label="interval_start_utc"
            )
        except Exception as exc:
            boxcox_summary = {"status": f"failed: {type(exc).__name__}: {exc}"}
    else:
        boxcox_summary = {
            "status": "skipped_requires_strictly_positive_actuals",
            "training_derived_offset": None,
            "sample_n": int(len(observed)),
        }

    # Window ranges are descriptive only and use complete observed 24-hour windows.
    values = raw.to_numpy(dtype=float)
    window_rows = []
    for index in range(max(0, len(values) - 48 + 1)):
        window = values[index:index + 48]
        if np.isfinite(window).all():
            low, high, average = float(window.min()), float(window.max()), float(window.mean())
            window_rows.append({
                "window_start_utc": grid[index],
                "range_gco2_per_kwh": high - low,
                "mean_minus_min_gco2_per_kwh": average - low,
                "relative_minimum_reduction": (average - low) / average if average > 0 else np.nan,
            })
    window_frame = pd.DataFrame(window_rows)
    window_frame.to_csv(output / "development_24h_windows.csv", index=False)
    opportunity_summary = {
        "status": "descriptive_complete_observed_windows_only",
        "window_slots": 48,
        "window_count": int(len(window_frame)),
        "median_range": float(window_frame.range_gco2_per_kwh.median()) if len(window_frame) else None,
        "median_mean_minus_min": (
            float(window_frame.mean_minus_min_gco2_per_kwh.median()) if len(window_frame) else None
        ),
        "median_relative_minimum_reduction": (
            float(window_frame.relative_minimum_reduction.median()) if len(window_frame) else None
        ),
        "interpretation": "Observed within-window range, not a forecast-savings estimate.",
    }

    # Figures
    fig, axis = plt.subplots(figsize=(14, 4))
    axis.plot(raw.index, raw.to_numpy(dtype=float), color="#286b7d", linewidth=0.55)
    axis.set_title("Observed actual carbon intensity, development period")
    axis.set_ylabel("gCO2/kWh")
    axis.set_xlabel("UTC interval start")
    fig.tight_layout()
    fig.savefig(plots_dir / "series.png", dpi=130)
    plt.close(fig)

    complete_week = next(
        (raw.iloc[i:i + 336] for i in range(max(0, len(raw) - 335))
         if raw.iloc[i:i + 336].notna().all()),
        _finite_segment(adjusted).iloc[:336],
    )
    fig, axis = plt.subplots(figsize=(13, 3.5))
    if len(complete_week):
        axis.plot(complete_week.index, complete_week.to_numpy(dtype=float), color="#d95f02", linewidth=1.0)
    axis.set_title("Representative development week")
    axis.set_ylabel("gCO2/kWh")
    axis.set_xlabel("UTC interval start")
    fig.tight_layout()
    fig.savefig(plots_dir / "representative_week.png", dpi=130)
    plt.close(fig)

    rolling = raw.rolling(48 * 7, min_periods=48 * 3)
    rolling_summary = pd.DataFrame({
        "actual": raw,
        "past_7d_mean": rolling.mean(),
        "past_7d_variance": rolling.var(),
    })
    rolling_summary.to_csv(output / "rolling_summary.csv", index_label="interval_start_utc")
    fig, axes = plt.subplots(2, 1, figsize=(14, 7), sharex=True)
    axes[0].plot(rolling_summary.index, rolling_summary.actual, alpha=0.25, linewidth=0.4)
    axes[0].plot(rolling_summary.index, rolling_summary.past_7d_mean, color="#1b9e77", linewidth=0.8)
    axes[0].set_ylabel("gCO2/kWh")
    axes[0].set_title("Past-only rolling 7-day mean")
    axes[1].plot(rolling_summary.index, rolling_summary.past_7d_variance, color="#7570b3", linewidth=0.8)
    axes[1].set_ylabel("Variance")
    axes[1].set_xlabel("UTC interval start")
    fig.tight_layout()
    fig.savefig(plots_dir / "rolling_summary.png", dpi=130)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    axes[0].hist(observed.to_numpy(dtype=float), bins=50, color="#287c8e", alpha=0.85)
    axes[0].set_title("Actual intensity")
    axes[0].set_xlabel("gCO2/kWh")
    axes[1].hist(np.log1p(observed.to_numpy(dtype=float)), bins=50, color="#d95f02", alpha=0.85)
    axes[1].set_title("log1p(actual)")
    axes[1].set_xlabel("log1p(gCO2/kWh)")
    fig.tight_layout()
    fig.savefig(plots_dir / "distribution.png", dpi=130)
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(13, 4))
    if len(monthly_stats):
        labels = monthly_stats.local_month.astype(str).tolist()
        data = [missing_rows.loc[missing_rows.local_month == label, "actual"].dropna().to_numpy()
                for label in labels]
        axis.boxplot(data, showfliers=False, widths=0.65)
        axis.set_xticks(np.arange(1, len(labels) + 1), labels, rotation=60, ha="right")
    axis.set_title("Month-by-month actual distributions")
    axis.set_ylabel("gCO2/kWh")
    fig.tight_layout()
    fig.savefig(plots_dir / "monthly_distribution.png", dpi=130)
    plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(13, 6))
    axes[0].plot(monthly_coverage.local_month.astype(str), monthly_coverage.coverage, marker="o",
                 color="#1b9e77", linewidth=1)
    axes[0].set_ylim(0, 1.01)
    axes[0].set_ylabel("Observed share")
    axes[0].set_xlabel("Local month")
    axes[0].tick_params(axis="x", labelrotation=60)
    axes[1].bar(missing_by_local_hour.local_hour, missing_by_local_hour.missing_rate,
                color="#d95f02")
    axes[1].set_ylabel("Missing share")
    axes[1].set_xlabel("Local hour")
    axes[1].set_xticks(range(24))
    fig.tight_layout()
    fig.savefig(plots_dir / "missingness.png", dpi=130)
    plt.close(fig)

    profile_mean = profile.pivot(index="local_half_hour", columns="local_day_name", values="mean")
    profile_mean = profile_mean.reindex(columns=[
        "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
    ])
    fig, axis = plt.subplots(figsize=(13, 4))
    for day in profile_mean.columns:
        axis.plot(profile_mean.index / 2.0, profile_mean[day], label=day, linewidth=0.9)
    axis.set_title("Weekday profile by Europe/London half-hour")
    axis.set_xlabel("Local time of day")
    axis.set_ylabel("gCO2/kWh")
    axis.set_xticks(range(0, 25, 2))
    axis.legend(ncol=4, fontsize=8)
    fig.tight_layout()
    fig.savefig(plots_dir / "weekday_local_profile.png", dpi=130)
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(13, 6))
    if not daily_slot.empty:
        image = axis.imshow(daily_slot.to_numpy(dtype=float), aspect="auto", interpolation="nearest",
                            origin="lower", cmap="viridis")
        fig.colorbar(image, ax=axis, label="gCO2/kWh")
        axis.set_yticks(
            np.linspace(0, len(daily_slot) - 1, min(8, len(daily_slot))).astype(int),
            [daily_slot.index[i] for i in np.linspace(0, len(daily_slot) - 1, min(8, len(daily_slot))).astype(int)],
        )
    axis.set_title("Actual intensity by local date and local half-hour")
    axis.set_xlabel("Europe/London half-hour slot")
    axis.set_ylabel("Europe/London date")
    fig.tight_layout()
    fig.savefig(plots_dir / "daily_slot_heatmap.png", dpi=130)
    plt.close(fig)

    if not periodogram_table.empty:
        fig, axis = plt.subplots(figsize=(12, 4))
        positive = periodogram_table.loc[periodogram_table.frequency_cycles_per_day > 0]
        axis.plot(positive.frequency_cycles_per_day, positive.power, color="#287c8e", linewidth=0.8)
        axis.axvline(1.0, color="#d95f02", linestyle="--", linewidth=0.8, label="daily")
        axis.axvline(1.0 / 7.0, color="#7570b3", linestyle="--", linewidth=0.8, label="weekly")
        axis.set_xlim(0, min(12, float(positive.frequency_cycles_per_day.max())))
        axis.set_xlabel("Cycles per day")
        axis.set_ylabel("Periodogram power")
        axis.set_title("Periodogram on longest short-gap-adjusted contiguous segment")
        axis.legend()
        fig.tight_layout()
        fig.savefig(plots_dir / "periodogram.png", dpi=130)
        plt.close(fig)
    else:
        fig, axis = plt.subplots()
        axis.text(0.5, 0.5, "Insufficient contiguous data for a periodogram", ha="center", va="center")
        axis.axis("off")
        fig.savefig(plots_dir / "periodogram.png", dpi=130)
        plt.close(fig)

    _save_acf_figure(acf_table, ["levels_identity", "levels_log1p"], plots_dir / "acf_pacf_levels.png")
    _save_acf_figure(
        acf_table,
        ["first_difference_identity", "seasonal_difference_48_identity"],
        plots_dir / "acf_pacf_differences.png",
    )
    _save_acf_figure(acf_table, ["levels_identity", "first_difference_identity"],
                     plots_dir / "acf_pacf_daily.png", (0, 96))
    _save_acf_figure(acf_table, ["levels_identity", "levels_log1p"],
                     plots_dir / "acf_pacf_weekly.png", (312, 360))

    fig, axes = plt.subplots(3, 1, figsize=(13, 7), sharex=True)
    if stl_components is not None:
        axes[0].plot(stl_components.index, stl_components.trend, color="#1b9e77", linewidth=0.8)
        axes[1].plot(stl_components.index, stl_components.seasonal_48, color="#d95f02", linewidth=0.7)
        axes[2].plot(stl_components.index, stl_components.remainder, color="#7570b3", linewidth=0.5)
    else:
        axes[0].text(0.5, 0.5, stl_summary["status"], ha="center", va="center")
    for axis, label in zip(axes, ("Trend", "48-slot seasonal", "Remainder")):
        axis.set_ylabel(label)
    axes[-1].set_xlabel("UTC interval start")
    fig.suptitle("Robust STL on the longest short-gap-adjusted contiguous segment")
    fig.tight_layout()
    fig.savefig(plots_dir / "stl48.png", dpi=130)
    plt.close(fig)

    acf_lag = acf_table.loc[
        (acf_table.variant == "levels_identity") & acf_table.lag.isin([48, 336]),
        ["lag", "acf"],
    ]
    seasonal_lags = {
        int(row.lag): float(row.acf)
        for row in acf_lag.itertuples(index=False)
        if pd.notna(row.acf)
    }
    summary = {
        "schema_version": 1,
        "development_only": True,
        "development_end_exclusive_utc": _DEVELOPMENT_END.isoformat(),
        "input_start_utc": start.isoformat(),
        "last_development_interval_start_utc": observed_end.isoformat(),
        "grid_slots": int(len(grid)),
        "observed_actuals": int(raw.notna().sum()),
        "missing_actuals": int(raw.isna().sum()),
        "input_absent_intervals": int((~present).sum()),
        "source_absence_note": ("Raw source missingness ledger determines record presence."
                               if source_missingness is not None else
                               "Series presence is not raw API record presence; inspect artifacts/data/source_missingness.csv."),
        "short_gap_imputed_slots": int(imputed_mask.sum()),
        "missing_policy": (
            "Only gaps of at most two slots are filled, first from the observed same UTC "
            "slot on the previous day, otherwise from a past-only last observation within "
            "two slots; longer outages remain missing."
        ),
        "longest_observed_segment_slots": int(len(identity_segment)),
        "longest_adjusted_segment_slots": int(len(diagnostic_segment)),
        "adf": {
            "maxlag_cap": _MAX_ADF_LAG,
            "autolag": ["AIC", "BIC"],
            "deterministics": ["c", "ct"],
            "rows": int(len(adf)),
        },
        "kpss_rows": int(len(kpss_table)),
        "seasonal_acf": seasonal_lags,
        "periodogram_peaks": periodogram_peaks,
        "stl48": stl_summary,
        "boxcox": boxcox_summary,
        "development_opportunity": opportunity_summary,
        "dst_profile_note": (
            "Europe/London profile groups repeated autumn local half-hours together; "
            "UTC grid and UTC diagnostics remain primary."
        ),
        "artifacts": {
            "tables": [
                "gaps.csv", "monthly_coverage.csv", "missing_by_local_hour.csv",
                "distribution.csv", "monthly_distribution.csv", "year_season.csv",
                "weekday_local_profile.csv", "daily_slot_heatmap.csv", "adf.csv",
                "kpss.csv", "acf_pacf.csv", "periodogram.csv",
                "stl48_components.csv", "boxcox_teaching.csv",
                "development_24h_windows.csv", "rolling_summary.csv",
            ],
            "figures": list(_PLOTS),
        },
        "future_data_use": "All intervals starting on or after 2024-01-01T00:00:00Z were excluded.",
    }
    _write_json(output / "diagnostics.json", summary)
    return summary


__all__ = ["diagnose"]
