from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yaml


APP_ROOT = Path(__file__).resolve().parents[1]


def _find_package_root() -> Path:
    candidates = (
        APP_ROOT,
        APP_ROOT.parent.parent / "outputs" / "GridShift",
    )
    for candidate in candidates:
        if (candidate / "src" / "gridshift" / "__init__.py").is_file():
            return candidate.resolve()
    return APP_ROOT.resolve()


PACKAGE_ROOT = _find_package_root()
ROOT = Path(os.environ.get("GRIDSHIFT_ROOT", PACKAGE_ROOT)).expanduser().resolve()
package_src = str(PACKAGE_ROOT / "src")
if package_src not in sys.path:
    sys.path.insert(0, package_src)

try:
    from gridshift import live, scheduling
    from gridshift.artifacts import require_freeze
    from gridshift.baselines import BASELINES
    from gridshift.data import load as load_dataset
    from gridshift.domain import ForecastPath, Job, SLOT, grid_time
    from gridshift.study import forecast_config, run_dir
except Exception as exc:  # Keep the unavailable-dependency state visible in the UI.
    live = None
    scheduling = None
    require_freeze = None
    BASELINES = ("persistence", "daily_naive", "weekly_naive", "calendar_mean")
    load_dataset = None
    ForecastPath = None
    Job = None
    SLOT = pd.Timedelta(minutes=30)
    grid_time = None
    forecast_config = None
    run_dir = None
    IMPORT_ERROR = f"{type(exc).__name__}: {exc}"
else:
    IMPORT_ERROR = None


VIEWS = ("Schedule", "Forecasts", "Model comparison", "Backtests", "Data and evidence")
DEFAULT_ORIGIN_DATE = dt.date(2025, 6, 1)
DEFAULT_ORIGIN_TIME = dt.time(0, 0)
DATA_SOURCE_NAME = "https://api.carbonintensity.org.uk"


@st.cache_data(show_spinner=False)
def _cached_actual_series(root: str, normalized_hash: str) -> pd.Series:
    if load_dataset is None:
        raise RuntimeError(IMPORT_ERROR or "GridShift package is unavailable")
    return load_dataset(root).actual


@st.cache_data(ttl=900, show_spinner=False)
def _cached_live_observations(origin_iso: str, refresh_nonce: int) -> pd.Series:
    if live is None:
        raise RuntimeError(IMPORT_ERROR or "GridShift package is unavailable")
    return live.fetch_recent(pd.Timestamp(origin_iso))


def _read_json(path: Path) -> tuple[Any | None, str | None]:
    if not path.is_file():
        return None, None
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"{type(exc).__name__}: {exc}"


def _read_csv(path: Path) -> pd.DataFrame | None:
    if not path.is_file():
        return None
    try:
        return pd.read_csv(path)
    except (OSError, pd.errors.ParserError, UnicodeDecodeError):
        return None


def _config(root: Path) -> tuple[dict[str, Any] | None, str | None]:
    path = root / "configs" / "study.yaml"
    if not path.is_file():
        return None, f"Configuration file not found: {path}"
    try:
        config = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return None, f"{type(exc).__name__}: {exc}"
    if not isinstance(config, dict):
        return None, "Study configuration must contain a YAML mapping"
    return config, None


def _format_utc(value: Any) -> str:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        return f"{timestamp.isoformat()} (timezone missing)"
    return timestamp.tz_convert("UTC").strftime("%Y-%m-%d %H:%MZ")


def _artifact_error(exc: Exception, missing_message: str) -> str:
    if isinstance(exc, FileNotFoundError):
        return missing_message
    if isinstance(exc, (ValueError, TypeError, OverflowError)):
        return str(exc)
    return f"{type(exc).__name__}: operation could not be completed."


def _json_text(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, default=str)
    except (TypeError, ValueError):
        return str(value)


def _records_frame(value: Any) -> pd.DataFrame:
    if isinstance(value, pd.DataFrame):
        return value.copy()
    if isinstance(value, list):
        if not value:
            return pd.DataFrame()
        if all(isinstance(row, dict) for row in value):
            return pd.json_normalize(value, sep=".")
        return pd.DataFrame({"value": [_json_text(item) for item in value]})
    if not isinstance(value, dict) or not value:
        return pd.DataFrame()

    for key in ("rows", "records", "data"):
        if isinstance(value.get(key), list):
            return _records_frame(value[key])

    if any(key in value for key in ("model_id", "horizon", "mae", "rmse", "metric")):
        return pd.json_normalize([value], sep=".")

    if all(isinstance(item, dict) for item in value.values()):
        frame = pd.DataFrame.from_dict(value, orient="index")
        frame.index.name = "group"
        return frame.reset_index()

    grouped_rows: list[dict[str, Any]] = []
    for group, items in value.items():
        if isinstance(items, list) and all(isinstance(row, dict) for row in items):
            grouped_rows.extend({"group": group, **row} for row in items)
    if grouped_rows:
        return pd.json_normalize(grouped_rows, sep=".")

    return pd.DataFrame(
        {"field": list(value), "value": [_json_text(item) for item in value.values()]}
    )


def _neutral_metric_labels(frame: pd.DataFrame) -> pd.DataFrame:
    renamed: dict[str, str] = {}
    for column in frame.columns:
        label = str(column)
        lowered = label.casefold()
        if "savings" in lowered or "avoided" in lowered:
            label = label.replace("savings", "modeled_emissions_contrast")
            label = label.replace("Savings", "Modeled emissions contrast")
            label = label.replace("avoided", "modeled_emissions_contrast")
            label = label.replace("Avoided", "Modeled emissions contrast")
        renamed[column] = label
    return frame.rename(columns=renamed)


def _frame_download(
    label: str,
    frame: pd.DataFrame,
    file_name: str,
    key: str,
    neutral_labels: bool = False,
) -> None:
    if frame.empty:
        return
    output = _neutral_metric_labels(frame) if neutral_labels else frame
    st.download_button(
        label,
        data=output.to_csv(index=False).encode("utf-8"),
        file_name=file_name,
        mime="text/csv",
        key=key,
    )


