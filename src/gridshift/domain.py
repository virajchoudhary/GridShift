"""Validated UTC and energy contracts shared by the study and scheduler."""

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

SLOT = pd.Timedelta(minutes=30)


def utc(value) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        raise ValueError("An explicit UTC offset is required")
    return timestamp.tz_convert("UTC")


def grid_time(value) -> pd.Timestamp:
    timestamp = utc(value)
    if timestamp.value % SLOT.value:
        raise ValueError("Time must lie on the half-hour UTC grid")
    return timestamp


@dataclass(frozen=True)
class Job:
    id: str
    release: pd.Timestamp
    duration_hours: float
    deadline: pd.Timestamp
    power_kw: float = 0.4
    pue: float = 1.2
    profile: tuple[float, ...] | None = None

    def __post_init__(self):
        object.__setattr__(self, "release", grid_time(self.release))
        object.__setattr__(self, "deadline", utc(self.deadline))
        if not np.isfinite(self.duration_hours) or self.duration_hours <= 0:
            raise ValueError("Duration must be finite and positive")
        if self.release + pd.Timedelta(hours=self.duration_hours) > self.deadline:
            raise ValueError("The job cannot finish by its deadline")
        if not np.isfinite(self.power_kw) or self.power_kw <= 0:
            raise ValueError("IT power must be finite and positive")
        if not np.isfinite(self.pue) or self.pue < 1:
            raise ValueError("PUE must be at least one")
        if self.profile is not None:
            if len(self.profile) != self.slots or not np.all(np.isfinite(self.profile)):
                raise ValueError("Energy profile must cover every occupied slot")
            if min(self.profile) < 0:
                raise ValueError("Energy multipliers cannot be negative")

    @property
    def slots(self) -> int:
        return int(np.ceil(self.duration_hours * 2))

    @property
    def energy_kwh(self) -> np.ndarray:
        overlap = np.minimum(0.5, np.maximum(0, self.duration_hours - np.arange(self.slots) * 0.5))
        multiplier = np.ones(self.slots) if self.profile is None else np.asarray(self.profile)
        return overlap * self.power_kw * self.pue * multiplier


@dataclass(frozen=True)
class ForecastPath:
    origin: pd.Timestamp
    mean: np.ndarray
    model_id: str
    training_cutoff: pd.Timestamp
    std: np.ndarray | None = None
    status: Literal["ok", "fallback", "unavailable"] = "ok"

    def __post_init__(self):
        object.__setattr__(self, "origin", grid_time(self.origin))
        object.__setattr__(self, "training_cutoff", utc(self.training_cutoff))
        values = np.array(self.mean, dtype=float, copy=True)
        if values.ndim != 1 or not len(values) or not np.all(np.isfinite(values)):
            raise ValueError("A complete finite forecast path is required")
        values.setflags(write=False)
        object.__setattr__(self, "mean", values)
        if self.training_cutoff > self.origin:
            raise ValueError("Training cutoff exceeds forecast origin")
        if self.std is not None:
            std = np.array(self.std, dtype=float, copy=True)
            if std.shape != values.shape or np.any(std < 0) or not np.all(np.isfinite(std)):
                raise ValueError("Invalid forecast standard deviations")
            std.setflags(write=False)
            object.__setattr__(self, "std", std)


@dataclass(frozen=True)
class Decision:
    job_id: str
    status: Literal["scheduled", "infeasible", "unavailable"]
    start: pd.Timestamp | None
    finish: pd.Timestamp | None
    predicted_grams: float | None
    reason: str
    model_id: str
