# GridShift observed results

Study `d2dee2d358735d7d` evaluates the locked 2025 test after validation-only
selection. All numbers below derive from `artifacts/results.json` and the
corresponding content-addressed test tables. Final software acceptance is
recorded separately in `COMPLETION_CHECKLIST.md`.

## Data

The official NESO API collection contains 70,128 UTC half-hours across
2022-2025. Estimated actual is observed in 69,950 slots. There are 178 missing
targets, including 122 absent intervals and 56 explicit nulls. Overall coverage
is 99.746%. Every 2025 half-hour is observed.

## Forecasting

All nine test competitors have 17,473 issue origins and 24-hour paths.
The common no-fallback intersection contains 16,465 origins. The table reports
the arithmetic mean of endpoint MAEs at leads 0.5, 2, 6, 12, and 24 hours,
in gCO2/kWh.

| Model | Common endpoint MAE | End-to-end endpoint MAE |
| --- | ---: | ---: |
| AR(7,0,0) | 29.123431 | 28.864540 |
| MA(0,0,8), log1p | 39.294032 | 38.757894 |
| ARMA(3,0,2) | 28.673827 | 28.720150 |
| ARIMA(3,1,3) | 26.743624 | 26.983413 |
| SARIMA(1,0,1)x(1,0,0,48) | 24.452878 | 24.330379 |
| Persistence | 29.122004 | 29.059601 |
| Daily naive | 40.765490 | 40.589332 |
| Weekly naive | 56.756720 | 56.128141 |
| Calendar mean | 47.033039 | 46.470379 |

The frozen SARIMA forecast improves the common mean endpoint MAE by 16.033%
relative to validation-selected persistence. The secondary descriptive
seven-day paired bootstrap interval is 13.373%-18.702%.

MA, ARMA, and ARIMA each use a documented daily-naive fallback for 336 origins.
SARIMA has no fallback origins, but its 24-hour intervals cover only 70.6% and
87.0% against nominal 80% and 95%. Do not treat those intervals as calibrated
joint job-cost guarantees.

Sources: `test/forecast_common_metrics.csv`, `test/forecast_metrics.csv`,
`test/forecast_loss_bootstrap.csv`, and `test/forecasts/`, under the study run.

## Isolated jobs

The default experiment has 2,913 independent two-hour jobs, each with ten
hours of slack. Declared allocated IT power is 0.4 kW and PUE is 1.2, giving
0.96 facility kWh per case. These overlapping cases are correlated
counterfactuals, not one runnable combined trace.

Earliest execution totals 361,306.56 modeled grams. The frozen calendar-mean
policy totals 316,453.92 modeled grams. Its difference is 44,852.64 g, or
12.414012%, with seven-day paired 95% interval 10.951237%-13.828262%.
There are zero deadline misses and identical completed work.

The validation-selected scheduling model remains calendar mean. Test SARIMA
has a descriptive 14.812640% reduction, but that observation does not promote
it after the test. Calendar mean's result establishes simple timing value,
not added scheduling value from classical deployment.

Sources: `test/single_job/primary_summary.csv`, `primary_bootstrap.csv`,
`primary_decisions.parquet`, and `artifacts/tests/locked_primary_review.md`.

## Shared GPU

Eighteen frozen traces cover three loads, three seeds, and two slack settings.
All 136,675 accepted reservations are feasible and all policies have zero
deadline misses. Every offered job, including rejected work, remains recorded.

Across the separately simulated scenarios, earliest and persistence complete
46,127 of 48,078 offered cases and reject 1,951, or 4.058%. Calendar mean
completes 43,522 and rejects 4,556, or 9.476%. Pooled median waits are one hour
and six hours, respectively.

The 42,844-case common completion intersection shows a descriptive 4.816%
lower modeled cost for calendar mean. The policy also rejects 2,605 more cases.
This is an emissions-service tradeoff, not fixed-work savings.

Sources: `test/queue/queue_summary.csv`, `queue_bootstrap.csv`, all trace
Parquet files, and `artifacts/tests/locked_queue_review.md`.

## Interpretation

The study supports forecast skill for the frozen SARIMA comparison and
modeled isolated-job timing benefit under the declared assumptions. It does
not establish classical scheduling added value, a queue-wide fixed-work
reduction, measured GPU energy, verified net savings, or actual avoided grid
emissions.

Retrospective estimated actuals have no verified historical forecast vintages.
Publication delay is assumed. Real workload duration, energy, idle power,
forecasting overhead, marginal emissions, and embodied emissions are not
measured by this project. Local trusted model inference is verified; a
container build, public hosting, and GPU execution are not.