def _store(root: Path, config: dict[str, Any] | None, stage: str) -> dict[str, str]:
    if run_dir is None or config is None:
        return {}
    try:
        value, _ = _read_json(run_dir(root, config, stage) / "forecast_store.json")
    except (OSError, KeyError, ValueError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def _model_options(
    root: Path,
    config: dict[str, Any] | None,
    results: dict[str, Any] | None,
    test_results_verified: bool = False,
) -> list[str]:
    ordered: list[str] = []
    if isinstance(results, dict):
        for field in ("deployment_model", "forecast_champion", "strongest_simple"):
            model_id = results.get(field)
            if isinstance(model_id, str) and model_id:
                ordered.append(model_id)
    stages = ("test", "validation") if test_results_verified else ("validation",)
    for stage in stages:
        ordered.extend(_store(root, config, stage))
    if isinstance(results, dict):
        for field in ("models", "selected_orders", "model_metadata"):
            value = results.get(field)
            if isinstance(value, dict):
                ordered.extend(str(key) for key in value)
            elif isinstance(value, list):
                ordered.extend(
                    row["model_id"]
                    for row in value
                    if isinstance(row, dict) and isinstance(row.get("model_id"), str)
                )
    if not ordered:
        ordered.extend(BASELINES)
    return list(dict.fromkeys(ordered))


def _stage_for_origin(origin: pd.Timestamp, config: dict[str, Any]) -> str:
    study = config.get("study", {})
    for stage in ("validation", "test"):
        start = study.get(f"{stage}_start")
        end = study.get(f"{stage}_end")
        if start and end and pd.Timestamp(start) <= origin < pd.Timestamp(end):
            return stage
    raise ValueError("Historical origins must fall inside a stored validation or test period")


def _read_model_metadata(
    root: Path,
    config: dict[str, Any],
    stage: str,
    model_id: str,
) -> dict[str, Any]:
    mapping = _store(root, config, stage)
    file_name = mapping.get(model_id)
    if not file_name:
        return {}
    artifact = (root / file_name).with_suffix(".json")
    metadata, _ = _read_json(artifact)
    return metadata if isinstance(metadata, dict) else {}


def _fetch_clicked_live(origin: pd.Timestamp, bypass_cache: bool) -> None:
    origin_key = origin.isoformat()
    nonce = int(pd.Timestamp.now(tz="UTC").value) if bypass_cache else 0
    try:
        observations = _cached_live_observations(origin_key, nonce)
        if not isinstance(observations, pd.Series):
            raise ValueError("The provider response did not produce an intensity series")
        state = st.session_state.setdefault("_gridshift_live_data", {})
        state[origin_key] = observations
        errors = st.session_state.setdefault("_gridshift_live_errors", {})
        errors.pop(origin_key, None)
        st.success(
            f"Loaded {int(observations.notna().sum())} observed intervals ending at "
            f"{_format_utc(origin)}."
        )
    except Exception as exc:
        errors = st.session_state.setdefault("_gridshift_live_errors", {})
        errors[origin_key] = _artifact_error(
            exc,
            "A required local artifact is missing.",
        )
        st.error("Live observations could not be refreshed. Existing cached observations are retained.")


def _live_observations(origin: pd.Timestamp) -> tuple[pd.Series | None, str | None]:
    origin_key = origin.isoformat()
    observations = st.session_state.get("_gridshift_live_data", {}).get(origin_key)
    error = st.session_state.get("_gridshift_live_errors", {}).get(origin_key)
    return observations, error


def _make_forecast(
    root: Path,
    config: dict[str, Any],
    origin: pd.Timestamp,
    mode: str,
    model_id: str,
    test_results_verified: bool = False,
    result_error: str | None = None,
) -> tuple[ForecastPath | None, dict[str, np.ndarray], dict[str, Any], str | None, pd.Series | None]:
    if live is None:
        return None, {}, {}, IMPORT_ERROR, None

    if mode == "Historical":
        try:
            stage = _stage_for_origin(origin, config)
            if stage == "test" and not test_results_verified:
                detail = (
                    "The 2025 test forecast is hidden until results.json matches the frozen data, "
                    "protocol, software, and validation-artifact hashes."
                )
                if result_error:
                    detail = f"{detail} Verification status: {result_error}"
                return (
                    None,
                    {},
                    {},
                    detail,
                    None,
                )
            path, bounds = live.historical_path(root, config, origin, model_id, stage=stage)
            metadata = _read_model_metadata(root, config, stage, model_id)
            return path, bounds, metadata, None, None
        except FileNotFoundError:
            return (
                None,
                {},
                {},
                "No issued forecast store or path file is available for this model and origin.",
                None,
            )
        except Exception as exc:
            return (
                None,
                {},
                {},
                _artifact_error(exc, "A required forecast artifact is missing."),
                None,
            )

    observations, refresh_error = _live_observations(origin)
    if observations is None:
        detail = (
            f"Refresh failed: {refresh_error}"
            if refresh_error
            else "Live observations have not been fetched for this UTC origin."
        )
        return None, {}, {}, detail, None

    try:
        state = live.operational_state(
            observations,
            origin,
            config.get("study", {}).get("publication_delay_slots", 1),
        )
    except Exception as exc:
        return (
            None,
            {},
            {},
            f"Operational state check failed: {_artifact_error(exc, 'Observation state is unavailable.')}",
            observations,
        )
    if refresh_error:
        return (
            None,
            {},
            {"operational_state": state},
            "The latest live refresh failed. Carbon recommendation is disabled until a successful refresh.",
            observations,
        )
    if state["status"] != "fresh":
        detail = (
            f"Live observations are {state['status']}. Carbon recommendation is disabled; "
            "the earliest feasible time is shown only as a non-carbon fallback."
        )
        return None, {}, {"operational_state": state}, detail, observations

    try:
        path, state = live.predict_live(root, config, observations, origin)
        return path, {}, {"operational_state": state}, None, observations
    except Exception as exc:
        return (
            None,
            {},
            {"operational_state": state},
            "Trusted live model unavailable: "
            + _artifact_error(exc, "A required deployment artifact is missing."),
            observations,
        )


def _forecast_frame(
    path: ForecastPath,
    bounds: dict[str, np.ndarray],
    metadata: dict[str, Any],
) -> tuple[pd.DataFrame, str]:
    index = pd.date_range(path.origin, periods=len(path.mean), freq=SLOT, tz="UTC")
    frame = pd.DataFrame(
        {
            "interval_start_utc": index,
            "interval_end_utc": index + SLOT,
            "horizon_slot": np.arange(1, len(path.mean) + 1),
            "forecast_mean_gco2_per_kwh": np.asarray(path.mean, dtype=float),
        }
    )
    if path.std is not None:
        frame["forecast_sd_gco2_per_kwh"] = np.asarray(path.std, dtype=float)
    for key in ("lower80", "upper80", "lower95", "upper95"):
        values = bounds.get(key)
        if values is not None and len(values) == len(frame):
            frame[f"{key}_gco2_per_kwh"] = np.asarray(values, dtype=float)

    if all(key in bounds for key in ("lower80", "upper80", "lower95", "upper95")):
        note = metadata.get("interval_note") or (
            "Stored forecast bounds; use the calibration metrics shown separately."
        )
    elif path.std is not None:
        sd = np.asarray(path.std, dtype=float)
        frame["lower80_gco2_per_kwh"] = np.maximum(0, path.mean - 1.2815515655 * sd)
        frame["upper80_gco2_per_kwh"] = np.maximum(0, path.mean + 1.2815515655 * sd)
        frame["lower95_gco2_per_kwh"] = np.maximum(0, path.mean - 1.9599639845 * sd)
        frame["upper95_gco2_per_kwh"] = np.maximum(0, path.mean + 1.9599639845 * sd)
        note = "Live normal approximation from model standard deviation; empirical coverage is not guaranteed."
    else:
        note = "No forecast interval or standard deviation is available."
    return frame, str(note)


def _plot_path(
    path: ForecastPath,
    bounds: dict[str, np.ndarray],
    observations: pd.Series | None,
    mode: str,
    show_retrospective_actual: bool,
) -> tuple[go.Figure, str]:
    frame, interval_note = _forecast_frame(path, bounds, {})
    fig = go.Figure()

    if observations is not None:
        observed = observations.dropna()
        eligible = observed.loc[
            (observed.index <= path.training_cutoff)
            & (observed.index >= path.origin - pd.Timedelta(days=7))
        ]
        if not eligible.empty:
            fig.add_trace(
                go.Scatter(
                    x=eligible.index,
                    y=eligible.to_numpy(float),
                    name="Eligible observed history",
                    mode="lines",
                    line={"color": "#596872", "width": 1.6},
                )
            )
        if mode == "Historical" and show_retrospective_actual:
            end = frame["interval_end_utc"].iloc[-1]
            realized = observed.loc[(observed.index >= path.origin) & (observed.index < end)]
            if not realized.empty:
                fig.add_trace(
                    go.Scatter(
                        x=realized.index,
                        y=realized.to_numpy(float),
                        name="Realized actual (retrospective)",
                        mode="lines",
                        line={"color": "#b7791f", "width": 1.4, "dash": "dot"},
                    )
                )

    if all(name in frame for name in ("lower95_gco2_per_kwh", "upper95_gco2_per_kwh")):
        fig.add_trace(
            go.Scatter(
                x=frame["interval_start_utc"],
                y=frame["upper95_gco2_per_kwh"],
                mode="lines",
                line={"width": 0},
                showlegend=False,
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=frame["interval_start_utc"],
                y=frame["lower95_gco2_per_kwh"],
                mode="lines",
                line={"width": 0},
                fill="tonexty",
                fillcolor="rgba(89,104,114,0.10)",
                name="95% band",
                hoverinfo="skip",
            )
        )
    if all(name in frame for name in ("lower80_gco2_per_kwh", "upper80_gco2_per_kwh")):
        fig.add_trace(
            go.Scatter(
                x=frame["interval_start_utc"],
                y=frame["upper80_gco2_per_kwh"],
                mode="lines",
                line={"width": 0},
                showlegend=False,
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=frame["interval_start_utc"],
                y=frame["lower80_gco2_per_kwh"],
                mode="lines",
                line={"width": 0},
                fill="tonexty",
                fillcolor="rgba(13,126,120,0.18)",
                name="80% band",
                hoverinfo="skip",
            )
        )

    fig.add_trace(
        go.Scatter(
            x=frame["interval_start_utc"],
            y=frame["forecast_mean_gco2_per_kwh"],
            name="Forecast mean",
            mode="lines",
            line={"color": "#087f78", "width": 2.4},
        )
    )
    fig.update_layout(
        height=390,
        margin={"l": 12, "r": 12, "t": 18, "b": 12},
        xaxis_title="Interval start (UTC)",
        yaxis_title="Carbon intensity (gCO2/kWh)",
        legend={"orientation": "h", "y": 1.08, "x": 0},
        hovermode="x unified",
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
    )
    return fig, interval_note


def _candidate_display(frame: pd.DataFrame, selected_start: Any = None, fallback: bool = False) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    output = frame.copy()
    output["start_utc"] = output["start"].map(
        lambda value: _format_utc(value) if pd.notna(value) else ""
    )
    output["finish_utc"] = output["finish"].map(
        lambda value: _format_utc(value) if pd.notna(value) else ""
    )
    output["selected"] = output["start"].map(lambda value: value == selected_start)
    if fallback and output["selected"].any():
        output.loc[output["selected"], "status"] = "earliest_feasible_fallback"
        output.loc[output["selected"], "predicted_grams"] = np.nan
    return output.rename(
        columns={
            "start_utc": "Start (UTC)",
            "finish_utc": "Finish (UTC)",
            "waiting_hours": "Wait (hours)",
            "predicted_grams": "Predicted job emissions (gCO2)",
            "status": "Status",
            "reason": "Reason",
            "model_id": "Model",
            "selected": "Selected",
        }
    )[
        [
            "candidate_index",
            "Start (UTC)",
            "Finish (UTC)",
            "Wait (hours)",
            "Predicted job emissions (gCO2)",
            "Status",
            "Reason",
            "Model",
            "Selected",
        ]
    ]


def _candidate_timeline(frame: pd.DataFrame, selected_start: Any, fallback: bool) -> None:
    if frame.empty:
        return
    feasible = frame.loc[frame["start"].notna() & frame["finish"].notna()].copy()
    if feasible.empty:
        st.info("No feasible start window is available.")
        return

    if fallback:
        rows = feasible.head(1).copy()
        rows["choice"] = "Earliest feasible fallback"
    else:
        scored = feasible.loc[np.isfinite(pd.to_numeric(feasible["predicted_grams"], errors="coerce"))]
        rows = scored.nsmallest(6, "predicted_grams").copy()
        if selected_start is not None:
            selected = feasible.loc[feasible["start"] == selected_start]
            if not selected.empty and not (rows["start"] == selected_start).any():
                rows = pd.concat([rows, selected.head(1)])
        rows["choice"] = "Alternative"
        rows.loc[rows["start"] == selected_start, "choice"] = "Selected model recommendation"
    if rows.empty:
        st.info("No complete forecast-covered candidate windows are available to chart.")
        return
    rows["window"] = rows.apply(
        lambda row: f"{_format_utc(row['start'])} to {_format_utc(row['finish'])}",
        axis=1,
    )
    fig = px.timeline(
        rows,
        x_start="start",
        x_end="finish",
        y="window",
        color="choice",
        color_discrete_map={
            "Selected model recommendation": "#087f78",
            "Alternative": "#9aa7ae",
            "Earliest feasible fallback": "#b7791f",
        },
    )
    fig.update_yaxes(autorange="reversed", title=None)
    fig.update_xaxes(title="Candidate job interval (UTC)")
    fig.update_layout(
        height=max(180, 48 * len(rows) + 80),
        margin={"l": 12, "r": 12, "t": 18, "b": 12},
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        legend={"orientation": "h", "y": 1.12, "x": 0},
    )
    st.plotly_chart(fig, use_container_width=True)


def _stage_metric_frame(
    root: Path,
    config: dict[str, Any] | None,
    results: dict[str, Any] | None,
    field: str,
    stage: str,
    test_results_verified: bool = False,
) -> pd.DataFrame:
    if stage == "test" and not test_results_verified:
        return pd.DataFrame()
    value = results.get(field) if isinstance(results, dict) else None
    frame = _records_frame(value)
    if not frame.empty:
        return frame
    if config is None or run_dir is None:
        return pd.DataFrame()
    try:
        path = run_dir(root, config, stage) / "forecast_common_metrics.csv"
    except (OSError, KeyError, ValueError, TypeError):
        return pd.DataFrame()
    frame = _read_csv(path)
    return frame if frame is not None else pd.DataFrame()


def _artifact_frame(
    root: Path,
    config: dict[str, Any] | None,
    stage: str,
    relative: str,
    test_results_verified: bool = False,
) -> pd.DataFrame:
    if stage == "test" and not test_results_verified:
        return pd.DataFrame()
    if config is None or run_dir is None:
        return pd.DataFrame()
    try:
        path = run_dir(root, config, stage) / relative
    except (OSError, KeyError, ValueError, TypeError):
        return pd.DataFrame()
    result = _read_csv(path)
    return result if result is not None else pd.DataFrame()


def _render_metric_table(
    title: str,
    frame: pd.DataFrame,
    key: str,
    allow_filters: bool = False,
    neutral_labels: bool = True,
) -> None:
    st.subheader(title)
    if frame.empty:
        st.info("No accepted table is available for this section.")
        return
    display = frame.copy()
    if allow_filters:
        display = _filter_frame(display, key)
    if neutral_labels:
        display = _neutral_metric_labels(display)
    st.dataframe(display, use_container_width=True, hide_index=True)
    _frame_download(
        "Download table",
        frame,
        f"gridshift_{key}.csv",
        f"download_{key}",
        neutral_labels=neutral_labels,
    )


def _filter_frame(frame: pd.DataFrame, prefix: str) -> pd.DataFrame:
    output = frame.copy()
    filter_specs = (
        ("model", "Model"),
        ("month", "Month"),
        ("duration", "Duration"),
        ("slack", "Slack"),
        ("scenario", "Scenario"),
        ("policy", "Policy"),
        ("horizon", "Lead horizon"),
        ("status", "Status"),
    )
    for token, label in filter_specs:
        column = next(
            (name for name in output.columns if token in str(name).casefold()),
            None,
        )
        if column is None:
            continue
        values = output[column].dropna().astype(str).unique().tolist()
        if not 1 < len(values) <= 40:
            continue
        values = sorted(values)
        selected = st.multiselect(
            f"{label} filter",
            options=values,
            key=f"{prefix}_filter_{token}",
        )
        if selected:
            output = output.loc[output[column].astype(str).isin(selected)]
    return output


def _load_historical_actual(
    root: Path,
    manifest: dict[str, Any] | None,
) -> tuple[pd.Series | None, str | None]:
    if not isinstance(manifest, dict) or load_dataset is None:
        return None, None
    normalized_hash = str(manifest.get("normalized_hash", ""))
    if not normalized_hash:
        return None, "Data manifest does not contain a normalized dataset hash."
    try:
        return _cached_actual_series(str(root), normalized_hash), None
    except Exception as exc:
        return None, _artifact_error(exc, "The normalized dataset or manifest is missing.")


def _render_schedule(
    root: Path,
    config: dict[str, Any] | None,
    results: dict[str, Any] | None,
    test_results_verified: bool,
    result_error: str | None,
    manifest: dict[str, Any] | None,
    origin: pd.Timestamp | None,
    mode: str,
    model_id: str,
    duration: float,
    slack: float,
    power: float,
    pue: float,
    explicit_deadline_offset: float | None,
) -> dict[str, Any]:
    st.title("GridShift")
    st.caption("Single-job carbon-aware scheduling and forecast evidence")
    st.subheader("Schedule")

    if config is None or origin is None or Job is None or scheduling is None:
        st.error("A valid UTC origin and the GridShift configuration are required.")
        return {}

    try:
        origin = grid_time(origin)
    except (TypeError, ValueError) as exc:
        st.error(f"Origin must be on the half-hour UTC grid: {exc}")
        return {}

    deadline_hours = (
        explicit_deadline_offset
        if explicit_deadline_offset is not None
        else duration + slack
    )
    deadline = origin + pd.to_timedelta(deadline_hours, unit="h")
    try:
        job = Job(
            id="dashboard-job",
            release=origin,
            duration_hours=duration,
            deadline=deadline,
            power_kw=power,
            pue=pue,
        )
    except (TypeError, ValueError, OverflowError) as exc:
        st.error(f"Job is infeasible: {exc}")
        st.caption("No forecast is scored and no carbon recommendation is made for this workload.")
        return {"job": None, "path": None, "candidates": pd.DataFrame(), "fallback": False}

    energy_kwh = float(job.energy_kwh.sum())
    metric_columns = st.columns(3)
    metric_columns[0].metric("Forecast date (UTC)", origin.strftime("%Y-%m-%d"))
    metric_columns[1].metric("Duration", f"{duration:g} h")
    metric_columns[2].metric("Facility energy", f"{energy_kwh:.3f} kWh")
    st.caption(
        f"Forecast origin: {_format_utc(origin)}. Model: {model_id or 'unavailable'}. "
        f"Hard deadline: {_format_utc(deadline)}. PUE is applied once to IT power. "
        "Predicted job emissions are modeled operational CO2, not realized or avoided emissions."
    )

    if mode == "Historical":
        st.caption("Historical issue mode uses only the frozen path stored for the selected origin.")
    else:
        st.caption("Live mode uses only observations fetched by the explicit refresh button.")

    if not model_id:
        path, bounds, metadata, path_error, observations = None, {}, {}, "No model is selected.", None
    else:
        path, bounds, metadata, path_error, observations = _make_forecast(
            root, config, origin, mode, model_id, test_results_verified, result_error
        )

    if mode == "Live":
        actual_for_chart = observations
        history_error = None
    elif path is not None:
        actual_for_chart, history_error = _load_historical_actual(root, manifest)
    else:
        actual_for_chart, history_error = None, None

    if mode == "Live":
        live_observations, refresh_error = _live_observations(origin)
        if refresh_error:
            st.warning(
                f"Live API refresh failed: {refresh_error}. "
                "Carbon recommendation is disabled until a successful refresh."
            )
        if live_observations is None:
            st.info("Live observations have not been fetched for this origin. No network request is made on rerun.")
        elif refresh_error:
            st.caption(
                "The last successful observation snapshot is retained for inspection, but is not used to rank schedules."
            )
        else:
            state = live.operational_state(
                live_observations,
                origin,
                config.get("study", {}).get("publication_delay_slots", 1),
            )
            if state["status"] == "fresh":
                st.success(
                    f"Observation state: fresh. Latest eligible interval: "
                    f"{_format_utc(state['last_observation'])}."
                )
            else:
                last_value = state.get("last_observation") or "none"
                age = state.get("age_hours")
                age_text = f"; age {age:.2f} hours" if age is not None else ""
                st.warning(
                    f"Observation state: {state['status']}. Latest eligible interval: "
                    f"{last_value}{age_text}. Carbon recommendation is disabled."
                )

    if path is None:
        if path_error:
            st.warning(f"Forecast unavailable: {path_error}")
        if history_error and mode == "Historical":
            st.warning(f"Historical data could not be loaded: {history_error}")

    try:
        candidate_frame = scheduling.candidates(job, path)
    except Exception as exc:
        st.error(f"Candidate generation failed: {type(exc).__name__}: {exc}")
        return {"job": job, "path": path, "candidates": pd.DataFrame(), "fallback": False}

    decision = None
    selected_start = None
    fallback = False
    fallback_reason = None
    if path is not None:
        try:
            decision = scheduling.recommend(job, path)
        except Exception as exc:
            fallback_reason = f"Scheduler could not rank the forecast path: {type(exc).__name__}: {exc}"
        if decision is not None and decision.status == "scheduled":
            selected_start = decision.start
            st.info(
                f"Forecast-ranked start: {_format_utc(decision.start)} to "
                f"{_format_utc(decision.finish)}. Integrated predicted job emissions: "
                f"{decision.predicted_grams:,.2f} gCO2."
            )
            st.caption(
                "This is a forecast-based operating suggestion. It is not a measured outcome or an avoided-emissions claim."
            )
            st.caption(
                "Calibrated job-cost intervals are unavailable for this recommendation. "
                "The plotted bands describe individual forecast intervals and cannot be added "
                "to obtain a job-cost interval. Model comparison includes representative "
                "validation examples using joint conditional paths."
            )
        elif decision is not None and decision.status == "infeasible":
            st.error(f"No feasible candidate: {decision.reason}")
        else:
            fallback_reason = fallback_reason or (
                decision.reason if decision is not None else "Forecast ranking is unavailable."
            )

    if selected_start is None:
        feasible_rows = candidate_frame.loc[
            candidate_frame["start"].notna() & candidate_frame["finish"].notna()
        ] if not candidate_frame.empty else pd.DataFrame()
        if not feasible_rows.empty and (decision is None or decision.status == "unavailable"):
            fallback = True
            selected_start = feasible_rows.iloc[0]["start"]
            fallback_reason = fallback_reason or "A complete forecast-covered ranking is not available."
            st.warning(
                f"Earliest feasible fallback: {_format_utc(selected_start)}. "
                "It is not carbon-ranked; no emissions estimate is shown."
            )
        elif candidate_frame.empty or feasible_rows.empty:
            st.error("No feasible start interval is available for this workload and deadline.")

    if fallback and fallback_reason:
        st.caption(f"Fallback reason: {fallback_reason}")

    if path is not None:
        chart, interval_note = _plot_path(
            path,
            bounds,
            actual_for_chart,
            mode,
            show_retrospective_actual=False,
        )
        st.plotly_chart(chart, use_container_width=True)
        st.caption(
            f"Forecast issue time: {_format_utc(path.origin)}. "
            f"Latest eligible observation / training cutoff: {_format_utc(path.training_cutoff)}. "
            f"Path status: {path.status}. {interval_note}"
        )
    else:
        st.info(
            "Forecast path is unavailable. The table below contains time-feasible windows only; "
            "their carbon costs are unscored."
        )

    _candidate_timeline(candidate_frame, selected_start, fallback)
    display_candidates = _candidate_display(candidate_frame, selected_start, fallback)
    if not display_candidates.empty:
        st.dataframe(display_candidates, use_container_width=True, hide_index=True)
        _frame_download(
            "Download all candidate windows",
            display_candidates,
            "gridshift_candidate_windows.csv",
            "download_schedule_candidates",
        )
    return {
        "job": job,
        "path": path,
        "bounds": bounds,
        "metadata": metadata,
        "candidates": candidate_frame,
        "selected_start": selected_start,
        "fallback": fallback,
        "actual": actual_for_chart,
        "interval_note": None,
        "path_error": path_error,
        "decision": decision,
    }


def _render_forecasts(
    root: Path,
    config: dict[str, Any] | None,
    context: dict[str, Any],
    origin: pd.Timestamp | None,
    mode: str,
    model_id: str,
    test_results_verified: bool,
    result_error: str | None,
) -> None:
    st.title("GridShift")
    st.caption("Forecast issue paths and interval evidence")
    st.subheader("Forecasts")
    if config is None or origin is None or not model_id:
        st.info("Select a valid origin and an available model to inspect forecast intervals.")
        return

    path, bounds, metadata, error, observations = _make_forecast(
        root, config, origin, mode, model_id, test_results_verified, result_error
    )
    if path is None:
        st.warning(f"Forecast unavailable: {error or 'No stored path is available.'}")
        return

    historical_actual, history_error = _load_historical_actual(root, context.get("manifest"))
    series = observations if mode == "Live" else historical_actual
    chart, interval_note = _plot_path(
        path,
        bounds,
        series,
        mode,
        show_retrospective_actual=(mode == "Historical"),
    )
    st.plotly_chart(chart, use_container_width=True)

    state = metadata.get("operational_state", {})
    latest_eligible = state.get("last_observation") or _format_utc(path.training_cutoff)
    st.caption(
        f"Issue time: {_format_utc(path.origin)}. Latest eligible observation: {latest_eligible}. "
        f"Model: {path.model_id}. Status: {path.status}. {interval_note}"
    )
    if mode == "Historical":
        st.caption(
            "The realized-actual overlay is retrospective and appears only in Historical mode. "
            "It does not enter the scheduler's candidate costs."
        )
    elif history_error:
        st.warning(f"Live history is shown only from the fetched response: {history_error}")

    frame, _ = _forecast_frame(path, bounds, metadata)
    st.dataframe(frame, use_container_width=True, hide_index=True)
    _frame_download(
        "Download forecast intervals",
        frame,
        "gridshift_forecast_intervals.csv",
        "download_forecast_intervals",
    )

    if mode == "Historical":
        stage = _stage_for_origin(origin, config)
        baseline_id = "calendar_mean"
        if path.model_id == baseline_id:
            st.caption("Calendar-mean baseline is selected; no duplicate baseline line is shown.")
        else:
            try:
                baseline, baseline_bounds = live.historical_path(
                    root, config, origin, baseline_id, stage=stage
                )
                comparison = pd.DataFrame(
                    {
                        "interval_start_utc": pd.date_range(
                            origin, periods=len(path.mean), freq=SLOT, tz="UTC"
                        ),
                        f"{path.model_id}_mean_gco2_per_kwh": path.mean,
                        f"{baseline_id}_mean_gco2_per_kwh": baseline.mean,
                    }
                )
                st.subheader("Baseline comparison")
                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(
                        x=comparison["interval_start_utc"],
                        y=comparison[f"{path.model_id}_mean_gco2_per_kwh"],
                        name=path.model_id,
                        mode="lines",
                        line={"color": "#087f78", "width": 2.2},
                    )
                )
                fig.add_trace(
                    go.Scatter(
                        x=comparison["interval_start_utc"],
                        y=comparison[f"{baseline_id}_mean_gco2_per_kwh"],
                        name=baseline_id,
                        mode="lines",
                        line={"color": "#b7791f", "width": 1.8, "dash": "dash"},
                    )
                )
                fig.update_layout(
                    height=300,
                    margin={"l": 12, "r": 12, "t": 16, "b": 12},
                    xaxis_title="Interval start (UTC)",
                    yaxis_title="Forecast mean (gCO2/kWh)",
                    plot_bgcolor="#ffffff",
                    paper_bgcolor="#ffffff",
                )
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(comparison, use_container_width=True, hide_index=True)
                _frame_download(
                    "Download model and baseline paths",
                    comparison,
                    "gridshift_baseline_comparison.csv",
                    "download_baseline_comparison",
                )
            except Exception as exc:
                st.info(f"Baseline comparison is unavailable: {type(exc).__name__}: {exc}")


