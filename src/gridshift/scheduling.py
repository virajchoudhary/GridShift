"""Single-job carbon-aware scheduling on the UTC half-hour grid."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from gridshift.domain import Decision, ForecastPath, Job, SLOT, grid_time, utc


_CANDIDATE_COLUMNS = (
    "candidate_index",
    "start",
    "finish",
    "waiting_hours",
    "predicted_grams",
    "status",
    "reason",
    "model_id",
)


def _candidate_windows(job: Job) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    duration = pd.Timedelta(hours=job.duration_hours)
    latest_start = job.deadline - duration
    if latest_start < job.release:
        return []
    count = (latest_start.value - job.release.value) // SLOT.value + 1
    starts = job.release + np.arange(count, dtype=np.int64) * SLOT
    return [(start, start + duration) for start in starts]


def _normalise_reservations(
    reservations: Iterable[object] | None,
) -> tuple[tuple[pd.Timestamp, pd.Timestamp], ...]:
    if reservations is None:
        return ()
    if isinstance(reservations, (str, bytes)):
        raise ValueError("Reservations must be intervals or scheduled decisions")

    intervals: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    try:
        values = iter(reservations)
    except TypeError as exc:
        raise ValueError("Reservations must be iterable") from exc

    for reservation in values:
        if isinstance(reservation, Decision):
            if reservation.status != "scheduled":
                continue
            start, finish = reservation.start, reservation.finish
        elif hasattr(reservation, "start") and hasattr(reservation, "finish"):
            start, finish = reservation.start, reservation.finish
        else:
            try:
                start, finish = reservation
            except (TypeError, ValueError) as exc:
                raise ValueError("Each reservation must have a start and finish") from exc

        if start is None or finish is None:
            raise ValueError("Reservation boundaries cannot be empty")
        start_utc = utc(start)
        finish_utc = utc(finish)
        if finish_utc <= start_utc:
            raise ValueError("Reservation finish must follow its start")
        intervals.append((start_utc, finish_utc))
    return tuple(intervals)


def _empty_rows(
    windows: list[tuple[pd.Timestamp, pd.Timestamp]],
    model_id: str,
    status: str,
    reason: str,
) -> pd.DataFrame:
    rows = [
        {
            "candidate_index": index,
            "start": start,
            "finish": finish,
            "waiting_hours": (start - windows[0][0]).total_seconds() / 3600,
            "predicted_grams": np.nan,
            "status": status,
            "reason": reason,
            "model_id": model_id,
        }
        for index, (start, finish) in enumerate(windows)
    ]
    return pd.DataFrame(rows, columns=_CANDIDATE_COLUMNS)


def _unavailable_decision(job: Job, model_id: str, reason: str) -> Decision:
    return Decision(
        job_id=job.id,
        status="unavailable",
        start=None,
        finish=None,
        predicted_grams=None,
        reason=reason,
        model_id=model_id,
    )


def _canonical_series(series: pd.Series) -> pd.Series:
    if not isinstance(series, pd.Series):
        raise TypeError("Intensity values must be provided as a pandas Series")
    if not isinstance(series.index, pd.DatetimeIndex) or series.index.tz is None:
        raise ValueError("Intensity timestamps must be timezone-aware")

    index = series.index.tz_convert("UTC")
    if index.has_duplicates:
        raise ValueError("Intensity timestamps must be unique")
    if np.any(index.asi8 % SLOT.value):
        raise ValueError("Intensity timestamps must lie on the half-hour grid")
    try:
        values = pd.to_numeric(series, errors="raise").to_numpy(dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("Intensity values must be numeric") from exc
    return pd.Series(values, index=index, name=series.name).sort_index()


def integrated_cost(job: Job, start, series: pd.Series) -> float:
    """Return job emissions in grams using interval-overlap energy in kWh."""
    if not isinstance(job, Job):
        raise TypeError("job must be a validated gridshift.domain.Job")
    start_utc = grid_time(start)
    finish = start_utc + pd.Timedelta(hours=job.duration_hours)
    if start_utc < job.release or finish > job.deadline:
        raise ValueError("Start violates the job release or deadline")

    values = _canonical_series(series)
    slot_starts = start_utc + np.arange(job.slots, dtype=np.int64) * SLOT
    positions = values.index.get_indexer(slot_starts)
    if np.any(positions < 0):
        raise ValueError("Intensity series does not cover every occupied interval")
    intensities = values.to_numpy()[positions]
    if not np.all(np.isfinite(intensities)):
        raise ValueError("Intensity series has missing or non-finite occupied values")
    if np.any(intensities < 0):
        raise ValueError("Carbon intensity cannot be negative")
    return float(np.dot(job.energy_kwh, intensities))


def candidates(
    job: Job,
    path: ForecastPath | None,
    reservations: Iterable[object] = (),
) -> pd.DataFrame:
    """List every half-hour start and its point-forecast cost or failure reason."""
    model_id = getattr(path, "model_id", "unknown")
    if not isinstance(job, Job):
        return pd.DataFrame(
            [
                {
                    "candidate_index": None,
                    "start": None,
                    "finish": None,
                    "waiting_hours": np.nan,
                    "predicted_grams": np.nan,
                    "status": "unavailable",
                    "reason": "Invalid job",
                    "model_id": model_id,
                }
            ],
            columns=_CANDIDATE_COLUMNS,
        )

    windows = _candidate_windows(job)
    if not windows:
        return pd.DataFrame(
            [
                {
                    "candidate_index": None,
                    "start": None,
                    "finish": None,
                    "waiting_hours": np.nan,
                    "predicted_grams": np.nan,
                    "status": "infeasible",
                    "reason": "No half-hour start meets the deadline",
                    "model_id": model_id,
                }
            ],
            columns=_CANDIDATE_COLUMNS,
        )

    try:
        occupied = _normalise_reservations(reservations)
    except (TypeError, ValueError, OverflowError) as exc:
        return _empty_rows(windows, model_id, "unavailable", f"Invalid reservation: {exc}")

    blocked = np.asarray(
        [
            any(start < reserved_finish and finish > reserved_start for reserved_start, reserved_finish in occupied)
            for start, finish in windows
        ],
        dtype=bool,
    )
    rows = [
        {
            "candidate_index": index,
            "start": start,
            "finish": finish,
            "waiting_hours": (start - job.release).total_seconds() / 3600,
            "predicted_grams": np.nan,
            "status": "reservation_conflict" if blocked[index] else "unavailable",
            "reason": "Overlaps a committed reservation" if blocked[index] else "",
            "model_id": model_id,
        }
        for index, (start, finish) in enumerate(windows)
    ]

    open_indices = np.flatnonzero(~blocked)
    if not len(open_indices):
        return pd.DataFrame(rows, columns=_CANDIDATE_COLUMNS)
    if not isinstance(path, ForecastPath):
        for index in open_indices:
            rows[index]["reason"] = "Forecast path is missing or has an invalid type"
        return pd.DataFrame(rows, columns=_CANDIDATE_COLUMNS)
    if path.status not in {"ok", "fallback"}:
        for index in open_indices:
            rows[index]["reason"] = f"Forecast path status is {path.status!r}"
        return pd.DataFrame(rows, columns=_CANDIDATE_COLUMNS)
    if path.origin != job.release:
        for index in open_indices:
            rows[index]["reason"] = "Forecast origin does not match the job release"
        return pd.DataFrame(rows, columns=_CANDIDATE_COLUMNS)

    values = np.maximum(np.asarray(path.mean, dtype=float), 0.0)
    slot_offsets = np.asarray(
        [(windows[index][0].value - path.origin.value) // SLOT.value for index in open_indices],
        dtype=np.int64,
    )
    finish_offsets = slot_offsets + job.slots
    uncovered = finish_offsets > len(values)
    for local_index in np.flatnonzero(uncovered):
        index = open_indices[local_index]
        rows[index]["reason"] = "Forecast path does not cover the full candidate window"

    covered_local = np.flatnonzero(~uncovered)
    if len(covered_local):
        windows_view = np.lib.stride_tricks.sliding_window_view(values, job.slots)
        costs = windows_view[slot_offsets[covered_local]] @ job.energy_kwh
        for local_index, cost in zip(covered_local, costs, strict=True):
            index = open_indices[local_index]
            rows[index]["predicted_grams"] = float(cost)
            rows[index]["status"] = "feasible"
            if path.status == "fallback":
                rows[index]["reason"] = "Using fallback forecast"
            else:
                rows[index]["reason"] = ""
    return pd.DataFrame(rows, columns=_CANDIDATE_COLUMNS)


def recommend(
    job: Job,
    path: ForecastPath | None,
    reservations: Iterable[object] = (),
) -> Decision:
    """Choose the lowest-cost fully covered start without observing future truth."""
    model_id = getattr(path, "model_id", "unknown")
    if not isinstance(job, Job):
        return Decision(
            job_id=str(getattr(job, "id", "")),
            status="infeasible",
            start=None,
            finish=None,
            predicted_grams=None,
            reason="Invalid job",
            model_id=model_id,
        )

    frame = candidates(job, path, reservations)
    if frame.empty:
        return _unavailable_decision(job, model_id, "No candidate rows were produced")
    unavailable = frame.loc[frame["status"] == "unavailable"]
    if not unavailable.empty:
        reason = str(unavailable.iloc[0]["reason"] or "Forecast candidate is unavailable")
        return _unavailable_decision(job, model_id, reason)

    feasible = frame.loc[frame["status"] == "feasible"]
    if feasible.empty:
        reason = (
            "All candidate starts overlap committed reservations"
            if (frame["status"] == "reservation_conflict").all()
            else "No feasible start remains"
        )
        return Decision(
            job_id=job.id,
            status="infeasible",
            start=None,
            finish=None,
            predicted_grams=None,
            reason=reason,
            model_id=model_id,
        )

    chosen = feasible.iloc[earliest_minimum(feasible["predicted_grams"].to_numpy(float))]
    minimum = float(chosen["predicted_grams"])
    reason = "Minimum integrated forecast cost; exact ties favor the earliest start"
    if getattr(path, "status", None) == "fallback":
        reason += "; fallback forecast"
    return Decision(
        job_id=job.id,
        status="scheduled",
        start=chosen["start"],
        finish=chosen["finish"],
        predicted_grams=minimum,
        reason=reason,
        model_id=model_id,
    )


def earliest_minimum(costs):
    """Choose the earliest minimum, treating machine-roundoff differences as ties."""
    values = np.asarray(costs, dtype=float)
    if values.ndim != 1 or not len(values) or not np.isfinite(values).all():
        raise ValueError("Finite candidate costs are required")
    minimum = float(values.min())
    tolerance = 32 * np.finfo(float).eps * float(np.abs(values).max())
    return int(np.flatnonzero(values <= minimum + tolerance)[0])
