import numpy as np
import pandas as pd
import pytest

from gridshift.domain import ForecastPath, Job, SLOT
from gridshift.replay import arrivals, simulate, score_trace

ORIGIN = pd.Timestamp("2023-01-01T00:00Z")


def path(origin):
    return ForecastPath(origin, np.r_[np.full(4, 100), np.full(44, 20)], "fixture", origin - 2 * SLOT)


def test_committed_reservations_never_overlap_and_deadlines_hold():
    jobs = [Job(str(i), ORIGIN, 2, ORIGIN + pd.Timedelta(hours=6)) for i in range(5)]
    result = simulate(jobs, path, "selected")
    scheduled = result.loc[result.status == "scheduled"].sort_values("start")
    assert len(scheduled) == 3
    assert (scheduled.finish <= scheduled.deadline).all()
    assert all(a <= b for a, b in zip(scheduled.finish.iloc[:-1], scheduled.start.iloc[1:]))
    assert (result.status == "infeasible").sum() == 2


def test_unknown_arrivals_cannot_change_prior_reservations():
    first = Job("first", ORIGIN, 2, ORIGIN + pd.Timedelta(hours=8))
    later = Job("later", ORIGIN + pd.Timedelta(hours=1), 4, ORIGIN + pd.Timedelta(hours=7))
    a = simulate([first], path, "selected")
    b = simulate([first, later], path, "selected")
    pd.testing.assert_series_equal(a.iloc[0], b.iloc[0])


def test_missing_future_truth_does_not_remove_offered_jobs_or_decisions():
    jobs = [Job("first", ORIGIN, 2, ORIGIN + pd.Timedelta(hours=6))]
    decisions = simulate(jobs, path, "selected")
    index = pd.date_range(ORIGIN, periods=48, freq=SLOT)
    a = pd.Series(100., index=index)
    b = a.copy()
    b.iloc[10] = np.nan
    score_a = score_trace(jobs, decisions, a, ORIGIN, ORIGIN + pd.Timedelta(days=1))
    score_b = score_trace(jobs, decisions, b, ORIGIN, ORIGIN + pd.Timedelta(days=1))
    assert len(score_a) == len(score_b) == 1
    assert score_a.start.iloc[0] == score_b.start.iloc[0]
    assert score_a.realized_grams.notna().all()
    assert score_b.realized_grams.isna().all()


def test_seeded_arrivals_are_carbon_independent_and_snapped_up():
    config = {"queue": {"warmup_hours": 48, "drain_hours": 24, "durations_hours": [1, 2, 4],
                       "probabilities": [.5, .3, .2]},
              "scheduling": {"power_kw": .4, "pue": 1.2}}
    a = arrivals(ORIGIN, ORIGIN + pd.Timedelta(days=10), .6, 1729, 6, config)
    b = arrivals(ORIGIN, ORIGIN + pd.Timedelta(days=10), .6, 1729, 6, config)
    assert [(j.release, j.duration_hours) for j in a] == [(j.release, j.duration_hours) for j in b]
    assert all(j.release.value % SLOT.value == 0 for j in a)