def _render_model_comparison(
    root: Path,
    config: dict[str, Any] | None,
    results: dict[str, Any] | None,
    test_results_verified: bool,
    result_error: str | None,
) -> None:
    st.title("GridShift")
    st.caption("Validation selection, locked-test evidence, and diagnostics")
    st.subheader("Model comparison")
    st.info("This view does not fit models or score the 2025 test period.")
    if not test_results_verified:
        reason = f" Verification status: {result_error}" if result_error else ""
        st.warning(
            "2025 test artifacts are hidden until results.json matches the frozen data, protocol, "
            f"software, and validation-artifact hashes.{reason}"
        )
    if isinstance(results, dict):
        selection_columns = st.columns(3)
        for column, field, label in zip(
            selection_columns,
            ("forecast_champion", "strongest_simple", "deployment_model"),
            ("Forecast champion", "Strongest simple model", "Deployment model"),
            strict=True,
        ):
            value = results.get(field)
            column.metric(label, str(value) if value else "Not recorded")
    else:
        st.info("`artifacts/results.json` is not available; recorded model choices are not shown.")

    validation = _stage_metric_frame(root, config, results, "validation_metrics", "validation")
    test = _stage_metric_frame(
        root, config, results, "test_metrics", "test", test_results_verified
    )
    _render_metric_table("Validation metrics", validation, "validation_metrics", neutral_labels=False)
    _render_metric_table("Test metrics (recorded)", test, "test_metrics", neutral_labels=False)
    for stage, title in (("validation", "Validation common-origin metrics"), ("test", "Test common-origin metrics")):
        common = _artifact_frame(root, config, stage, "forecast_common_metrics.csv", test_results_verified)
        if not common.empty:
            _render_metric_table(title, common, f"{stage}_common", neutral_labels=False)

    order_rows: list[dict[str, Any]] = []
    choices = None
    if config is not None and run_dir is not None:
        try:
            choices, _ = _read_json(
                run_dir(root, config, "validation") / "validation_choices.json"
            )
        except (OSError, KeyError, ValueError, TypeError):
            choices = None
    if isinstance(choices, dict):
        for spec in choices.get("family_finalists", []):
            if isinstance(spec, dict):
                order_rows.append(
                    {
                        "model_id": spec.get("name"),
                        "family": spec.get("family"),
                        "order": _json_text(spec.get("order")),
                        "seasonal_order": _json_text(spec.get("seasonal_order")),
                        "transform": spec.get("transform"),
                    }
                )
    if order_rows:
        _render_metric_table(
            "Validation-selected model orders",
            pd.DataFrame(order_rows),
            "selected_orders",
            neutral_labels=False,
        )
    elif isinstance(results, dict) and results.get("selected_orders") is not None:
        _render_metric_table(
            "Selected model orders",
            _records_frame(results["selected_orders"]),
            "selected_orders",
            neutral_labels=False,
        )
    else:
        st.info("Model-order details are not present in the available result artifacts.")

    selection_ledger = _artifact_frame(root, config, "selection", "selection_ledger.csv")
    if not selection_ledger.empty:
        _render_metric_table(
            "Comparable-group order-search ledger",
            selection_ledger,
            "selection_ledger",
            neutral_labels=False,
        )
    else:
        st.info("AIC/BIC order-search groups are not present in the available result artifacts.")

    for title, relative, key in (
        ("Residual diagnostics", "residuals/ljung_box.csv", "residual_diagnostics"),
        ("Innovation distribution", "residuals/innovation_distribution.csv", "innovation_distribution"),
    ):
        frame = _artifact_frame(root, config, "validation", relative)
        if not frame.empty:
            _render_metric_table(title, frame, key, neutral_labels=False)
        else:
            st.caption(f"{title}: not included in the available artifacts.")

    uncertainty_rows = []
    if isinstance(choices, dict) and config is not None and run_dir is not None:
        residual_dir = run_dir(root, config, "validation") / "residuals"
        for filename in sorted(residual_dir.glob("model_*_job_uncertainty.json")):
            record, _ = _read_json(filename)
            if isinstance(record, dict):
                uncertainty_rows.append({
                    key: record.get(key) for key in (
                        "model_id", "origin", "chosen_start", "duration_hours", "energy_kwh",
                        "mean_grams", "lower80", "upper80", "lower95", "upper95", "simulations",
                    )
                })
    if uncertainty_rows:
        st.subheader("Representative job-cost uncertainty")
        st.caption(
            "Stored validation examples integrate 1,000 joint conditional state-space paths. "
            "Costs and bounds are in gCO2 for a 2-hour, 0.96 kWh job at the recorded start. "
            "They preserve temporal error dependence but exclude parameter uncertainty. "
            "These are not calibrated intervals for the workload in Schedule."
        )
        st.dataframe(pd.DataFrame(uncertainty_rows), use_container_width=True, hide_index=True)

    if isinstance(results, dict) and results.get("limitations"):
        st.subheader("Limitations")
        limitations = results["limitations"]
        if isinstance(limitations, list):
            for item in limitations:
                st.write(f"- {item}")
        else:
            st.write(limitations)


