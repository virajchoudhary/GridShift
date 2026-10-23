"""Causal classical forecasting, bounded order selection, and compact artifacts."""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
import warnings
from collections.abc import Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import scipy
import statsmodels
from scipy.stats import norm
from statsmodels.tsa.statespace.sarimax import SARIMAX

from gridshift.domain import SLOT, grid_time, utc


_SEASONAL_PERIOD = 48
_SUPPORTED_FAMILIES = {"AR", "MA", "ARMA", "ARIMA", "SARIMA"}
_SELECTION_SERIES: pd.Series | None = None
_SELECTION_CONFIG: dict[str, Any] | None = None
_REDUCED_SEASONAL_ORDERS = (
    ((1, 0, 0), (1, 0, 0, _SEASONAL_PERIOD)),
    ((0, 0, 1), (0, 0, 1, _SEASONAL_PERIOD)),
    ((1, 0, 1), (1, 0, 0, _SEASONAL_PERIOD)),
    ((1, 0, 0), (0, 0, 1, _SEASONAL_PERIOD)),
)


@dataclass(frozen=True, slots=True)
class ModelSpec:
    """One SARIMAX parameterization; no exogenous regressors are permitted."""

    name: str
    family: str
    order: tuple[int, int, int]
    seasonal_order: tuple[int, int, int, int]
    transform: str = "identity"

    def __post_init__(self) -> None:
        if self.family not in _SUPPORTED_FAMILIES:
            raise ValueError(f"Unsupported model family: {self.family}")
        if self.transform not in {"identity", "log1p"}:
            raise ValueError(f"Unsupported transform: {self.transform}")
        if len(self.order) != 3 or len(self.seasonal_order) != 4:
            raise ValueError("ARIMA orders must have lengths 3 and 4")
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0
               for value in (*self.order, *self.seasonal_order)):
            raise ValueError("Model orders must be nonnegative integers")
        if self.seasonal_order[3] not in {0, _SEASONAL_PERIOD}:
            raise ValueError("The core seasonal period is 48 half-hours")

    @property
    def trend(self) -> str:
        return "n" if self.order[1] or self.seasonal_order[1] else "c"

    @property
    def effective_key(self) -> tuple[Any, ...]:
        p, d, q = self.order
        P, D, Q, m = self.seasonal_order
        if not any((P, D, Q)):
            m = 0
        return (p, d, q, P, D, Q, m, self.trend, self.transform)

    @property
    def comparison_group(self) -> tuple[Any, ...]:
        return (
            self.family,
            self.transform,
            self.order[1],
            self.seasonal_order[1],
            self.seasonal_order[3] if any(self.seasonal_order[:3]) else 0,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "family": self.family,
            "order": list(self.order),
            "seasonal_order": list(self.seasonal_order),
            "transform": self.transform,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ModelSpec":
        return cls(
            name=str(value["name"]),
            family=str(value["family"]),
            order=tuple(int(v) for v in value["order"]),
            seasonal_order=tuple(int(v) for v in value["seasonal_order"]),
            transform=str(value.get("transform", "identity")),
        )


@dataclass(frozen=True)
class ForecastConfig:
    """Stable knobs for fitting, selection, and rolling forecast generation."""

    training_window_days: int = 180
    publication_delay_slots: int = 1
    refit_days: int = 7
    horizon_slots: int = 48
    reported_horizons: tuple[int, ...] = (1, 4, 12, 24, 48)
    validation_start: str = "2024-01-01T00:00:00Z"
    validation_end: str = "2025-01-01T00:00:00Z"
    transforms: tuple[str, ...] = ("identity",)
    d_values: tuple[int, ...] = (0,)
    D_values: tuple[int, ...] = (0,)
    allow_double_differencing: bool = False
    catalogue_mode: str = "full"
    catalogue_reason: str = ""
    top_k_per_group: int = 3
    min_converged_anchors: int = 10
    fit_workers: int = 1
    maxiter: int = 100
    fit_method: str = "lbfgs"
    loglikelihood_burn: int = 96
    initialization: str = "stationary"
    diffuse_variance: float = 1_000_000.0
    missing_policy: str = "short_gap"
    strict_library_versions: bool = True


@dataclass
class FittedModel:
    """A fit whose endog, parameters, and state can be reproduced without pickle."""

    spec: ModelSpec
    result: Any
    training_start: pd.Timestamp
    training_cutoff: pd.Timestamp
    training_endog: np.ndarray
    config: dict[str, Any]
    fit_seconds: float


@dataclass(frozen=True)
class ForecastArtifacts:
    forecasts: Path
    metadata: Path
    metrics: Path


def _config_dict(config: Mapping[str, Any] | ForecastConfig | None) -> dict[str, Any]:
    defaults = asdict(ForecastConfig())
    if config is None:
        result = defaults
    elif isinstance(config, ForecastConfig):
        result = asdict(config)
    elif isinstance(config, Mapping):
        unknown = set(config) - {field.name for field in fields(ForecastConfig)}
        if unknown:
            raise ValueError(f"Unknown forecast config keys: {sorted(unknown)}")
        result = {**defaults, **dict(config)}
    else:
        raise TypeError("config must be a mapping, ForecastConfig, or None")
    for key in ("reported_horizons", "transforms", "d_values", "D_values"):
        result[key] = tuple(result[key])
    if result["training_window_days"] < 1 or result["refit_days"] < 1:
        raise ValueError("Training and refit windows must be positive")
    if result["publication_delay_slots"] < 0:
        raise ValueError("publication_delay_slots cannot be negative")
    if result["horizon_slots"] != 48:
        raise ValueError("Core forecasts must contain exactly 48 half-hour slots")
    if any(h < 1 or h > result["horizon_slots"] for h in result["reported_horizons"]):
        raise ValueError("Reported horizons must be within the 48-slot forecast path")
    if not result["transforms"] or not set(result["transforms"]) <= {"identity", "log1p"}:
        raise ValueError("transforms must contain identity and/or log1p")
    if not result["d_values"] or not set(result["d_values"]) <= {0, 1}:
        raise ValueError("Core nonseasonal differencing is limited to d in {0, 1}")
    if not result["D_values"] or not set(result["D_values"]) <= {0, 1}:
        raise ValueError("Core seasonal differencing is limited to D in {0, 1}")
    if 1 in result["d_values"] and 1 in result["D_values"] and not result["allow_double_differencing"]:
        raise ValueError("Both difference orders require an explicit training-only justification")
    if result["catalogue_mode"] not in {"full", "reduced"}:
        raise ValueError("catalogue_mode must be 'full' or 'reduced'")
    if result["catalogue_mode"] == "reduced" and not str(result["catalogue_reason"]).strip():
        raise ValueError("A reduced catalogue requires a recorded evidence-based catalogue_reason")
    if result["initialization"] not in {"stationary", "approximate_diffuse"}:
        raise ValueError("initialization must be stationary or approximate_diffuse")
    if result["missing_policy"] not in {"short_gap", "native"}:
        raise ValueError("missing_policy must be short_gap or native")
    if result["maxiter"] < 1 or result["loglikelihood_burn"] < 0:
        raise ValueError("maxiter must be positive and likelihood burn nonnegative")
    if result["top_k_per_group"] < 1 or result["min_converged_anchors"] < 1:
        raise ValueError("Selection limits must be positive")
    if result["fit_workers"] < 1:
        raise ValueError("fit_workers must be positive")
    return result


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (pd.Timestamp, np.datetime64)):
        return str(pd.Timestamp(value))
    if isinstance(value, np.generic):
        return value.item()
    return value


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(_jsonable(value), indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _actual_series(series: pd.Series) -> pd.Series:
    if not isinstance(series, pd.Series):
        raise TypeError("The forecasting boundary accepts one actual-intensity Series only")
    if not isinstance(series.index, pd.DatetimeIndex) or series.index.tz is None:
        raise ValueError("Actuals require an offset-aware UTC interval-start index")
    index = series.index.tz_convert("UTC")
    if index.has_duplicates:
        raise ValueError("Actual interval starts must be unique")
    if len(index) and np.any(index.asi8 % SLOT.value):
        raise ValueError("Actual interval starts must lie on the half-hour UTC grid")
    values = pd.to_numeric(series, errors="raise").to_numpy(dtype=float)
    invalid = np.isinf(values) | (np.isfinite(values) & (values < 0))
    if invalid.any():
        raise ValueError("Actual intensities must be finite nonnegative values or missing")
    normalized = pd.Series(values, index=index, name="actual").sort_index()
    normalized.attrs["unit"] = "gCO2/kWh"
    normalized.attrs["target"] = "actual"
    return normalized


def _regular_window(
    series: pd.Series,
    start: pd.Timestamp,
    end_inclusive: pd.Timestamp,
) -> pd.Series:
    if end_inclusive < start:
        return pd.Series(dtype=float, index=pd.DatetimeIndex([], tz="UTC"), name="actual")
    grid = pd.date_range(start, end_inclusive, freq=SLOT)
    return series.reindex(grid).rename("actual")


def _eligible_window(
    series: pd.Series,
    origin: pd.Timestamp,
    config: Mapping[str, Any],
) -> tuple[pd.Series, pd.Timestamp, pd.Timestamp]:
    latest_start = origin - SLOT * (1 + config["publication_delay_slots"])
    window_start = origin - pd.Timedelta(days=config["training_window_days"])
    history = _regular_window(series, window_start, latest_start)
    return history, window_start, latest_start


def _fill_short_gaps(values: pd.Series) -> tuple[pd.Series, np.ndarray]:
    filled = values.astype(float).copy()
    raw = filled.to_numpy(copy=True)
    result = filled.to_numpy(copy=True)
    imputed = np.zeros(len(result), dtype=bool)
    missing = ~np.isfinite(raw)
    edges = np.diff(np.r_[False, missing, False].astype(np.int8))
    begins = np.flatnonzero(edges == 1)
    finishes = np.flatnonzero(edges == -1)
    for begin, finish in zip(begins, finishes):
        if finish - begin > 2:
            continue
        for position in range(begin, finish):
            donor = position - _SEASONAL_PERIOD
            if donor >= 0 and np.isfinite(raw[donor]):
                result[position] = raw[donor]
                imputed[position] = True
                continue
            previous = [i for i in range(max(0, position - 2), position)
                        if np.isfinite(result[i])]
            if previous:
                result[position] = result[previous[-1]]
                imputed[position] = True
    return pd.Series(result, index=values.index, name=values.name), imputed


def _fit_endog(history: pd.Series, spec: ModelSpec, config: Mapping[str, Any]) -> np.ndarray:
    values = history.astype(float)
    if config["missing_policy"] == "short_gap":
        values, _ = _fill_short_gaps(values)
    endog = values.to_numpy(dtype=float)
    if spec.transform == "log1p":
        with np.errstate(invalid="ignore"):
            endog = np.log1p(endog)
    return endog


def _build_model(endog: np.ndarray, spec: ModelSpec, config: Mapping[str, Any]) -> SARIMAX:
    if len(endog) <= config["loglikelihood_burn"] + 5:
        raise ValueError("Training history is too short for the configured likelihood burn")
    model = SARIMAX(
        endog,
        order=spec.order,
        seasonal_order=spec.seasonal_order,
        trend=spec.trend,
        enforce_stationarity=True,
        enforce_invertibility=True,
        simple_differencing=False,
        concentrate_scale=False,
        use_exact_diffuse=False,
    )
    if config["initialization"] == "approximate_diffuse":
        model.ssm.initialize_approximate_diffuse(variance=config["diffuse_variance"])
    model.loglikelihood_burn = int(config["loglikelihood_burn"])
    return model


def fit_model(
    history: pd.Series,
    spec: ModelSpec,
    config: Mapping[str, Any] | ForecastConfig | None = None,
    *,
    training_start: Any | None = None,
    training_cutoff: Any | None = None,
) -> FittedModel:
    """Fit one specification on a bounded, already eligible history window."""
    cfg = _config_dict(config)
    history = _actual_series(history)
    if len(history) and not history.index.is_monotonic_increasing:
        raise ValueError("Training history must be ordered")
    if len(history) == 0:
        raise ValueError("Training history is empty")
    endog = _fit_endog(history, spec, cfg)
    if np.isinf(endog).any():
        raise ValueError("Transformed training values are nonfinite")
    model = _build_model(endog, spec, cfg)
    started = time.perf_counter()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = model.fit(
            method=cfg["fit_method"],
            maxiter=int(cfg["maxiter"]),
            disp=False,
            full_output=True,
            cov_type="none",
        )
    result._gridshift_fit_warnings = [str(item.message) for item in caught]
    started_at = utc(training_start) if training_start is not None else history.index[0]
    cutoff = utc(training_cutoff) if training_cutoff is not None else history.index[-1]
    return FittedModel(
        spec=spec,
        result=result,
        training_start=started_at,
        training_cutoff=cutoff,
        training_endog=endog,
        config=cfg,
        fit_seconds=time.perf_counter() - started,
    )


def _fit_status(fitted: FittedModel) -> tuple[bool, str]:
    retvals = getattr(fitted.result, "mle_retvals", {}) or {}
    converged = bool(retvals.get("converged", False))
    params = np.asarray(fitted.result.params, dtype=float)
    if not np.all(np.isfinite(params)):
        return False, "nonfinite_parameters"
    if not np.isfinite(float(fitted.result.llf)):
        return False, "nonfinite_loglikelihood"
    return converged, "converged" if converged else "unconverged"


def _information_criteria(
    result: Any,
    endog: np.ndarray,
    config: Mapping[str, Any],
) -> dict[str, float | int]:
    params = np.asarray(result.params, dtype=float)
    k = int(params.size)
    burn = int(config["loglikelihood_burn"])
    effective = int(np.isfinite(np.asarray(endog)[burn:]).sum())
    llf = float(result.llf)
    aic = -2.0 * llf + 2.0 * k
    bic = -2.0 * llf + k * math.log(effective) if effective > 0 else float("nan")
    aicc = (
        aic + (2.0 * k * (k + 1)) / (effective - k - 1)
        if effective > k + 1 else float("nan")
    )
    return {
        "log_likelihood": llf,
        "parameter_count": k,
        "loglikelihood_burn": burn,
        "effective_n": effective,
        "aic": aic,
        "bic": bic,
        "aicc": aicc,
    }


def _model_name(family: str, order: tuple[int, int, int],
                seasonal: tuple[int, int, int, int], transform: str) -> str:
    p, d, q = order
    P, D, Q, m = seasonal
    if family == "SARIMA":
        base = f"SARIMA({p},{d},{q})x({P},{D},{Q},{m})"
    else:
        base = f"{family}({p},{d},{q})"
    return base if transform == "identity" else f"{base}[{transform}]"


def candidate_catalogue(
    config: Mapping[str, Any] | ForecastConfig | None = None,
) -> list[ModelSpec]:
    """Return the bounded approved grid; a reduced seasonal set is always explicit."""
    cfg = _config_dict(config)
    specs: list[ModelSpec] = []
    seen: set[tuple[Any, ...]] = set()

    def add(family: str, order: tuple[int, int, int],
            seasonal: tuple[int, int, int, int], transform: str) -> None:
        spec = ModelSpec(
            name=_model_name(family, order, seasonal, transform),
            family=family,
            order=order,
            seasonal_order=seasonal,
            transform=transform,
        )
        if spec.effective_key not in seen:
            seen.add(spec.effective_key)
            specs.append(spec)

    for transform in cfg["transforms"]:
        for p in range(1, 9):
            add("AR", (p, 0, 0), (0, 0, 0, 0), transform)
        for q in range(1, 9):
            add("MA", (0, 0, q), (0, 0, 0, 0), transform)
        for p in range(1, 4):
            for q in range(1, 4):
                add("ARMA", (p, 0, q), (0, 0, 0, 0), transform)

        for d in cfg["d_values"]:
            if d:
                for p in range(4):
                    for q in range(4):
                        add("ARIMA", (p, d, q), (0, 0, 0, 0), transform)

        if cfg["catalogue_mode"] == "reduced":
            for order, seasonal in _REDUCED_SEASONAL_ORDERS:
                add("SARIMA", order, seasonal, transform)
        else:
            for d in cfg["d_values"]:
                for D in cfg["D_values"]:
                    if d and D and not cfg["allow_double_differencing"]:
                        continue
                    for p in range(3):
                        for q in range(3):
                            for P in range(2):
                                for Q in range(2):
                                    if not (P or Q or D):
                                        continue
                                    add(
                                        "SARIMA",
                                        (p, d, q),
                                        (P, D, Q, _SEASONAL_PERIOD),
                                        transform,
                                    )
    return specs


def _anchor_times(config: Mapping[str, Any]) -> list[pd.Timestamp]:
    start = grid_time(config["validation_start"])
    end = grid_time(config["validation_end"])
    if start.day != 1 or start != start.normalize():
        raise ValueError("Selection anchors must begin at the first UTC half-hour of a month")
    anchors = list(pd.date_range(start, end, freq="MS", inclusive="left"))
    if len(anchors) != 12:
        raise ValueError("Selection requires all 12 first-of-month validation anchors")
    return anchors


def _selection_row(
    series: pd.Series,
    spec: ModelSpec,
    anchor: pd.Timestamp,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    history, window_start, cutoff = _eligible_window(series, anchor, config)
    base = {
        **spec.to_dict(),
        "order": json.dumps(spec.order),
        "seasonal_order": json.dumps(spec.seasonal_order),
        "anchor": anchor.isoformat(),
        "training_start": window_start.isoformat(),
        "training_cutoff": cutoff.isoformat(),
        "observed_n": int(history.notna().sum()),
        "filled_n": 0,
        "fit_seconds": 0.0,
        "fit_status": "failed",
        "converged": False,
        "error": "",
        "warnings": "",
        "log_likelihood": np.nan,
        "parameter_count": np.nan,
        "loglikelihood_burn": config["loglikelihood_burn"],
        "effective_n": 0,
        "aic": np.nan,
        "bic": np.nan,
        "aicc": np.nan,
    }
    try:
        if config["missing_policy"] == "short_gap":
            _, filled = _fill_short_gaps(history)
            base["filled_n"] = int(filled.sum())
        fitted = fit_model(
            history, spec, config,
            training_start=window_start,
            training_cutoff=cutoff,
        )
        converged, status = _fit_status(fitted)
        base.update(_information_criteria(fitted.result, fitted.training_endog, config))
        base.update(
            fit_seconds=fitted.fit_seconds,
            fit_status=status,
            converged=converged,
            warnings=" | ".join(getattr(fitted.result, "_gridshift_fit_warnings", [])),
        )
        if not converged:
            base["fit_status"] = "unconverged"
    except Exception as exc:
        base["error"] = f"{type(exc).__name__}: {exc}"
    return base


def _init_selection_worker(series: pd.Series, config: Mapping[str, Any]) -> None:
    global _SELECTION_SERIES, _SELECTION_CONFIG
    _SELECTION_SERIES = _actual_series(series)
    _SELECTION_CONFIG = dict(config)


def _selection_worker(task: tuple[pd.Timestamp, ModelSpec]) -> dict[str, Any]:
    if _SELECTION_SERIES is None or _SELECTION_CONFIG is None:
        raise RuntimeError("Selection worker was not initialized")
    anchor, spec = task
    return _selection_row(_SELECTION_SERIES, spec, anchor, _SELECTION_CONFIG)


def run_selection(
    series: pd.Series,
    outdir: str | Path,
    config: Mapping[str, Any] | ForecastConfig | None = None,
) -> tuple[list[ModelSpec], pd.DataFrame]:
    """Fit the configured grid at 12 monthly anchors and rank comparable candidates."""
    cfg = _config_dict(config)
    data = _actual_series(series)
    anchors = _anchor_times(cfg)
    specs = candidate_catalogue(cfg)
    if not specs:
        raise ValueError("The configured catalogue is empty")
    tasks = [(anchor, spec) for anchor in anchors for spec in specs]
    workers = int(cfg["fit_workers"])
    if workers == 1:
        rows = [_selection_row(data, spec, anchor, cfg) for anchor, spec in tasks]
    else:
        with ProcessPoolExecutor(
            max_workers=workers,
            initializer=_init_selection_worker,
            initargs=(data, cfg),
        ) as pool:
            rows = list(pool.map(_selection_worker, tasks, chunksize=1))

    ledger = pd.DataFrame(rows)
    ledger["aicc_rank"] = np.nan
    ledger["bic_rank"] = np.nan
    ledger["d_value"] = [tuple(json.loads(x))[1] for x in ledger.order]
    ledger["D_value"] = [tuple(json.loads(x))[1] for x in ledger.seasonal_order]
    ledger["period"] = [
        tuple(json.loads(x))[3] if any(tuple(json.loads(x))[:3]) else 0
        for x in ledger.seasonal_order
    ]
    # IC ranks are per anchor and comparable representation/differencing group.
    rank_groups = ["family", "transform", "d_value", "D_value", "period"]
    for _, indices in ledger.groupby(rank_groups, sort=False).groups.items():
        rows_for_family = ledger.loc[indices]
        for anchor, anchor_rows in rows_for_family.groupby("anchor", sort=False):
            candidates = anchor_rows.loc[anchor_rows.converged.astype(bool)]
            if candidates.empty:
                continue
            for column, rank_column in (("aicc", "aicc_rank"), ("bic", "bic_rank")):
                ranks = candidates[column].rank(method="average", ascending=True)
                ledger.loc[ranks.index, rank_column] = ranks

    selected: list[ModelSpec] = []
    ledger["median_aicc_rank"] = np.nan
    ledger["median_bic_rank"] = np.nan
    ledger["converged_anchors"] = 0
    ledger["selected"] = False
    for _, group in ledger.groupby(rank_groups, sort=False):
        summaries = []
        for name, candidate in group.groupby("name", sort=False):
            good = candidate.loc[candidate.converged.astype(bool)]
            ledger.loc[candidate.index, "converged_anchors"] = len(good)
            if len(good) < int(cfg["min_converged_anchors"]):
                continue
            median_aicc = float(good.aicc_rank.median())
            median_bic = float(good.bic_rank.median())
            count = int(good.parameter_count.iloc[0])
            ledger.loc[candidate.index, "median_aicc_rank"] = median_aicc
            ledger.loc[candidate.index, "median_bic_rank"] = median_bic
            summaries.append((median_aicc, median_bic, count, name, candidate.iloc[0]))
        summaries.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
        for _, _, _, _, row in summaries[:int(cfg["top_k_per_group"])]:
            spec = ModelSpec.from_dict({
                "name": row["name"],
                "family": row["family"],
                "order": json.loads(row["order"]),
                "seasonal_order": json.loads(row["seasonal_order"]),
                "transform": row["transform"],
            })
            selected.append(spec)
            ledger.loc[ledger.name == spec.name, "selected"] = True

    output = Path(outdir)
    output.mkdir(parents=True, exist_ok=True)
    ledger.to_csv(output / "selection_ledger.csv", index=False)
    summary = {
        "schema_version": 1,
        "config": cfg,
        "selection_anchors": [anchor.isoformat() for anchor in anchors],
        "candidate_count": len(specs),
        "fit_attempt_count": len(ledger),
        "selected": [spec.to_dict() for spec in selected],
        "comparison_note": (
            "AICc and BIC ranks are aggregated within family, transform, "
            "differencing, seasonal-period, and anchor groups; absolute IC is "
            "not compared across windows or representations."
        ),
    }
    _write_json(output / "selection_summary.json", summary)
    return selected, ledger


def _ssm_matrix(ssm: Any, name: str, ndim: int) -> np.ndarray:
    value = np.asarray(getattr(ssm, name), dtype=float)
    if value.ndim == ndim + 1:
        return value[..., 0]
    return value


def _forecast_system(result: Any) -> tuple[np.ndarray, ...]:
    ssm = result.model.ssm
    transition = _ssm_matrix(ssm, "transition", 2)
    design = _ssm_matrix(ssm, "design", 2)
    state_intercept = _ssm_matrix(ssm, "state_intercept", 1).reshape(-1)
    obs_intercept = _ssm_matrix(ssm, "obs_intercept", 1).reshape(-1)
    selection = _ssm_matrix(ssm, "selection", 2)
    state_cov = _ssm_matrix(ssm, "state_cov", 2)
    obs_cov = _ssm_matrix(ssm, "obs_cov", 2)
    if design.shape[0] != 1 or obs_intercept.size != 1 or obs_cov.shape[0] != 1:
        raise ValueError("Only univariate SARIMAX models are supported")
    process_cov = selection @ state_cov @ selection.T
    return (
        transition,
        design[0],
        state_intercept,
        float(obs_intercept[0]),
        process_cov,
        float(obs_cov[0, 0]),
    )


def _vectorized_state_forecasts(
    result: Any,
    states: np.ndarray,
    covariances: np.ndarray,
    steps: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Forecast many causal filtered snapshots with shared time-invariant matrices."""
    transition, design, state_intercept, obs_intercept, process_cov, obs_cov = _forecast_system(result)
    row = design.copy()
    deterministic = 0.0
    accumulated_noise = 0.0
    means = np.empty((len(states), steps), dtype=float)
    variances = np.empty_like(means)
    for step in range(steps):
        accumulated_noise += float(row @ process_cov @ row)
        deterministic += float(row @ state_intercept)
        row = row @ transition
        means[:, step] = states @ row + deterministic + obs_intercept
        variances[:, step] = (
            np.einsum("i,nij,j->n", row, covariances, row, optimize=True)
            + accumulated_noise + obs_cov
        )
    return means, np.maximum(variances, 0.0)


def _inverse_distribution(
    mean: np.ndarray,
    variance: np.ndarray,
    transform: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if transform == "identity":
        std = np.sqrt(np.maximum(variance, 0.0))
        median = mean
        lower80 = mean + norm.ppf(0.10) * std
        upper80 = mean + norm.ppf(0.90) * std
        lower95 = mean + norm.ppf(0.025) * std
        upper95 = mean + norm.ppf(0.975) * std
        return mean, std, median, lower80, upper80, lower95, upper95
    std_z = np.sqrt(np.maximum(variance, 0.0))
    with np.errstate(over="ignore", invalid="ignore"):
        median = np.expm1(mean)
        expected = np.expm1(mean + 0.5 * variance)
        std = np.sqrt(np.maximum(
            0.0,
            np.expm1(variance) * np.exp(2.0 * mean + variance),
        ))
        lower80 = np.expm1(mean + norm.ppf(0.10) * std_z)
        upper80 = np.expm1(mean + norm.ppf(0.90) * std_z)
        lower95 = np.expm1(mean + norm.ppf(0.025) * std_z)
        upper95 = np.expm1(mean + norm.ppf(0.975) * std_z)
    return expected, std, median, lower80, upper80, lower95, upper95


def _fallback_scale(history: pd.Series) -> float:
    values = history.to_numpy(dtype=float)
    if len(values) <= _SEASONAL_PERIOD:
        return float(np.nanstd(values)) if np.isfinite(values).any() else 0.0
    pairs = values[_SEASONAL_PERIOD:]
    previous = values[:-_SEASONAL_PERIOD]
    valid = np.isfinite(pairs) & np.isfinite(previous)
    return float(np.sqrt(np.mean(np.square(pairs[valid] - previous[valid])))) if valid.any() else 0.0


def _fallback_path(
    series: pd.Series,
    origin: pd.Timestamp,
    horizon: int,
    config: Mapping[str, Any],
) -> tuple[np.ndarray, np.ndarray]:
    latest_start = origin - SLOT * (1 + config["publication_delay_slots"])
    history, _, _ = _eligible_window(series, origin, config)
    available, _ = _fill_short_gaps(history)
    last_values = available.loc[available.notna()]
    if last_values.empty:
        return np.zeros(horizon, dtype=float), np.zeros(horizon, dtype=float)
    latest_value = float(last_values.iloc[-1])
    cutoff = latest_start
    scale = _fallback_scale(history)
    path = np.empty(horizon, dtype=float)
    for i in range(horizon):
        target = origin + i * SLOT
        for days_back in range(1, 15):
            donor = target - days_back * _SEASONAL_PERIOD * SLOT
            if donor <= cutoff and donor in available.index and np.isfinite(available.loc[donor]):
                path[i] = float(available.loc[donor])
                break
        else:
            path[i] = latest_value
    return path, np.full(horizon, scale, dtype=float)


def _capture_state(result: Any) -> tuple[np.ndarray, np.ndarray]:
    filter_results = result.filter_results
    state = np.asarray(filter_results.filtered_state[:, -1], dtype=float).copy()
    covariance = np.asarray(filter_results.filtered_state_cov[:, :, -1], dtype=float).copy()
    if not np.all(np.isfinite(state)) or not np.all(np.isfinite(covariance)):
        raise ValueError("Nonfinite filtered state")
    return state, covariance


def _weekly_forecasts(
    series: pd.Series,
    spec: ModelSpec,
    origins: pd.DatetimeIndex,
    config: Mapping[str, Any],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[dict[str, Any]]]:
    horizon = int(config["horizon_slots"])
    delay = int(config["publication_delay_slots"])
    bridge_slots = delay
    steps = horizon + bridge_slots
    forecasts = np.empty((len(origins), horizon), dtype=float)
    forecast_std = np.empty_like(forecasts)
    lower80 = np.empty_like(forecasts)
    upper80 = np.empty_like(forecasts)
    lower95 = np.empty_like(forecasts)
    upper95 = np.empty_like(forecasts)
    fallback = np.ones(len(origins), dtype=bool)
    refits: list[dict[str, Any]] = []
    block_size = int(config["refit_days"] * 48)
    for block_start in range(0, len(origins), block_size):
        block_end = min(block_start + block_size, len(origins))
        block_origins = origins[block_start:block_end]
        fit_origin = block_origins[0]
        history, training_start, cutoff = _eligible_window(series, fit_origin, config)
        started = time.perf_counter()
        state_rows: list[np.ndarray] = []
        covariance_rows: list[np.ndarray] = []
        active_result = None
        last_cutoff = cutoff
        failure = ""
        fit_seconds = 0.0
        converged = False
        try:
            fitted = fit_model(
                history,
                spec,
                config,
                training_start=training_start,
                training_cutoff=cutoff,
            )
            fit_seconds = fitted.fit_seconds
            converged, fit_status = _fit_status(fitted)
            if not converged:
                failure = fit_status
            else:
                active_result = fitted.result
        except Exception as exc:
            failure = f"{type(exc).__name__}: {exc}"

        if active_result is not None:
            try:
                state, covariance = _capture_state(active_result)
                state_rows.append(state)
                covariance_rows.append(covariance)
                final_cutoff = block_origins[-1] - SLOT * (1 + delay)
                if final_cutoff > cutoff:
                    new_index = pd.date_range(cutoff + SLOT, final_cutoff, freq=SLOT)
                    raw_updates = series.reindex(new_index).astype(float)
                    updates = raw_updates.copy()
                    if config["missing_policy"] == "short_gap":
                        prefix = pd.concat([history, raw_updates])
                        for position in np.flatnonzero(raw_updates.isna()):
                            eligible_prefix = prefix.iloc[:len(history) + position + 1]
                            filled_prefix, _ = _fill_short_gaps(eligible_prefix)
                            updates.iloc[position] = filled_prefix.iloc[-1]
                    update = updates.to_numpy(dtype=float)
                    if spec.transform == "log1p":
                        update = np.log1p(update)
                    # Filtering is causal at every snapshot, unlike smoothing.
                    extended = active_result.extend(update)
                    fr = extended.filter_results
                    states = fr.filtered_state.T
                    covs = np.moveaxis(fr.filtered_state_cov, 2, 0)
                    if not np.isfinite(states).all() or not np.isfinite(covs).all():
                        raise ValueError("Nonfinite extended filtered states")
                    state_rows.extend(states)
                    covariance_rows.extend(covs)
            except Exception as exc:
                failure = f"extend {type(exc).__name__}: {exc}"

        good_count = len(state_rows)
        if good_count:
            try:
                state_predictions, state_variances = _vectorized_state_forecasts(
                    fitted.result,
                    np.stack(state_rows),
                    np.stack(covariance_rows),
                    steps,
                )
                selected_mean = state_predictions[:, bridge_slots:bridge_slots + horizon]
                selected_variance = state_variances[:, bridge_slots:bridge_slots + horizon]
                transformed = _inverse_distribution(selected_mean, selected_variance, spec.transform)
                valid = np.ones(good_count, dtype=bool)
                for values in transformed:
                    valid &= np.isfinite(values).all(axis=1)
            except Exception as exc:
                failure = f"forecast {type(exc).__name__}: {exc}"
                transformed = ()
                valid = np.zeros(good_count, dtype=bool)
            for local_i in range(good_count):
                global_i = block_start + local_i
                if valid[local_i]:
                    forecasts[global_i] = transformed[0][local_i]
                    forecast_std[global_i] = transformed[1][local_i]
                    lower80[global_i] = transformed[3][local_i]
                    upper80[global_i] = transformed[4][local_i]
                    lower95[global_i] = transformed[5][local_i]
                    upper95[global_i] = transformed[6][local_i]
                    fallback[global_i] = False
                else:
                    path, std = _fallback_path(series, block_origins[local_i], horizon, config)
                    forecasts[global_i], forecast_std[global_i] = path, std
                    lower80[global_i] = path + norm.ppf(0.10) * std
                    upper80[global_i] = path + norm.ppf(0.90) * std
                    lower95[global_i] = path + norm.ppf(0.025) * std
                    upper95[global_i] = path + norm.ppf(0.975) * std
        for local_i in range(good_count, len(block_origins)):
            path, std = _fallback_path(series, block_origins[local_i], horizon, config)
            global_i = block_start + local_i
            forecasts[global_i], forecast_std[global_i] = path, std
            lower80[global_i] = path + norm.ppf(0.10) * std
            upper80[global_i] = path + norm.ppf(0.90) * std
            lower95[global_i] = path + norm.ppf(0.025) * std
            upper95[global_i] = path + norm.ppf(0.975) * std
        refits.append({
            "refit_origin": fit_origin.isoformat(),
            "training_start": training_start.isoformat(),
            "training_cutoff": cutoff.isoformat(),
            "fit_seconds": float(fit_seconds),
            "block_seconds": float(time.perf_counter() - started),
            "converged": bool(converged),
            "status": "converged" if converged and not failure else (failure or "failed"),
            "origins": int(len(block_origins)),
            "causal_states_captured": int(good_count),
        })
    return (
        forecasts,
        forecast_std,
        lower80,
        upper80,
        lower95,
        upper95,
        fallback,
        refits,
    )


def _forecast_metrics(
    series: pd.Series,
    origins: pd.DatetimeIndex,
    mean: np.ndarray,
    std: np.ndarray,
    lower80: np.ndarray,
    upper80: np.ndarray,
    lower95: np.ndarray,
    upper95: np.ndarray,
    fallback: np.ndarray,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    scales = mase_scales(series, origins, config)
    horizon_values = np.asarray(config["reported_horizons"], dtype=int)
    for h in horizon_values:
        target_times = origins + (int(h) - 1) * SLOT
        target = series.reindex(target_times).to_numpy(dtype=float)
        prediction = mean[:, int(h) - 1].astype(float)
        lo80, hi80 = lower80[:, int(h) - 1], upper80[:, int(h) - 1]
        lo95, hi95 = lower95[:, int(h) - 1], upper95[:, int(h) - 1]
        valid = np.isfinite(target) & np.isfinite(prediction)
        seasons = np.asarray([
            {12: "winter", 1: "winter", 2: "winter",
             3: "spring", 4: "spring", 5: "spring",
             6: "summer", 7: "summer", 8: "summer",
             9: "autumn", 10: "autumn", 11: "autumn"}[int(t.month)]
            for t in target_times.tz_convert("Europe/London")
        ], dtype=object)
        for label in ("all", "winter", "spring", "summer", "autumn"):
            subset = valid if label == "all" else (valid & (seasons == label))
            indices = np.flatnonzero(subset)
            errors = prediction[indices] - target[indices]
            coverage80 = (
                float(np.mean((target[indices] >= lo80[indices]) & (target[indices] <= hi80[indices])))
                if len(indices) else np.nan
            )
            coverage95 = (
                float(np.mean((target[indices] >= lo95[indices]) & (target[indices] <= hi95[indices])))
                if len(indices) else np.nan
            )
            valid_scale = np.isfinite(scales[indices]) & (scales[indices] > 0)
            mase_values = np.abs(errors[valid_scale]) / scales[indices][valid_scale]
            def interval_score(y: np.ndarray, low: np.ndarray, high: np.ndarray, alpha: float) -> float:
                if not len(y):
                    return np.nan
                penalty = np.maximum(low - y, 0.0) + np.maximum(y - high, 0.0)
                return float(np.mean((high - low) + (2.0 / alpha) * penalty))

            records.append({
                "group_type": "season" if label != "all" else "overall",
                "group": label,
                "horizon": int(h),
                "n": int(len(indices)),
                "mae": float(np.mean(np.abs(errors))) if len(indices) else np.nan,
                "rmse": float(np.sqrt(np.mean(np.square(errors)))) if len(indices) else np.nan,
                "mean_error": float(np.mean(errors)) if len(indices) else np.nan,
                "mase": float(np.mean(mase_values)) if len(mase_values) else np.nan,
                "coverage80": coverage80,
                "coverage95": coverage95,
                "width80": float(np.mean(hi80[indices] - lo80[indices])) if len(indices) else np.nan,
                "width95": float(np.mean(hi95[indices] - lo95[indices])) if len(indices) else np.nan,
                "interval_score80": interval_score(target[indices], lo80[indices], hi80[indices], 0.20),
                "interval_score95": interval_score(target[indices], lo95[indices], hi95[indices], 0.05),
                "fallback_origins": int(fallback[indices].sum()),
            })
    return pd.DataFrame(records)


def cumulative_path_metrics(series, origins, mean, horizons, origin_mask=None):
    """Score complete observed prefixes in original intensity units."""
    mean = np.asarray(mean, dtype=float)
    origins = pd.DatetimeIndex(origins)
    if mean.ndim != 2 or mean.shape[0] != len(origins):
        raise ValueError("Forecast path shape differs from the origin grid")
    mask = np.ones(len(origins), dtype=bool) if origin_mask is None else np.asarray(origin_mask, dtype=bool)
    if mask.shape != (len(origins),):
        raise ValueError("Origin mask must have one value per forecast path")
    target_times = origins.asi8[:, None] + np.arange(mean.shape[1]) * SLOT.value
    actual = series.reindex(pd.to_datetime(target_times.ravel(), utc=True)).to_numpy(float).reshape(mean.shape)
    rows = []
    for horizon in horizons:
        if not 1 <= horizon <= mean.shape[1]:
            raise ValueError("Cumulative horizon exceeds the forecast path")
        valid = mask & np.isfinite(actual[:, :horizon]).all(axis=1) & np.isfinite(mean[:, :horizon]).all(axis=1)
        errors = mean[valid, :horizon] - actual[valid, :horizon]
        average_error = errors.mean(axis=1)
        rows.append({
            "horizon": int(horizon), "n_complete_paths": int(valid.sum()),
            "path_mae": float(np.abs(errors).mean()) if valid.any() else np.nan,
            "path_rmse": float(np.sqrt(np.square(errors).mean())) if valid.any() else np.nan,
            "prefix_mean_mae": float(np.abs(average_error).mean()) if valid.any() else np.nan,
            "prefix_mean_bias": float(average_error.mean()) if valid.any() else np.nan,
            "units": "gCO2/kWh",
        })
    return pd.DataFrame(rows)


def mase_scales(series, origins, config):
    grid = series.asfreq(SLOT)
    raw = grid.to_numpy(dtype=float)
    lag = _SEASONAL_PERIOD
    sums = np.zeros(len(raw))
    counts = np.zeros(len(raw), dtype=int)
    valid = np.isfinite(raw[lag:]) & np.isfinite(raw[:-lag])
    sums[lag:] = np.where(valid, np.abs(raw[lag:] - raw[:-lag]), 0)
    counts[lag:] = valid
    sum_prefix = np.r_[0., np.cumsum(sums)]
    count_prefix = np.r_[0, np.cumsum(counts)]
    left = origins - pd.Timedelta(days=config["training_window_days"]) + lag * SLOT
    right = origins - SLOT * (1 + config["publication_delay_slots"])
    a = grid.index.searchsorted(left)
    b = grid.index.searchsorted(right, side="right")
    n = count_prefix[b] - count_prefix[a]
    return np.divide(sum_prefix[b] - sum_prefix[a], n, out=np.full(len(origins), np.nan), where=n > 0)


def rolling_forecasts(
    series: pd.Series,
    spec: ModelSpec,
    start: Any,
    end: Any,
    outpath: str | Path,
    config: Mapping[str, Any] | ForecastConfig | None = None,
    *,
    experiment_root: str | Path | None = None,
    synthetic: bool = False,
) -> ForecastArtifacts:
    """Write causal every-half-hour 48-slot forecasts and score only after saving."""
    cfg = _config_dict(config)
    from .artifacts import authorize_period
    frozen = authorize_period(series, start, end, experiment_root=experiment_root, synthetic=synthetic)
    if frozen is not None:
        from .study import forecast_config
        if cfg != _config_dict(forecast_config(frozen["protocol"]["config"])):
            raise ValueError("Forecast settings differ from frozen protocol")
        if spec.to_dict() not in frozen["protocol"]["family_finalists"]:
            raise ValueError("Forecast model was not selected on validation")
    data = _actual_series(series)
    start_time, end_time = grid_time(start), grid_time(end)
    if end_time <= start_time:
        raise ValueError("Forecast stage end must be after start")
    final_origin = end_time - SLOT * int(cfg["horizon_slots"])
    if final_origin < start_time:
        origins = pd.DatetimeIndex([], tz="UTC")
    else:
        origins = pd.date_range(start_time, final_origin, freq=SLOT)
    forecast_path = Path(outpath)
    if forecast_path.suffix.lower() != ".npz":
        forecast_path = forecast_path.with_suffix(".npz")
    forecast_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path = forecast_path.with_suffix(".json")
    metrics_path = forecast_path.with_name(forecast_path.stem + ".metrics.csv")
    started = time.perf_counter()

    if len(origins):
        (
            modeled_mean,
            modeled_std,
            lower80,
            upper80,
            lower95,
            upper95,
            fallback,
            refits,
        ) = _weekly_forecasts(
            data, spec, origins, cfg
        )
    else:
        modeled_mean = np.empty((0, cfg["horizon_slots"]), dtype=float)
        modeled_std = np.empty_like(modeled_mean)
        fallback = np.empty(0, dtype=bool)
        lower80 = upper80 = lower95 = upper95 = np.empty_like(modeled_mean)
        refits = []

    with forecast_path.open("wb") as stream:
        np.savez_compressed(
            stream,
            origins_ns=origins.asi8.astype(np.int64),
            mean=modeled_mean.astype(np.float32),
            std=modeled_std.astype(np.float32),
            fallback=fallback.astype(bool),
            lower80=lower80.astype(np.float32),
            upper80=upper80.astype(np.float32),
            lower95=lower95.astype(np.float32),
            upper95=upper95.astype(np.float32),
        )
    # The persisted forecasts are fixed before any target values are joined.
    with np.load(forecast_path, allow_pickle=False) as saved:
        metrics = _forecast_metrics(
            data, origins, saved["mean"], saved["std"], saved["lower80"], saved["upper80"],
            saved["lower95"], saved["upper95"], saved["fallback"], cfg,
        )
    metrics.to_csv(metrics_path, index=False)
    metadata = {
        "schema_version": 1,
        "model_spec": spec.to_dict(),
        "forecast_start": start_time.isoformat(),
        "stage_end_exclusive": end_time.isoformat(),
        "last_origin": origins[-1].isoformat() if len(origins) else None,
        "origin_count": int(len(origins)),
        "horizon_slots": int(cfg["horizon_slots"]),
        "bridge_slots": int(cfg["publication_delay_slots"]),
        "publication_delay_slots": int(cfg["publication_delay_slots"]),
        "training_window_days": int(cfg["training_window_days"]),
        "refit_days": int(cfg["refit_days"]),
        "fallback_count": int(fallback.sum()),
        "raw_negative_forecast_count": int(np.count_nonzero(modeled_mean < 0.0)),
        "operational_negative_correction": "none; raw negative point forecasts are retained",
        "fit_count": len(refits),
        "runtime_seconds": float(time.perf_counter() - started),
        "refits": refits,
        "intervals": {
            "levels": [0.80, 0.95],
            "identity": "Gaussian state-space predictive distribution",
            "log1p": "inverse lognormal predictive quantiles",
            "fallback": "daily seasonal naive with training daily-error scale",
        },
        "likelihood": {
            "initialization": cfg["initialization"],
            "loglikelihood_burn": cfg["loglikelihood_burn"],
            "enforce_stationarity": True,
            "enforce_invertibility": True,
            "missing_policy": cfg["missing_policy"],
        },
        "libraries": {
            "python": ".".join(map(str, os.sys.version_info[:3])),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
            "statsmodels": statsmodels.__version__,
        },
        "forecast_file": forecast_path.name,
        "forecast_sha256": hashlib.sha256(forecast_path.read_bytes()).hexdigest(),
        "metrics_file": metrics_path.name,
        "metrics_schema": list(metrics.columns),
        "target_access_order": "NPZ persisted before future actuals are joined for scoring",
    }
    _write_json(metadata_path, metadata)
    return ForecastArtifacts(forecast_path, metadata_path, metrics_path)


def save_bundle(fitted: FittedModel, path: str | Path) -> tuple[Path, Path]:
    """Persist parameters and training endog as JSON plus pickle-free NPZ arrays."""
    json_path = Path(path)
    if json_path.suffix.lower() != ".json":
        json_path = json_path.with_suffix(".json")
    arrays_path = json_path.with_suffix(".npz")
    arrays_path.parent.mkdir(parents=True, exist_ok=True)
    array_tmp = arrays_path.with_name(arrays_path.name + ".tmp")
    with array_tmp.open("wb") as stream:
        np.savez_compressed(
            stream,
            params=np.asarray(fitted.result.params, dtype=np.float64),
            training_endog=np.asarray(fitted.training_endog, dtype=np.float64),
        )
    arrays_hash = hashlib.sha256(array_tmp.read_bytes()).hexdigest()
    manifest = {
        "schema_version": 1,
        "model_spec": fitted.spec.to_dict(),
        "training_start": fitted.training_start.isoformat(),
        "training_cutoff": fitted.training_cutoff.isoformat(),
        "training_length": int(len(fitted.training_endog)),
        "arrays_file": arrays_path.name,
        "arrays_sha256": arrays_hash,
        "config": fitted.config,
        "libraries": {
            "python": ".".join(map(str, os.sys.version_info[:3])),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
            "statsmodels": statsmodels.__version__,
        },
        "fit_seconds": float(fitted.fit_seconds),
    }
    json_tmp = json_path.with_name(json_path.name + ".tmp")
    json_tmp.write_text(
        json.dumps(_jsonable(manifest), indent=2, sort_keys=True, allow_nan=False),
        encoding="utf-8",
    )
    os.replace(array_tmp, arrays_path)
    os.replace(json_tmp, json_path)
    return json_path, arrays_path


def load_bundle(
    path: str | Path,
    *,
    allow_version_mismatch: bool = False,
) -> FittedModel:
    """Reload a local parameter bundle without executing serialized Python objects."""
    json_path = Path(path)
    if json_path.suffix.lower() != ".json":
        json_path = json_path.with_suffix(".json")
    manifest = json.loads(json_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise ValueError("Unsupported model bundle schema")
    arrays_path = json_path.with_name(manifest["arrays_file"])
    if Path(manifest["arrays_file"]).name != manifest["arrays_file"]:
        raise ValueError("Model bundle array path must be a sibling file")
    payload = arrays_path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != manifest["arrays_sha256"]:
        raise ValueError("Model bundle array hash mismatch")
    current_versions = {
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scipy": scipy.__version__,
        "statsmodels": statsmodels.__version__,
    }
    saved_versions = manifest["libraries"]
    if not allow_version_mismatch and any(
        saved_versions.get(name) != value for name, value in current_versions.items()
    ):
        raise ValueError("Model bundle library versions do not match this runtime")
    with np.load(arrays_path, allow_pickle=False) as arrays:
        params = np.asarray(arrays["params"], dtype=float)
        endog = np.asarray(arrays["training_endog"], dtype=float)
    if (
        len(endog) != int(manifest["training_length"])
        or not np.all(np.isfinite(endog) | np.isnan(endog))
        or not np.all(np.isfinite(params))
    ):
        raise ValueError("Invalid model bundle training endog")
    spec = ModelSpec.from_dict(manifest["model_spec"])
    cfg = _config_dict(manifest["config"])
    model = _build_model(endog, spec, cfg)
    result = model.filter(params, transformed=True)
    if not np.isfinite(float(result.llf)):
        raise ValueError("Reloaded model bundle has a nonfinite likelihood")
    return FittedModel(
        spec=spec,
        result=result,
        training_start=utc(manifest["training_start"]),
        training_cutoff=utc(manifest["training_cutoff"]),
        training_endog=endog,
        config=cfg,
        fit_seconds=float(manifest["fit_seconds"]),
    )


__all__ = [
    "ForecastArtifacts",
    "ForecastConfig",
    "FittedModel",
    "ModelSpec",
    "candidate_catalogue",
    "fit_model",
    "load_bundle",
    "rolling_forecasts",
    "run_selection",
    "save_bundle",
]