def _render_backtests(
    results: dict[str, Any] | None,
    result_error: str | None,
) -> None:
    st.title("GridShift")
    st.caption("Recorded historical replay outputs")
    st.subheader("Backtests")
    st.info(
        "This page only reads existing replay summaries. It does not rerun a backtest or make a live savings claim."
    )
    if not isinstance(results, dict):
        if result_error:
            st.warning(f"Backtest evidence is hidden because `artifacts/results.json` was not accepted: {result_error}")
        else:
            st.warning("Backtest evidence is unavailable because `artifacts/results.json` has not been produced.")
        return

    sections = (
        ("primary_summary", "Single-job primary summary"),
        ("primary_bootstrap", "Paired uncertainty summary"),
        ("queue_summary", "Queue service summary"),
    )
    found = False
    for field, title in sections:
        frame = _records_frame(results.get(field))
        if frame.empty:
            st.caption(f"{title}: not included in the result bundle.")
            continue
        found = True
        _render_metric_table(title, frame, field, allow_filters=True, neutral_labels=True)
    if not found:
        st.warning("No backtest summary tables are present in `artifacts/results.json`.")
    limitations = results.get("limitations")
    if limitations:
        st.subheader("Interpretation limits")
        if isinstance(limitations, list):
            for item in limitations:
                st.write(f"- {item}")
        else:
            st.write(limitations)


def _render_evidence(
    root: Path,
    manifest: dict[str, Any] | None,
    quality: dict[str, Any] | None,
    freeze: dict[str, Any] | None,
    deployment: dict[str, Any] | None,
    results: dict[str, Any] | None,
    result_error: str | None,
) -> None:
    st.title("GridShift")
    st.caption("Data lineage, frozen protocol, and deployment bundle")
    st.subheader("Data and evidence")
    if manifest:
        columns = st.columns(3)
        columns[0].metric("Source", str(manifest.get("source", DATA_SOURCE_NAME)))
        columns[1].metric("Licence", str(manifest.get("licence", "Not recorded")))
        columns[2].metric("Data hash", str(manifest.get("normalized_hash", "Not recorded"))[:18])
        st.caption(f"Normalized dataset hash: `{manifest.get('normalized_hash', 'Not recorded')}`")
        st.write(
            {
                "Retrieved / frozen at (UTC)": manifest.get("frozen_at_utc"),
                "Target": manifest.get("target"),
                "Units": manifest.get("units"),
                "Observed slots": manifest.get("observed_slots"),
                "Expected slots": manifest.get("expected_slots"),
                "Normalized slots": manifest.get("normalized_slots"),
            }
        )
        _frame_download(
            "Download data manifest",
            pd.DataFrame([manifest]),
            "gridshift_data_manifest.csv",
            "download_data_manifest",
        )
    else:
        st.warning(f"No data manifest is available under `{root / 'data'}`.")

    if quality:
        st.subheader("Coverage and quality")
        st.write(
            {
                "Overall coverage": quality.get("overall_coverage"),
                "Minimum monthly coverage": quality.get("minimum_monthly_coverage"),
                "Minimum test-month coverage": quality.get("minimum_test_monthly_coverage"),
                "Observed values": quality.get("observed"),
                "Missing actuals": quality.get("missing"),
                "Regular UTC grid": quality.get("regular_grid"),
                "Data gate": quality.get("data_gate_pass"),
                "Availability basis": "Interval end plus 30 minutes; not vintage verified",
            }
        )
        coverage = _read_csv(root / "artifacts" / "data" / "monthly_coverage.csv")
        if coverage is not None:
            st.dataframe(coverage, use_container_width=True, hide_index=True)
            _frame_download(
                "Download monthly coverage",
                coverage,
                "gridshift_monthly_coverage.csv",
                "download_monthly_coverage",
            )

    missingness_path = root / "artifacts" / "data" / "source_missingness.csv"
    missingness = _read_csv(missingness_path)
    st.subheader("Missingness provenance")
    if missingness is None:
        st.info("The raw-source missingness ledger is not available.")
    elif "reason" not in missingness:
        st.warning("The missingness ledger has no `reason` column; source categories are unavailable.")
    else:
        labels = {
            "absent_interval": "No raw source interval was returned",
            "explicit_null_actual": "Raw source interval had a null actual",
        }
        reasons = missingness["reason"].fillna("unclassified").astype(str)
        summary = reasons.value_counts(dropna=False).rename_axis("reason").reset_index(name="intervals")
        summary["interpretation"] = summary["reason"].map(labels).fillna("Unclassified source reason")
        summary = summary[["reason", "interpretation", "intervals"]]
        st.dataframe(summary, use_container_width=True, hide_index=True)
        st.caption(f"Reason counts are derived from `{missingness_path.relative_to(root)}`.")
        _frame_download(
            "Download missingness summary",
            summary,
            "gridshift_missingness_summary.csv",
            "download_missingness_summary",
        )
        _frame_download(
            "Download missingness ledger",
            missingness,
            "gridshift_source_missingness.csv",
            "download_source_missingness",
        )

    if freeze:
        protocol = freeze.get("protocol", {})
        st.subheader("Frozen protocol")
        st.write(
            {
                "Protocol hash": freeze.get("protocol_hash"),
                "Data hash": freeze.get("data_hash"),
                "Frozen at (UTC)": freeze.get("frozen_at_utc"),
                "Study ID": protocol.get("study_id"),
                "Test period": freeze.get("test_period"),
                "Deployment model": protocol.get("deployment_model"),
                "Accounting": protocol.get("accounting"),
            }
        )
    else:
        st.info("No frozen protocol is present.")

    if deployment:
        st.subheader("Trusted deployment bundle")
        st.write(
            {
                "Schema version": deployment.get("schema_version"),
                "Model": deployment.get("model_id"),
                "Kind": deployment.get("kind"),
                "Training cutoff": deployment.get("training_cutoff"),
                "Protocol hash": deployment.get("protocol_hash"),
                "Data hash": deployment.get("data_hash"),
                "Bundle hash": deployment.get("file_hash"),
                "Library versions": deployment.get("library_versions"),
            }
        )
    else:
        st.info("No trusted deployment manifest is available.")

    if result_error:
        st.error(f"`artifacts/results.json` is not accepted: {result_error}")
    elif results:
        st.subheader("Result bundle")
        st.write(
            {
                "Study ID": results.get("study_id"),
                "Forecast champion": results.get("forecast_champion"),
                "Strongest simple model": results.get("strongest_simple"),
                "Deployment model": results.get("deployment_model"),
                "Result fields": sorted(results.keys()),
            }
        )
        result_path = root / "artifacts" / "results.json"
        if result_path.is_file():
            st.download_button(
                "Download results.json",
                data=result_path.read_bytes(),
                file_name="gridshift_results.json",
                mime="application/json",
                key="download_results_json",
            )
    else:
        st.info(
            "`artifacts/results.json` is not available. Validation and live views remain usable; "
            "2025 test views require a verified result bundle."
        )

    st.caption(
        "Source: official NESO carbon intensity API. Estimated actuals are not vintage-verified; "
        "stored results retain their original protocol and data hashes."
    )


def _load_json_if_present(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    value, error = _read_json(path)
    if value is not None and not isinstance(value, dict):
        return None, "Expected a JSON object at the artifact boundary."
    return value, error


def _verified_results(
    root: Path,
    config: dict[str, Any] | None,
    results: dict[str, Any] | None,
    read_error: str | None,
) -> tuple[dict[str, Any] | None, str | None]:
    if results is None:
        return None, read_error
    if config is None or require_freeze is None:
        return None, "Frozen protocol verification is unavailable."

    try:
        frozen = require_freeze(root, config)
    except Exception as exc:
        detail = _artifact_error(exc, "The frozen protocol is missing.")
        return None, f"Frozen protocol verification failed: {detail}"

    if not isinstance(frozen, dict) or not isinstance(frozen.get("protocol"), dict):
        return None, "Frozen protocol verification returned an invalid record."
    protocol = frozen["protocol"]
    if results.get("schema_version") != 1:
        return None, "Unsupported results schema."
    if results.get("experimental_status") != "EXECUTED_FROZEN_2025":
        return None, "Results are not marked as an executed frozen 2025 study."

    # The result bundle has no self-digest, so bind its identity and model choices to the verified freeze.
    for field, expected in (
        ("study_id", protocol.get("study_id")),
        ("data_hash", frozen.get("data_hash")),
        ("protocol_hash", frozen.get("protocol_hash")),
        ("software_hash", protocol.get("software_hash")),
        ("forecast_champion", protocol.get("forecast_champion")),
        ("best_classical", protocol.get("best_classical")),
        ("strongest_simple", protocol.get("strongest_simple")),
        ("deployment_model", protocol.get("deployment_model")),
    ):
        if not isinstance(expected, str) or not expected or results.get(field) != expected:
            return None, f"Results field `{field}` does not match the verified protocol freeze."

    table_fields = (
        "validation_metrics",
        "test_metrics",
        "primary_summary",
        "primary_bootstrap",
        "queue_summary",
    )
    for field in table_fields:
        table = results.get(field)
        if not isinstance(table, list) or not table or any(not isinstance(row, dict) for row in table):
            return None, f"Results field `{field}` is missing or malformed."
    if not isinstance(results.get("limitations"), list) or not results["limitations"]:
        return None, "Results field `limitations` is missing or malformed."
    return results, None


def _change_data_mode() -> None:
    if st.session_state.get("gridshift_data_mode") == "Live":
        now = pd.Timestamp.now(tz="UTC").floor("30min")
        st.session_state["gridshift_origin_date"] = now.date()
        st.session_state["gridshift_origin_time"] = now.time()


def _preferred_model(results: dict[str, Any] | None, options: list[str]) -> str:
    preferred = None
    if isinstance(results, dict):
        preferred = (
            results.get("deployment_model")
            or results.get("forecast_champion")
            or results.get("strongest_simple")
        )
    if not preferred or preferred not in options:
        preferred = "calendar_mean" if "calendar_mean" in options else options[0]
    return preferred


def _test_leaderboard(
    results: dict[str, Any] | None,
    metric: str = "mase",
    label: str = "MASE",
    order: list[str] | None = None,
) -> pd.DataFrame:
    rows = [
        row
        for row in ((results or {}).get("test_common_metrics") or [])
        if isinstance(row, dict) and row.get("group_type") == "overall"
    ]
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows)
    if not {"model_id", "horizon", metric}.issubset(frame.columns):
        return pd.DataFrame()
    table = frame.pivot_table(index="model_id", columns="horizon", values=metric, aggfunc="first")
    if order:
        table = table.reindex([name for name in order if name in table.index])
    else:
        table = table.reindex(table.mean(axis=1).sort_values().index)
    table.columns = [f"{label} h{int(column)}" for column in table.columns]
    return table.round(3).reset_index().rename(columns={"model_id": "Model"})


def _seasonality_note(root: Path) -> str | None:
    diagnostics, _ = _load_json_if_present(root / "artifacts" / "diagnostics" / "diagnostics.json")
    if not isinstance(diagnostics, dict):
        return None
    seasonal_acf = diagnostics.get("seasonal_acf") or {}
    stl = diagnostics.get("stl48") or {}
    daily = seasonal_acf.get("48")
    weekly = seasonal_acf.get("336")
    strength = stl.get("daily_seasonal_strength")
    period = stl.get("period_slots")
    if daily is None or strength is None or period is None:
        return None
    note = (
        f"**Why the seasonal model wins.** Half-hourly data makes one day exactly {int(period)} "
        f"slots, and that daily cycle is the strongest structure in the series: autocorrelation is "
        f"{float(daily):.2f} at lag {int(period)}"
    )
    if weekly is not None:
        note += f", against {float(weekly):.2f} at lag 336 (a week)"
    note += (
        f", and an STL decomposition puts daily seasonal strength at {float(strength):.2f}. "
        f"The `x(1,0,0,{int(period)})` term is a seasonal autoregressive term at that lag — in effect "
        "\"what was intensity at this time yesterday\". The non-seasonal models have no such term, so "
        "beyond a few hours their forecasts decay toward the series mean and their error climbs past "
        "the seasonal-naive benchmark."
    )
    return note


def _calibration_note(results: dict[str, Any] | None, champion: str | None) -> str | None:
    if not champion:
        return None
    rows = [
        row
        for row in ((results or {}).get("test_common_metrics") or [])
        if isinstance(row, dict)
        and row.get("group_type") == "overall"
        and row.get("model_id") == champion
        and row.get("coverage80") is not None
    ]
    if not rows:
        return None
    worst = min(rows, key=lambda row: float(row["coverage80"]))
    return (
        "**But its uncertainty bands are too narrow.** Point accuracy and interval calibration are "
        f"different things: at horizon h{int(worst['horizon'])} the 80% intervals of `{champion}` cover "
        f"only {float(worst['coverage80']):.1%} of outcomes against a nominal 80%. Several less accurate "
        "models track 80% far more closely. Trust the recommended window more than the width of the band "
        "drawn around it."
    )


def _render_model_guidance(root: Path, results: dict[str, Any] | None, model_id: str) -> None:
    st.markdown("#### Which model is best?")
    if not isinstance(results, dict):
        st.caption("Recorded test metrics are unavailable, so no ranking can be shown.")
        return

    champion = results.get("forecast_champion")
    simple = results.get("strongest_simple")
    deployed = results.get("deployment_model")

    notes = []
    if champion:
        notes.append(
            f"**Most accurate:** `{champion}`. It has the lowest error at every horizon from "
            "2 hours ahead (h4) out to 24 hours ahead (h48) — the range a deadline-constrained "
            "job actually depends on. Only one slot ahead is it narrowly beaten."
        )
    if simple:
        notes.append(
            f"**Best simple baseline:** `{simple}`. Carrying the last reading forward costs nothing "
            "to fit, and a full day out it still comes second only to the champion."
        )
    if deployed:
        kind = (
            "a baseline, not a fitted classical model"
            if results.get("deployment_is_classical") is False
            else "a fitted classical model"
        )
        notes.append(
            f"**Deployed here:** `{deployed}` — {kind}. It is the least accurate of the three, "
            "so the recommended window it produces is driven by the daily shape of the grid "
            "rather than by forecast skill."
        )
    st.markdown("\n\n".join(f"- {note}" for note in notes))

    seasonality = _seasonality_note(root)
    if seasonality:
        st.markdown(seasonality)
    calibration = _calibration_note(results, champion)
    if calibration:
        st.markdown(calibration)

    interpretation = results.get("h3_interpretation")
    if interpretation:
        st.caption(f"Recorded study conclusion: {interpretation}.")
    st.caption(
        "MASE is scaled against a seasonal-naive reference: below 1 beats it, above 1 is worse. "
        "h1 is 30 minutes ahead and h48 is 24 hours ahead."
    )
    if model_id and champion and model_id != champion:
        st.caption(f"You have `{model_id}` selected. For the lowest forecast error, choose `{champion}`.")

    table = _test_leaderboard(results)
    if not table.empty:
        with st.expander("Recorded 2025 test accuracy by horizon"):
            st.caption("Point accuracy as MASE. Lower is better; below 1 beats the seasonal-naive reference.")
            st.dataframe(table, use_container_width=True, hide_index=True)
            coverage = _test_leaderboard(
                results, "coverage80", "Cover80", order=list(table["Model"])
            )
            if not coverage.empty:
                st.caption(
                    "Share of outcomes falling inside the 80% interval, in the same model order. "
                    "Nominal is 0.80: below that the bands are too narrow, above it they are too wide."
                )
                st.dataframe(coverage, use_container_width=True, hide_index=True)


def _render_simple(
    root: Path,
    config: dict[str, Any] | None,
    results: dict[str, Any] | None,
    test_results_verified: bool,
    result_error: str | None,
    model_options: list[str],
    defaults: dict[str, float],
) -> None:
    st.title("GridShift")
    st.caption("Choose a fitted model, then run the forecast.")

    if config is None:
        st.error("A readable study configuration is required.")
        return

    controls = st.columns([3, 1], vertical_alignment="bottom")
    model_id = controls[0].selectbox(
        "Fitted model",
        options=model_options,
        index=model_options.index(_preferred_model(results, model_options)),
        key="simple_model",
        disabled=IMPORT_ERROR is not None,
    )
    if controls[1].button(
        "Run forecast",
        type="primary",
        use_container_width=True,
        disabled=IMPORT_ERROR is not None,
        key="simple_run",
    ):
        st.session_state["simple_ran"] = True

    with st.expander("Job settings"):
        setting_columns = st.columns(3)
        origin_date = setting_columns[0].date_input(
            "Origin date (UTC)", value=DEFAULT_ORIGIN_DATE, key="simple_origin_date"
        )
        origin_time = setting_columns[1].time_input(
            "Origin time (UTC)", value=DEFAULT_ORIGIN_TIME, step=1800, key="simple_origin_time"
        )
        duration = setting_columns[2].number_input(
            "Duration (hours)",
            min_value=0.5,
            max_value=48.0,
            value=float(defaults["duration_hours"]),
            step=0.5,
            key="simple_duration",
        )
        slack = setting_columns[0].number_input(
            "Slack after duration (hours)",
            min_value=0.0,
            max_value=48.0,
            value=float(defaults["slack_hours"]),
            step=0.5,
            key="simple_slack",
        )
        power = setting_columns[1].number_input(
            "IT power (kW)",
            min_value=0.01,
            max_value=100000.0,
            value=float(defaults["power_kw"]),
            step=0.1,
            key="simple_power",
        )
        pue = setting_columns[2].number_input(
            "PUE",
            min_value=1.0,
            max_value=5.0,
            value=float(defaults["pue"]),
            step=0.05,
            key="simple_pue",
        )

    if not st.session_state.get("simple_ran"):
        st.info("Press Run forecast to score the half-hour windows before this job's deadline.")
        return

    if Job is None or scheduling is None:
        st.error(f"GridShift package is unavailable: {IMPORT_ERROR}")
        return

    try:
        origin = pd.Timestamp(dt.datetime.combine(origin_date, origin_time), tz="UTC")
        if grid_time is not None:
            origin = grid_time(origin)
    except (TypeError, ValueError) as exc:
        st.error(f"Invalid origin: {exc}")
        return

    deadline = origin + pd.to_timedelta(float(duration) + float(slack), unit="h")
    try:
        job = Job(
            id="dashboard-job",
            release=origin,
            duration_hours=float(duration),
            deadline=deadline,
            power_kw=float(power),
            pue=float(pue),
        )
    except (TypeError, ValueError, OverflowError) as exc:
        st.error(f"Job is infeasible: {exc}")
        return

    path, bounds, metadata, path_error, _ = _make_forecast(
        root, config, origin, "Historical", model_id, test_results_verified, result_error
    )
    if path is None:
        st.warning(
            f"Forecast unavailable: {path_error or 'No stored path for this model and origin.'}"
        )
        return

    decision = None
    try:
        decision = scheduling.recommend(job, path)
    except Exception as exc:
        st.warning(f"Scheduler could not rank this path: {type(exc).__name__}: {exc}")

    scheduled = decision is not None and decision.status == "scheduled"
    metrics = st.columns(3)
    metrics[0].metric(
        "Best start (UTC)",
        decision.start.strftime("%Y-%m-%d %H:%M") if scheduled else "—",
    )
    metrics[1].metric(
        "Predicted emissions",
        f"{decision.predicted_grams:,.1f} gCO2" if scheduled else "—",
    )
    metrics[2].metric("Facility energy", f"{float(job.energy_kwh.sum()):.3f} kWh")

    if scheduled:
        st.success(
            f"Run between {_format_utc(decision.start)} and {_format_utc(decision.finish)}."
        )
    elif decision is not None and decision.status == "infeasible":
        st.error(f"No feasible window: {decision.reason}")
    else:
        st.warning("No carbon-ranked window is available for this origin and deadline.")

    chart, interval_note = _plot_path(path, bounds, None, "Historical", show_retrospective_actual=False)
    st.plotly_chart(chart, use_container_width=True)
    st.markdown(
        "**How to read this.** The solid line is the forecast mean carbon intensity for each "
        "half-hour slot, in gCO2 per kWh. The teal band around it is the 80% prediction interval "
        "and the wider grey band the 95% interval, so bands that widen to the right mean the model "
        "is less sure further ahead. Low points on the line are cleaner slots: the scheduler scores "
        "every window long enough to fit the job and finishing before the deadline, then picks the "
        "one with the lowest predicted emissions."
    )
    st.caption(
        f"Model: {path.model_id}. Issued {_format_utc(path.origin)}. "
        f"Hard deadline: {_format_utc(deadline)}. {interval_note} "
        "The bands describe single slots and cannot be added together to get an interval for the "
        "whole job. Predicted operational CO2 from a forecast, not a measured or avoided-emissions result."
    )
    _render_model_guidance(root, results, model_id)

    with st.expander("Forecast intervals and candidate windows"):
        frame, _ = _forecast_frame(path, bounds, metadata)
        st.dataframe(frame, use_container_width=True, hide_index=True)
        try:
            display = _candidate_display(
                scheduling.candidates(job, path),
                decision.start if scheduled else None,
            )
        except Exception as exc:
            st.caption(f"Candidate windows unavailable: {type(exc).__name__}: {exc}")
        else:
            if not display.empty:
                st.dataframe(display, use_container_width=True, hide_index=True)


def main() -> None:
    st.set_page_config(
        page_title="GridShift",
        layout="wide",
        initial_sidebar_state="auto",
    )
    st.markdown(
        """
        <style>
        :root {
            --grid-ink: #17252d;
            --grid-muted: #5e6c73;
            --grid-teal: #087f78;
            --grid-gold: #b7791f;
            --grid-red: #a94442;
            --grid-line: #dce3e5;
            --grid-page: #f5f8f8;
            --primary-color: #087f78;
            --text-color: #17252d;
            --background-color: #f5f8f8;
            --secondary-background-color: #ffffff;
            color-scheme: light;
        }
        body, [data-testid="stHeader"], [data-testid="stAppViewContainer"],
        [data-testid="stMain"], .stApp {
            background: var(--grid-page) !important;
            color: var(--grid-ink) !important;
        }
        section[data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid var(--grid-line);
        }
        .block-container { max-width: 1320px; padding-top: 1.3rem; }
        h1, h2, h3 { color: var(--grid-ink); letter-spacing: 0; }
        h1 { font-size: 1.8rem; }
        h2 { font-size: 1.3rem; }
        h3 { font-size: 1.05rem; }
        .stApp p, .stApp label, .stApp span, .stApp li,
        .stApp [data-testid="stMarkdownContainer"],
        .stApp [data-testid="stMarkdownContainer"] *,
        .stApp [data-testid="stAlert"] *,
        .stApp [data-testid="stMetric"] *,
        section[data-testid="stSidebar"] * {
            color: var(--grid-ink) !important;
        }
        .stApp input, .stApp textarea, .stApp [role="combobox"],
        .stApp [data-baseweb="select"] {
            background-color: #ffffff !important;
            color: var(--grid-ink) !important;
            border-color: var(--grid-line) !important;
        }
        .stApp [data-testid="stDateInput"] [data-baseweb="input"],
        .stApp [data-testid="stTimeInput"] [data-baseweb="input"],
        .stApp [data-testid="stNumberInput"] [data-baseweb="input"] {
            background-color: #ffffff !important;
            color: var(--grid-ink) !important;
            border-color: var(--grid-line) !important;
        }
        .stApp [data-testid="stDateInputField"],
        .stApp [data-testid="stTimeInputTimeDisplay"],
        .stApp [data-testid="stNumberInputContainer"] {
            background-color: #ffffff !important;
            color: var(--grid-ink) !important;
            border-color: var(--grid-line) !important;
        }
        .stApp [data-testid="stNumberInput"] button {
            background-color: #ffffff !important;
            color: var(--grid-ink) !important;
            border-color: var(--grid-line) !important;
        }
        .stApp label[data-testid="stRadioOption"][data-selected="true"] > div > div:first-child {
            background-color: var(--grid-teal) !important;
            border-color: var(--grid-teal) !important;
        }
        .stApp button { color: var(--grid-ink) !important; }
        .stApp [data-testid="stSelectbox"] > div > div {
            background-color: #ffffff !important;
            border-color: var(--grid-line) !important;
        }
        .stApp [data-testid="stSelectbox"] svg { fill: var(--grid-muted) !important; }
        .stApp [data-testid="stExpander"] details {
            background-color: #ffffff !important;
            border: 1px solid var(--grid-line) !important;
            border-radius: 6px;
        }
        .stApp [data-testid="stExpander"] summary {
            background-color: #ffffff !important;
            border-radius: 6px;
        }
        .stApp [data-testid="stExpander"] summary:hover { background-color: #eef4f4 !important; }
        .stApp [data-testid="stMarkdownContainer"] code,
        .stApp [data-testid="stMarkdownContainer"] strong code {
            background-color: #eef4f4 !important;
            color: var(--grid-teal) !important;
        }
        [data-testid="stSelectboxVirtualDropdown"] {
            background-color: #ffffff !important;
            border: 1px solid var(--grid-line) !important;
        }
        [data-testid="stSelectboxVirtualDropdown"] [role="option"],
        [data-testid="stSelectboxVirtualDropdown"] [role="option"] * {
            color: var(--grid-ink) !important;
        }
        [data-testid="stSelectboxVirtualDropdown"] [role="option"]:hover,
        [data-testid="stSelectboxVirtualDropdown"] [role="option"][aria-selected="true"] {
            background-color: #eef4f4 !important;
        }
        .stApp button[kind="primary"],
        .stApp [data-testid="stBaseButton-primary"] {
            background-color: var(--grid-teal) !important;
            border-color: var(--grid-teal) !important;
            color: #ffffff !important;
        }
        .stApp button[kind="primary"]:hover,
        .stApp [data-testid="stBaseButton-primary"]:hover {
            background-color: #0a6b65 !important;
            border-color: #0a6b65 !important;
            color: #ffffff !important;
        }
        div[data-testid="stAlert"] {
            color: var(--grid-ink) !important;
            background: #eef4f4 !important;
            border-radius: 6px;
        }
        div[data-testid="stMetric"] {
            border-left: 3px solid var(--grid-teal);
            padding: 0.45rem 0.7rem;
            background: #ffffff;
            border-radius: 6px;
        }
        div[data-testid="stAlert"] { border-radius: 6px; }
        div[data-testid="stDataFrame"] { border: 1px solid var(--grid-line); border-radius: 6px; }
        @media (max-width: 640px) {
            .block-container { padding: 0.7rem 0.7rem 2rem; }
            h1 { font-size: 1.5rem; }
            div[data-testid="stMetric"] { padding: 0.35rem 0.45rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    config, config_error = _config(ROOT)
    raw_results, results_read_error = _load_json_if_present(ROOT / "artifacts" / "results.json")
    results, result_error = _verified_results(
        ROOT, config, raw_results, results_read_error
    )
    test_results_verified = results is not None
    manifest, manifest_error = _load_json_if_present(ROOT / "data" / "manifest.json")
    quality, _ = _load_json_if_present(ROOT / "artifacts" / "data" / "quality.json")
    freeze, _ = _load_json_if_present(ROOT / "artifacts" / "protocol_freeze.json")
    deployment, _ = _load_json_if_present(ROOT / "artifacts" / "deployment" / "deployment.json")

    if IMPORT_ERROR:
        st.error(f"GridShift package is unavailable: {IMPORT_ERROR}")
    if config_error:
        st.error(config_error)
    if manifest_error:
        st.warning(f"Data manifest could not be read: {manifest_error}")

    scheduling_config = (config or {}).get("scheduling", {})
    defaults = {
        "duration_hours": scheduling_config.get("default_duration_hours", 2.0),
        "slack_hours": scheduling_config.get("default_slack_hours", 10.0),
        "power_kw": scheduling_config.get("power_kw", 0.4),
        "pue": scheduling_config.get("pue", 1.2),
    }
    model_options = _model_options(ROOT, config, results, test_results_verified)

    with st.sidebar:
        research = st.toggle(
            "Research mode",
            value=False,
            key="gridshift_research_mode",
            help="Show the full evidence views: forecasts, model comparison, backtests, and provenance.",
        )

    if not research:
        _render_simple(
            ROOT,
            config,
            results,
            test_results_verified,
            result_error,
            model_options,
            defaults,
        )
        return

    with st.sidebar:
        st.markdown("### Workspace")
        view = st.radio("View", VIEWS, index=0, key="gridshift_view")
        st.markdown("---")
        st.markdown("### Workload")
        mode = st.radio(
            "Data mode",
            ("Historical", "Live"),
            horizontal=True,
            key="gridshift_data_mode",
            on_change=_change_data_mode,
        )
        origin_date = st.date_input(
            "Origin date (UTC)",
            value=DEFAULT_ORIGIN_DATE,
            key="gridshift_origin_date",
        )
        origin_time = st.time_input(
            "Origin time (UTC)",
            value=DEFAULT_ORIGIN_TIME,
            step=1800,
            key="gridshift_origin_time",
        )
        duration = st.number_input(
            "Duration (hours)",
            min_value=0.5,
            max_value=48.0,
            value=float(defaults["duration_hours"]),
            step=0.5,
            key="gridshift_duration",
        )
        slack = st.number_input(
            "Slack after duration (hours)",
            min_value=0.0,
            max_value=48.0,
            value=float(defaults["slack_hours"]),
            step=0.5,
            key="gridshift_slack",
        )
        power = st.number_input(
            "IT power (kW)",
            min_value=0.01,
            max_value=100000.0,
            value=float(defaults["power_kw"]),
            step=0.1,
            key="gridshift_power",
        )
        pue = st.number_input(
            "PUE",
            min_value=1.0,
            max_value=5.0,
            value=float(defaults["pue"]),
            step=0.05,
            key="gridshift_pue",
        )
        preferred_model = _preferred_model(results, model_options)
        model = st.selectbox(
            "Forecast model",
            options=model_options,
            index=model_options.index(preferred_model),
            key="gridshift_model",
            disabled=IMPORT_ERROR is not None,
        )

        use_deadline_override = st.checkbox(
            "Set a hard deadline offset",
            value=False,
            key="gridshift_use_deadline_override",
        )
        deadline_offset = None
        if use_deadline_override:
            default_offset = max(float(duration + slack), 0.5)
            deadline_offset = st.number_input(
                "Hard deadline after release (hours)",
                min_value=0.0,
                max_value=168.0,
                value=default_offset,
                step=0.5,
                key="gridshift_hard_deadline_offset",
            )

        try:
            origin = pd.Timestamp(dt.datetime.combine(origin_date, origin_time), tz="UTC")
            if grid_time is not None:
                origin = grid_time(origin)
        except (TypeError, ValueError) as exc:
            origin = None
            st.error(f"Invalid origin: {exc}")

        if mode == "Live":
            st.markdown("---")
            st.markdown("### Live observations")
            st.caption("No provider request is made on rerun.")
            bypass_cache = st.checkbox(
                "Bypass the 15-minute response cache",
                value=False,
                key="gridshift_bypass_cache",
            )
            if st.button(
                "Fetch / refresh observations",
                icon=":material/refresh:",
                disabled=origin is None or live is None,
                key="gridshift_live_refresh",
            ):
                _fetch_clicked_live(origin, bypass_cache)
        else:
            bypass_cache = False

    if config is None:
        st.info("The interface is available, but schedule calculations require a readable study configuration.")
        return

    if view == "Schedule":
        _render_schedule(
            ROOT,
            config,
            results,
            test_results_verified,
            result_error,
            manifest,
            origin,
            mode,
            model,
            float(duration),
            float(slack),
            float(power),
            float(pue),
            float(deadline_offset) if deadline_offset is not None else None,
        )
    elif view == "Forecasts":
        context = {"manifest": manifest}
        _render_forecasts(
            ROOT, config, context, origin, mode, model, test_results_verified, result_error
        )
    elif view == "Model comparison":
        _render_model_comparison(
            ROOT, config, results, test_results_verified, result_error
        )
    elif view == "Backtests":
        _render_backtests(results, result_error)
    elif view == "Data and evidence":
        _render_evidence(
            ROOT,
            manifest,
            quality,
            freeze,
            deployment,
            results,
            result_error,
        )


main()
