# GridShift: carbon-aware GPU workload scheduling

## Abstract

This report evaluates a frozen classical time-series forecasting and workload-scheduling study. The study identifier is `d2dee2d358735d7d`. The validation-selected forecast champion is `SARIMA(1,0,1)x(1,0,0,48)`. The validation-selected scheduling model is `calendar_mean`. Modeled isolated-job benefit under declared assumptions. The certified seven-day paired block estimate is 12.414% (95% interval 10.951 to 13.828%) across 2913 scheduled primary-policy jobs; the bootstrap paired 2913 jobs. This estimates modeled operational CO2 under the declared job, energy, and deadline assumptions.

The target is NESO estimated GB carbon intensity in gCO2/kWh. Scheduling emissions are modeled from declared job energy and the estimated-actual series. They are not measured GPU energy or causal grid-emissions reductions.

## Research question and scope

Under declared duration, energy, deadline, and capacity assumptions, do forecasts of NESO estimated GB carbon intensity reduce modeled operational CO2 for completed GPU workloads compared with earliest-feasible execution and simple forecast baselines?

The study compares half-hourly forecasts with persistence, daily and weekly seasonal-naive, and calendar-mean controls. It uses chronological validation and a locked test period. The isolated-job experiment estimates temporal placement value. The one-GPU queue simulation examines how a simple reservation policy behaves under synthetic arrivals.

The carbon oracle uses realized future intensity and is an unattainable opportunity bound. It is never presented as a deployable forecast.

## Data and provenance

- Study ID: `d2dee2d358735d7d`
- Data source: https://api.carbonintensity.org.uk
- Declared interval: `2022-01-01T00:00:00Z` to `2026-01-01T00:00:00Z`
- Normalized data hash: `f57548d5bc197f884b5b35bb84faaaadcb38b7b46dc3e8c925a150b8ea5a5a1e`
- Target: NESO estimated actual carbon intensity. Provider forecasts remain separate and are not scored as as-issued historical forecasts without issue-time provenance. [S1-S5]

## Data-quality results

The raw reconstruction verified 209 source chunks and 70128 UTC half-hour slots. It identifies 122 intervals without a raw API record and 56 records with an explicit null actual. These categories come from the raw interval audit; diagnostics.input_absent_intervals describes the development-series input and cannot establish raw API absence.

| measure | value |
| --- | --- |
| slots | 70128 |
| observed | 69950 |
| missing | 178 |
| overall\_coverage | 0.99746 |
| minimum\_monthly\_coverage | 0.93884 |
| minimum\_test\_monthly\_coverage | 1 |
| unique\_utc\_intervals | true |
| regular\_grid | true |
| data\_gate\_pass | true |
| availability\_is\_assumed | true |

Monthly coverage rows are read from the data-quality artifact when present.

| interval\_start\_utc | observed\_slots | expected\_slots | coverage |
| --- | --- | --- | --- |
| 2022-01 | 1488 | 1488 | 1 |
| 2022-02 | 1344 | 1344 | 1 |
| 2022-03 | 1478 | 1488 | 0.99328 |
| 2022-04 | 1440 | 1440 | 1 |
| 2022-05 | 1488 | 1488 | 1 |
| 2022-06 | 1440 | 1440 | 1 |
| 2022-07 | 1488 | 1488 | 1 |
| 2022-08 | 1488 | 1488 | 1 |
| 2022-09 | 1440 | 1440 | 1 |
| 2022-10 | 1488 | 1488 | 1 |
| 2022-11 | 1440 | 1440 | 1 |
| 2022-12 | 1447 | 1488 | 0.97245 |
| 2023-01 | 1483 | 1488 | 0.99664 |
| 2023-02 | 1344 | 1344 | 1 |
| 2023-03 | 1488 | 1488 | 1 |
| 2023-04 | 1440 | 1440 | 1 |
| 2023-05 | 1488 | 1488 | 1 |
| 2023-06 | 1440 | 1440 | 1 |
| 2023-07 | 1488 | 1488 | 1 |
| 2023-08 | 1488 | 1488 | 1 |
| 2023-09 | 1440 | 1440 | 1 |
| 2023-10 | 1397 | 1488 | 0.93884 |
| 2023-11 | 1440 | 1440 | 1 |
| 2023-12 | 1488 | 1488 | 1 |
| 2024-01 | 1488 | 1488 | 1 |
| 2024-02 | 1392 | 1392 | 1 |
| 2024-03 | 1488 | 1488 | 1 |
| 2024-04 | 1440 | 1440 | 1 |
| 2024-05 | 1488 | 1488 | 1 |
| 2024-06 | 1409 | 1440 | 0.97847 |
| 2024-07 | 1488 | 1488 | 1 |
| 2024-08 | 1488 | 1488 | 1 |
| 2024-09 | 1440 | 1440 | 1 |
| 2024-10 | 1488 | 1488 | 1 |
| 2024-11 | 1440 | 1440 | 1 |
| 2024-12 | 1488 | 1488 | 1 |
| 2025-01 | 1488 | 1488 | 1 |
| 2025-02 | 1344 | 1344 | 1 |
| 2025-03 | 1488 | 1488 | 1 |
| 2025-04 | 1440 | 1440 | 1 |
| 2025-05 | 1488 | 1488 | 1 |
| 2025-06 | 1440 | 1440 | 1 |
| 2025-07 | 1488 | 1488 | 1 |
| 2025-08 | 1488 | 1488 | 1 |
| 2025-09 | 1440 | 1440 | 1 |
| 2025-10 | 1488 | 1488 | 1 |
| 2025-11 | 1440 | 1440 | 1 |
| 2025-12 | 1488 | 1488 | 1 |

Coverage is reported from the stored audit. Missing or excluded intervals remain visible. The observed target is not replaced with a provider forecast. [S2, S4, S6]

## Development diagnostics

Diagnostics used data through `2024-01-01T00:00:00+00:00`. They support model design only. They do not establish test-year forecast skill.

![Observed development-period intensity](../artifacts/diagnostics/figures/series.png)

![Representative development week](../artifacts/diagnostics/figures/representative_week.png)

![Intensity by local date and half-hour](../artifacts/diagnostics/figures/daily_slot_heatmap.png)

![Robust STL decomposition](../artifacts/diagnostics/figures/stl48.png)

Diagnostic table files remain at `../artifacts/diagnostics/`. The exporter includes every listed table and figure that exists. Missing listed files appear in the export manifest rather than being replaced with invented values.

## Forecast methods

The study uses AR, MA, ARMA, ARIMA, and daily-seasonal SARIMA structures with persistence, seasonal-naive, and calendar-mean baselines. It compares information criteria only within compatible groups, then selects across groups by validation loss. [S9-S13]

### Order-search record

AIC = -2 log L + 2k. BIC = -2 log L + k log(n_effective). AICc adds 2k(k+1)/(n_effective-k-1). Estimated variance and deterministic parameters count in k. The first-anchor shortlist below spans separate likelihood groups; cross-transformation IC comparisons are invalid.

| family | transform | order | seasonal\_order | aic | bic | aicc | converged\_anchors |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AR | identity | \[7, 0, 0\] | \[0, 0, 0, 0\] | 54004 | 54067 | 54004 | 12 |
| MA | identity | \[0, 0, 8\] | \[0, 0, 0, 0\] | 58235 | 58305 | 58235 | 12 |
| ARMA | identity | \[3, 0, 2\] | \[0, 0, 0, 0\] | 54031 | 54080 | 54031 | 12 |
| ARIMA | identity | \[3, 1, 3\] | \[0, 0, 0, 0\] | 53979 | 54029 | 53979 | 12 |
| SARIMA | identity | \[1, 0, 1\] | \[1, 0, 0, 48\] | 54616 | 54651 | 54616 | 12 |
| AR | log1p | \[8, 0, 0\] | \[0, 0, 0, 0\] | -26140 | -26069 | -26140 | 12 |
| MA | log1p | \[0, 0, 8\] | \[0, 0, 0, 0\] | -22222 | -22152 | -22222 | 12 |
| ARMA | log1p | \[3, 0, 1\] | \[0, 0, 0, 0\] | -26116 | -26074 | -26116 | 12 |
| ARIMA | log1p | \[2, 1, 1\] | \[0, 0, 0, 0\] | -26012 | -25984 | -26012 | 12 |
| SARIMA | log1p | \[1, 0, 1\] | \[1, 0, 0, 48\] | -25724 | -25689 | -25724 | 10 |

| name | family | order | seasonal\_order | transform | anchor | training\_start | training\_cutoff | observed\_n | filled\_n | fit\_seconds | fit\_status | converged | error | warnings | log\_likelihood | parameter\_count | loglikelihood\_burn | effective\_n | aic | bic | aicc | aicc\_rank | bic\_rank | d\_value | D\_value | period | median\_aicc\_rank | median\_bic\_rank | converged\_anchors | selected |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AR(1,0,0) | AR | \[1, 0, 0\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 0.95357 | converged | True | NA | NA | -28748 | 3 | 96 | 8452 | 57503 | 57524 | 57503 | 8 | 8 | 0 | 0 | 0 | 8 | 8 | 12 | False |
| AR(2,0,0) | AR | \[2, 0, 0\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 2.0195 | converged | True | NA | NA | -27134 | 4 | 96 | 8452 | 54277 | 54305 | 54277 | 7 | 7 | 0 | 0 | 0 | 7 | 7 | 12 | False |
| AR(3,0,0) | AR | \[3, 0, 0\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 1.9612 | converged | True | NA | NA | -27010 | 5 | 96 | 8452 | 54029 | 54064 | 54029 | 3 | 1 | 0 | 0 | 0 | 5 | 2.5 | 12 | False |
| AR(4,0,0) | AR | \[4, 0, 0\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 2.5419 | converged | True | NA | NA | -27009 | 6 | 96 | 8452 | 54030 | 54073 | 54030 | 4 | 4 | 0 | 0 | 0 | 5 | 3.5 | 12 | False |
| AR(5,0,0) | AR | \[5, 0, 0\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 5.0443 | converged | True | NA | NA | -27008 | 7 | 96 | 8452 | 54030 | 54080 | 54030 | 5 | 5 | 0 | 0 | 0 | 3.5 | 5 | 12 | False |
| AR(6,0,0) | AR | \[6, 0, 0\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 6.778 | converged | True | NA | NA | -27008 | 8 | 96 | 8452 | 54032 | 54088 | 54032 | 6 | 6 | 0 | 0 | 0 | 4 | 6 | 12 | False |
| AR(7,0,0) | AR | \[7, 0, 0\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 5.7187 | converged | True | NA | NA | -26993 | 9 | 96 | 8452 | 54004 | 54067 | 54004 | 2 | 2 | 0 | 0 | 0 | 1.5 | 1 | 12 | True |
| AR(8,0,0) | AR | \[8, 0, 0\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 6.7869 | converged | True | NA | NA | -26991 | 10 | 96 | 8452 | 54002 | 54072 | 54002 | 1 | 3 | 0 | 0 | 0 | 1.5 | 3.5 | 12 | False |
| MA(0,0,1) | MA | \[0, 0, 1\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 1.2733 | converged | True | NA | NA | -41879 | 3 | 96 | 8452 | 83764 | 83785 | 83764 | 6 | 6 | 0 | 0 | 0 | 8 | 8 | 12 | False |
| MA(0,0,2) | MA | \[0, 0, 2\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 3.4315 | converged | True | NA | NA | -37791 | 4 | 96 | 8452 | 75591 | 75619 | 75591 | 5 | 5 | 0 | 0 | 0 | 7 | 7 | 12 | False |
| MA(0,0,3) | MA | \[0, 0, 3\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 7.6752 | converged | True | NA | Non-invertible starting MA parameters found. Using zeros as starting parameters. | -34712 | 5 | 96 | 8452 | 69434 | 69469 | 69434 | 4 | 4 | 0 | 0 | 0 | 6 | 6 | 12 | False |
| MA(0,0,4) | MA | \[0, 0, 4\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 6.8414 | converged | True | NA | Non-invertible starting MA parameters found. Using zeros as starting parameters. | -32793 | 6 | 96 | 8452 | 65599 | 65641 | 65599 | 3 | 3 | 0 | 0 | 0 | 5 | 5 | 12 | False |
| MA(0,0,5) | MA | \[0, 0, 5\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 4.9157 | converged | True | NA | Non-invertible starting MA parameters found. Using zeros as starting parameters. | -41908 | 7 | 96 | 8452 | 83830 | 83879 | 83830 | 7 | 7 | 0 | 0 | 0 | 4 | 4 | 12 | False |
| MA(0,0,6) | MA | \[0, 0, 6\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 14.63 | converged | True | NA | Non-invertible starting MA parameters found. Using zeros as starting parameters. | -30348 | 8 | 96 | 8452 | 60713 | 60769 | 60713 | 2 | 2 | 0 | 0 | 0 | 3 | 3 | 12 | False |
| MA(0,0,7) | MA | \[0, 0, 7\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 6.8026 | converged | True | NA | Non-invertible starting MA parameters found. Using zeros as starting parameters. | -6.8428e+09 | 9 | 96 | 8452 | 1.3686e+10 | 1.3686e+10 | 1.3686e+10 | 8 | 8 | 0 | 0 | 0 | 2 | 2 | 12 | False |
| MA(0,0,8) | MA | \[0, 0, 8\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 19.987 | converged | True | NA | Non-invertible starting MA parameters found. Using zeros as starting parameters. | -29107 | 10 | 96 | 8452 | 58235 | 58305 | 58235 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 12 | True |
| ARMA(1,0,1) | ARMA | \[1, 0, 1\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 2.5961 | converged | True | NA | NA | -27720 | 4 | 96 | 8452 | 55449 | 55477 | 55449 | 9 | 9 | 0 | 0 | 0 | 9 | 9 | 12 | False |
| ARMA(1,0,2) | ARMA | \[1, 0, 2\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 3.0352 | converged | True | NA | NA | -27265 | 5 | 96 | 8452 | 54540 | 54576 | 54540 | 8 | 8 | 0 | 0 | 0 | 8 | 8 | 12 | False |
| ARMA(1,0,3) | ARMA | \[1, 0, 3\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 3.3491 | converged | True | NA | NA | -27121 | 6 | 96 | 8452 | 54254 | 54297 | 54254 | 7 | 7 | 0 | 0 | 0 | 7 | 7 | 12 | False |
| ARMA(2,0,1) | ARMA | \[2, 0, 1\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 1.8334 | converged | True | NA | NA | -27024 | 5 | 96 | 8452 | 54057 | 54092 | 54057 | 6 | 6 | 0 | 0 | 0 | 6 | 6 | 12 | False |
| ARMA(2,0,2) | ARMA | \[2, 0, 2\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 3.2015 | converged | True | NA | NA | -27009 | 6 | 96 | 8452 | 54029 | 54072 | 54030 | 1 | 1 | 0 | 0 | 0 | 3 | 2 | 12 | False |
| ARMA(2,0,3) | ARMA | \[2, 0, 3\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 3.7094 | converged | True | NA | NA | -27009 | 7 | 96 | 8452 | 54031 | 54081 | 54031 | 4 | 4 | 0 | 0 | 0 | 3.5 | 5 | 12 | False |
| ARMA(3,0,1) | ARMA | \[3, 0, 1\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 2.9493 | converged | True | NA | NA | -27009 | 6 | 96 | 8452 | 54030 | 54073 | 54030 | 2 | 2 | 0 | 0 | 0 | 4.5 | 3 | 12 | False |
| ARMA(3,0,2) | ARMA | \[3, 0, 2\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 4.0469 | converged | True | NA | NA | -27009 | 7 | 96 | 8452 | 54031 | 54080 | 54031 | 3 | 3 | 0 | 0 | 0 | 2.5 | 2.5 | 12 | True |
| ARMA(3,0,3) | ARMA | \[3, 0, 3\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 4.8864 | converged | True | NA | NA | -27009 | 8 | 96 | 8452 | 54033 | 54089 | 54033 | 5 | 5 | 0 | 0 | 0 | NA | NA | 9 | False |
| ARIMA(0,1,0) | ARIMA | \[0, 1, 0\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 0.15003 | converged | True | NA | NA | -28761 | 1 | 96 | 8452 | 57524 | 57531 | 57524 | 16 | 16 | 1 | 0 | 0 | 16 | 16 | 12 | False |
| ARIMA(0,1,1) | ARIMA | \[0, 1, 1\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 0.56938 | converged | True | NA | NA | -27740 | 2 | 96 | 8452 | 55484 | 55498 | 55484 | 15 | 15 | 1 | 0 | 0 | 15 | 15 | 12 | False |
| ARIMA(0,1,2) | ARIMA | \[0, 1, 2\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 0.83879 | converged | True | NA | NA | -27293 | 3 | 96 | 8452 | 54592 | 54613 | 54592 | 14 | 14 | 1 | 0 | 0 | 14 | 14 | 12 | False |
| ARIMA(0,1,3) | ARIMA | \[0, 1, 3\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 1.2299 | converged | True | NA | NA | -27156 | 4 | 96 | 8452 | 54320 | 54348 | 54320 | 12 | 12 | 1 | 0 | 0 | 12 | 12 | 12 | False |
| ARIMA(1,1,0) | ARIMA | \[1, 1, 0\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 0.35892 | converged | True | NA | NA | -27180 | 2 | 96 | 8452 | 54364 | 54378 | 54364 | 13 | 13 | 1 | 0 | 0 | 12.5 | 12 | 12 | False |
| ARIMA(1,1,1) | ARIMA | \[1, 1, 1\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 0.49267 | converged | True | NA | NA | -27089 | 3 | 96 | 8452 | 54185 | 54206 | 54185 | 11 | 11 | 1 | 0 | 0 | 11 | 11 | 12 | False |
| ARIMA(1,1,2) | ARIMA | \[1, 1, 2\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 0.56949 | converged | True | NA | NA | -27068 | 4 | 96 | 8452 | 54145 | 54173 | 54145 | 6 | 6 | 1 | 0 | 0 | 6 | 6 | 12 | False |
| ARIMA(1,1,3) | ARIMA | \[1, 1, 3\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 1.1861 | converged | True | NA | NA | -27068 | 5 | 96 | 8452 | 54147 | 54182 | 54147 | 7 | 10 | 1 | 0 | 0 | 6 | 7 | 12 | False |
| ARIMA(2,1,0) | ARIMA | \[2, 1, 0\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 0.34757 | converged | True | NA | NA | -27073 | 3 | 96 | 8452 | 54152 | 54173 | 54152 | 10 | 7 | 1 | 0 | 0 | 10 | 7.5 | 12 | False |
| ARIMA(2,1,1) | ARIMA | \[2, 1, 1\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 0.57289 | converged | True | NA | NA | -27071 | 4 | 96 | 8452 | 54151 | 54179 | 54151 | 9 | 9 | 1 | 0 | 0 | 9 | 9 | 12 | False |
| ARIMA(2,1,2) | ARIMA | \[2, 1, 2\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 2.6829 | converged | True | NA | NA | -26998 | 5 | 96 | 8452 | 54006 | 54041 | 54006 | 4 | 2 | 1 | 0 | 0 | 4 | 2.5 | 12 | False |
| ARIMA(2,1,3) | ARIMA | \[2, 1, 3\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 3.4793 | converged | True | NA | NA | -26996 | 6 | 96 | 8452 | 54005 | 54047 | 54005 | 3 | 5 | 1 | 0 | 0 | 3 | 3 | 11 | False |
| ARIMA(3,1,0) | ARIMA | \[3, 1, 0\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 0.61383 | converged | True | NA | NA | -27071 | 4 | 96 | 8452 | 54149 | 54177 | 54149 | 8 | 8 | 1 | 0 | 0 | 8 | 8 | 12 | False |
| ARIMA(3,1,1) | ARIMA | \[3, 1, 1\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 4.0606 | converged | True | NA | NA | -26999 | 5 | 96 | 8452 | 54007 | 54042 | 54007 | 5 | 3 | 1 | 0 | 0 | 4 | 3.5 | 12 | False |
| ARIMA(3,1,2) | ARIMA | \[3, 1, 2\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 4.3363 | converged | True | NA | NA | -26996 | 6 | 96 | 8452 | 54003 | 54045 | 54003 | 2 | 4 | 1 | 0 | 0 | 2 | 3.5 | 10 | False |
| ARIMA(3,1,3) | ARIMA | \[3, 1, 3\] | \[0, 0, 0, 0\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 3.8436 | converged | True | NA | NA | -26983 | 7 | 96 | 8452 | 53979 | 54029 | 53979 | 1 | 1 | 1 | 0 | 0 | 2 | 3 | 12 | True |
| SARIMA(1,0,0)x(1,0,0,48) | SARIMA | \[1, 0, 0\] | \[1, 0, 0, 48\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 48.502 | converged | True | NA | NA | -28067 | 4 | 96 | 8452 | 56142 | 56170 | 56142 | 2 | 2 | 0 | 0 | 48 | 2 | 2 | 12 | False |
| SARIMA(0,0,1)x(0,0,1,48) | SARIMA | \[0, 0, 1\] | \[0, 0, 1, 48\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 46.505 | converged | True | NA | Non-invertible starting seasonal moving average Using zeros as starting parameters. | -40639 | 4 | 96 | 8452 | 81285 | 81313 | 81285 | 4 | 4 | 0 | 0 | 48 | 4 | 4 | 12 | False |
| SARIMA(1,0,1)x(1,0,0,48) | SARIMA | \[1, 0, 1\] | \[1, 0, 0, 48\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 84.187 | converged | True | NA | NA | -27303 | 5 | 96 | 8452 | 54616 | 54651 | 54616 | 1 | 1 | 0 | 0 | 48 | 1 | 1 | 12 | True |
| SARIMA(1,0,0)x(0,0,1,48) | SARIMA | \[1, 0, 0\] | \[0, 0, 1, 48\] | identity | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 37.181 | converged | True | NA | Non-invertible starting seasonal moving average Using zeros as starting parameters. | -28280 | 4 | 96 | 8452 | 56568 | 56597 | 56568 | 3 | 3 | 0 | 0 | 48 | 3 | 3 | 12 | False |
| AR(1,0,0)\[log1p\] | AR | \[1, 0, 0\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 1.6052 | converged | True | NA | NA | 11811 | 3 | 96 | 8452 | -23616 | -23595 | -23616 | 8 | 8 | 0 | 0 | 0 | 8 | 8 | 12 | False |
| AR(2,0,0)\[log1p\] | AR | \[2, 0, 0\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 1.5859 | converged | True | NA | NA | 12946 | 4 | 96 | 8452 | -25884 | -25856 | -25884 | 7 | 7 | 0 | 0 | 0 | 7 | 7 | 12 | False |
| AR(3,0,0)\[log1p\] | AR | \[3, 0, 0\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 3.5073 | converged | True | NA | NA | 13064 | 5 | 96 | 8452 | -26118 | -26083 | -26118 | 3 | 1 | 0 | 0 | 0 | 6 | 1 | 12 | False |
| AR(4,0,0)\[log1p\] | AR | \[4, 0, 0\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 6.0763 | converged | True | NA | NA | 13065 | 6 | 96 | 8452 | -26118 | -26076 | -26118 | 4 | 2 | 0 | 0 | 0 | 4 | 2 | 12 | False |
| AR(5,0,0)\[log1p\] | AR | \[5, 0, 0\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 4.2969 | converged | True | NA | NA | 13066 | 7 | 96 | 8452 | -26118 | -26068 | -26118 | 5 | 5 | 0 | 0 | 0 | 4 | 4 | 12 | False |
| AR(6,0,0)\[log1p\] | AR | \[6, 0, 0\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 4.5972 | converged | True | NA | NA | 13066 | 8 | 96 | 8452 | -26116 | -26059 | -26116 | 6 | 6 | 0 | 0 | 0 | 5 | 6 | 12 | False |
| AR(7,0,0)\[log1p\] | AR | \[7, 0, 0\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 8.8456 | converged | True | NA | NA | 13077 | 9 | 96 | 8452 | -26136 | -26073 | -26136 | 2 | 3 | 0 | 0 | 0 | 2 | 3 | 12 | False |
| AR(8,0,0)\[log1p\] | AR | \[8, 0, 0\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 13.482 | converged | True | NA | NA | 13080 | 10 | 96 | 8452 | -26140 | -26069 | -26140 | 1 | 4 | 0 | 0 | 0 | 1 | 5 | 12 | True |
| MA(0,0,1)\[log1p\] | MA | \[0, 0, 1\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 1.088 | converged | True | NA | NA | -881.19 | 3 | 96 | 8452 | 1768.4 | 1789.5 | 1768.4 | 8 | 8 | 0 | 0 | 0 | 8 | 8 | 12 | False |
| MA(0,0,2)\[log1p\] | MA | \[0, 0, 2\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 1.7536 | converged | True | NA | NA | 3087.6 | 4 | 96 | 8452 | -6167.2 | -6139 | -6167.2 | 7 | 7 | 0 | 0 | 0 | 7 | 7 | 12 | False |
| MA(0,0,3)\[log1p\] | MA | \[0, 0, 3\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 2.7534 | converged | True | NA | Non-invertible starting MA parameters found. Using zeros as starting parameters. | 5970.5 | 5 | 96 | 8452 | -11931 | -11896 | -11931 | 6 | 6 | 0 | 0 | 0 | 6 | 6 | 12 | False |
| MA(0,0,4)\[log1p\] | MA | \[0, 0, 4\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 4.1808 | converged | True | NA | Non-invertible starting MA parameters found. Using zeros as starting parameters. | 7777.1 | 6 | 96 | 8452 | -15542 | -15500 | -15542 | 5 | 5 | 0 | 0 | 0 | 5 | 5 | 12 | False |
| MA(0,0,5)\[log1p\] | MA | \[0, 0, 5\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 4.4799 | converged | True | NA | Non-invertible starting MA parameters found. Using zeros as starting parameters. | 9143.5 | 7 | 96 | 8452 | -18273 | -18224 | -18273 | 4 | 4 | 0 | 0 | 0 | 4 | 4 | 12 | False |
| MA(0,0,6)\[log1p\] | MA | \[0, 0, 6\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 7.0844 | converged | True | NA | Non-invertible starting MA parameters found. Using zeros as starting parameters. | 9974.1 | 8 | 96 | 8452 | -19932 | -19876 | -19932 | 3 | 3 | 0 | 0 | 0 | 3 | 3 | 12 | False |
| MA(0,0,7)\[log1p\] | MA | \[0, 0, 7\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 11.513 | converged | True | NA | Non-invertible starting MA parameters found. Using zeros as starting parameters. | 10691 | 9 | 96 | 8452 | -21364 | -21301 | -21364 | 2 | 2 | 0 | 0 | 0 | 2 | 2 | 12 | False |
| MA(0,0,8)\[log1p\] | MA | \[0, 0, 8\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 7.9767 | converged | True | NA | Non-invertible starting MA parameters found. Using zeros as starting parameters. | 11121 | 10 | 96 | 8452 | -22222 | -22152 | -22222 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 12 | True |
| ARMA(1,0,1)\[log1p\] | ARMA | \[1, 0, 1\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 3.6624 | converged | True | NA | NA | 12563 | 4 | 96 | 8452 | -25117 | -25089 | -25117 | 9 | 9 | 0 | 0 | 0 | 8 | 8 | 12 | False |
| ARMA(1,0,2)\[log1p\] | ARMA | \[1, 0, 2\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 2.7313 | converged | True | NA | NA | 12920 | 5 | 96 | 8452 | -25829 | -25794 | -25829 | 8 | 8 | 0 | 0 | 0 | 7 | 7 | 12 | False |
| ARMA(1,0,3)\[log1p\] | ARMA | \[1, 0, 3\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 10.649 | converged | True | NA | NA | 12993 | 6 | 96 | 8452 | -25975 | -25932 | -25975 | 7 | 7 | 0 | 0 | 0 | 6 | 6 | 12 | False |
| ARMA(2,0,1)\[log1p\] | ARMA | \[2, 0, 1\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 12.127 | converged | True | NA | NA | 13050 | 5 | 96 | 8452 | -26089 | -26054 | -26089 | 6 | 6 | 0 | 0 | 0 | 5 | 4.5 | 12 | False |
| ARMA(2,0,2)\[log1p\] | ARMA | \[2, 0, 2\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 8.0112 | converged | True | NA | NA | 13062 | 6 | 96 | 8452 | -26111 | -26069 | -26111 | 4 | 3 | 0 | 0 | 0 | 2.5 | 3 | 12 | False |
| ARMA(2,0,3)\[log1p\] | ARMA | \[2, 0, 3\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 6.2688 | converged | True | NA | NA | 13062 | 7 | 96 | 8452 | -26110 | -26061 | -26110 | 5 | 5 | 0 | 0 | 0 | NA | NA | 9 | False |
| ARMA(3,0,1)\[log1p\] | ARMA | \[3, 0, 1\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 3.76 | converged | True | NA | NA | 13064 | 6 | 96 | 8452 | -26116 | -26074 | -26116 | 3 | 2 | 0 | 0 | 0 | 1.5 | 1.5 | 12 | True |
| ARMA(3,0,2)\[log1p\] | ARMA | \[3, 0, 2\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 7.4095 | converged | True | NA | NA | 13065 | 7 | 96 | 8452 | -26117 | -26068 | -26117 | 2 | 4 | 0 | 0 | 0 | 2.5 | 3.5 | 12 | False |
| ARMA(3,0,3)\[log1p\] | ARMA | \[3, 0, 3\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 13.332 | converged | True | NA | Non-stationary starting autoregressive parameters found. Using zeros as starting parameters. | 13080 | 8 | 96 | 8452 | -26145 | -26088 | -26145 | 1 | 1 | 0 | 0 | 0 | NA | NA | 1 | False |
| ARIMA(0,1,0)\[log1p\] | ARIMA | \[0, 1, 0\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 0.68225 | unconverged | False | NA | Maximum Likelihood optimization failed to converge. Check mle\_retvals | 11797 | 1 | 96 | 8452 | -23592 | -23585 | -23592 | NA | NA | 1 | 0 | 0 | 15 | 15 | 10 | False |
| ARIMA(0,1,1)\[log1p\] | ARIMA | \[0, 1, 1\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 1.1815 | unconverged | False | NA | Maximum Likelihood optimization failed to converge. Check mle\_retvals | 12541 | 2 | 96 | 8452 | -25078 | -25064 | -25078 | NA | NA | 1 | 0 | 0 | 14 | 14 | 11 | False |
| ARIMA(0,1,2)\[log1p\] | ARIMA | \[0, 1, 2\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 0.94325 | converged | True | NA | NA | 12895 | 3 | 96 | 8452 | -25785 | -25764 | -25785 | 12 | 12 | 1 | 0 | 0 | 13 | 13 | 12 | False |
| ARIMA(0,1,3)\[log1p\] | ARIMA | \[0, 1, 3\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 2.2957 | converged | True | NA | NA | 12957 | 4 | 96 | 8452 | -25905 | -25877 | -25905 | 10 | 10 | 1 | 0 | 0 | 11 | 11 | 12 | False |
| ARIMA(1,1,0)\[log1p\] | ARIMA | \[1, 1, 0\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 0.71009 | converged | True | NA | NA | 12905 | 2 | 96 | 8452 | -25805 | -25791 | -25805 | 11 | 11 | 1 | 0 | 0 | 12 | 12 | 12 | False |
| ARIMA(1,1,1)\[log1p\] | ARIMA | \[1, 1, 1\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 0.75556 | converged | True | NA | NA | 12990 | 3 | 96 | 8452 | -25974 | -25953 | -25974 | 9 | 9 | 1 | 0 | 0 | 10 | 9 | 11 | False |
| ARIMA(1,1,2)\[log1p\] | ARIMA | \[1, 1, 2\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 1.5038 | converged | True | NA | NA | 13007 | 4 | 96 | 8452 | -26007 | -25979 | -26007 | 8 | 4 | 1 | 0 | 0 | 7 | 4.5 | 12 | False |
| ARIMA(1,1,3)\[log1p\] | ARIMA | \[1, 1, 3\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 1.7963 | converged | True | NA | NA | 13009 | 5 | 96 | 8452 | -26008 | -25973 | -26008 | 6 | 7 | 1 | 0 | 0 | 6 | 7 | 12 | False |
| ARIMA(2,1,0)\[log1p\] | ARIMA | \[2, 1, 0\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 0.38581 | converged | True | NA | NA | 13007 | 3 | 96 | 8452 | -26008 | -25986 | -26008 | 7 | 1 | 1 | 0 | 0 | 6.5 | 2.5 | 12 | False |
| ARIMA(2,1,1)\[log1p\] | ARIMA | \[2, 1, 1\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 0.74872 | converged | True | NA | NA | 13010 | 4 | 96 | 8452 | -26012 | -25984 | -26012 | 2 | 3 | 1 | 0 | 0 | 3.5 | 3.5 | 12 | True |
| ARIMA(2,1,2)\[log1p\] | ARIMA | \[2, 1, 2\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 0.88508 | converged | True | NA | NA | 13010 | 5 | 96 | 8452 | -26010 | -25975 | -26010 | 3 | 5 | 1 | 0 | 0 | 3.5 | 5 | 12 | False |
| ARIMA(2,1,3)\[log1p\] | ARIMA | \[2, 1, 3\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 7.9249 | unconverged | False | NA | Maximum Likelihood optimization failed to converge. Check mle\_retvals | 13071 | 6 | 96 | 8452 | -26130 | -26088 | -26130 | NA | NA | 1 | 0 | 0 | NA | NA | 7 | False |
| ARIMA(3,1,0)\[log1p\] | ARIMA | \[3, 1, 0\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 0.89543 | converged | True | NA | NA | 13010 | 4 | 96 | 8452 | -26012 | -25984 | -26012 | 1 | 2 | 1 | 0 | 0 | 3.5 | 4 | 12 | False |
| ARIMA(3,1,1)\[log1p\] | ARIMA | \[3, 1, 1\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 2.3052 | converged | True | NA | Non-stationary starting autoregressive parameters found. Using zeros as starting parameters. \| Non-invertible starting MA parameters found. Using zeros as starting parameters. | 13010 | 5 | 96 | 8452 | -26010 | -25975 | -26010 | 4 | 6 | 1 | 0 | 0 | 5 | 7 | 12 | False |
| ARIMA(3,1,2)\[log1p\] | ARIMA | \[3, 1, 2\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 2.6498 | converged | True | NA | Non-stationary starting autoregressive parameters found. Using zeros as starting parameters. \| Non-invertible starting MA parameters found. Using zeros as starting parameters. | 13010 | 6 | 96 | 8452 | -26008 | -25966 | -26008 | 5 | 8 | 1 | 0 | 0 | 6.5 | 9 | 10 | False |
| ARIMA(3,1,3)\[log1p\] | ARIMA | \[3, 1, 3\] | \[0, 0, 0, 0\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 12.762 | unconverged | False | NA | Non-stationary starting autoregressive parameters found. Using zeros as starting parameters. \| Non-invertible starting MA parameters found. Using zeros as starting parameters. \| Maximum Likelihood optimization failed to converge. Check mle\_retvals | 13013 | 7 | 96 | 8452 | -26012 | -25963 | -26012 | NA | NA | 1 | 0 | 0 | NA | NA | 7 | False |
| SARIMA(1,0,0)x(1,0,0,48)\[log1p\] | SARIMA | \[1, 0, 0\] | \[1, 0, 0, 48\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 26.426 | converged | True | NA | NA | 10541 | 4 | 96 | 8452 | -21073 | -21045 | -21073 | 3 | 3 | 0 | 0 | 48 | 2.5 | 2.5 | 12 | False |
| SARIMA(0,0,1)x(0,0,1,48)\[log1p\] | SARIMA | \[0, 0, 1\] | \[0, 0, 1, 48\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 40.544 | converged | True | NA | Non-invertible starting seasonal moving average Using zeros as starting parameters. | 413 | 4 | 96 | 8452 | -818 | -789.83 | -818 | 4 | 4 | 0 | 0 | 48 | 4 | 4 | 12 | False |
| SARIMA(1,0,1)x(1,0,0,48)\[log1p\] | SARIMA | \[1, 0, 1\] | \[1, 0, 0, 48\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 185.22 | converged | True | NA | NA | 12867 | 5 | 96 | 8452 | -25724 | -25689 | -25724 | 1 | 1 | 0 | 0 | 48 | 1 | 1 | 10 | True |
| SARIMA(1,0,0)x(0,0,1,48)\[log1p\] | SARIMA | \[1, 0, 0\] | \[0, 0, 1, 48\] | log1p | 2024-01-01T00:00:00+00:00 | 2023-07-05T00:00:00+00:00 | 2023-12-31T23:00:00+00:00 | 8548 | 0 | 18.885 | converged | True | NA | Non-invertible starting seasonal moving average Using zeros as starting parameters. | 12139 | 4 | 96 | 8452 | -24271 | -24243 | -24271 | 2 | 2 | 0 | 0 | 48 | 2 | 2 | 12 | False |
| AR(1,0,0) | AR | \[1, 0, 0\] | \[0, 0, 0, 0\] | identity | 2024-02-01T00:00:00+00:00 | 2023-08-05T00:00:00+00:00 | 2024-01-31T23:00:00+00:00 | 8548 | 0 | 0.71058 | converged | True | NA | NA | -28854 | 3 | 96 | 8452 | 57713 | 57735 | 57713 | 8 | 8 | 0 | 0 | 0 | 8 | 8 | 12 | False |
| AR(2,0,0) | AR | \[2, 0, 0\] | \[0, 0, 0, 0\] | identity | 2024-02-01T00:00:00+00:00 | 2023-08-05T00:00:00+00:00 | 2024-01-31T23:00:00+00:00 | 8548 | 0 | 1.3903 | converged | True | NA | NA | -27115 | 4 | 96 | 8452 | 54239 | 54267 | 54239 | 7 | 7 | 0 | 0 | 0 | 7 | 7 | 12 | False |
| AR(3,0,0) | AR | \[3, 0, 0\] | \[0, 0, 0, 0\] | identity | 2024-02-01T00:00:00+00:00 | 2023-08-05T00:00:00+00:00 | 2024-01-31T23:00:00+00:00 | 8548 | 0 | 1.7008 | converged | True | NA | NA | -26999 | 5 | 96 | 8452 | 54007 | 54043 | 54007 | 3 | 3 | 0 | 0 | 0 | 5 | 2.5 | 12 | False |
| AR(4,0,0) | AR | \[4, 0, 0\] | \[0, 0, 0, 0\] | identity | 2024-02-01T00:00:00+00:00 | 2023-08-05T00:00:00+00:00 | 2024-01-31T23:00:00+00:00 | 8548 | 0 | 2.1366 | converged | True | NA | NA | -26998 | 6 | 96 | 8452 | 54008 | 54050 | 54008 | 4 | 4 | 0 | 0 | 0 | 5 | 3.5 | 12 | False |
| AR(5,0,0) | AR | \[5, 0, 0\] | \[0, 0, 0, 0\] | identity | 2024-02-01T00:00:00+00:00 | 2023-08-05T00:00:00+00:00 | 2024-01-31T23:00:00+00:00 | 8548 | 0 | 3.2997 | converged | True | NA | NA | -26997 | 7 | 96 | 8452 | 54008 | 54058 | 54008 | 5 | 5 | 0 | 0 | 0 | 3.5 | 5 | 12 | False |
| AR(6,0,0) | AR | \[6, 0, 0\] | \[0, 0, 0, 0\] | identity | 2024-02-01T00:00:00+00:00 | 2023-08-05T00:00:00+00:00 | 2024-01-31T23:00:00+00:00 | 8548 | 0 | 4.11 | converged | True | NA | NA | -26997 | 8 | 96 | 8452 | 54010 | 54066 | 54010 | 6 | 6 | 0 | 0 | 0 | 4 | 6 | 12 | False |
| AR(7,0,0) | AR | \[7, 0, 0\] | \[0, 0, 0, 0\] | identity | 2024-02-01T00:00:00+00:00 | 2023-08-05T00:00:00+00:00 | 2024-01-31T23:00:00+00:00 | 8548 | 0 | 8.8739 | converged | True | NA | NA | -26976 | 9 | 96 | 8452 | 53970 | 54033 | 53970 | 2 | 1 | 0 | 0 | 0 | 1.5 | 1 | 12 | True |
| AR(8,0,0) | AR | \[8, 0, 0\] | \[0, 0, 0, 0\] | identity | 2024-02-01T00:00:00+00:00 | 2023-08-05T00:00:00+00:00 | 2024-01-31T23:00:00+00:00 | 8548 | 0 | 9.5628 | converged | True | NA | NA | -26974 | 10 | 96 | 8452 | 53967 | 54038 | 53967 | 1 | 2 | 0 | 0 | 0 | 1.5 | 3.5 | 12 | False |
| MA(0,0,1) | MA | \[0, 0, 1\] | \[0, 0, 0, 0\] | identity | 2024-02-01T00:00:00+00:00 | 2023-08-05T00:00:00+00:00 | 2024-01-31T23:00:00+00:00 | 8548 | 0 | 1.3118 | converged | True | NA | NA | -42239 | 3 | 96 | 8452 | 84484 | 84505 | 84484 | 8 | 8 | 0 | 0 | 0 | 8 | 8 | 12 | False |
| MA(0,0,2) | MA | \[0, 0, 2\] | \[0, 0, 0, 0\] | identity | 2024-02-01T00:00:00+00:00 | 2023-08-05T00:00:00+00:00 | 2024-01-31T23:00:00+00:00 | 8548 | 0 | 2.893 | converged | True | NA | NA | -38090 | 4 | 96 | 8452 | 76189 | 76217 | 76189 | 7 | 7 | 0 | 0 | 0 | 7 | 7 | 12 | False |

_Table shows 100 rows. The complete table remains in the referenced CSV artifact._

Search ledger source: `C:\Users\viraj\Documents\Codex\2026-10-22\plan-gridshift-a-complete-ats-mini\outputs\GridShift\artifacts\runs\d2dee2d358735d7d\selection\selection_ledger.csv`.

Forecasts use a 48-slot path and report lead times from the configured horizon list. Comparisons use common eligible targets and retain counts by horizon. The 2025 test is evaluated after the validation protocol is frozen. The exporter does not change the validation-selected forecast champion after observing test metrics.

### Validation-selected forecast results

Common-origin results exclude origins where any competitor falls back. Full end-to-end tables retain those cases. These are different estimands.

Champion: `SARIMA(1,0,1)x(1,0,0,48)`. Strongest simple baseline: `persistence`.

| model\_id | group | horizon | n | mae | rmse | mean\_error | mase | coverage80 | coverage95 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AR(7,0,0) | all | 1 | 15683 | 7.1718 | 9.7911 | -0.1169 | 0.17471 | 0.84525 | 0.94472 |
| AR(7,0,0) | all | 4 | 15680 | 17.077 | 22.62 | -0.42498 | 0.41724 | 0.82819 | 0.94107 |
| AR(7,0,0) | all | 12 | 15672 | 34.812 | 42.385 | -1.1867 | 0.85231 | 0.78509 | 0.95214 |
| AR(7,0,0) | all | 24 | 15660 | 39.932 | 48.229 | -1.4143 | 0.97742 | 0.83934 | 0.96207 |
| AR(7,0,0) | all | 48 | 15654 | 45.774 | 55.09 | -0.74635 | 1.118 | 0.83499 | 0.94979 |
| MA(0,0,8) | all | 1 | 15683 | 11.92 | 14.735 | 0.32013 | 0.2899 | 0.77689 | 0.93802 |
| MA(0,0,8) | all | 4 | 15680 | 36.282 | 43.49 | 1.5764 | 0.88206 | 0.62105 | 0.88176 |
| MA(0,0,8) | all | 12 | 15672 | 51.246 | 61.262 | 2.2804 | 1.2464 | 0.50287 | 0.78005 |
| MA(0,0,8) | all | 24 | 15660 | 51.194 | 61.205 | 2.1266 | 1.2453 | 0.50396 | 0.78052 |
| MA(0,0,8) | all | 48 | 15654 | 51.221 | 61.237 | 1.7958 | 1.246 | 0.50364 | 0.78006 |
| ARMA(3,0,2) | all | 1 | 15683 | 7.1547 | 9.7232 | 0.021131 | 0.17426 | 0.84455 | 0.94433 |
| ARMA(3,0,2) | all | 4 | 15680 | 16.924 | 22.261 | 0.076628 | 0.41328 | 0.82704 | 0.94222 |
| ARMA(3,0,2) | all | 12 | 15672 | 33.517 | 41.079 | 0.40218 | 0.81813 | 0.79186 | 0.94953 |
| ARMA(3,0,2) | all | 24 | 15660 | 37.67 | 45.736 | 1.3624 | 0.91805 | 0.82075 | 0.95977 |
| ARMA(3,0,2) | all | 48 | 15654 | 43.474 | 51.93 | 2.0782 | 1.0575 | 0.82522 | 0.96359 |
| ARIMA(3,1,3) | all | 1 | 15683 | 7.1418 | 9.7256 | -0.0078794 | 0.17398 | 0.84384 | 0.94465 |
| ARIMA(3,1,3) | all | 4 | 15680 | 16.719 | 22.262 | -0.016219 | 0.40848 | 0.82838 | 0.93967 |
| ARIMA(3,1,3) | all | 12 | 15672 | 32.351 | 41.419 | -0.067015 | 0.79109 | 0.79824 | 0.93989 |
| ARIMA(3,1,3) | all | 24 | 15660 | 36.826 | 47.445 | -0.22032 | 0.89945 | 0.80747 | 0.94253 |
| ARIMA(3,1,3) | all | 48 | 15654 | 42.408 | 54.697 | -0.47711 | 1.0359 | 0.82209 | 0.95228 |
| SARIMA(1,0,1)x(1,0,0,48) | all | 1 | 15683 | 7.1242 | 9.8643 | -0.026331 | 0.17364 | 0.83249 | 0.93713 |
| SARIMA(1,0,1)x(1,0,0,48) | all | 4 | 15680 | 15.047 | 20.585 | -0.056733 | 0.36707 | 0.75108 | 0.8854 |
| SARIMA(1,0,1)x(1,0,0,48) | all | 12 | 15672 | 27.922 | 35.998 | -0.12639 | 0.68077 | 0.66807 | 0.8422 |
| SARIMA(1,0,1)x(1,0,0,48) | all | 24 | 15660 | 33.816 | 43.572 | -0.2568 | 0.82261 | 0.69821 | 0.87203 |
| SARIMA(1,0,1)x(1,0,0,48) | all | 48 | 15654 | 40.205 | 51.229 | -0.30946 | 0.97832 | 0.71982 | 0.88846 |
| AR(8,0,0)\[log1p\] | all | 1 | 15683 | 7.285 | 9.9415 | -0.16315 | 0.1777 | 0.84015 | 0.93853 |
| AR(8,0,0)\[log1p\] | all | 4 | 15680 | 17.382 | 23.058 | -0.38091 | 0.42528 | 0.82411 | 0.93112 |
| AR(8,0,0)\[log1p\] | all | 12 | 15672 | 35.419 | 43.218 | -0.66295 | 0.86802 | 0.7821 | 0.94691 |
| AR(8,0,0)\[log1p\] | all | 24 | 15660 | 40.303 | 49.038 | -0.49132 | 0.98741 | 0.81418 | 0.97867 |
| AR(8,0,0)\[log1p\] | all | 48 | 15654 | 45.827 | 55.382 | 0.53982 | 1.1202 | 0.80759 | 0.98154 |
| MA(0,0,8)\[log1p\] | all | 1 | 15683 | 12.458 | 16.14 | -3.3794 | 0.30519 | 0.79844 | 0.94657 |
| MA(0,0,8)\[log1p\] | all | 4 | 15680 | 35.769 | 44.328 | -6.3304 | 0.87371 | 0.63425 | 0.87698 |
| MA(0,0,8)\[log1p\] | all | 12 | 15672 | 50.455 | 60.963 | -5.8386 | 1.2294 | 0.52138 | 0.76889 |
| MA(0,0,8)\[log1p\] | all | 24 | 15660 | 50.428 | 60.93 | -5.9916 | 1.2288 | 0.52261 | 0.7698 |
| MA(0,0,8)\[log1p\] | all | 48 | 15654 | 50.507 | 61.014 | -6.322 | 1.2308 | 0.52153 | 0.77054 |
| ARMA(3,0,1)\[log1p\] | all | 1 | 15683 | 7.3295 | 9.9861 | -0.20026 | 0.17884 | 0.84002 | 0.93834 |
| ARMA(3,0,1)\[log1p\] | all | 4 | 15680 | 17.622 | 23.338 | -0.48925 | 0.43127 | 0.82194 | 0.93004 |
| ARMA(3,0,1)\[log1p\] | all | 12 | 15672 | 36.257 | 44.159 | -0.966 | 0.88873 | 0.77406 | 0.94761 |
| ARMA(3,0,1)\[log1p\] | all | 24 | 15660 | 41.145 | 50.052 | -0.84371 | 1.0085 | 0.80913 | 0.98046 |
| ARMA(3,0,1)\[log1p\] | all | 48 | 15654 | 46.78 | 56.441 | 0.38402 | 1.1433 | 0.79705 | 0.97866 |
| ARIMA(2,1,1)\[log1p\] | all | 1 | 15683 | 7.2922 | 10.112 | 1.0346 | 0.17774 | 0.8418 | 0.93738 |
| ARIMA(2,1,1)\[log1p\] | all | 4 | 15680 | 17.846 | 24.398 | 3.7686 | 0.43644 | 0.82366 | 0.92647 |
| ARIMA(2,1,1)\[log1p\] | all | 12 | 15672 | 40.245 | 51.089 | 13.15 | 0.98704 | 0.8013 | 0.94079 |
| ARIMA(2,1,1)\[log1p\] | all | 24 | 15660 | 51.649 | 66.026 | 29.043 | 1.2679 | 0.9037 | 0.9933 |
| ARIMA(2,1,1)\[log1p\] | all | 48 | 15654 | 79.967 | 103.3 | 67.016 | 1.9711 | 0.97311 | 0.99866 |
| SARIMA(1,0,1)x(1,0,0,48)\[log1p\] | all | 1 | 15683 | 7.8398 | 11.012 | 0.48249 | 0.1913 | 0.83045 | 0.92846 |
| SARIMA(1,0,1)x(1,0,0,48)\[log1p\] | all | 4 | 15680 | 16.352 | 22.794 | 1.3639 | 0.39936 | 0.76505 | 0.89094 |
| SARIMA(1,0,1)x(1,0,0,48)\[log1p\] | all | 12 | 15672 | 30.566 | 41.493 | 3.7805 | 0.74488 | 0.69513 | 0.85815 |
| SARIMA(1,0,1)x(1,0,0,48)\[log1p\] | all | 24 | 15660 | 39.538 | 53.684 | 7.2535 | 0.96046 | 0.7076 | 0.8848 |
| SARIMA(1,0,1)x(1,0,0,48)\[log1p\] | all | 48 | 15654 | 48.822 | 67.909 | 12.565 | 1.1869 | 0.75067 | 0.90629 |
| persistence | all | 1 | 15683 | 8.7815 | 12.448 | -0.020022 | 0.21456 | 0.99962 | 1 |
| persistence | all | 4 | 15680 | 18.99 | 26.114 | -0.037054 | 0.46467 | 0.97583 | 0.9986 |
| persistence | all | 12 | 15672 | 35.44 | 45.406 | -0.085184 | 0.86799 | 0.86135 | 0.97314 |
| persistence | all | 24 | 15660 | 39.123 | 50.357 | -0.23167 | 0.95649 | 0.8341 | 0.95447 |
| persistence | all | 48 | 15654 | 41.435 | 54.263 | -0.47036 | 1.0096 | 0.80855 | 0.93669 |
| daily\_naive | all | 1 | 15683 | 40.796 | 53.492 | 0.25467 | 0.99315 | 0.81381 | 0.94025 |
| daily\_naive | all | 4 | 15680 | 40.782 | 53.481 | 0.19483 | 0.99301 | 0.81378 | 0.94024 |
| daily\_naive | all | 12 | 15672 | 40.792 | 53.484 | 0.034456 | 0.99362 | 0.81381 | 0.94028 |
| daily\_naive | all | 24 | 15660 | 40.81 | 53.519 | -0.22088 | 0.99424 | 0.81315 | 0.93978 |
| daily\_naive | all | 48 | 15654 | 51.33 | 66.335 | -0.14399 | 1.2528 | 0.71138 | 0.88176 |
| weekly\_naive | all | 1 | 15683 | 56.818 | 72.304 | -0.51916 | 1.3745 | 0.67583 | 0.85628 |
| weekly\_naive | all | 4 | 15680 | 56.847 | 72.322 | -0.5396 | 1.3752 | 0.6757 | 0.85631 |
| weekly\_naive | all | 12 | 15672 | 56.985 | 72.415 | -0.64242 | 1.3786 | 0.674 | 0.85586 |
| weekly\_naive | all | 24 | 15660 | 57.023 | 72.439 | -0.8334 | 1.3798 | 0.67292 | 0.85536 |
| weekly\_naive | all | 48 | 15654 | 57.046 | 72.406 | -1.325 | 1.3812 | 0.67114 | 0.85537 |
| calendar\_mean | all | 1 | 15683 | 47.837 | 58.13 | 2.3276 | 1.162 | 0.76663 | 0.94134 |
| calendar\_mean | all | 4 | 15680 | 47.837 | 58.13 | 2.3034 | 1.162 | 0.76658 | 0.94133 |
| calendar\_mean | all | 12 | 15672 | 47.844 | 58.138 | 2.2314 | 1.1622 | 0.76627 | 0.94123 |
| calendar\_mean | all | 24 | 15660 | 47.779 | 58.03 | 2.0905 | 1.1608 | 0.76692 | 0.94176 |
| calendar\_mean | all | 48 | 15654 | 47.734 | 57.985 | 1.815 | 1.1599 | 0.76773 | 0.94155 |

Full validation metrics: `../artifacts/runs/d2dee2d358735d7d/validation/forecast_metrics.csv`.

### Locked-test forecast results

| model\_id | group | horizon | n | mae | rmse | mean\_error | mase | coverage80 | coverage95 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AR(7,0,0) | all | 1 | 16465 | 6.8126 | 9.0806 | 0.024024 | 0.17383 | 0.83152 | 0.94467 |
| AR(7,0,0) | all | 4 | 16465 | 16.917 | 22.142 | 0.10963 | 0.43125 | 0.82296 | 0.94169 |
| AR(7,0,0) | all | 12 | 16465 | 35.719 | 43.298 | 0.41066 | 0.91063 | 0.79672 | 0.9607 |
| AR(7,0,0) | all | 24 | 16465 | 40.526 | 48.256 | 0.75554 | 1.0398 | 0.83681 | 0.97905 |
| AR(7,0,0) | all | 48 | 16465 | 45.643 | 53.934 | 1.4374 | 1.1713 | 0.84033 | 0.97419 |
| MA(0,0,8)\[log1p\] | all | 1 | 16465 | 11.783 | 15.051 | -2.9861 | 0.30276 | 0.80571 | 0.94176 |
| MA(0,0,8)\[log1p\] | all | 4 | 16465 | 35.141 | 42.929 | -5.703 | 0.90131 | 0.63365 | 0.8843 |
| MA(0,0,8)\[log1p\] | all | 12 | 16465 | 49.826 | 59.458 | -5.3451 | 1.2762 | 0.50999 | 0.77461 |
| MA(0,0,8)\[log1p\] | all | 24 | 16465 | 49.862 | 59.506 | -5.5187 | 1.2771 | 0.50951 | 0.77498 |
| MA(0,0,8)\[log1p\] | all | 48 | 16465 | 49.859 | 59.536 | -5.5612 | 1.2771 | 0.51017 | 0.77419 |
| ARMA(3,0,2) | all | 1 | 16465 | 6.7988 | 9.0301 | -0.020042 | 0.1737 | 0.83359 | 0.9468 |
| ARMA(3,0,2) | all | 4 | 16465 | 16.81 | 21.887 | -0.060132 | 0.4298 | 0.81834 | 0.94042 |
| ARMA(3,0,2) | all | 12 | 16465 | 35.164 | 43.074 | -0.21344 | 0.90224 | 0.78664 | 0.94886 |
| ARMA(3,0,2) | all | 24 | 16465 | 40.43 | 49.158 | -0.47097 | 1.0443 | 0.80528 | 0.95664 |
| ARMA(3,0,2) | all | 48 | 16465 | 44.166 | 52.945 | 0.14313 | 1.1395 | 0.81822 | 0.96259 |
| ARIMA(3,1,3) | all | 1 | 16465 | 6.7679 | 8.9832 | -0.037965 | 0.17273 | 0.83377 | 0.94601 |
| ARIMA(3,1,3) | all | 4 | 16465 | 16.451 | 21.618 | -0.14002 | 0.41929 | 0.82041 | 0.94018 |
| ARIMA(3,1,3) | all | 12 | 16465 | 32.72 | 41.863 | -0.44936 | 0.83191 | 0.80036 | 0.9434 |
| ARIMA(3,1,3) | all | 24 | 16465 | 36.614 | 47.101 | -0.61259 | 0.93367 | 0.80401 | 0.94254 |
| ARIMA(3,1,3) | all | 48 | 16465 | 41.165 | 52.505 | -0.64936 | 1.0513 | 0.84209 | 0.96168 |
| SARIMA(1,0,1)x(1,0,0,48) | all | 1 | 16465 | 6.926 | 9.3619 | -0.021016 | 0.1766 | 0.81397 | 0.93094 |
| SARIMA(1,0,1)x(1,0,0,48) | all | 4 | 16465 | 14.877 | 20.081 | -0.055257 | 0.37879 | 0.72602 | 0.86954 |
| SARIMA(1,0,1)x(1,0,0,48) | all | 12 | 16465 | 27.787 | 35.845 | -0.1243 | 0.70739 | 0.63699 | 0.8212 |
| SARIMA(1,0,1)x(1,0,0,48) | all | 24 | 16465 | 33.412 | 43.22 | -0.12814 | 0.85239 | 0.68946 | 0.85084 |
| SARIMA(1,0,1)x(1,0,0,48) | all | 48 | 16465 | 39.262 | 50.733 | 0.18086 | 1.0024 | 0.70635 | 0.87003 |
| persistence | all | 1 | 16465 | 9.1005 | 12.565 | -0.044215 | 0.23133 | 0.99994 | 1 |
| persistence | all | 4 | 16465 | 20.069 | 27.168 | -0.10756 | 0.50953 | 0.97188 | 0.99915 |
| persistence | all | 12 | 16465 | 37.386 | 47.634 | -0.27428 | 0.94914 | 0.82563 | 0.96362 |
| persistence | all | 24 | 16465 | 39.25 | 50.548 | -0.44792 | 0.99996 | 0.80389 | 0.94461 |
| persistence | all | 48 | 16465 | 39.805 | 51.801 | -0.49043 | 1.0167 | 0.80121 | 0.92882 |
| daily\_naive | all | 1 | 16465 | 39.021 | 50.95 | -0.88236 | 0.99541 | 0.80698 | 0.93313 |
| daily\_naive | all | 4 | 16465 | 39.013 | 50.936 | -0.91698 | 0.9954 | 0.80729 | 0.93313 |
| daily\_naive | all | 12 | 16465 | 38.965 | 50.891 | -0.96435 | 0.99456 | 0.8079 | 0.93307 |
| daily\_naive | all | 24 | 16465 | 38.966 | 50.892 | -0.90841 | 0.99498 | 0.80765 | 0.93295 |
| daily\_naive | all | 48 | 16465 | 47.862 | 61.342 | -1.339 | 1.2224 | 0.71819 | 0.89147 |
| weekly\_naive | all | 1 | 16465 | 56.711 | 72.27 | 0.35797 | 1.4554 | 0.65175 | 0.82539 |
| weekly\_naive | all | 4 | 16465 | 56.729 | 72.294 | 0.22338 | 1.4559 | 0.65181 | 0.82514 |
| weekly\_naive | all | 12 | 16465 | 56.739 | 72.316 | -0.11236 | 1.4562 | 0.65169 | 0.8249 |
| weekly\_naive | all | 24 | 16465 | 56.76 | 72.36 | -0.43644 | 1.4571 | 0.65138 | 0.82381 |
| weekly\_naive | all | 48 | 16465 | 56.846 | 72.401 | -0.54728 | 1.4596 | 0.65102 | 0.82375 |
| calendar\_mean | all | 1 | 16465 | 47.058 | 56.996 | 2.6258 | 1.2052 | 0.74176 | 0.93301 |
| calendar\_mean | all | 4 | 16465 | 47.065 | 57.004 | 2.5584 | 1.2053 | 0.74151 | 0.93301 |
| calendar\_mean | all | 12 | 16465 | 47.073 | 57 | 2.3842 | 1.2055 | 0.74169 | 0.93319 |
| calendar\_mean | all | 24 | 16465 | 47.003 | 56.912 | 2.1991 | 1.2038 | 0.74261 | 0.9338 |
| calendar\_mean | all | 48 | 16465 | 46.967 | 56.866 | 2.1514 | 1.2028 | 0.74327 | 0.93362 |

Full test metrics: `../artifacts/runs/d2dee2d358735d7d/test/forecast_metrics.csv`.

### Paired forecast-loss contrast

The validation-selected classical model is compared with the validation-selected simple forecast using equal-weight endpoint MAE at common no-fallback origins. Positive loss reduction favors the classical model. The seven-day block is the declared primary block length; this forecast contrast is secondary and descriptive.

| block\_days | paired\_origin\_count | estimate\_loss\_reduction\_pct | ci95\_loss\_reduction\_pct\_low | ci95\_loss\_reduction\_pct\_high |
| --- | --- | --- | --- | --- |
| 3 | 16465 | 16.033 | 13.67 | 18.387 |
| 7 | 16465 | 16.033 | 13.373 | 18.702 |
| 14 | 16465 | 16.033 | 13.27 | 18.729 |

### Cumulative forecast-path errors

Path MAE and RMSE score all half-hours in each prefix. Prefix-mean MAE scores the time-average intensity over that prefix. Complete observed prefixes use a common target mask. These descriptive metrics do not alter endpoint-based model selection.

| model\_id | horizon | n\_complete\_paths | path\_mae | path\_rmse | prefix\_mean\_mae |
| --- | --- | --- | --- | --- | --- |
| SARIMA(1,0,1)x(1,0,0,48) | 1 | 16465 | 6.926 | 9.3619 | 6.926 |
| SARIMA(1,0,1)x(1,0,0,48) | 4 | 16465 | 11.004 | 15.424 | 10.631 |
| SARIMA(1,0,1)x(1,0,0,48) | 12 | 16465 | 19.044 | 26.451 | 17.594 |
| SARIMA(1,0,1)x(1,0,0,48) | 24 | 16465 | 25.137 | 34.083 | 21.707 |
| SARIMA(1,0,1)x(1,0,0,48) | 48 | 16465 | 31.435 | 42.079 | 25.544 |
| persistence | 1 | 16465 | 9.1005 | 12.565 | 9.1005 |
| persistence | 4 | 16465 | 14.695 | 20.811 | 14.379 |
| persistence | 12 | 16465 | 25.826 | 35.655 | 23.988 |
| persistence | 24 | 16465 | 32.235 | 43.075 | 27.371 |
| persistence | 48 | 16465 | 37.539 | 49.57 | 30.314 |

Test scores describe the locked period. They do not authorize changing the frozen deployment candidate or claiming performance beyond the observed year. [S9, S10]

## Scheduling methods

### Residual adequacy

| model\_id | n\_contiguous | lb\_stat | lb\_pvalue |
| --- | --- | --- | --- |
| AR(7,0,0) | 8226 | 1543.6 | 2.5134e-297 |
| MA(0,0,8)\[log1p\] | 8226 | 12731 | 0 |
| ARMA(3,0,2) | 8226 | 1202.7 | 6.1073e-224 |
| ARIMA(3,1,3) | 8226 | 1173.3 | 1.653e-218 |
| SARIMA(1,0,1)x(1,0,0,48) | 8226 | 2458.9 | 0 |

| model\_id | normality\_p\_value | skew | excess\_kurtosis |
| --- | --- | --- | --- |
| AR(7,0,0) | 0 | -0.2198 | 4.6994 |
| MA(0,0,8)\[log1p\] | 0 | -0.80752 | 2.4699 |
| ARMA(3,0,2) | 0 | -0.22005 | 4.6236 |
| ARIMA(3,1,3) | 0 | -0.21582 | 4.5227 |
| SARIMA(1,0,1)x(1,0,0,48) | 0 | -0.047748 | 3.8004 |

Small Ljung-Box p-values indicate residual serial dependence. Small Jarque-Bera p-values challenge Gaussian innovation assumptions. Printed zero p-values are numerical underflow, not proof of an exactly zero probability. Forecast skill must be judged separately by chronological errors and empirical coverage.

For each feasible start, the scheduler minimizes integrated predicted carbon cost over the full job duration. Deadlines and reservations are hard constraints. Exact ties use the earliest start. Isolated releases are counterfactual cases, not one simultaneous workload trace.

The primary accounting uses modeled energy-intensity products. The default power and PUE values are declared scenarios, not telemetry. Queue arrivals are synthetic and one-GPU reservations are not globally optimal. [S5, S9]

### Primary scheduling results

Modeled isolated-job benefit under declared assumptions. The certified seven-day paired block estimate is 12.414% (95% interval 10.951 to 13.828%) across 2913 scheduled primary-policy jobs; the bootstrap paired 2913 jobs. This estimates modeled operational CO2 under the declared job, energy, and deadline assumptions.

The deployment model is selected independently of the forecast-MAE champion. If the deployment choice is a simple baseline, its benefit establishes temporal-placement value under the assumptions, not added value from classical forecasting. Persistence can have low forecast MAE yet schedule at release because its point path is flat. The complete policy table is necessary to assess stronger timing baselines.

| scenario\_id | policy | model\_id | n\_eligible\_jobs | n\_scheduled | fallback\_rate | mean\_realized\_grams | paired\_savings\_grams | paired\_savings\_pct | oracle\_regret\_grams |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| duration\_2h\_slack\_10h | earliest | NA | 2913 | 2913 | 0 | 124.03 | 0 | NA | 26.809 |
| duration\_2h\_slack\_10h | seeded\_random | NA | 2913 | 2913 | 0 | 123.53 | 1469.5 | 0.40672 | 26.304 |
| duration\_2h\_slack\_10h | oracle | oracle | 2913 | 2913 | 0 | 97.224 | 78094 | 21.614 | 0 |
| duration\_2h\_slack\_10h | forecast | AR(7,0,0) | 2913 | 2913 | 0 | 114.09 | 28966 | 8.017 | 16.865 |
| duration\_2h\_slack\_10h | forecast | ARIMA(3,1,3) | 2913 | 2913 | 0.019224 | 114.76 | 27016 | 7.4773 | 17.534 |
| duration\_2h\_slack\_10h | forecast | ARMA(3,0,2) | 2913 | 2913 | 0.019224 | 113.86 | 29621 | 8.1982 | 16.64 |
| duration\_2h\_slack\_10h | forecast | MA(0,0,8)\[log1p\] | 2913 | 2913 | 0.019224 | 118.28 | 16763 | 4.6395 | 21.054 |
| duration\_2h\_slack\_10h | forecast | SARIMA(1,0,1)x(1,0,0,48) | 2913 | 2913 | 0 | 105.66 | 53519 | 14.813 | 8.4363 |
| duration\_2h\_slack\_10h | forecast | calendar\_mean | 2913 | 2913 | 0 | 108.64 | 44853 | 12.414 | 11.411 |
| duration\_2h\_slack\_10h | forecast | daily\_naive | 2913 | 2913 | 0 | 107.73 | 47492 | 13.144 | 10.505 |
| duration\_2h\_slack\_10h | forecast | persistence | 2913 | 2913 | 0 | 124.03 | 0 | 0 | 26.809 |
| duration\_2h\_slack\_10h | forecast | weekly\_naive | 2913 | 2913 | 0 | 107.6 | 47878 | 13.251 | 10.373 |

Source: `C:\Users\viraj\Documents\Codex\2026-10-22\plan-gridshift-a-complete-ats-mini\outputs\GridShift\artifacts\runs\d2dee2d358735d7d\test\single_job\primary_summary.csv`.

### Paired block uncertainty

| block\_days | paired\_job\_count | estimate\_savings\_pct | ci95\_savings\_pct\_low | ci95\_savings\_pct\_high | is\_primary\_block |
| --- | --- | --- | --- | --- | --- |
| 3 | 2913 | 12.414 | 11.1 | 13.649 | False |
| 7 | 2913 | 12.414 | 10.951 | 13.828 | True |
| 14 | 2913 | 12.414 | 10.643 | 14.07 | False |

Source: `C:\Users\viraj\Documents\Codex\2026-10-22\plan-gridshift-a-complete-ats-mini\outputs\GridShift\artifacts\runs\d2dee2d358735d7d\test\single_job\primary_bootstrap.csv`. Secondary block estimates are descriptive sensitivity checks. The primary block is the configured seven-day block when available.

### Selected policy versus the strongest simple forecast

No classical deployment was selected; selected-policy improvement is simple timing value, not classical added value

| block\_days | paired\_job\_count | estimate\_savings\_pct | ci95\_savings\_pct\_low | ci95\_savings\_pct\_high |
| --- | --- | --- | --- | --- |
| 3 | 2913 | 12.414 | 11.1 | 13.649 |
| 7 | 2913 | 12.414 | 10.951 | 13.828 |
| 14 | 2913 | 12.414 | 10.643 | 14.07 |

### Complete declared scenario outcomes

Every declared duration/slack scenario is included below. These are secondary descriptive comparisons. The full policy and metric table remains in the cited source CSV.

| scenario\_id | n\_eligible\_jobs | n\_scheduled | fallback\_rate | mean\_realized\_grams | paired\_savings\_pct | oracle\_regret\_grams |
| --- | --- | --- | --- | --- | --- | --- |
| duration\_0.5h\_slack\_0h | 2913 | 2913 | 0 | 31.064 | 0 | 0 |
| duration\_0.5h\_slack\_2h | 2913 | 2913 | 0 | 29.563 | 4.8319 | 0.67444 |
| duration\_0.5h\_slack\_6h | 2913 | 2913 | 0 | 27.76 | 10.637 | 1.9448 |
| duration\_0.5h\_slack\_12h | 2913 | 2913 | 0 | 27.132 | 12.657 | 3.9983 |
| duration\_0.5h\_slack\_20h | 2913 | 2913 | 0 | 26.694 | 14.068 | 5.9414 |
| duration\_1h\_slack\_0h | 2913 | 2913 | 0 | 62.111 | 0 | 0 |
| duration\_1h\_slack\_2h | 2913 | 2913 | 0 | 59.07 | 4.8966 | 1.0486 |
| duration\_1h\_slack\_6h | 2913 | 2913 | 0 | 55.627 | 10.439 | 3.6657 |
| duration\_1h\_slack\_12h | 2913 | 2913 | 0 | 54.32 | 12.544 | 7.7066 |
| duration\_1h\_slack\_20h | 2913 | 2913 | 0 | 53.4 | 14.025 | 11.537 |
| duration\_2h\_slack\_0h | 2913 | 2913 | 0 | 124.03 | 0 | 0 |
| duration\_2h\_slack\_2h | 2913 | 2913 | 0 | 118 | 4.8611 | 1.5638 |
| duration\_2h\_slack\_6h | 2913 | 2913 | 0 | 111.2 | 10.349 | 6.4704 |
| duration\_2h\_slack\_10h | 2913 | 2913 | 0 | 108.64 | 12.414 | 11.411 |
| duration\_2h\_slack\_12h | 2913 | 2913 | 0 | 108.66 | 12.398 | 14.467 |
| duration\_2h\_slack\_20h | 2913 | 2913 | 0 | 106.99 | 13.738 | 22.153 |
| duration\_4h\_slack\_0h | 2913 | 2913 | 0 | 248.16 | 0 | 0 |
| duration\_4h\_slack\_2h | 2913 | 2913 | 0 | 238.49 | 3.8974 | 3.8005 |
| duration\_4h\_slack\_6h | 2913 | 2913 | 0 | 223.41 | 9.9733 | 10.35 |
| duration\_4h\_slack\_12h | 2913 | 2913 | 0 | 220.21 | 11.262 | 27.548 |
| duration\_4h\_slack\_20h | 2913 | 2913 | 0 | 215.93 | 12.987 | 41.469 |

### Monthly scheduling outcomes

| month\_utc | scenario\_id | policy | model\_id | n\_eligible\_jobs | n\_scheduled | mean\_realized\_grams | paired\_savings\_pct | fallback\_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025-01 | duration\_2h\_slack\_10h | earliest | NA | 248 | 248 | 161.55 | NA | 0 |
| 2025-01 | duration\_2h\_slack\_10h | seeded\_random | NA | 248 | 248 | 162.2 | -0.40316 | 0 |
| 2025-01 | duration\_2h\_slack\_10h | oracle | oracle | 248 | 248 | 135.32 | 16.232 | 0 |
| 2025-01 | duration\_2h\_slack\_10h | forecast | AR(7,0,0) | 248 | 248 | 151.44 | 6.2523 | 0 |
| 2025-01 | duration\_2h\_slack\_10h | forecast | ARIMA(3,1,3) | 248 | 248 | 153.14 | 5.2028 | 0 |
| 2025-01 | duration\_2h\_slack\_10h | forecast | ARMA(3,0,2) | 248 | 248 | 151.68 | 6.1062 | 0 |
| 2025-01 | duration\_2h\_slack\_10h | forecast | MA(0,0,8)\[log1p\] | 248 | 248 | 157.53 | 2.4867 | 0 |
| 2025-01 | duration\_2h\_slack\_10h | forecast | SARIMA(1,0,1)x(1,0,0,48) | 248 | 248 | 142.77 | 11.62 | 0 |
| 2025-01 | duration\_2h\_slack\_10h | forecast | calendar\_mean | 248 | 248 | 140.11 | 13.268 | 0 |
| 2025-01 | duration\_2h\_slack\_10h | forecast | daily\_naive | 248 | 248 | 145.61 | 9.8622 | 0 |
| 2025-01 | duration\_2h\_slack\_10h | forecast | persistence | 248 | 248 | 161.55 | 0 | 0 |
| 2025-01 | duration\_2h\_slack\_10h | forecast | weekly\_naive | 248 | 248 | 149.14 | 7.6793 | 0 |
| 2025-02 | duration\_2h\_slack\_10h | earliest | NA | 224 | 224 | 141.77 | NA | 0 |
| 2025-02 | duration\_2h\_slack\_10h | seeded\_random | NA | 224 | 224 | 140.11 | 1.1714 | 0 |
| 2025-02 | duration\_2h\_slack\_10h | oracle | oracle | 224 | 224 | 114.02 | 19.574 | 0 |
| 2025-02 | duration\_2h\_slack\_10h | forecast | AR(7,0,0) | 224 | 224 | 131.86 | 6.9942 | 0 |
| 2025-02 | duration\_2h\_slack\_10h | forecast | ARIMA(3,1,3) | 224 | 224 | 132.63 | 6.4509 | 0 |
| 2025-02 | duration\_2h\_slack\_10h | forecast | ARMA(3,0,2) | 224 | 224 | 130.86 | 7.6963 | 0 |
| 2025-02 | duration\_2h\_slack\_10h | forecast | MA(0,0,8)\[log1p\] | 224 | 224 | 136.4 | 3.7892 | 0 |
| 2025-02 | duration\_2h\_slack\_10h | forecast | SARIMA(1,0,1)x(1,0,0,48) | 224 | 224 | 122.77 | 13.406 | 0 |
| 2025-02 | duration\_2h\_slack\_10h | forecast | calendar\_mean | 224 | 224 | 120.58 | 14.947 | 0 |
| 2025-02 | duration\_2h\_slack\_10h | forecast | daily\_naive | 224 | 224 | 124.98 | 11.848 | 0 |
| 2025-02 | duration\_2h\_slack\_10h | forecast | persistence | 224 | 224 | 141.77 | 0 | 0 |
| 2025-02 | duration\_2h\_slack\_10h | forecast | weekly\_naive | 224 | 224 | 124.36 | 12.281 | 0 |
| 2025-03 | duration\_2h\_slack\_10h | earliest | NA | 248 | 248 | 140.58 | NA | 0 |
| 2025-03 | duration\_2h\_slack\_10h | seeded\_random | NA | 248 | 248 | 141.88 | -0.92384 | 0 |
| 2025-03 | duration\_2h\_slack\_10h | oracle | oracle | 248 | 248 | 109.26 | 22.281 | 0 |
| 2025-03 | duration\_2h\_slack\_10h | forecast | AR(7,0,0) | 248 | 248 | 131.31 | 6.5942 | 0 |
| 2025-03 | duration\_2h\_slack\_10h | forecast | ARIMA(3,1,3) | 248 | 248 | 131.32 | 6.5825 | 0 |
| 2025-03 | duration\_2h\_slack\_10h | forecast | ARMA(3,0,2) | 248 | 248 | 128.57 | 8.5451 | 0 |
| 2025-03 | duration\_2h\_slack\_10h | forecast | MA(0,0,8)\[log1p\] | 248 | 248 | 133.59 | 4.9709 | 0 |
| 2025-03 | duration\_2h\_slack\_10h | forecast | SARIMA(1,0,1)x(1,0,0,48) | 248 | 248 | 119.78 | 14.794 | 0 |
| 2025-03 | duration\_2h\_slack\_10h | forecast | calendar\_mean | 248 | 248 | 123.08 | 12.448 | 0 |
| 2025-03 | duration\_2h\_slack\_10h | forecast | daily\_naive | 248 | 248 | 122.22 | 13.058 | 0 |
| 2025-03 | duration\_2h\_slack\_10h | forecast | persistence | 248 | 248 | 140.58 | 0 | 0 |
| 2025-03 | duration\_2h\_slack\_10h | forecast | weekly\_naive | 248 | 248 | 123.84 | 11.909 | 0 |
| 2025-04 | duration\_2h\_slack\_10h | earliest | NA | 240 | 240 | 127.75 | NA | 0 |
| 2025-04 | duration\_2h\_slack\_10h | seeded\_random | NA | 240 | 240 | 127.88 | -0.10568 | 0 |
| 2025-04 | duration\_2h\_slack\_10h | oracle | oracle | 240 | 240 | 96.437 | 24.509 | 0 |
| 2025-04 | duration\_2h\_slack\_10h | forecast | AR(7,0,0) | 240 | 240 | 116.75 | 8.6045 | 0 |
| 2025-04 | duration\_2h\_slack\_10h | forecast | ARIMA(3,1,3) | 240 | 240 | 118.29 | 7.4006 | 0 |
| 2025-04 | duration\_2h\_slack\_10h | forecast | ARMA(3,0,2) | 240 | 240 | 115.14 | 9.8703 | 0 |
| 2025-04 | duration\_2h\_slack\_10h | forecast | MA(0,0,8)\[log1p\] | 240 | 240 | 120.37 | 5.7778 | 0 |
| 2025-04 | duration\_2h\_slack\_10h | forecast | SARIMA(1,0,1)x(1,0,0,48) | 240 | 240 | 104.76 | 17.991 | 0 |
| 2025-04 | duration\_2h\_slack\_10h | forecast | calendar\_mean | 240 | 240 | 116.8 | 8.5716 | 0 |
| 2025-04 | duration\_2h\_slack\_10h | forecast | daily\_naive | 240 | 240 | 106.15 | 16.905 | 0 |
| 2025-04 | duration\_2h\_slack\_10h | forecast | persistence | 240 | 240 | 127.75 | 0 | 0 |
| 2025-04 | duration\_2h\_slack\_10h | forecast | weekly\_naive | 240 | 240 | 107.79 | 15.625 | 0 |
| 2025-05 | duration\_2h\_slack\_10h | earliest | NA | 248 | 248 | 102.1 | NA | 0 |
| 2025-05 | duration\_2h\_slack\_10h | seeded\_random | NA | 248 | 248 | 102.44 | -0.3346 | 0 |
| 2025-05 | duration\_2h\_slack\_10h | oracle | oracle | 248 | 248 | 74.818 | 26.718 | 0 |
| 2025-05 | duration\_2h\_slack\_10h | forecast | AR(7,0,0) | 248 | 248 | 92.537 | 9.363 | 0 |
| 2025-05 | duration\_2h\_slack\_10h | forecast | ARIMA(3,1,3) | 248 | 248 | 93.342 | 8.5754 | 0 |
| 2025-05 | duration\_2h\_slack\_10h | forecast | ARMA(3,0,2) | 248 | 248 | 91.01 | 10.859 | 0 |
| 2025-05 | duration\_2h\_slack\_10h | forecast | MA(0,0,8)\[log1p\] | 248 | 248 | 96.466 | 5.5147 | 0 |
| 2025-05 | duration\_2h\_slack\_10h | forecast | SARIMA(1,0,1)x(1,0,0,48) | 248 | 248 | 82.841 | 18.861 | 0 |
| 2025-05 | duration\_2h\_slack\_10h | forecast | calendar\_mean | 248 | 248 | 91.438 | 10.44 | 0 |
| 2025-05 | duration\_2h\_slack\_10h | forecast | daily\_naive | 248 | 248 | 84.172 | 17.556 | 0 |
| 2025-05 | duration\_2h\_slack\_10h | forecast | persistence | 248 | 248 | 102.1 | 0 | 0 |
| 2025-05 | duration\_2h\_slack\_10h | forecast | weekly\_naive | 248 | 248 | 82.25 | 19.439 | 0 |
| 2025-06 | duration\_2h\_slack\_10h | earliest | NA | 240 | 240 | 94.6 | NA | 0 |
| 2025-06 | duration\_2h\_slack\_10h | seeded\_random | NA | 240 | 240 | 94.097 | 0.53171 | 0 |
| 2025-06 | duration\_2h\_slack\_10h | oracle | oracle | 240 | 240 | 69.128 | 26.926 | 0 |
| 2025-06 | duration\_2h\_slack\_10h | forecast | AR(7,0,0) | 240 | 240 | 85.941 | 9.1533 | 0 |
| 2025-06 | duration\_2h\_slack\_10h | forecast | ARIMA(3,1,3) | 240 | 240 | 85.961 | 9.1321 | 0 |
| 2025-06 | duration\_2h\_slack\_10h | forecast | ARMA(3,0,2) | 240 | 240 | 84.34 | 10.846 | 0 |
| 2025-06 | duration\_2h\_slack\_10h | forecast | MA(0,0,8)\[log1p\] | 240 | 240 | 88.885 | 6.0412 | 0 |
| 2025-06 | duration\_2h\_slack\_10h | forecast | SARIMA(1,0,1)x(1,0,0,48) | 240 | 240 | 79.404 | 16.063 | 0 |
| 2025-06 | duration\_2h\_slack\_10h | forecast | calendar\_mean | 240 | 240 | 77.361 | 18.223 | 0 |
| 2025-06 | duration\_2h\_slack\_10h | forecast | daily\_naive | 240 | 240 | 81.356 | 14 | 0 |
| 2025-06 | duration\_2h\_slack\_10h | forecast | persistence | 240 | 240 | 94.6 | 0 | 0 |
| 2025-06 | duration\_2h\_slack\_10h | forecast | weekly\_naive | 240 | 240 | 80.438 | 14.97 | 0 |
| 2025-07 | duration\_2h\_slack\_10h | earliest | NA | 248 | 248 | 124.05 | NA | 0 |
| 2025-07 | duration\_2h\_slack\_10h | seeded\_random | NA | 248 | 248 | 122.64 | 1.1421 | 0 |
| 2025-07 | duration\_2h\_slack\_10h | oracle | oracle | 248 | 248 | 96.859 | 21.922 | 0 |
| 2025-07 | duration\_2h\_slack\_10h | forecast | AR(7,0,0) | 248 | 248 | 111.8 | 9.8767 | 0 |
| 2025-07 | duration\_2h\_slack\_10h | forecast | ARIMA(3,1,3) | 248 | 248 | 112.67 | 9.1754 | 0.22581 |
| 2025-07 | duration\_2h\_slack\_10h | forecast | ARMA(3,0,2) | 248 | 248 | 112.67 | 9.1786 | 0 |
| 2025-07 | duration\_2h\_slack\_10h | forecast | MA(0,0,8)\[log1p\] | 248 | 248 | 118.13 | 4.7757 | 0 |
| 2025-07 | duration\_2h\_slack\_10h | forecast | SARIMA(1,0,1)x(1,0,0,48) | 248 | 248 | 103.84 | 16.295 | 0 |
| 2025-07 | duration\_2h\_slack\_10h | forecast | calendar\_mean | 248 | 248 | 103.24 | 16.779 | 0 |
| 2025-07 | duration\_2h\_slack\_10h | forecast | daily\_naive | 248 | 248 | 105.15 | 15.238 | 0 |
| 2025-07 | duration\_2h\_slack\_10h | forecast | persistence | 248 | 248 | 124.05 | 0 | 0 |
| 2025-07 | duration\_2h\_slack\_10h | forecast | weekly\_naive | 248 | 248 | 103.96 | 16.202 | 0 |
| 2025-08 | duration\_2h\_slack\_10h | earliest | NA | 248 | 248 | 118.6 | NA | 0 |
| 2025-08 | duration\_2h\_slack\_10h | seeded\_random | NA | 248 | 248 | 115.93 | 2.2553 | 0 |
| 2025-08 | duration\_2h\_slack\_10h | oracle | oracle | 248 | 248 | 93.735 | 20.969 | 0 |
| 2025-08 | duration\_2h\_slack\_10h | forecast | AR(7,0,0) | 248 | 248 | 109.5 | 7.6764 | 0 |
| 2025-08 | duration\_2h\_slack\_10h | forecast | ARIMA(3,1,3) | 248 | 248 | 107.94 | 8.9884 | 0 |
| 2025-08 | duration\_2h\_slack\_10h | forecast | ARMA(3,0,2) | 248 | 248 | 110.65 | 6.7087 | 0 |
| 2025-08 | duration\_2h\_slack\_10h | forecast | MA(0,0,8)\[log1p\] | 248 | 248 | 109.78 | 7.4389 | 0.22581 |
| 2025-08 | duration\_2h\_slack\_10h | forecast | SARIMA(1,0,1)x(1,0,0,48) | 248 | 248 | 100.75 | 15.057 | 0 |
| 2025-08 | duration\_2h\_slack\_10h | forecast | calendar\_mean | 248 | 248 | 99.168 | 16.387 | 0 |
| 2025-08 | duration\_2h\_slack\_10h | forecast | daily\_naive | 248 | 248 | 101.69 | 14.262 | 0 |
| 2025-08 | duration\_2h\_slack\_10h | forecast | persistence | 248 | 248 | 118.6 | 0 | 0 |
| 2025-08 | duration\_2h\_slack\_10h | forecast | weekly\_naive | 248 | 248 | 104.27 | 12.083 | 0 |
| 2025-09 | duration\_2h\_slack\_10h | earliest | NA | 240 | 240 | 107.84 | NA | 0 |
| 2025-09 | duration\_2h\_slack\_10h | seeded\_random | NA | 240 | 240 | 109.64 | -1.6766 | 0 |
| 2025-09 | duration\_2h\_slack\_10h | oracle | oracle | 240 | 240 | 84.709 | 21.446 | 0 |
| 2025-09 | duration\_2h\_slack\_10h | forecast | AR(7,0,0) | 240 | 240 | 102.62 | 4.8342 | 0 |
| 2025-09 | duration\_2h\_slack\_10h | forecast | ARIMA(3,1,3) | 240 | 240 | 97.363 | 9.712 | 0 |
| 2025-09 | duration\_2h\_slack\_10h | forecast | ARMA(3,0,2) | 240 | 240 | 104.28 | 3.2976 | 0 |
| 2025-09 | duration\_2h\_slack\_10h | forecast | MA(0,0,8)\[log1p\] | 240 | 240 | 102.58 | 4.8713 | 0 |
| 2025-09 | duration\_2h\_slack\_10h | forecast | SARIMA(1,0,1)x(1,0,0,48) | 240 | 240 | 94.897 | 11.999 | 0 |
| 2025-09 | duration\_2h\_slack\_10h | forecast | calendar\_mean | 240 | 240 | 91.103 | 15.517 | 0 |
| 2025-09 | duration\_2h\_slack\_10h | forecast | daily\_naive | 240 | 240 | 95.23 | 11.69 | 0 |
| 2025-09 | duration\_2h\_slack\_10h | forecast | persistence | 240 | 240 | 107.84 | 0 | 0 |
| 2025-09 | duration\_2h\_slack\_10h | forecast | weekly\_naive | 240 | 240 | 94.984 | 11.918 | 0 |
| 2025-10 | duration\_2h\_slack\_10h | earliest | NA | 248 | 248 | 132.65 | NA | 0 |
| 2025-10 | duration\_2h\_slack\_10h | seeded\_random | NA | 248 | 248 | 131.57 | 0.81344 | 0 |
| 2025-10 | duration\_2h\_slack\_10h | oracle | oracle | 248 | 248 | 110.66 | 16.581 | 0 |
| 2025-10 | duration\_2h\_slack\_10h | forecast | AR(7,0,0) | 248 | 248 | 126.2 | 4.8667 | 0 |
| 2025-10 | duration\_2h\_slack\_10h | forecast | ARIMA(3,1,3) | 248 | 248 | 124.7 | 5.9975 | 0 |
| 2025-10 | duration\_2h\_slack\_10h | forecast | ARMA(3,0,2) | 248 | 248 | 127.25 | 4.0701 | 0 |
| 2025-10 | duration\_2h\_slack\_10h | forecast | MA(0,0,8)\[log1p\] | 248 | 248 | 129.04 | 2.7241 | 0 |
| 2025-10 | duration\_2h\_slack\_10h | forecast | SARIMA(1,0,1)x(1,0,0,48) | 248 | 248 | 117.99 | 11.05 | 0 |
| 2025-10 | duration\_2h\_slack\_10h | forecast | calendar\_mean | 248 | 248 | 120.5 | 9.1601 | 0 |
| 2025-10 | duration\_2h\_slack\_10h | forecast | daily\_naive | 248 | 248 | 120.69 | 9.0134 | 0 |
| 2025-10 | duration\_2h\_slack\_10h | forecast | persistence | 248 | 248 | 132.65 | 0 | 0 |
| 2025-10 | duration\_2h\_slack\_10h | forecast | weekly\_naive | 248 | 248 | 118.22 | 10.882 | 0 |
| 2025-11 | duration\_2h\_slack\_10h | earliest | NA | 240 | 240 | 121.2 | NA | 0 |
| 2025-11 | duration\_2h\_slack\_10h | seeded\_random | NA | 240 | 240 | 119 | 1.8111 | 0 |
| 2025-11 | duration\_2h\_slack\_10h | oracle | oracle | 240 | 240 | 92.809 | 23.425 | 0 |
| 2025-11 | duration\_2h\_slack\_10h | forecast | AR(7,0,0) | 240 | 240 | 108.52 | 10.46 | 0 |
| 2025-11 | duration\_2h\_slack\_10h | forecast | ARIMA(3,1,3) | 240 | 240 | 112.91 | 6.8408 | 0 |
| 2025-11 | duration\_2h\_slack\_10h | forecast | ARMA(3,0,2) | 240 | 240 | 108.24 | 10.691 | 0 |
| 2025-11 | duration\_2h\_slack\_10h | forecast | MA(0,0,8)\[log1p\] | 240 | 240 | 115.71 | 4.533 | 0 |
| 2025-11 | duration\_2h\_slack\_10h | forecast | SARIMA(1,0,1)x(1,0,0,48) | 240 | 240 | 102.23 | 15.65 | 0 |
| 2025-11 | duration\_2h\_slack\_10h | forecast | calendar\_mean | 240 | 240 | 112.95 | 6.8045 | 0 |
| 2025-11 | duration\_2h\_slack\_10h | forecast | daily\_naive | 240 | 240 | 105.46 | 12.99 | 0 |
| 2025-11 | duration\_2h\_slack\_10h | forecast | persistence | 240 | 240 | 121.2 | 0 | 0 |
| 2025-11 | duration\_2h\_slack\_10h | forecast | weekly\_naive | 240 | 240 | 102.1 | 15.761 | 0 |
| 2025-12 | duration\_2h\_slack\_10h | earliest | NA | 241 | 241 | 115.74 | NA | 0 |
| 2025-12 | duration\_2h\_slack\_10h | seeded\_random | NA | 241 | 241 | 114.9 | 0.72533 | 0 |
| 2025-12 | duration\_2h\_slack\_10h | oracle | oracle | 241 | 241 | 88.842 | 23.241 | 0 |
| 2025-12 | duration\_2h\_slack\_10h | forecast | AR(7,0,0) | 241 | 241 | 100.54 | 13.131 | 0 |
| 2025-12 | duration\_2h\_slack\_10h | forecast | ARIMA(3,1,3) | 241 | 241 | 106.9 | 7.6413 | 0 |
| 2025-12 | duration\_2h\_slack\_10h | forecast | ARMA(3,0,2) | 241 | 241 | 101.58 | 12.239 | 0.23237 |
| 2025-12 | duration\_2h\_slack\_10h | forecast | MA(0,0,8)\[log1p\] | 241 | 241 | 110.94 | 4.1515 | 0 |
| 2025-12 | duration\_2h\_slack\_10h | forecast | SARIMA(1,0,1)x(1,0,0,48) | 241 | 241 | 95.927 | 17.119 | 0 |
| 2025-12 | duration\_2h\_slack\_10h | forecast | calendar\_mean | 241 | 241 | 107.23 | 7.3514 | 0 |
| 2025-12 | duration\_2h\_slack\_10h | forecast | daily\_naive | 241 | 241 | 100.11 | 13.502 | 0 |
| 2025-12 | duration\_2h\_slack\_10h | forecast | persistence | 241 | 241 | 115.74 | 0 | 0 |
| 2025-12 | duration\_2h\_slack\_10h | forecast | weekly\_naive | 241 | 241 | 99.766 | 13.802 | 0 |

Source: `C:\Users\viraj\Documents\Codex\2026-10-22\plan-gridshift-a-complete-ats-mini\outputs\GridShift\artifacts\runs\d2dee2d358735d7d\test\single_job\primary_monthly.csv`. Monthly results are shown for the default duration and slack when those fields are present.

### Queue outcomes

| offered\_load | seed | slack\_hours | policy | offered\_jobs | completed\_jobs | rejected\_jobs | deadline\_misses | matched\_savings\_pct | unmatched\_completed\_jobs | interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.3 | 1729 | 6 | earliest | 1411 | 1404 | 7 | 0 | 0 | 29 | descriptive completion intersection; service differs |
| 0.3 | 1729 | 6 | selected | 1411 | 1380 | 31 | 0 | 7.3217 | 5 | descriptive completion intersection; service differs |
| 0.3 | 1729 | 6 | strongest\_simple | 1411 | 1404 | 7 | 0 | 0 | 29 | descriptive completion intersection; service differs |
| 0.3 | 1729 | 12 | earliest | 1411 | 1410 | 1 | 0 | 0 | 7 | descriptive completion intersection; service differs |
| 0.3 | 1729 | 12 | selected | 1411 | 1404 | 7 | 0 | 9.2072 | 1 | descriptive completion intersection; service differs |
| 0.3 | 1729 | 12 | strongest\_simple | 1411 | 1410 | 1 | 0 | 0 | 7 | descriptive completion intersection; service differs |
| 0.3 | 2718 | 6 | earliest | 1324 | 1317 | 7 | 0 | 0 | 25 | descriptive completion intersection; service differs |
| 0.3 | 2718 | 6 | selected | 1324 | 1294 | 30 | 0 | 5.7025 | 2 | descriptive completion intersection; service differs |
| 0.3 | 2718 | 6 | strongest\_simple | 1324 | 1317 | 7 | 0 | 0 | 25 | descriptive completion intersection; service differs |
| 0.3 | 2718 | 12 | earliest | 1324 | 1324 | 0 | 0 | 0 | 6 | descriptive completion intersection; service differs |
| 0.3 | 2718 | 12 | selected | 1324 | 1318 | 6 | 0 | 8.2914 | 0 | descriptive completion intersection; service differs |
| 0.3 | 2718 | 12 | strongest\_simple | 1324 | 1324 | 0 | 0 | 0 | 6 | descriptive completion intersection; service differs |
| 0.3 | 31415 | 6 | earliest | 1393 | 1387 | 6 | 0 | 0 | 34 | descriptive completion intersection; service differs |
| 0.3 | 31415 | 6 | selected | 1393 | 1356 | 37 | 0 | 7.3119 | 3 | descriptive completion intersection; service differs |
| 0.3 | 31415 | 6 | strongest\_simple | 1393 | 1387 | 6 | 0 | 0 | 34 | descriptive completion intersection; service differs |
| 0.3 | 31415 | 12 | earliest | 1393 | 1393 | 0 | 0 | 0 | 2 | descriptive completion intersection; service differs |
| 0.3 | 31415 | 12 | selected | 1393 | 1391 | 2 | 0 | 8.0945 | 0 | descriptive completion intersection; service differs |
| 0.3 | 31415 | 12 | strongest\_simple | 1393 | 1393 | 0 | 0 | 0 | 2 | descriptive completion intersection; service differs |
| 0.6 | 1729 | 6 | earliest | 2732 | 2629 | 103 | 0 | 0 | 198 | descriptive completion intersection; service differs |
| 0.6 | 1729 | 6 | selected | 2732 | 2462 | 270 | 0 | 4.3873 | 31 | descriptive completion intersection; service differs |
| 0.6 | 1729 | 6 | strongest\_simple | 2732 | 2629 | 103 | 0 | 0 | 198 | descriptive completion intersection; service differs |
| 0.6 | 1729 | 12 | earliest | 2732 | 2711 | 21 | 0 | 0 | 96 | descriptive completion intersection; service differs |
| 0.6 | 1729 | 12 | selected | 2732 | 2626 | 106 | 0 | 4.6477 | 11 | descriptive completion intersection; service differs |
| 0.6 | 1729 | 12 | strongest\_simple | 2732 | 2711 | 21 | 0 | 0 | 96 | descriptive completion intersection; service differs |
| 0.6 | 2718 | 6 | earliest | 2722 | 2616 | 106 | 0 | 0 | 195 | descriptive completion intersection; service differs |
| 0.6 | 2718 | 6 | selected | 2722 | 2455 | 267 | 0 | 4.61 | 34 | descriptive completion intersection; service differs |
| 0.6 | 2718 | 6 | strongest\_simple | 2722 | 2616 | 106 | 0 | 0 | 195 | descriptive completion intersection; service differs |
| 0.6 | 2718 | 12 | earliest | 2722 | 2715 | 7 | 0 | 0 | 103 | descriptive completion intersection; service differs |
| 0.6 | 2718 | 12 | selected | 2722 | 2615 | 107 | 0 | 5.2051 | 3 | descriptive completion intersection; service differs |
| 0.6 | 2718 | 12 | strongest\_simple | 2722 | 2715 | 7 | 0 | 0 | 103 | descriptive completion intersection; service differs |
| 0.6 | 31415 | 6 | earliest | 2787 | 2694 | 93 | 0 | 0 | 207 | descriptive completion intersection; service differs |
| 0.6 | 31415 | 6 | selected | 2787 | 2524 | 263 | 0 | 4.1595 | 37 | descriptive completion intersection; service differs |
| 0.6 | 31415 | 6 | strongest\_simple | 2787 | 2694 | 93 | 0 | 0 | 207 | descriptive completion intersection; service differs |
| 0.6 | 31415 | 12 | earliest | 2787 | 2781 | 6 | 0 | 0 | 105 | descriptive completion intersection; service differs |
| 0.6 | 31415 | 12 | selected | 2787 | 2678 | 109 | 0 | 5.5991 | 2 | descriptive completion intersection; service differs |
| 0.6 | 31415 | 12 | strongest\_simple | 2787 | 2781 | 6 | 0 | 0 | 105 | descriptive completion intersection; service differs |
| 0.85 | 1729 | 6 | earliest | 3932 | 3497 | 435 | 0 | 0 | 427 | descriptive completion intersection; service differs |
| 0.85 | 1729 | 6 | selected | 3932 | 3205 | 727 | 0 | 3.3599 | 135 | descriptive completion intersection; service differs |
| 0.85 | 1729 | 6 | strongest\_simple | 3932 | 3497 | 435 | 0 | 0 | 427 | descriptive completion intersection; service differs |
| 0.85 | 1729 | 12 | earliest | 3932 | 3750 | 182 | 0 | 0 | 348 | descriptive completion intersection; service differs |
| 0.85 | 1729 | 12 | selected | 3932 | 3480 | 452 | 0 | 3.4766 | 78 | descriptive completion intersection; service differs |
| 0.85 | 1729 | 12 | strongest\_simple | 3932 | 3750 | 182 | 0 | 0 | 348 | descriptive completion intersection; service differs |
| 0.85 | 2718 | 6 | earliest | 3792 | 3456 | 336 | 0 | 0 | 413 | descriptive completion intersection; service differs |
| 0.85 | 2718 | 6 | selected | 3792 | 3148 | 644 | 0 | 3.6621 | 105 | descriptive completion intersection; service differs |
| 0.85 | 2718 | 6 | strongest\_simple | 3792 | 3456 | 336 | 0 | 0 | 413 | descriptive completion intersection; service differs |
| 0.85 | 2718 | 12 | earliest | 3792 | 3650 | 142 | 0 | 0 | 288 | descriptive completion intersection; service differs |
| 0.85 | 2718 | 12 | selected | 3792 | 3419 | 373 | 0 | 4.1502 | 57 | descriptive completion intersection; service differs |
| 0.85 | 2718 | 12 | strongest\_simple | 3792 | 3650 | 142 | 0 | 0 | 288 | descriptive completion intersection; service differs |
| 0.85 | 31415 | 6 | earliest | 3946 | 3577 | 369 | 0 | 0 | 448 | descriptive completion intersection; service differs |
| 0.85 | 31415 | 6 | selected | 3946 | 3246 | 700 | 0 | 3.691 | 117 | descriptive completion intersection; service differs |
| 0.85 | 31415 | 6 | strongest\_simple | 3946 | 3577 | 369 | 0 | 0 | 448 | descriptive completion intersection; service differs |
| 0.85 | 31415 | 12 | earliest | 3946 | 3816 | 130 | 0 | 0 | 352 | descriptive completion intersection; service differs |
| 0.85 | 31415 | 12 | selected | 3946 | 3521 | 425 | 0 | 3.4653 | 57 | descriptive completion intersection; service differs |
| 0.85 | 31415 | 12 | strongest\_simple | 3946 | 3816 | 130 | 0 | 0 | 352 | descriptive completion intersection; service differs |

Queue source: `C:\Users\viraj\Documents\Codex\2026-10-22\plan-gridshift-a-complete-ats-mini\outputs\GridShift\artifacts\runs\d2dee2d358735d7d\test\queue\queue_summary.csv`. Compare emissions with service outcomes. The completion intersection can be selective when policies accept different work.

## Limitations and claim boundaries

### Computing overhead

At an illustrative computing-supply intensity of 100 gCO2/kWh, the recorded gross benefit corresponds to 0.15397 kWh per isolated counterfactual case. Actual forecasting and scheduler energy is unmeasured. This is a break-even scenario, not a verified net-emissions result. Runtime is recorded in forecast metadata and the selection ledger.

### Bounded validation sensitivities

These six variants cover four three-day quarterly episodes in 2024. They are descriptive checks, not full-year robustness or test-driven model selection.

| month | variant | model\_id | n\_scheduled | paired\_savings\_pct | fallback\_rate |
| --- | --- | --- | --- | --- | --- |
| 1 | default | SARIMA(1,0,1)x(1,0,0,48) | 17 | 18.068 | 0 |
| 1 | delay\_0min | SARIMA(1,0,1)x(1,0,0,48) | 17 | 18 | 0 |
| 1 | delay\_60min | SARIMA(1,0,1)x(1,0,0,48) | 17 | 18.136 | 0 |
| 1 | window\_90days | SARIMA(1,0,1)x(1,0,0,48) | 17 | 18.085 | 0 |
| 1 | window\_365days | SARIMA(1,0,1)x(1,0,0,48) | 17 | 18.068 | 0 |
| 1 | native\_missing | SARIMA(1,0,1)x(1,0,0,48) | 17 | 18.068 | 0 |
| 4 | default | SARIMA(1,0,1)x(1,0,0,48) | 17 | 2.4242 | 0 |
| 4 | delay\_0min | SARIMA(1,0,1)x(1,0,0,48) | 17 | 2.6936 | 0 |
| 4 | delay\_60min | SARIMA(1,0,1)x(1,0,0,48) | 17 | 3.2458 | 0 |
| 4 | window\_90days | SARIMA(1,0,1)x(1,0,0,48) | 17 | 2.4242 | 0 |
| 4 | window\_365days | SARIMA(1,0,1)x(1,0,0,48) | 17 | 5.9259 | 0 |
| 4 | native\_missing | SARIMA(1,0,1)x(1,0,0,48) | 17 | 2.4242 | 0 |
| 7 | default | SARIMA(1,0,1)x(1,0,0,48) | 17 | 18.138 | 0 |
| 7 | delay\_0min | SARIMA(1,0,1)x(1,0,0,48) | 17 | 18.431 | 0 |
| 7 | delay\_60min | SARIMA(1,0,1)x(1,0,0,48) | 17 | 18.4 | 0 |
| 7 | window\_90days | SARIMA(1,0,1)x(1,0,0,48) | 17 | 18.292 | 0 |
| 7 | window\_365days | SARIMA(1,0,1)x(1,0,0,48) | 17 | 19.985 | 0 |
| 7 | native\_missing | SARIMA(1,0,1)x(1,0,0,48) | 17 | 18.138 | 0 |
| 10 | default | SARIMA(1,0,1)x(1,0,0,48) | 17 | 12.435 | 0 |
| 10 | delay\_0min | SARIMA(1,0,1)x(1,0,0,48) | 17 | 12.586 | 0 |
| 10 | delay\_60min | SARIMA(1,0,1)x(1,0,0,48) | 17 | 12.586 | 0 |
| 10 | window\_90days | SARIMA(1,0,1)x(1,0,0,48) | 17 | 12.256 | 0 |
| 10 | window\_365days | SARIMA(1,0,1)x(1,0,0,48) | 17 | 13.082 | 0 |
| 10 | native\_missing | SARIMA(1,0,1)x(1,0,0,48) | 17 | 12.435 | 0 |

- Retrospective NESO estimated actuals have no verified historical publication vintages.
- Thirty-minute publication delay is an assumed replay policy.
- Power, PUE, known durations, and arrivals are synthetic. No GPU energy was measured.
- Costs are modeled intensity-weighted operational CO2, not actual avoided grid emissions.
- National GB intensity is a proxy for a hypothetical GB-powered workload.
- Predictive intervals condition on fitted parameters and may be poorly calibrated.
- Queue completion intersections are descriptive when policies accept different jobs.
- Net computing overhead, marginal emissions, and embodied emissions are unmeasured.
- The untouched test covers 2025 only. No post-test model promotion is justified.
- Local packaging and runtime verification do not establish public deployment.
- NESO `actual` is an estimated target for generation-related CO2, not a full lifecycle or all-GHG inventory. [S2, S5]
- Historical publication delay and revision history are not fully established. The replay is pseudo-real-time under the declared availability assumption. [S2, S4]
- GPU energy, PUE, job duration, and queue arrivals are modeled inputs unless a verified telemetry record states otherwise.
- Savings are attributional estimates under the declared accounting boundary. They do not measure a causal change in grid emissions.
- A lower queue total is not a saving when policies complete different work. Report workload and service outcomes alongside emissions.

## Appendix: complete validation metrics

| group\_type | group | horizon | n | mae | rmse | mean\_error | mase | coverage80 | coverage95 | width80 | width95 | interval\_score80 | interval\_score95 | fallback\_origins | model\_id |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| overall | all | 1 | 17490 | 7.2432 | 9.9251 | -0.12582 | 0.17574 | 0.8426 | 0.94311 | 25.657 | 39.239 | 36.252 | 54.963 | 0 | AR(7,0,0) |
| season | winter | 1 | 4321 | 7.2156 | 9.856 | -0.10597 | 0.16656 | 0.85582 | 0.95371 | 26.473 | 40.487 | 36.037 | 54.697 | 0 | AR(7,0,0) |
| season | spring | 1 | 4414 | 7.0947 | 9.5506 | 0.53303 | 0.15816 | 0.84798 | 0.94721 | 26.172 | 40.027 | 35.44 | 51.049 | 0 | AR(7,0,0) |
| season | summer | 1 | 4385 | 7.1449 | 10.139 | 0.5098 | 0.17569 | 0.84356 | 0.93637 | 24.896 | 38.074 | 36.68 | 58.423 | 0 | AR(7,0,0) |
| season | autumn | 1 | 4370 | 7.5189 | 10.145 | -1.4487 | 0.20262 | 0.82311 | 0.93524 | 25.095 | 38.379 | 36.855 | 55.706 | 0 | AR(7,0,0) |
| overall | all | 4 | 17490 | 17.203 | 22.835 | -0.45814 | 0.41875 | 0.82579 | 0.93991 | 58.274 | 89.122 | 82.804 | 121.49 | 0 | AR(7,0,0) |
| season | winter | 4 | 4321 | 16.73 | 22.417 | -0.3745 | 0.38694 | 0.85189 | 0.95533 | 60.626 | 92.72 | 81.481 | 121.66 | 0 | AR(7,0,0) |
| season | spring | 4 | 4414 | 16.191 | 21.511 | 1.8808 | 0.36079 | 0.84798 | 0.95061 | 59.427 | 90.885 | 79.396 | 112.21 | 0 | AR(7,0,0) |
| season | summer | 4 | 4385 | 16.889 | 22.418 | 1.8133 | 0.41515 | 0.81916 | 0.93523 | 55.821 | 85.37 | 80.807 | 118.61 | 0 | AR(7,0,0) |
| season | autumn | 4 | 4370 | 19.007 | 24.866 | -5.1826 | 0.51235 | 0.78421 | 0.91854 | 57.244 | 87.546 | 89.558 | 133.56 | 0 | AR(7,0,0) |
| overall | all | 12 | 17490 | 34.835 | 42.477 | -1.2731 | 0.84968 | 0.78359 | 0.95163 | 107.4 | 164.26 | 146.4 | 189.28 | 0 | AR(7,0,0) |
| season | winter | 12 | 4321 | 34.813 | 42.463 | -1.0884 | 0.80833 | 0.81439 | 0.96621 | 113.91 | 174.21 | 146.06 | 190.41 | 0 | AR(7,0,0) |
| season | spring | 12 | 4414 | 31.65 | 39.302 | 5.7824 | 0.70548 | 0.84504 | 0.97236 | 111.48 | 170.5 | 138.54 | 187.93 | 0 | AR(7,0,0) |
| season | summer | 12 | 4385 | 32.975 | 39.827 | 5.4309 | 0.81081 | 0.80091 | 0.95576 | 101.39 | 155.07 | 134.86 | 176.82 | 0 | AR(7,0,0) |
| season | autumn | 12 | 4370 | 39.94 | 47.817 | -15.309 | 1.0752 | 0.67368 | 0.91213 | 102.88 | 157.34 | 166.25 | 202.02 | 0 | AR(7,0,0) |
| overall | all | 24 | 17490 | 39.597 | 47.903 | -1.4833 | 0.96455 | 0.84202 | 0.96472 | 132.76 | 203.03 | 166.17 | 223.84 | 0 | AR(7,0,0) |
| season | winter | 24 | 4321 | 44.195 | 52.358 | -1.7181 | 1.0305 | 0.81833 | 0.97755 | 142.73 | 218.28 | 176.51 | 226.89 | 0 | AR(7,0,0) |
| season | spring | 24 | 4414 | 35.743 | 42.87 | 10.292 | 0.79463 | 0.92343 | 0.99207 | 143.27 | 219.11 | 155.84 | 222.41 | 0 | AR(7,0,0) |
| season | summer | 24 | 4385 | 32.618 | 38.898 | 9.2879 | 0.8026 | 0.90832 | 0.99521 | 125.1 | 191.33 | 136.47 | 192.94 | 0 | AR(7,0,0) |
| season | autumn | 24 | 4370 | 45.947 | 55.666 | -23.953 | 1.2335 | 0.7167 | 0.89382 | 119.95 | 183.45 | 196.17 | 253.27 | 0 | AR(7,0,0) |
| overall | all | 48 | 17490 | 45.39 | 54.605 | -0.62514 | 1.1035 | 0.83945 | 0.95352 | 147.96 | 226.29 | 188.44 | 265.48 | 0 | AR(7,0,0) |
| season | winter | 48 | 4321 | 50.415 | 59.736 | -1.9933 | 1.1788 | 0.83684 | 0.96019 | 160.41 | 245.33 | 202.38 | 280.52 | 0 | AR(7,0,0) |
| season | spring | 48 | 4414 | 43.856 | 51.663 | 16.079 | 0.97375 | 0.91414 | 0.99977 | 166.72 | 254.97 | 177.33 | 254.99 | 0 | AR(7,0,0) |
| season | summer | 48 | 4385 | 36.449 | 42.366 | 13.874 | 0.8975 | 0.91653 | 0.99954 | 139.14 | 212.79 | 145.45 | 212.82 | 0 | AR(7,0,0) |
| season | autumn | 48 | 4370 | 50.943 | 62.518 | -30.693 | 1.3667 | 0.68924 | 0.854 | 125.57 | 192.05 | 229.02 | 314.03 | 0 | AR(7,0,0) |
| overall | all | 1 | 17490 | 11.907 | 14.74 | 0.20027 | 0.28826 | 0.77867 | 0.93836 | 36.073 | 55.169 | 51.356 | 69.421 | 0 | MA(0,0,8) |
| season | winter | 1 | 4321 | 12.974 | 15.833 | -0.36051 | 0.30085 | 0.76255 | 0.93775 | 38.234 | 58.474 | 54.755 | 72.234 | 0 | MA(0,0,8) |
| season | spring | 1 | 4414 | 11.861 | 14.569 | 4.1045 | 0.26387 | 0.83348 | 0.96987 | 39.686 | 60.695 | 49.964 | 68.15 | 0 | MA(0,0,8) |
| season | summer | 1 | 4385 | 10.5 | 13.067 | 3.3349 | 0.25837 | 0.82303 | 0.95986 | 34.371 | 52.565 | 45.153 | 61.874 | 0 | MA(0,0,8) |
| season | autumn | 1 | 4370 | 12.31 | 15.36 | -6.3341 | 0.33044 | 0.69474 | 0.88558 | 31.996 | 48.934 | 55.627 | 75.497 | 0 | MA(0,0,8) |
| overall | all | 4 | 17490 | 36.075 | 43.237 | 1.1353 | 0.87272 | 0.62773 | 0.88479 | 85.331 | 130.5 | 155.67 | 212.01 | 0 | MA(0,0,8) |
| season | winter | 4 | 4321 | 40.933 | 48.173 | -1.1975 | 0.95143 | 0.59037 | 0.8748 | 92.053 | 140.78 | 175.03 | 233.2 | 0 | MA(0,0,8) |
| season | spring | 4 | 4414 | 36.488 | 42.842 | 15.777 | 0.81064 | 0.67694 | 0.95809 | 97.663 | 149.36 | 143.28 | 161.66 | 0 | MA(0,0,8) |
| season | summer | 4 | 4385 | 29.442 | 34.53 | 12.272 | 0.72506 | 0.69327 | 0.95211 | 79.518 | 121.61 | 115.36 | 134.73 | 0 | MA(0,0,8) |
| season | autumn | 4 | 4370 | 37.51 | 46.227 | -22.522 | 1.0058 | 0.5492 | 0.75309 | 72.06 | 110.21 | 189.47 | 319.45 | 0 | MA(0,0,8) |
| overall | all | 12 | 17490 | 50.886 | 60.785 | 1.663 | 1.2314 | 0.51006 | 0.78588 | 98.722 | 150.98 | 242.04 | 359.5 | 0 | MA(0,0,8) |
| season | winter | 12 | 4321 | 58.217 | 68.164 | -1.7725 | 1.3545 | 0.4735 | 0.75121 | 106.46 | 162.82 | 278.69 | 411.68 | 0 | MA(0,0,8) |
| season | spring | 12 | 4414 | 51.349 | 59.963 | 23.177 | 1.1403 | 0.54712 | 0.84255 | 112.84 | 172.57 | 222.46 | 245.71 | 0 | MA(0,0,8) |
| season | summer | 12 | 4385 | 40.725 | 47.365 | 18.167 | 1.0032 | 0.56556 | 0.87594 | 92.145 | 140.92 | 171.33 | 189.22 | 0 | MA(0,0,8) |
| season | autumn | 12 | 4370 | 53.366 | 65.654 | -33.231 | 1.4305 | 0.45309 | 0.67254 | 83.409 | 127.56 | 296.52 | 593.73 | 0 | MA(0,0,8) |
| overall | all | 24 | 17490 | 50.867 | 60.766 | 1.6546 | 1.2311 | 0.51041 | 0.78622 | 98.722 | 150.98 | 241.89 | 359.34 | 0 | MA(0,0,8) |
| season | winter | 24 | 4321 | 58.132 | 68.07 | -1.8809 | 1.3534 | 0.47327 | 0.75283 | 106.4 | 162.73 | 277.97 | 410.54 | 0 | MA(0,0,8) |
| season | spring | 24 | 4414 | 51.341 | 59.958 | 23.226 | 1.1399 | 0.54826 | 0.84323 | 112.86 | 172.6 | 222.42 | 245.83 | 0 | MA(0,0,8) |
| season | summer | 24 | 4385 | 40.72 | 47.367 | 18.226 | 1.0028 | 0.56648 | 0.87503 | 92.208 | 141.02 | 171.26 | 189.16 | 0 | MA(0,0,8) |
| season | autumn | 24 | 4370 | 53.386 | 65.683 | -33.266 | 1.4313 | 0.45263 | 0.67254 | 83.388 | 127.53 | 296.74 | 594.12 | 0 | MA(0,0,8) |
| overall | all | 48 | 17490 | 50.88 | 60.78 | 1.6901 | 1.2317 | 0.50989 | 0.78651 | 98.722 | 150.98 | 242.01 | 359.33 | 0 | MA(0,0,8) |
| season | winter | 48 | 4321 | 58.164 | 68.091 | -1.8864 | 1.3557 | 0.46957 | 0.75283 | 106.28 | 162.54 | 278.36 | 410.05 | 0 | MA(0,0,8) |
| season | spring | 48 | 4414 | 51.323 | 59.936 | 23.323 | 1.139 | 0.54894 | 0.84255 | 112.9 | 172.66 | 222.32 | 245.66 | 0 | MA(0,0,8) |
| season | summer | 48 | 4385 | 40.711 | 47.334 | 18.344 | 1.0021 | 0.56762 | 0.87617 | 92.335 | 141.21 | 170.94 | 187.74 | 0 | MA(0,0,8) |
| season | autumn | 48 | 4370 | 53.436 | 65.759 | -33.336 | 1.4331 | 0.4524 | 0.67323 | 83.345 | 127.46 | 297.26 | 596.15 | 0 | MA(0,0,8) |
| overall | all | 1 | 17490 | 7.2253 | 9.8535 | 0.0055265 | 0.17525 | 0.84237 | 0.94334 | 25.456 | 38.931 | 35.924 | 54.207 | 0 | ARMA(3,0,2) |
| season | winter | 1 | 4321 | 7.22 | 9.8502 | -0.065528 | 0.16665 | 0.8579 | 0.95395 | 26.394 | 40.366 | 35.953 | 54.46 | 0 | ARMA(3,0,2) |
| season | spring | 1 | 4414 | 7.1273 | 9.5835 | 0.5701 | 0.15889 | 0.84957 | 0.94721 | 26.223 | 40.105 | 35.544 | 51.22 | 0 | ARMA(3,0,2) |
| season | summer | 1 | 4385 | 7.0834 | 9.9766 | 0.3836 | 0.17413 | 0.8447 | 0.93843 | 24.636 | 37.678 | 35.984 | 56.938 | 0 | ARMA(3,0,2) |
| season | autumn | 1 | 4370 | 7.4721 | 10.001 | -0.87385 | 0.2014 | 0.81739 | 0.93387 | 24.576 | 37.585 | 36.221 | 54.234 | 0 | ARMA(3,0,2) |
| overall | all | 4 | 17490 | 17.045 | 22.452 | 0.020047 | 0.41455 | 0.8247 | 0.94151 | 57.498 | 87.936 | 81.151 | 117.9 | 0 | ARMA(3,0,2) |
| season | winter | 4 | 4321 | 16.803 | 22.407 | -0.22631 | 0.38859 | 0.84772 | 0.95279 | 60.067 | 91.864 | 81.086 | 120.87 | 0 | ARMA(3,0,2) |
| season | spring | 4 | 4414 | 16.32 | 21.688 | 2.0096 | 0.36363 | 0.84368 | 0.94857 | 59.459 | 90.935 | 79.873 | 112.84 | 0 | ARMA(3,0,2) |
| season | summer | 4 | 4385 | 16.398 | 21.553 | 1.3694 | 0.40292 | 0.8244 | 0.94139 | 54.893 | 83.952 | 77.317 | 112.12 | 0 | ARMA(3,0,2) |
| season | autumn | 4 | 4370 | 18.664 | 24.079 | -3.0999 | 0.50333 | 0.78307 | 0.92334 | 55.593 | 85.022 | 86.355 | 125.87 | 0 | ARMA(3,0,2) |
| overall | all | 12 | 17490 | 33.529 | 41.143 | 0.25411 | 0.81502 | 0.79108 | 0.9502 | 104.41 | 159.68 | 142.43 | 189.92 | 0 | ARMA(3,0,2) |
| season | winter | 12 | 4321 | 34.565 | 42.168 | -0.63878 | 0.80112 | 0.81208 | 0.96066 | 112.18 | 171.56 | 144.71 | 190.1 | 0 | ARMA(3,0,2) |
| season | spring | 12 | 4414 | 32.543 | 40.16 | 6.2587 | 0.7254 | 0.84187 | 0.97213 | 113.08 | 172.94 | 140.41 | 189.8 | 0 | ARMA(3,0,2) |
| season | summer | 12 | 4385 | 30.389 | 37.319 | 4.0448 | 0.7467 | 0.8114 | 0.95895 | 97.017 | 148.38 | 128.54 | 170.88 | 0 | ARMA(3,0,2) |
| season | autumn | 12 | 4370 | 36.653 | 44.612 | -8.7318 | 0.98782 | 0.69863 | 0.90892 | 95.392 | 145.89 | 156.14 | 208.96 | 0 | ARMA(3,0,2) |
| overall | all | 24 | 17490 | 37.624 | 45.681 | 1.2072 | 0.9123 | 0.8251 | 0.96232 | 125.8 | 192.39 | 159.91 | 219.48 | 0 | ARMA(3,0,2) |
| season | winter | 24 | 4321 | 42.33 | 50.187 | -1.0217 | 0.98211 | 0.8174 | 0.97454 | 138.6 | 211.97 | 169.63 | 225.07 | 0 | ARMA(3,0,2) |
| season | spring | 24 | 4414 | 36.351 | 43.336 | 11.322 | 0.80797 | 0.93068 | 0.99524 | 147.55 | 225.66 | 158.13 | 227.61 | 0 | ARMA(3,0,2) |
| season | summer | 24 | 4385 | 31.418 | 38.305 | 6.6441 | 0.77174 | 0.86431 | 0.97993 | 113.31 | 173.29 | 134.12 | 181.99 | 0 | ARMA(3,0,2) |
| season | autumn | 24 | 4370 | 40.485 | 49.922 | -12.261 | 1.0897 | 0.68673 | 0.89931 | 103.7 | 158.6 | 177.99 | 243.33 | 0 | ARMA(3,0,2) |
| overall | all | 48 | 17490 | 43.388 | 51.78 | 2.1248 | 1.05 | 0.83007 | 0.96661 | 142.67 | 218.2 | 176.64 | 240.69 | 0 | ARMA(3,0,2) |
| season | winter | 48 | 4321 | 48.894 | 57.486 | -1.3291 | 1.138 | 0.80838 | 0.97107 | 156.28 | 239.01 | 193.46 | 254.74 | 0 | ARMA(3,0,2) |
| season | spring | 48 | 4414 | 44.678 | 52.511 | 17.377 | 0.99184 | 0.92048 | 1 | 169.77 | 259.64 | 178.77 | 259.64 | 0 | ARMA(3,0,2) |
| season | summer | 48 | 4385 | 34.512 | 40.542 | 10.578 | 0.8479 | 0.90992 | 0.99749 | 129.45 | 197.98 | 140.56 | 198.45 | 0 | ARMA(3,0,2) |
| season | autumn | 48 | 4370 | 45.549 | 55.035 | -18.348 | 1.2245 | 0.68009 | 0.89748 | 115.12 | 176.06 | 194.05 | 250.02 | 0 | ARMA(3,0,2) |
| overall | all | 1 | 17490 | 7.2176 | 9.8512 | -0.0046445 | 0.17509 | 0.84168 | 0.94374 | 25.531 | 39.046 | 35.967 | 54.184 | 0 | ARIMA(3,1,3) |
| season | winter | 1 | 4321 | 7.2153 | 9.8531 | -0.019153 | 0.16648 | 0.85698 | 0.95209 | 26.435 | 40.428 | 36.011 | 54.752 | 0 | ARIMA(3,1,3) |
| season | spring | 1 | 4414 | 7.0814 | 9.5179 | 0.044334 | 0.15787 | 0.85093 | 0.94971 | 26.175 | 40.031 | 35.306 | 50.688 | 0 | ARIMA(3,1,3) |
| season | summer | 1 | 4385 | 7.0924 | 9.9915 | -0.023772 | 0.17434 | 0.8447 | 0.93843 | 24.757 | 37.862 | 36.119 | 57.086 | 0 | ARIMA(3,1,3) |
| season | autumn | 1 | 4370 | 7.4829 | 10.036 | -0.020578 | 0.20174 | 0.81419 | 0.93478 | 24.762 | 37.871 | 36.437 | 54.241 | 0 | ARIMA(3,1,3) |
| overall | all | 4 | 17490 | 16.868 | 22.443 | -0.0091889 | 0.41049 | 0.82647 | 0.93945 | 57.613 | 88.111 | 81.709 | 118.94 | 0 | ARIMA(3,1,3) |
| season | winter | 4 | 4321 | 16.671 | 22.357 | -0.062329 | 0.38529 | 0.85027 | 0.94932 | 59.804 | 91.462 | 81.323 | 121.28 | 0 | ARIMA(3,1,3) |
| season | spring | 4 | 4414 | 15.886 | 21.373 | 0.15352 | 0.35414 | 0.84753 | 0.95174 | 59.239 | 90.598 | 79.36 | 112.46 | 0 | ARIMA(3,1,3) |
| season | summer | 4 | 4385 | 16.339 | 21.709 | -0.055537 | 0.40134 | 0.82645 | 0.94116 | 55.31 | 84.589 | 78.353 | 114.29 | 0 | ARIMA(3,1,3) |
| season | autumn | 4 | 4370 | 18.587 | 24.236 | -0.074481 | 0.50151 | 0.78169 | 0.91556 | 56.114 | 85.819 | 87.831 | 127.84 | 0 | ARIMA(3,1,3) |
| overall | all | 12 | 17490 | 32.493 | 41.456 | -0.014612 | 0.79118 | 0.79726 | 0.94185 | 104.83 | 160.33 | 147.97 | 201.75 | 0 | ARIMA(3,1,3) |
| season | winter | 12 | 4321 | 33.167 | 42.143 | -0.15943 | 0.76841 | 0.82018 | 0.95047 | 111.12 | 169.94 | 149.47 | 201.28 | 0 | ARIMA(3,1,3) |
| season | spring | 12 | 4414 | 30.542 | 39.422 | 0.47463 | 0.68128 | 0.83756 | 0.96126 | 110.11 | 168.41 | 142.38 | 194.26 | 0 | ARIMA(3,1,3) |
| season | summer | 12 | 4385 | 29.989 | 38.326 | -0.13826 | 0.73635 | 0.80114 | 0.9512 | 99.287 | 151.85 | 136.91 | 181.45 | 0 | ARIMA(3,1,3) |
| season | autumn | 12 | 4370 | 36.309 | 45.59 | -0.24151 | 0.97974 | 0.72998 | 0.90435 | 98.855 | 151.19 | 163.22 | 230.16 | 0 | ARIMA(3,1,3) |
| overall | all | 24 | 17490 | 36.836 | 47.308 | -0.021452 | 0.89515 | 0.81212 | 0.94437 | 123.3 | 188.57 | 170.44 | 236.33 | 0 | ARIMA(3,1,3) |
| season | winter | 24 | 4321 | 39.631 | 51.002 | -0.26451 | 0.92017 | 0.80143 | 0.93798 | 131.1 | 200.5 | 184.33 | 252.71 | 0 | ARIMA(3,1,3) |
| season | spring | 24 | 4414 | 35.291 | 45.141 | 0.76753 | 0.78569 | 0.86679 | 0.97213 | 134.6 | 205.85 | 163.67 | 225.22 | 0 | ARIMA(3,1,3) |
| season | summer | 24 | 4385 | 32.133 | 40.4 | -0.21544 | 0.78847 | 0.85564 | 0.97241 | 117.15 | 179.16 | 144.18 | 194.32 | 0 | ARIMA(3,1,3) |
| season | autumn | 24 | 4370 | 40.355 | 51.858 | -0.38339 | 1.088 | 0.7238 | 0.89451 | 110.35 | 168.77 | 189.91 | 273.49 | 0 | ARIMA(3,1,3) |
| overall | all | 48 | 17490 | 42.257 | 54.397 | 0.06771 | 1.0271 | 0.82607 | 0.95495 | 149.9 | 229.26 | 198.11 | 268.15 | 0 | ARIMA(3,1,3) |
| season | winter | 48 | 4321 | 44.425 | 59.051 | -0.1233 | 1.0385 | 0.80815 | 0.94052 | 157.96 | 241.57 | 221.59 | 305.14 | 0 | ARIMA(3,1,3) |
| season | spring | 48 | 4414 | 43.636 | 55.524 | 1.0432 | 0.9707 | 0.84685 | 0.96738 | 160.85 | 245.99 | 200.81 | 263.83 | 0 | ARIMA(3,1,3) |
| season | summer | 48 | 4385 | 33.924 | 43.035 | -0.2425 | 0.83167 | 0.90308 | 0.99111 | 146.35 | 223.82 | 163.67 | 226.14 | 0 | ARIMA(3,1,3) |
| season | autumn | 48 | 4370 | 47.081 | 58.502 | -0.41741 | 1.2687 | 0.74554 | 0.92037 | 134.46 | 205.64 | 206.73 | 278.11 | 0 | ARIMA(3,1,3) |
| overall | all | 1 | 17490 | 7.1967 | 9.9722 | -0.013004 | 0.17463 | 0.83013 | 0.93636 | 24.714 | 37.796 | 36.399 | 56.557 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | winter | 1 | 4321 | 7.0972 | 10.017 | -0.058985 | 0.16388 | 0.84818 | 0.94585 | 25.627 | 39.193 | 36.629 | 58.197 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | spring | 1 | 4414 | 7.1302 | 9.8064 | 0.29959 | 0.15882 | 0.84504 | 0.93883 | 25.625 | 39.191 | 36.305 | 55.076 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | summer | 1 | 4385 | 7.0562 | 9.7918 | 0.23518 | 0.17347 | 0.83284 | 0.94253 | 24.013 | 36.724 | 35.163 | 54.482 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | autumn | 1 | 4370 | 7.5033 | 10.268 | -0.53231 | 0.20239 | 0.79451 | 0.91831 | 23.594 | 36.083 | 37.507 | 58.512 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| overall | all | 4 | 17490 | 15.202 | 20.762 | -0.035355 | 0.36929 | 0.74906 | 0.88491 | 41.797 | 63.924 | 76.888 | 126.95 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | winter | 4 | 4321 | 14.968 | 20.764 | -0.17128 | 0.3457 | 0.78408 | 0.90349 | 43.401 | 66.376 | 75.642 | 126.58 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | spring | 4 | 4414 | 14.759 | 20.293 | 0.81091 | 0.32866 | 0.77503 | 0.90009 | 43.469 | 66.48 | 74.681 | 120.73 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | summer | 4 | 4385 | 14.87 | 20.086 | 0.63985 | 0.36535 | 0.74139 | 0.8894 | 40.58 | 62.062 | 73.924 | 118.06 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | autumn | 4 | 4370 | 16.215 | 21.866 | -1.4333 | 0.43761 | 0.69588 | 0.84668 | 39.745 | 60.785 | 83.325 | 142.51 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| overall | all | 12 | 17490 | 28.098 | 36.189 | -0.082237 | 0.68217 | 0.66518 | 0.84202 | 66.283 | 101.37 | 137.29 | 219.93 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | winter | 12 | 4321 | 28.348 | 36.922 | -0.44428 | 0.65441 | 0.69035 | 0.84934 | 69.055 | 105.61 | 139.5 | 225.9 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | spring | 12 | 4414 | 27.369 | 35.633 | 2.1035 | 0.60982 | 0.69937 | 0.8686 | 69.565 | 106.39 | 132.66 | 207.46 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | summer | 12 | 4385 | 26.704 | 34.043 | 1.613 | 0.6558 | 0.66545 | 0.85063 | 64.28 | 98.308 | 127.01 | 192.44 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | autumn | 12 | 4370 | 29.984 | 38.056 | -3.6331 | 0.80914 | 0.60549 | 0.79931 | 62.236 | 95.182 | 150.1 | 254.22 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| overall | all | 24 | 17490 | 33.775 | 43.568 | -0.10011 | 0.81749 | 0.69949 | 0.87307 | 86.591 | 132.43 | 161.08 | 243.2 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | winter | 24 | 4321 | 36.713 | 46.842 | -0.7311 | 0.84837 | 0.68179 | 0.86369 | 90.604 | 138.57 | 174.33 | 262.09 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | spring | 24 | 4414 | 33.873 | 43.955 | 3.7954 | 0.75365 | 0.71772 | 0.88786 | 92.037 | 140.76 | 161.64 | 236.21 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | summer | 24 | 4385 | 29.261 | 37.064 | 2.947 | 0.71826 | 0.74413 | 0.92109 | 83.838 | 128.22 | 131.47 | 180.37 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | autumn | 24 | 4370 | 35.301 | 45.798 | -6.4685 | 0.951 | 0.65378 | 0.81922 | 79.883 | 122.17 | 177.12 | 294.62 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| overall | all | 48 | 17490 | 39.918 | 50.995 | 0.06119 | 0.96707 | 0.72561 | 0.89102 | 108.1 | 165.32 | 185.67 | 271.71 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | winter | 48 | 4321 | 41.789 | 53.512 | -0.8477 | 0.97154 | 0.73571 | 0.88868 | 113.82 | 174.07 | 195.78 | 287.52 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | spring | 48 | 4414 | 42.464 | 54.639 | 6.3761 | 0.94482 | 0.7295 | 0.88151 | 117.25 | 179.31 | 201.08 | 291.69 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | summer | 48 | 4385 | 32.844 | 41.421 | 5.2946 | 0.8059 | 0.79726 | 0.94116 | 104.38 | 159.63 | 146.87 | 197.92 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | autumn | 48 | 4370 | 42.595 | 53.287 | -10.67 | 1.1468 | 0.63982 | 0.85263 | 96.93 | 148.24 | 199.05 | 309.95 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| overall | all | 1 | 17490 | 7.3477 | 10.066 | -0.14809 | 0.17851 | 0.84111 | 0.93831 | 31.137 | 47.785 | 40.614 | 62.047 | 0 | AR(8,0,0)\[log1p\] |
| season | winter | 1 | 4321 | 7.3536 | 10.009 | -0.18714 | 0.16998 | 0.84494 | 0.94446 | 33.591 | 51.531 | 42.684 | 65.676 | 0 | AR(8,0,0)\[log1p\] |
| season | spring | 1 | 4414 | 7.0697 | 9.5946 | 0.67008 | 0.15758 | 0.82034 | 0.92478 | 28.011 | 42.977 | 37.972 | 57.711 | 0 | AR(8,0,0)\[log1p\] |
| season | summer | 1 | 4385 | 7.0938 | 10.093 | 0.73997 | 0.1744 | 0.80958 | 0.92406 | 25.731 | 39.502 | 37.042 | 57.704 | 0 | AR(8,0,0)\[log1p\] |
| season | autumn | 1 | 4370 | 7.8775 | 10.55 | -1.827 | 0.21222 | 0.88993 | 0.96018 | 37.291 | 57.249 | 44.82 | 67.195 | 0 | AR(8,0,0)\[log1p\] |
| overall | all | 4 | 17490 | 17.478 | 23.231 | -0.34486 | 0.42599 | 0.82396 | 0.9323 | 65.989 | 102.51 | 89.166 | 133.37 | 0 | AR(8,0,0)\[log1p\] |
| season | winter | 4 | 4321 | 17.198 | 23.023 | -0.35353 | 0.39859 | 0.8461 | 0.93728 | 72.294 | 112.16 | 94.667 | 146.37 | 0 | AR(8,0,0)\[log1p\] |
| season | spring | 4 | 4414 | 16.156 | 21.66 | 2.3043 | 0.36002 | 0.81128 | 0.92161 | 60.114 | 93.282 | 82.615 | 124.17 | 0 | AR(8,0,0)\[log1p\] |
| season | summer | 4 | 4385 | 16.753 | 22.364 | 2.3752 | 0.41177 | 0.7854 | 0.91859 | 54.585 | 84.834 | 80.079 | 117.96 | 0 | AR(8,0,0)\[log1p\] |
| season | autumn | 4 | 4370 | 19.819 | 25.692 | -5.7415 | 0.53399 | 0.85355 | 0.95195 | 77.132 | 120.04 | 99.462 | 145.26 | 0 | AR(8,0,0)\[log1p\] |
| overall | all | 12 | 17490 | 35.38 | 43.224 | -0.60839 | 0.86369 | 0.78559 | 0.94848 | 114.82 | 184.36 | 149.64 | 204.81 | 0 | AR(8,0,0)\[log1p\] |
| season | winter | 12 | 4321 | 35.643 | 43.739 | -0.42075 | 0.82921 | 0.8137 | 0.94631 | 127.51 | 204.15 | 160.84 | 223.8 | 0 | AR(8,0,0)\[log1p\] |
| season | spring | 12 | 4414 | 31.632 | 39.592 | 6.837 | 0.70539 | 0.78727 | 0.93294 | 109.64 | 175.57 | 144.57 | 204.75 | 0 | AR(8,0,0)\[log1p\] |
| season | summer | 12 | 4385 | 33.504 | 40.428 | 6.6548 | 0.82393 | 0.74755 | 0.93637 | 98.866 | 158.88 | 138.76 | 185.54 | 0 | AR(8,0,0)\[log1p\] |
| season | autumn | 12 | 4370 | 40.789 | 48.607 | -15.602 | 1.0976 | 0.79428 | 0.97849 | 123.53 | 199.25 | 154.59 | 205.42 | 0 | AR(8,0,0)\[log1p\] |
| overall | all | 24 | 17490 | 39.944 | 48.656 | -0.40452 | 0.97378 | 0.8227 | 0.97965 | 138.38 | 227.31 | 164.52 | 232.74 | 0 | AR(8,0,0)\[log1p\] |
| season | winter | 24 | 4321 | 45.06 | 53.805 | -0.45836 | 1.0524 | 0.79264 | 0.98727 | 155.25 | 254.34 | 181.91 | 257.56 | 0 | AR(8,0,0)\[log1p\] |
| season | spring | 24 | 4414 | 35.36 | 43.112 | 11.849 | 0.78628 | 0.84504 | 0.9633 | 141.81 | 233.22 | 162.69 | 243.96 | 0 | AR(8,0,0)\[log1p\] |
| season | summer | 24 | 4385 | 32.911 | 39.344 | 10.982 | 0.80986 | 0.85678 | 0.97446 | 123.78 | 203.66 | 138.04 | 208.37 | 0 | AR(8,0,0)\[log1p\] |
| season | autumn | 24 | 4370 | 46.574 | 56.41 | -24.154 | 1.2499 | 0.79565 | 0.99382 | 132.87 | 218.35 | 175.75 | 221.32 | 0 | AR(8,0,0)\[log1p\] |
| overall | all | 48 | 17490 | 45.454 | 54.889 | 0.77173 | 1.1058 | 0.81675 | 0.98336 | 152.79 | 254.95 | 187.05 | 258.84 | 0 | AR(8,0,0)\[log1p\] |
| season | winter | 48 | 4321 | 50.307 | 60.05 | -0.30547 | 1.1781 | 0.81995 | 0.99306 | 171.82 | 286.2 | 205.32 | 287.54 | 0 | AR(8,0,0)\[log1p\] |
| season | spring | 48 | 4414 | 43.54 | 51.659 | 17.965 | 0.96671 | 0.84232 | 0.96828 | 168.35 | 283.21 | 186.29 | 292.86 | 0 | AR(8,0,0)\[log1p\] |
| season | summer | 48 | 4385 | 36.877 | 42.893 | 15.657 | 0.90799 | 0.87845 | 0.97742 | 140.24 | 234.17 | 151.05 | 237.83 | 0 | AR(8,0,0)\[log1p\] |
| season | autumn | 48 | 4370 | 51.197 | 62.856 | -30.465 | 1.3733 | 0.72586 | 0.99497 | 130.84 | 216.35 | 205.9 | 217.2 | 0 | AR(8,0,0)\[log1p\] |
| overall | all | 1 | 17490 | 12.468 | 16.121 | -3.4673 | 0.30393 | 0.80389 | 0.94831 | 40.871 | 62.898 | 51.91 | 72.98 | 0 | MA(0,0,8)\[log1p\] |
| season | winter | 1 | 4321 | 14.001 | 17.865 | -4.5292 | 0.3253 | 0.80305 | 0.95024 | 45.165 | 69.479 | 56.468 | 78.51 | 0 | MA(0,0,8)\[log1p\] |
| season | spring | 1 | 4414 | 10.957 | 13.786 | 0.36521 | 0.24413 | 0.80652 | 0.9275 | 39.907 | 61.436 | 50.748 | 75.365 | 0 | MA(0,0,8)\[log1p\] |
| season | summer | 1 | 4385 | 9.7663 | 12.428 | 0.74218 | 0.24017 | 0.80593 | 0.93888 | 34.347 | 52.872 | 44.337 | 64.691 | 0 | MA(0,0,8)\[log1p\] |
| season | autumn | 1 | 4370 | 15.189 | 19.434 | -10.512 | 0.40719 | 0.8 | 0.97689 | 44.145 | 67.926 | 56.175 | 73.419 | 0 | MA(0,0,8)\[log1p\] |
| overall | all | 4 | 17490 | 35.647 | 44.135 | -6.725 | 0.86643 | 0.64231 | 0.88553 | 87.317 | 137.69 | 151.73 | 183.68 | 0 | MA(0,0,8)\[log1p\] |
| season | winter | 4 | 4321 | 41.172 | 50.118 | -9.8829 | 0.95734 | 0.61745 | 0.89308 | 97.434 | 153.56 | 169.91 | 199.01 | 0 | MA(0,0,8)\[log1p\] |
| season | spring | 4 | 4414 | 33.065 | 39.024 | 6.3153 | 0.73562 | 0.68668 | 0.87925 | 93.74 | 148.26 | 135.08 | 190.62 | 0 | MA(0,0,8)\[log1p\] |
| season | summer | 4 | 4385 | 26.991 | 32.392 | 5.8732 | 0.66428 | 0.69829 | 0.90832 | 77.55 | 122.28 | 111.15 | 146.86 | 0 | MA(0,0,8)\[log1p\] |
| season | autumn | 4 | 4370 | 41.476 | 52.165 | -29.416 | 1.1115 | 0.5659 | 0.86156 | 80.626 | 126.8 | 191.29 | 198.47 | 0 | MA(0,0,8)\[log1p\] |
| overall | all | 12 | 17490 | 50.174 | 60.593 | -6.507 | 1.2166 | 0.52819 | 0.78033 | 100.57 | 160.22 | 235.4 | 327.61 | 0 | MA(0,0,8)\[log1p\] |
| season | winter | 12 | 4321 | 57.989 | 68.829 | -10.708 | 1.3484 | 0.49526 | 0.76209 | 111.31 | 177.18 | 269.45 | 356.53 | 0 | MA(0,0,8)\[log1p\] |
| season | spring | 12 | 4414 | 48.866 | 56.774 | 12.762 | 1.0865 | 0.56389 | 0.80063 | 113.44 | 181.44 | 207.67 | 288.15 | 0 | MA(0,0,8)\[log1p\] |
| season | summer | 12 | 4385 | 38.4 | 44.897 | 10.711 | 0.94549 | 0.59042 | 0.83694 | 93.019 | 148.14 | 161.87 | 208.6 | 0 | MA(0,0,8)\[log1p\] |
| season | autumn | 12 | 4370 | 55.58 | 68.786 | -39.093 | 1.4898 | 0.46224 | 0.72105 | 84.533 | 134.13 | 303.53 | 458.27 | 0 | MA(0,0,8)\[log1p\] |
| overall | all | 24 | 17490 | 50.153 | 60.573 | -6.5154 | 1.2163 | 0.52882 | 0.78073 | 100.57 | 160.22 | 235.21 | 327.51 | 0 | MA(0,0,8)\[log1p\] |
| season | winter | 24 | 4321 | 57.901 | 68.745 | -10.807 | 1.3471 | 0.49549 | 0.76417 | 111.23 | 177.06 | 268.78 | 355.17 | 0 | MA(0,0,8)\[log1p\] |
| season | spring | 24 | 4414 | 48.852 | 56.76 | 12.808 | 1.0859 | 0.56479 | 0.80041 | 113.47 | 181.49 | 207.51 | 288.35 | 0 | MA(0,0,8)\[log1p\] |
| season | summer | 24 | 4385 | 38.399 | 44.894 | 10.762 | 0.94522 | 0.59179 | 0.83649 | 93.08 | 148.24 | 161.73 | 208.98 | 0 | MA(0,0,8)\[log1p\] |
| season | autumn | 24 | 4370 | 55.602 | 68.815 | -39.127 | 1.4907 | 0.46224 | 0.72128 | 84.51 | 134.09 | 303.74 | 458.64 | 0 | MA(0,0,8)\[log1p\] |
| overall | all | 48 | 17490 | 50.161 | 60.582 | -6.48 | 1.2168 | 0.52819 | 0.78107 | 100.57 | 160.22 | 235.28 | 327.75 | 0 | MA(0,0,8)\[log1p\] |
| season | winter | 48 | 4321 | 57.932 | 68.762 | -10.794 | 1.3493 | 0.49178 | 0.76232 | 111.09 | 176.83 | 269.1 | 354.44 | 0 | MA(0,0,8)\[log1p\] |
| season | spring | 48 | 4414 | 48.818 | 56.719 | 12.902 | 1.0847 | 0.56502 | 0.80131 | 113.54 | 181.59 | 207.29 | 288.44 | 0 | MA(0,0,8)\[log1p\] |
| season | summer | 48 | 4385 | 38.38 | 44.852 | 10.863 | 0.9443 | 0.5927 | 0.83808 | 93.201 | 148.44 | 161.39 | 208.64 | 0 | MA(0,0,8)\[log1p\] |
| season | autumn | 48 | 4370 | 55.653 | 68.89 | -39.194 | 1.4925 | 0.46224 | 0.72197 | 84.465 | 134.02 | 304.26 | 460.59 | 0 | MA(0,0,8)\[log1p\] |
| overall | all | 1 | 17490 | 7.7441 | 11.127 | -0.3136 | 0.18937 | 0.84191 | 0.93836 | 32.814 | 50.346 | 42.482 | 64.87 | 336 | ARMA(3,0,1)\[log1p\] |
| season | winter | 1 | 4321 | 7.3966 | 10.029 | -0.22062 | 0.17104 | 0.84633 | 0.94538 | 33.675 | 51.66 | 42.722 | 65.762 | 0 | ARMA(3,0,1)\[log1p\] |
| season | spring | 1 | 4414 | 7.0969 | 9.6221 | 0.68709 | 0.15819 | 0.81831 | 0.92343 | 28.088 | 43.096 | 38.08 | 57.871 | 0 | ARMA(3,0,1)\[log1p\] |
| season | summer | 1 | 4385 | 7.0936 | 10.106 | 0.78733 | 0.1744 | 0.81026 | 0.92383 | 25.792 | 39.595 | 37.134 | 57.859 | 0 | ARMA(3,0,1)\[log1p\] |
| season | autumn | 1 | 4370 | 9.3942 | 14.143 | -2.521 | 0.25403 | 0.89314 | 0.9611 | 43.781 | 67.158 | 52.058 | 78.093 | 336 | ARMA(3,0,1)\[log1p\] |
| overall | all | 4 | 17490 | 17.816 | 23.696 | -0.51251 | 0.43468 | 0.82441 | 0.93185 | 66.86 | 103.81 | 90.156 | 134.94 | 336 | ARMA(3,0,1)\[log1p\] |
| season | winter | 4 | 4321 | 17.442 | 23.243 | -0.45033 | 0.40437 | 0.84448 | 0.93751 | 72.276 | 112.14 | 94.72 | 146.3 | 0 | ARMA(3,0,1)\[log1p\] |
| season | spring | 4 | 4414 | 16.313 | 21.865 | 2.3663 | 0.36351 | 0.80788 | 0.92116 | 60.249 | 93.497 | 83.109 | 124.72 | 0 | ARMA(3,0,1)\[log1p\] |
| season | summer | 4 | 4385 | 16.879 | 22.557 | 2.5334 | 0.41489 | 0.78244 | 0.91608 | 54.741 | 85.08 | 80.751 | 119.07 | 0 | ARMA(3,0,1)\[log1p\] |
| season | autumn | 4 | 4370 | 20.643 | 26.826 | -6.5381 | 0.55638 | 0.86339 | 0.95286 | 80.342 | 124.78 | 102.2 | 149.95 | 336 | ARMA(3,0,1)\[log1p\] |
| overall | all | 12 | 17490 | 35.919 | 43.917 | -0.7599 | 0.87613 | 0.78027 | 0.9486 | 115.1 | 184.71 | 150.66 | 205.06 | 336 | ARMA(3,0,1)\[log1p\] |
| season | winter | 12 | 4321 | 36.359 | 44.591 | -0.63912 | 0.84623 | 0.80861 | 0.9477 | 128.03 | 205.11 | 161.1 | 224.19 | 0 | ARMA(3,0,1)\[log1p\] |
| season | spring | 12 | 4414 | 32.298 | 40.273 | 7.0231 | 0.72019 | 0.78478 | 0.93294 | 110.3 | 176.7 | 145.63 | 205.31 | 0 | ARMA(3,0,1)\[log1p\] |
| season | summer | 12 | 4385 | 34.264 | 41.161 | 7.0406 | 0.84261 | 0.73979 | 0.9366 | 99.524 | 160 | 140.32 | 186.35 | 0 | ARMA(3,0,1)\[log1p\] |
| season | autumn | 12 | 4370 | 40.801 | 49.141 | -16.568 | 1.0968 | 0.78833 | 0.97735 | 122.81 | 197.41 | 155.78 | 204.64 | 336 | ARMA(3,0,1)\[log1p\] |
| overall | all | 24 | 17490 | 40.602 | 49.46 | -0.36653 | 0.98986 | 0.81944 | 0.98142 | 139.44 | 229.19 | 166.91 | 233.71 | 336 | ARMA(3,0,1)\[log1p\] |
| season | winter | 24 | 4321 | 46.058 | 54.937 | -0.71191 | 1.0765 | 0.79357 | 0.9882 | 157.15 | 258.01 | 184.53 | 260.53 | 0 | ARMA(3,0,1)\[log1p\] |
| season | spring | 24 | 4414 | 35.766 | 43.322 | 12.306 | 0.79515 | 0.85002 | 0.96602 | 144.23 | 237.7 | 163.39 | 246.71 | 0 | ARMA(3,0,1)\[log1p\] |
| season | summer | 24 | 4385 | 33.28 | 39.611 | 11.616 | 0.81917 | 0.85633 | 0.97674 | 125.53 | 206.82 | 139.23 | 211.08 | 0 | ARMA(3,0,1)\[log1p\] |
| season | autumn | 24 | 4370 | 47.438 | 57.76 | -24.849 | 1.2721 | 0.77712 | 0.99497 | 131.05 | 214.54 | 180.8 | 216.76 | 336 | ARMA(3,0,1)\[log1p\] |
| overall | all | 48 | 17490 | 46.27 | 55.774 | 1.0433 | 1.1251 | 0.80766 | 0.9805 | 152.51 | 254.2 | 189.97 | 258.55 | 336 | ARMA(3,0,1)\[log1p\] |
| season | winter | 48 | 4321 | 51.857 | 61.558 | -0.66723 | 1.2141 | 0.81023 | 0.99121 | 171.4 | 285.51 | 207.47 | 287.07 | 0 | ARMA(3,0,1)\[log1p\] |
| season | spring | 48 | 4414 | 44.133 | 52.143 | 18.42 | 0.97968 | 0.84141 | 0.96715 | 169.45 | 285.23 | 186.82 | 294.63 | 0 | ARMA(3,0,1)\[log1p\] |
| season | summer | 48 | 4385 | 37.473 | 43.526 | 16.122 | 0.92278 | 0.86819 | 0.97514 | 140.31 | 234.12 | 151.96 | 238.26 | 0 | ARMA(3,0,1)\[log1p\] |
| season | autumn | 48 | 4370 | 51.732 | 63.687 | -29.948 | 1.3869 | 0.7103 | 0.98879 | 128.99 | 212.04 | 213.98 | 214.29 | 336 | ARMA(3,0,1)\[log1p\] |
| overall | all | 1 | 17490 | 7.3858 | 10.273 | 1.0427 | 0.17934 | 0.8422 | 0.93745 | 32.089 | 49.256 | 41.871 | 64.179 | 0 | ARIMA(2,1,1)\[log1p\] |
| season | winter | 1 | 4321 | 7.2752 | 10.036 | 1.0049 | 0.16768 | 0.84772 | 0.94353 | 34.499 | 52.93 | 43.796 | 67.462 | 0 | ARIMA(2,1,1)\[log1p\] |
| season | spring | 1 | 4414 | 7.2064 | 9.8237 | 0.927 | 0.16064 | 0.82397 | 0.92139 | 28.487 | 43.712 | 38.74 | 59.105 | 0 | ARIMA(2,1,1)\[log1p\] |
| season | summer | 1 | 4385 | 7.2222 | 10.509 | 0.95714 | 0.17755 | 0.80935 | 0.92497 | 26.306 | 40.397 | 38.298 | 60.2 | 0 | ARIMA(2,1,1)\[log1p\] |
| season | autumn | 1 | 4370 | 7.8406 | 10.701 | 1.2826 | 0.21155 | 0.8881 | 0.96018 | 39.146 | 60.111 | 46.716 | 70.052 | 0 | ARIMA(2,1,1)\[log1p\] |
| overall | all | 4 | 17490 | 18.069 | 24.689 | 3.7792 | 0.44034 | 0.82247 | 0.92744 | 71.018 | 110.49 | 96.491 | 146.88 | 0 | ARIMA(2,1,1)\[log1p\] |
| season | winter | 4 | 4321 | 17.314 | 23.707 | 3.7827 | 0.39961 | 0.84101 | 0.93543 | 77.042 | 119.66 | 101.19 | 158.45 | 0 | ARIMA(2,1,1)\[log1p\] |
| season | spring | 4 | 4414 | 16.855 | 23.025 | 3.2472 | 0.37578 | 0.81468 | 0.91776 | 62.384 | 96.89 | 87.158 | 133.49 | 0 | ARIMA(2,1,1)\[log1p\] |
| season | summer | 4 | 4385 | 17.699 | 24.512 | 3.2112 | 0.43498 | 0.78221 | 0.90969 | 57.287 | 89.174 | 86.984 | 132.32 | 0 | ARIMA(2,1,1)\[log1p\] |
| season | autumn | 4 | 4370 | 20.412 | 27.304 | 4.8831 | 0.55119 | 0.8524 | 0.94714 | 87.562 | 136.54 | 110.81 | 163.59 | 0 | ARIMA(2,1,1)\[log1p\] |
| overall | all | 12 | 17490 | 40.573 | 51.416 | 13.149 | 0.99148 | 0.80257 | 0.94328 | 146.38 | 239.16 | 187.48 | 274.27 | 0 | ARIMA(2,1,1)\[log1p\] |
| season | winter | 12 | 4321 | 38.75 | 49.252 | 13.45 | 0.89689 | 0.82319 | 0.94237 | 158.83 | 258.12 | 199.89 | 292.13 | 0 | ARIMA(2,1,1)\[log1p\] |
| season | spring | 12 | 4414 | 36.083 | 46.34 | 10.815 | 0.80544 | 0.79565 | 0.93543 | 125.51 | 203.21 | 166.86 | 242.29 | 0 | ARIMA(2,1,1)\[log1p\] |
| season | summer | 12 | 4385 | 39.938 | 50.148 | 10.429 | 0.98136 | 0.75439 | 0.92109 | 116.42 | 190.06 | 169.24 | 245.47 | 0 | ARIMA(2,1,1)\[log1p\] |
| season | autumn | 12 | 4370 | 47.546 | 59.069 | 17.939 | 1.2831 | 0.83753 | 0.97437 | 185.24 | 305.97 | 214.33 | 317.8 | 0 | ARIMA(2,1,1)\[log1p\] |
| overall | all | 24 | 17490 | 51.482 | 65.694 | 29.077 | 1.2579 | 0.90503 | 0.9932 | 228.77 | 402.09 | 246.33 | 406.34 | 0 | ARIMA(2,1,1)\[log1p\] |
| season | winter | 24 | 4321 | 56.506 | 69.837 | 29.912 | 1.3158 | 0.88405 | 0.99074 | 247.46 | 430.59 | 274.08 | 436.97 | 0 | ARIMA(2,1,1)\[log1p\] |
| season | spring | 24 | 4414 | 44.004 | 56.405 | 23.326 | 0.98021 | 0.8942 | 0.98822 | 193.31 | 332.81 | 211.45 | 341.35 | 0 | ARIMA(2,1,1)\[log1p\] |
| season | summer | 24 | 4385 | 43.189 | 55.4 | 22.59 | 1.0607 | 0.90513 | 0.99612 | 180.51 | 316.17 | 192.8 | 317.22 | 0 | ARIMA(2,1,1)\[log1p\] |
| season | autumn | 24 | 4370 | 62.389 | 78.464 | 40.569 | 1.679 | 0.93661 | 0.99771 | 294.54 | 530.11 | 307.85 | 531.11 | 0 | ARIMA(2,1,1)\[log1p\] |
| overall | all | 48 | 17490 | 80.008 | 102.65 | 67.117 | 1.9631 | 0.97376 | 0.9988 | 369.77 | 742.63 | 374.51 | 743.02 | 0 | ARIMA(2,1,1)\[log1p\] |
| season | winter | 48 | 4321 | 83.383 | 106.5 | 69.052 | 1.9524 | 0.97477 | 0.99977 | 397.25 | 784.1 | 403.03 | 784.35 | 0 | ARIMA(2,1,1)\[log1p\] |
| season | spring | 48 | 4414 | 68.962 | 89.147 | 51.694 | 1.5377 | 0.94812 | 0.99592 | 306.23 | 590.26 | 315.57 | 591.4 | 0 | ARIMA(2,1,1)\[log1p\] |
| season | summer | 48 | 4385 | 61.465 | 79.289 | 51.719 | 1.5077 | 0.98084 | 0.99954 | 289.91 | 577.02 | 291.91 | 577.18 | 0 | ARIMA(2,1,1)\[log1p\] |
| season | autumn | 48 | 4370 | 106.43 | 128.92 | 96.231 | 2.8601 | 0.99153 | 1 | 486.91 | 1021.7 | 488.73 | 1021.7 | 0 | ARIMA(2,1,1)\[log1p\] |
| overall | all | 1 | 17490 | 10.653 | 19.01 | 0.47823 | 0.25332 | 0.83042 | 0.9311 | 41.929 | 64.304 | 56.204 | 82.604 | 1344 | SARIMA(1,0,1)x(1,0,0,48)\[log1p\] |
| season | winter | 1 | 4321 | 13.027 | 24.446 | 0.37797 | 0.29597 | 0.83893 | 0.9308 | 52.342 | 80.186 | 70.488 | 105.19 | 672 | SARIMA(1,0,1)x(1,0,0,48)\[log1p\] |
| season | spring | 1 | 4414 | 10.572 | 18.69 | 0.85506 | 0.23268 | 0.8208 | 0.92524 | 40.919 | 62.752 | 54.695 | 80.297 | 336 | SARIMA(1,0,1)x(1,0,0,48)\[log1p\] |
| season | summer | 1 | 4385 | 10.698 | 19.191 | 0.59163 | 0.26062 | 0.79475 | 0.91494 | 35.569 | 54.557 | 51.663 | 73.317 | 336 | SARIMA(1,0,1)x(1,0,0,48)\[log1p\] |
| season | autumn | 1 | 4370 | 8.3404 | 11.534 | 0.082966 | 0.22468 | 0.86751 | 0.95355 | 39.036 | 59.947 | 48.16 | 71.924 | 0 | SARIMA(1,0,1)x(1,0,0,48)\[log1p\] |
| overall | all | 4 | 17490 | 18.565 | 27.039 | 1.2717 | 0.44736 | 0.76935 | 0.8964 | 62.062 | 95.739 | 94.965 | 147.86 | 1344 | SARIMA(1,0,1)x(1,0,0,48)\[log1p\] |
| season | winter | 4 | 4321 | 20.121 | 30.435 | 0.56684 | 0.46124 | 0.7894 | 0.89262 | 71.118 | 109.4 | 107.79 | 174.42 | 672 | SARIMA(1,0,1)x(1,0,0,48)\[log1p\] |
| season | spring | 4 | 4414 | 17.914 | 26.406 | 2.5638 | 0.39736 | 0.77254 | 0.89715 | 60.602 | 93.5 | 91.732 | 145.84 | 336 | SARIMA(1,0,1)x(1,0,0,48)\[log1p\] |
| season | summer | 4 | 4385 | 18.356 | 26.599 | 1.6381 | 0.44918 | 0.7268 | 0.87845 | 52.208 | 80.57 | 87.115 | 130.4 | 336 | SARIMA(1,0,1)x(1,0,0,48)\[log1p\] |
| season | autumn | 4 | 4370 | 17.892 | 24.412 | 0.2961 | 0.48232 | 0.78902 | 0.91739 | 64.472 | 99.718 | 93.428 | 141.15 | 0 | SARIMA(1,0,1)x(1,0,0,48)\[log1p\] |
| overall | all | 12 | 17490 | 31.657 | 42.798 | 3.4439 | 0.7665 | 0.7056 | 0.8677 | 91.673 | 143.46 | 154.07 | 237.47 | 1344 | SARIMA(1,0,1)x(1,0,0,48)\[log1p\] |
| season | winter | 12 | 4321 | 31.946 | 42.144 | 1.0152 | 0.73588 | 0.73178 | 0.86276 | 97.681 | 151.84 | 162.75 | 262.33 | 672 | SARIMA(1,0,1)x(1,0,0,48)\[log1p\] |
| season | spring | 12 | 4414 | 31.898 | 43.924 | 7.2724 | 0.71295 | 0.70616 | 0.85637 | 91.849 | 143.94 | 155.57 | 247.23 | 336 | SARIMA(1,0,1)x(1,0,0,48)\[log1p\] |
| season | summer | 12 | 4385 | 30.646 | 41.247 | 4.3299 | 0.75121 | 0.65656 | 0.85222 | 77.327 | 121.16 | 142.22 | 208.19 | 336 | SARIMA(1,0,1)x(1,0,0,48)\[log1p\] |
| season | autumn | 12 | 4370 | 32.143 | 43.803 | 1.0892 | 0.8662 | 0.72838 | 0.89954 | 99.949 | 157.08 | 155.85 | 232.41 | 0 | SARIMA(1,0,1)x(1,0,0,48)\[log1p\] |
| overall | all | 24 | 17490 | 39.526 | 53.485 | 6.6671 | 0.95509 | 0.72064 | 0.89194 | 117.49 | 187.09 | 184.3 | 271.2 | 1344 | SARIMA(1,0,1)x(1,0,0,48)\[log1p\] |
| season | winter | 24 | 4321 | 40.197 | 51.573 | 2.0089 | 0.92847 | 0.71835 | 0.88359 | 119.55 | 188.19 | 192.79 | 287.63 | 672 | SARIMA(1,0,1)x(1,0,0,48)\[log1p\] |
| season | spring | 24 | 4414 | 43.675 | 60.203 | 14.253 | 0.97856 | 0.69778 | 0.87041 | 122.85 | 196.5 | 200.41 | 307.27 | 336 | SARIMA(1,0,1)x(1,0,0,48)\[log1p\] |
| season | summer | 24 | 4385 | 34.568 | 46.227 | 7.9937 | 0.84752 | 0.7122 | 0.89304 | 99.8 | 159.28 | 155.06 | 217.06 | 336 | SARIMA(1,0,1)x(1,0,0,48)\[log1p\] |
| season | autumn | 24 | 4370 | 39.646 | 54.901 | 2.2794 | 1.0657 | 0.75446 | 0.92082 | 127.8 | 204.41 | 188.98 | 272.86 | 0 | SARIMA(1,0,1)x(1,0,0,48)\[log1p\] |
| overall | all | 48 | 17490 | 49.129 | 67.571 | 11.556 | 1.1868 | 0.75083 | 0.9076 | 147.95 | 241.86 | 218.54 | 324.53 | 1344 | SARIMA(1,0,1)x(1,0,0,48)\[log1p\] |
| season | winter | 48 | 4321 | 47.789 | 61.408 | 4.3832 | 1.1096 | 0.75283 | 0.90095 | 142.99 | 229.09 | 219.03 | 318.41 | 672 | SARIMA(1,0,1)x(1,0,0,48)\[log1p\] |
| season | spring | 48 | 4414 | 58.04 | 82.132 | 23.966 | 1.3 | 0.71477 | 0.87177 | 164.86 | 272.84 | 259.43 | 407.01 | 336 | SARIMA(1,0,1)x(1,0,0,48)\[log1p\] |
| season | summer | 48 | 4385 | 41.14 | 56.401 | 13.76 | 1.0081 | 0.76579 | 0.92018 | 127.27 | 208.76 | 176.5 | 251.13 | 336 | SARIMA(1,0,1)x(1,0,0,48)\[log1p\] |
| season | autumn | 48 | 4370 | 49.471 | 67.375 | 3.9037 | 1.3279 | 0.77025 | 0.93776 | 156.5 | 256.43 | 218.92 | 320.93 | 0 | SARIMA(1,0,1)x(1,0,0,48)\[log1p\] |
| overall | all | 1 | 17490 | 8.8888 | 12.582 | 0.00085763 | 0.21638 | 0.9996 | 1 | 140.99 | 215.62 | 141 | 215.62 | 0 | persistence |
| season | winter | 1 | 4321 | 8.3592 | 12.1 | -0.026846 | 0.19269 | 0.99977 | 1 | 148.2 | 226.66 | 148.21 | 226.66 | 0 | persistence |
| season | spring | 1 | 4414 | 8.4622 | 11.82 | 0.044404 | 0.18873 | 1 | 1 | 154.79 | 236.73 | 154.79 | 236.73 | 0 | persistence |
| season | summer | 1 | 4385 | 8.9503 | 12.602 | -0.0034208 | 0.21998 | 0.99932 | 1 | 137.22 | 209.85 | 137.23 | 209.85 | 0 | persistence |
| season | autumn | 1 | 4370 | 9.7817 | 13.724 | -0.011442 | 0.26412 | 0.99931 | 1 | 123.69 | 189.16 | 123.72 | 189.16 | 0 | persistence |
| overall | all | 4 | 17490 | 19.219 | 26.354 | -0.0030875 | 0.46867 | 0.97559 | 0.99851 | 140.99 | 215.62 | 144.11 | 216.1 | 0 | persistence |
| season | winter | 4 | 4321 | 17.766 | 25.06 | -0.076603 | 0.40969 | 0.98311 | 0.99931 | 148.18 | 226.63 | 151.01 | 226.95 | 0 | persistence |
| season | spring | 4 | 4414 | 17.903 | 24.52 | 0.11418 | 0.39946 | 0.99366 | 1 | 154.8 | 236.74 | 155.36 | 236.74 | 0 | persistence |
| season | summer | 4 | 4385 | 19.421 | 26.147 | -0.018472 | 0.47713 | 0.97742 | 0.99886 | 137.23 | 209.87 | 139.51 | 210.19 | 0 | persistence |
| season | autumn | 4 | 4370 | 21.783 | 29.42 | -0.03341 | 0.5884 | 0.94805 | 0.99588 | 123.69 | 189.16 | 130.54 | 190.45 | 0 | persistence |
| overall | all | 12 | 17490 | 35.72 | 45.604 | -0.01721 | 0.87173 | 0.86123 | 0.97439 | 140.99 | 215.62 | 169.6 | 232.04 | 0 | persistence |
| season | winter | 12 | 4321 | 34.23 | 44.569 | -0.18121 | 0.79059 | 0.89239 | 0.98149 | 148.13 | 226.54 | 170.43 | 236.77 | 0 | persistence |
| season | spring | 12 | 4414 | 32.321 | 41.827 | 0.32329 | 0.7212 | 0.92796 | 0.99343 | 154.83 | 236.79 | 167.81 | 239.6 | 0 | persistence |
| season | summer | 12 | 4385 | 35.057 | 44.332 | -0.11015 | 0.86099 | 0.87343 | 0.98039 | 137.25 | 209.91 | 161.76 | 221.18 | 0 | persistence |
| season | autumn | 12 | 4370 | 41.292 | 51.188 | -0.10572 | 1.1148 | 0.7508 | 0.94211 | 123.69 | 189.16 | 178.46 | 230.61 | 0 | persistence |
| overall | all | 24 | 17490 | 38.921 | 50.065 | -0.015723 | 0.94657 | 0.83951 | 0.957 | 140.98 | 215.62 | 182.81 | 256.26 | 0 | persistence |
| season | winter | 24 | 4321 | 42.769 | 54.578 | -0.28165 | 0.99155 | 0.81393 | 0.95279 | 148.04 | 226.41 | 196.29 | 263.97 | 0 | persistence |
| season | spring | 24 | 4414 | 35.415 | 45.791 | 0.62642 | 0.78834 | 0.90032 | 0.98799 | 154.87 | 236.85 | 175.26 | 245.6 | 0 | persistence |
| season | summer | 24 | 4385 | 34.14 | 42.746 | -0.084607 | 0.83788 | 0.89806 | 0.98221 | 137.29 | 209.97 | 157.23 | 221.39 | 0 | persistence |
| season | autumn | 24 | 4370 | 43.457 | 55.992 | -0.33227 | 1.171 | 0.74462 | 0.90458 | 123.69 | 189.16 | 202.77 | 294.4 | 0 | persistence |
| overall | all | 48 | 17490 | 41.262 | 54.018 | 0.10377 | 1.0002 | 0.81395 | 0.93899 | 140.98 | 215.62 | 197.69 | 272.56 | 0 | persistence |
| season | winter | 48 | 4321 | 43.511 | 57.956 | -0.15344 | 1.0124 | 0.80606 | 0.93057 | 147.88 | 226.16 | 216.78 | 304.12 | 0 | persistence |
| season | spring | 48 | 4414 | 43.732 | 56.831 | 0.87902 | 0.97303 | 0.82646 | 0.95016 | 154.95 | 236.98 | 205.76 | 266.61 | 0 | persistence |
| season | summer | 48 | 4385 | 33.346 | 43.248 | 0.12109 | 0.81773 | 0.87913 | 0.97628 | 137.38 | 210.11 | 162.16 | 221.15 | 0 | persistence |
| season | autumn | 48 | 4370 | 44.489 | 56.729 | -0.44233 | 1.1989 | 0.74371 | 0.89863 | 123.68 | 189.16 | 206.3 | 298.96 | 0 | persistence |
| overall | all | 1 | 17490 | 40.697 | 53.355 | 0.099257 | 0.9855 | 0.81761 | 0.94208 | 140.99 | 215.62 | 195.33 | 268.4 | 49 | daily\_naive |
| season | winter | 1 | 4321 | 43.077 | 57.312 | -0.26799 | 1 | 0.80629 | 0.93358 | 148.2 | 226.66 | 214.39 | 297.28 | 0 | daily\_naive |
| season | spring | 1 | 4414 | 43.212 | 56.204 | 0.87313 | 0.96122 | 0.82895 | 0.95242 | 154.79 | 236.73 | 203.55 | 263.84 | 0 | daily\_naive |
| season | summer | 1 | 4385 | 32.702 | 42.562 | 0.23216 | 0.80197 | 0.88712 | 0.97765 | 137.22 | 209.85 | 160.45 | 219.33 | 49 | daily\_naive |
| season | autumn | 1 | 4370 | 43.825 | 56.011 | -0.45263 | 1.1798 | 0.7476 | 0.90435 | 123.69 | 189.16 | 203.16 | 293.68 | 0 | daily\_naive |
| overall | all | 4 | 17490 | 40.716 | 53.362 | 0.12121 | 0.98618 | 0.81761 | 0.94191 | 140.99 | 215.62 | 195.38 | 268.58 | 52 | daily\_naive |
| season | winter | 4 | 4321 | 43.072 | 57.312 | -0.26336 | 1.0002 | 0.80653 | 0.93358 | 148.18 | 226.63 | 214.44 | 297.49 | 0 | daily\_naive |
| season | spring | 4 | 4414 | 43.212 | 56.204 | 0.87313 | 0.96135 | 0.82895 | 0.95197 | 154.8 | 236.74 | 203.6 | 263.98 | 0 | daily\_naive |
| season | summer | 4 | 4385 | 32.784 | 42.599 | 0.31517 | 0.80409 | 0.88689 | 0.97765 | 137.23 | 209.87 | 160.49 | 219.4 | 52 | daily\_naive |
| season | autumn | 4 | 4370 | 43.825 | 56.011 | -0.45263 | 1.1801 | 0.7476 | 0.90412 | 123.69 | 189.16 | 203.23 | 293.99 | 0 | daily\_naive |
| overall | all | 12 | 17490 | 40.752 | 53.388 | 0.15992 | 0.98744 | 0.81738 | 0.94174 | 140.99 | 215.62 | 195.48 | 268.94 | 60 | daily\_naive |
| season | winter | 12 | 4321 | 43.065 | 57.311 | -0.26961 | 1.0007 | 0.80653 | 0.93358 | 148.13 | 226.54 | 214.53 | 297.93 | 0 | daily\_naive |
| season | spring | 12 | 4414 | 43.212 | 56.204 | 0.87313 | 0.96156 | 0.82895 | 0.95197 | 154.83 | 236.79 | 203.69 | 264.24 | 0 | daily\_naive |
| season | summer | 12 | 4385 | 32.934 | 42.726 | 0.47571 | 0.80792 | 0.88575 | 0.97765 | 137.25 | 209.91 | 160.6 | 219.54 | 60 | daily\_naive |
| season | autumn | 12 | 4370 | 43.825 | 56.011 | -0.45263 | 1.1806 | 0.74783 | 0.90343 | 123.69 | 189.16 | 203.36 | 294.58 | 0 | daily\_naive |
| overall | all | 24 | 17490 | 40.775 | 53.413 | 0.14991 | 0.98824 | 0.81681 | 0.94128 | 140.98 | 215.62 | 195.63 | 269.18 | 72 | daily\_naive |
| season | winter | 24 | 4321 | 43.061 | 57.31 | -0.2791 | 1.0011 | 0.80583 | 0.93265 | 148.04 | 226.41 | 214.58 | 298.21 | 0 | daily\_naive |
| season | spring | 24 | 4414 | 43.212 | 56.204 | 0.87313 | 0.96164 | 0.82963 | 0.95197 | 154.87 | 236.85 | 203.78 | 264.43 | 0 | daily\_naive |
| season | summer | 24 | 4385 | 33.03 | 42.852 | 0.44515 | 0.81025 | 0.88347 | 0.97742 | 137.29 | 209.97 | 160.97 | 219.66 | 72 | daily\_naive |
| season | autumn | 24 | 4370 | 43.825 | 56.011 | -0.45263 | 1.181 | 0.74783 | 0.90275 | 123.69 | 189.16 | 203.44 | 294.98 | 0 | daily\_naive |
| overall | all | 48 | 17490 | 51.495 | 66.232 | 0.15758 | 1.2491 | 0.71269 | 0.88622 | 140.98 | 215.62 | 244.57 | 346.37 | 78 | daily\_naive |
| season | winter | 48 | 4321 | 59.464 | 76.67 | -0.46633 | 1.3934 | 0.66744 | 0.83962 | 147.88 | 226.16 | 296.56 | 454.16 | 0 | daily\_naive |
| season | spring | 48 | 4414 | 52.177 | 67.382 | 1.9594 | 1.1585 | 0.74218 | 0.91255 | 154.95 | 236.98 | 245.44 | 317.26 | 0 | daily\_naive |
| season | summer | 48 | 4385 | 38.086 | 48.253 | -0.71676 | 0.93249 | 0.84333 | 0.97628 | 137.38 | 210.11 | 170.43 | 227.5 | 78 | daily\_naive |
| season | autumn | 48 | 4370 | 56.382 | 69.441 | -0.16819 | 1.5157 | 0.59657 | 0.81533 | 123.68 | 189.16 | 266.66 | 388.46 | 0 | daily\_naive |
| overall | all | 1 | 17490 | 56.734 | 71.981 | -1.1718 | 1.3667 | 0.67444 | 0.86083 | 140.99 | 215.62 | 266.13 | 384.68 | 78 | weekly\_naive |
| season | winter | 1 | 4321 | 75 | 93.17 | -6.579 | 1.7353 | 0.56422 | 0.75607 | 148.2 | 226.66 | 378.97 | 630.57 | 0 | weekly\_naive |
| season | spring | 1 | 4414 | 58.229 | 71.892 | 5.886 | 1.2983 | 0.68147 | 0.89647 | 154.79 | 236.73 | 257.27 | 321.41 | 0 | weekly\_naive |
| season | summer | 1 | 4385 | 38.838 | 48.809 | -0.7683 | 0.95768 | 0.82965 | 0.96762 | 137.22 | 209.85 | 174.9 | 229.72 | 78 | weekly\_naive |
| season | autumn | 1 | 4370 | 55.119 | 67.399 | -3.3588 | 1.4819 | 0.62059 | 0.82128 | 123.69 | 189.16 | 255.06 | 360.95 | 0 | weekly\_naive |
| overall | all | 4 | 17490 | 56.76 | 71.99 | -1.1594 | 1.3674 | 0.67444 | 0.86095 | 140.99 | 215.62 | 266.14 | 384.73 | 78 | weekly\_naive |
| season | winter | 4 | 4321 | 74.999 | 93.17 | -6.573 | 1.7354 | 0.56422 | 0.75607 | 148.18 | 226.63 | 378.97 | 630.62 | 0 | weekly\_naive |
| season | spring | 4 | 4414 | 58.229 | 71.892 | 5.886 | 1.2983 | 0.68147 | 0.89669 | 154.8 | 236.74 | 257.28 | 321.45 | 0 | weekly\_naive |
| season | summer | 4 | 4385 | 38.942 | 48.859 | -0.72497 | 0.96014 | 0.82965 | 0.96762 | 137.23 | 209.87 | 174.91 | 229.72 | 78 | weekly\_naive |
| season | autumn | 4 | 4370 | 55.119 | 67.399 | -3.3588 | 1.4819 | 0.62059 | 0.82151 | 123.69 | 189.16 | 255.08 | 361.07 | 0 | weekly\_naive |
| overall | all | 12 | 17490 | 56.799 | 72.009 | -1.1371 | 1.3684 | 0.67444 | 0.86061 | 140.99 | 215.62 | 266.16 | 384.85 | 78 | weekly\_naive |
| season | winter | 12 | 4321 | 75.008 | 93.171 | -6.5536 | 1.7358 | 0.56422 | 0.75561 | 148.13 | 226.54 | 378.95 | 630.7 | 0 | weekly\_naive |
| season | spring | 12 | 4414 | 58.229 | 71.892 | 5.886 | 1.2982 | 0.68169 | 0.89647 | 154.83 | 236.79 | 257.31 | 321.54 | 0 | weekly\_naive |
| season | summer | 12 | 4385 | 39.089 | 48.97 | -0.65519 | 0.96357 | 0.82965 | 0.96762 | 137.25 | 209.91 | 174.92 | 229.75 | 78 | weekly\_naive |
| season | autumn | 12 | 4370 | 55.119 | 67.399 | -3.3588 | 1.4821 | 0.62037 | 0.82082 | 123.69 | 189.16 | 255.13 | 361.36 | 0 | weekly\_naive |
| overall | all | 24 | 17490 | 56.763 | 71.989 | -1.1194 | 1.3675 | 0.67456 | 0.86038 | 140.98 | 215.62 | 266.17 | 384.99 | 78 | weekly\_naive |
| season | winter | 24 | 4321 | 75.027 | 93.176 | -6.5054 | 1.7365 | 0.56422 | 0.75538 | 148.04 | 226.41 | 378.9 | 630.77 | 0 | weekly\_naive |
| season | spring | 24 | 4414 | 58.229 | 71.892 | 5.886 | 1.298 | 0.68169 | 0.89579 | 154.87 | 236.85 | 257.33 | 321.63 | 0 | weekly\_naive |
| season | summer | 24 | 4385 | 38.927 | 48.843 | -0.63193 | 0.95938 | 0.8301 | 0.96762 | 137.29 | 209.97 | 174.93 | 229.81 | 78 | weekly\_naive |
| season | autumn | 24 | 4370 | 55.119 | 67.399 | -3.3588 | 1.4823 | 0.62037 | 0.82082 | 123.69 | 189.16 | 255.2 | 361.68 | 0 | weekly\_naive |
| overall | all | 48 | 17490 | 56.771 | 71.985 | -1.0051 | 1.3678 | 0.67461 | 0.86066 | 140.98 | 215.62 | 266.17 | 385.16 | 78 | weekly\_naive |
| season | winter | 48 | 4321 | 74.976 | 93.141 | -6.1342 | 1.7363 | 0.56468 | 0.75538 | 147.88 | 226.16 | 378.79 | 630.9 | 0 | weekly\_naive |
| season | spring | 48 | 4414 | 58.229 | 71.892 | 5.886 | 1.2975 | 0.68192 | 0.89601 | 154.95 | 236.98 | 257.33 | 321.82 | 0 | weekly\_naive |
| season | summer | 48 | 4385 | 39.011 | 48.887 | -0.54208 | 0.96089 | 0.82965 | 0.9683 | 137.38 | 210.11 | 174.92 | 229.86 | 78 | weekly\_naive |
| season | autumn | 48 | 4370 | 55.119 | 67.399 | -3.3588 | 1.4827 | 0.62037 | 0.82105 | 123.68 | 189.16 | 255.3 | 361.98 | 0 | weekly\_naive |
| overall | all | 1 | 17490 | 47.501 | 57.705 | 1.7107 | 1.1482 | 0.77416 | 0.9446 | 140.99 | 215.62 | 197.02 | 264.26 | 0 | calendar\_mean |
| season | winter | 1 | 4321 | 55.297 | 65.159 | -1.2319 | 1.2834 | 0.71835 | 0.94423 | 148.2 | 226.66 | 216.93 | 288.86 | 0 | calendar\_mean |
| season | spring | 1 | 4414 | 49.555 | 58.591 | 23.023 | 1.1024 | 0.8097 | 0.97893 | 154.79 | 236.73 | 191.08 | 248.74 | 0 | calendar\_mean |
| season | summer | 1 | 4385 | 35.099 | 42.486 | 17.722 | 0.86561 | 0.89783 | 0.99521 | 137.22 | 209.85 | 150.92 | 210.64 | 0 | calendar\_mean |
| season | autumn | 1 | 4370 | 50.162 | 62.051 | -32.973 | 1.3443 | 0.66934 | 0.8595 | 123.69 | 189.16 | 229.59 | 309.4 | 0 | calendar\_mean |
| overall | all | 4 | 17490 | 47.497 | 57.702 | 1.707 | 1.1481 | 0.77416 | 0.9446 | 140.99 | 215.62 | 197.02 | 264.27 | 0 | calendar\_mean |
| season | winter | 4 | 4321 | 55.282 | 65.148 | -1.2466 | 1.2832 | 0.71835 | 0.94423 | 148.18 | 226.63 | 216.92 | 288.86 | 0 | calendar\_mean |
| season | spring | 4 | 4414 | 49.555 | 58.591 | 23.023 | 1.1023 | 0.8097 | 0.97893 | 154.8 | 236.74 | 191.08 | 248.72 | 0 | calendar\_mean |
| season | summer | 4 | 4385 | 35.099 | 42.486 | 17.722 | 0.86555 | 0.89783 | 0.99521 | 137.23 | 209.87 | 150.92 | 210.65 | 0 | calendar\_mean |
| season | autumn | 4 | 4370 | 50.162 | 62.051 | -32.973 | 1.3444 | 0.66934 | 0.8595 | 123.69 | 189.16 | 229.62 | 309.48 | 0 | calendar\_mean |
| overall | all | 12 | 17490 | 47.49 | 57.694 | 1.7 | 1.148 | 0.77427 | 0.94454 | 140.99 | 215.62 | 197.02 | 264.3 | 0 | calendar\_mean |
| season | winter | 12 | 4321 | 55.254 | 65.119 | -1.2749 | 1.283 | 0.71882 | 0.94423 | 148.13 | 226.54 | 216.85 | 288.82 | 0 | calendar\_mean |
| season | spring | 12 | 4414 | 49.555 | 58.591 | 23.023 | 1.1021 | 0.8097 | 0.97893 | 154.83 | 236.79 | 191.08 | 248.68 | 0 | calendar\_mean |
| season | summer | 12 | 4385 | 35.099 | 42.486 | 17.722 | 0.86537 | 0.89783 | 0.99521 | 137.25 | 209.91 | 150.92 | 210.69 | 0 | calendar\_mean |
| season | autumn | 12 | 4370 | 50.162 | 62.051 | -32.973 | 1.3445 | 0.66934 | 0.85927 | 123.69 | 189.16 | 229.66 | 309.64 | 0 | calendar\_mean |
| overall | all | 24 | 17490 | 47.468 | 57.658 | 1.6777 | 1.1476 | 0.77399 | 0.94477 | 140.98 | 215.62 | 196.87 | 264.33 | 0 | calendar\_mean |
| season | winter | 24 | 4321 | 55.164 | 64.988 | -1.3652 | 1.2818 | 0.71905 | 0.94469 | 148.04 | 226.41 | 216.19 | 288.72 | 0 | calendar\_mean |
| season | spring | 24 | 4414 | 49.555 | 58.591 | 23.023 | 1.1019 | 0.80879 | 0.97893 | 154.87 | 236.85 | 191.08 | 248.67 | 0 | calendar\_mean |
| season | summer | 24 | 4385 | 35.099 | 42.486 | 17.722 | 0.86508 | 0.89783 | 0.99521 | 137.29 | 209.97 | 150.93 | 210.75 | 0 | calendar\_mean |
| season | autumn | 24 | 4370 | 50.162 | 62.051 | -32.973 | 1.3447 | 0.66888 | 0.85973 | 123.69 | 189.16 | 229.71 | 309.8 | 0 | calendar\_mean |
| overall | all | 48 | 17490 | 47.483 | 57.674 | 1.6923 | 1.1482 | 0.77336 | 0.94443 | 140.98 | 215.62 | 197.04 | 264.46 | 0 | calendar\_mean |
| season | winter | 48 | 4321 | 55.223 | 65.046 | -1.3062 | 1.2849 | 0.7165 | 0.94353 | 147.88 | 226.16 | 216.72 | 288.82 | 0 | calendar\_mean |
| season | spring | 48 | 4414 | 49.555 | 58.591 | 23.023 | 1.1014 | 0.80947 | 0.97916 | 154.95 | 236.98 | 191.11 | 248.74 | 0 | calendar\_mean |
| season | summer | 48 | 4385 | 35.099 | 42.486 | 17.722 | 0.86455 | 0.89829 | 0.99521 | 137.38 | 210.11 | 150.97 | 210.87 | 0 | calendar\_mean |
| season | autumn | 48 | 4370 | 50.162 | 62.051 | -32.973 | 1.3451 | 0.66773 | 0.85927 | 123.68 | 189.16 | 229.78 | 310.03 | 0 | calendar\_mean |

Source CSV: `../artifacts/runs/d2dee2d358735d7d/validation/forecast_metrics.csv`.

## Appendix: complete locked-test metrics

| group\_type | group | horizon | n | mae | rmse | mean\_error | mase | coverage80 | coverage95 | width80 | width95 | interval\_score80 | interval\_score95 | fallback\_origins | model\_id |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| overall | all | 1 | 17473 | 6.7861 | 9.0526 | 0.031047 | 0.17344 | 0.83237 | 0.94471 | 23.619 | 36.122 | 32.943 | 48.248 | 0 | AR(7,0,0) |
| season | winter | 1 | 4273 | 6.6536 | 8.9299 | -0.41009 | 0.16693 | 0.85186 | 0.95366 | 24.222 | 37.044 | 32.579 | 48.35 | 0 | AR(7,0,0) |
| season | spring | 1 | 4414 | 6.9831 | 9.3183 | 0.48713 | 0.1613 | 0.82941 | 0.93702 | 24.103 | 36.863 | 34.138 | 49.707 | 0 | AR(7,0,0) |
| season | summer | 1 | 4416 | 6.6487 | 8.8431 | 0.29533 | 0.1703 | 0.8356 | 0.9486 | 23.377 | 35.753 | 32.199 | 46.763 | 0 | AR(7,0,0) |
| season | autumn | 1 | 4370 | 6.8556 | 9.1085 | -0.26535 | 0.19525 | 0.81304 | 0.93982 | 22.785 | 34.846 | 32.845 | 48.176 | 0 | AR(7,0,0) |
| overall | all | 4 | 17473 | 16.813 | 21.994 | 0.14098 | 0.4293 | 0.82459 | 0.94328 | 57.418 | 87.813 | 79.877 | 113.15 | 0 | AR(7,0,0) |
| season | winter | 4 | 4273 | 16.312 | 21.529 | -1.5093 | 0.40887 | 0.84835 | 0.94968 | 58.055 | 88.787 | 78.793 | 114.63 | 0 | AR(7,0,0) |
| season | spring | 4 | 4414 | 18.072 | 23.562 | 1.8406 | 0.41726 | 0.80245 | 0.92932 | 59.102 | 90.388 | 85.749 | 119.33 | 0 | AR(7,0,0) |
| season | summer | 4 | 4416 | 15.678 | 20.328 | 1.1333 | 0.40146 | 0.84647 | 0.96286 | 57.696 | 88.239 | 74.151 | 101.96 | 0 | AR(7,0,0) |
| season | autumn | 4 | 4370 | 17.177 | 22.421 | -0.96498 | 0.48959 | 0.8016 | 0.93135 | 54.813 | 83.83 | 80.792 | 116.76 | 0 | AR(7,0,0) |
| overall | all | 12 | 17473 | 35.448 | 43.002 | 0.54323 | 0.90508 | 0.7986 | 0.96223 | 111.49 | 170.51 | 147.23 | 188.81 | 0 | AR(7,0,0) |
| season | winter | 12 | 4273 | 34.698 | 42.301 | -4.7522 | 0.87 | 0.80248 | 0.967 | 111.04 | 169.82 | 144.51 | 186.02 | 0 | AR(7,0,0) |
| season | spring | 12 | 4414 | 38.361 | 46.364 | 5.9714 | 0.88582 | 0.77435 | 0.95696 | 115.48 | 176.62 | 158.44 | 198.97 | 0 | AR(7,0,0) |
| season | summer | 12 | 4416 | 32.452 | 39.351 | 3.7647 | 0.82974 | 0.84488 | 0.98483 | 113.58 | 173.71 | 135.41 | 180.62 | 0 | AR(7,0,0) |
| season | autumn | 12 | 4370 | 36.265 | 43.682 | -3.0171 | 1.035 | 0.77254 | 0.94005 | 105.78 | 161.77 | 150.51 | 189.56 | 0 | AR(7,0,0) |
| overall | all | 24 | 17473 | 40.239 | 47.944 | 0.98733 | 1.0338 | 0.83912 | 0.98026 | 134.79 | 206.15 | 161.75 | 216.4 | 0 | AR(7,0,0) |
| season | winter | 24 | 4273 | 43.092 | 51.04 | -8.123 | 1.0829 | 0.7992 | 0.98409 | 136.78 | 209.18 | 168.48 | 216.88 | 0 | AR(7,0,0) |
| season | spring | 24 | 4414 | 38.247 | 45.719 | 10.14 | 0.88367 | 0.89261 | 0.99524 | 142.73 | 218.29 | 157.36 | 219.72 | 0 | AR(7,0,0) |
| season | summer | 24 | 4416 | 35.334 | 42.23 | 6.392 | 0.90302 | 0.90104 | 0.99706 | 134.96 | 206.4 | 146.59 | 208.04 | 0 | AR(7,0,0) |
| season | autumn | 24 | 4370 | 44.418 | 52.25 | -4.8111 | 1.2695 | 0.76156 | 0.94439 | 124.67 | 190.66 | 174.92 | 221.04 | 0 | AR(7,0,0) |
| overall | all | 48 | 17473 | 45.037 | 53.314 | 1.6689 | 1.1568 | 0.84559 | 0.97568 | 146.7 | 224.35 | 176.86 | 244.55 | 0 | AR(7,0,0) |
| season | winter | 48 | 4273 | 47.151 | 55.829 | -12.084 | 1.1819 | 0.82518 | 0.99251 | 151.39 | 231.53 | 182.83 | 233.13 | 0 | AR(7,0,0) |
| season | spring | 48 | 4414 | 43.481 | 51.404 | 14.814 | 1.0043 | 0.88604 | 0.99887 | 158.69 | 242.69 | 171.51 | 242.77 | 0 | AR(7,0,0) |
| season | summer | 48 | 4416 | 38.638 | 45.137 | 9.5285 | 0.98642 | 0.92437 | 0.99909 | 144.73 | 221.35 | 152.4 | 221.57 | 0 | AR(7,0,0) |
| season | autumn | 48 | 4370 | 51.006 | 59.911 | -6.103 | 1.4585 | 0.74508 | 0.91213 | 131.98 | 201.85 | 201.14 | 280.73 | 0 | AR(7,0,0) |
| overall | all | 1 | 17473 | 12.069 | 15.802 | -2.6655 | 0.31115 | 0.80707 | 0.94185 | 39.908 | 61.329 | 50.765 | 71.629 | 336 | MA(0,0,8)\[log1p\] |
| season | winter | 1 | 4273 | 13.498 | 16.998 | -6.5543 | 0.33729 | 0.83127 | 0.95717 | 43.575 | 67.006 | 52.533 | 74.28 | 0 | MA(0,0,8)\[log1p\] |
| season | spring | 1 | 4414 | 10.317 | 12.952 | 0.080259 | 0.23822 | 0.81763 | 0.92478 | 38.101 | 58.553 | 48.832 | 73.19 | 0 | MA(0,0,8)\[log1p\] |
| season | summer | 1 | 4416 | 11.44 | 16.131 | 0.55103 | 0.29612 | 0.82563 | 0.94226 | 41.352 | 63.49 | 51.898 | 74.171 | 336 | MA(0,0,8)\[log1p\] |
| season | autumn | 1 | 4370 | 13.074 | 16.838 | -4.8867 | 0.37446 | 0.754 | 0.94371 | 36.69 | 56.398 | 49.846 | 64.891 | 0 | MA(0,0,8)\[log1p\] |
| overall | all | 4 | 17473 | 34.715 | 42.481 | -4.9436 | 0.89152 | 0.64202 | 0.88645 | 85.979 | 134.96 | 145.27 | 176.68 | 336 | MA(0,0,8)\[log1p\] |
| season | winter | 4 | 4273 | 39.583 | 48.312 | -17.611 | 0.98846 | 0.60098 | 0.91832 | 90.643 | 142.6 | 160.79 | 163.89 | 0 | MA(0,0,8)\[log1p\] |
| season | spring | 4 | 4414 | 32.485 | 38.51 | 4.6477 | 0.75012 | 0.69189 | 0.87381 | 91.817 | 144.21 | 134.78 | 192.3 | 0 | MA(0,0,8)\[log1p\] |
| season | summer | 4 | 4416 | 28.362 | 33.935 | 4.2461 | 0.72638 | 0.73279 | 0.91418 | 84.262 | 131.92 | 116 | 158.56 | 336 | MA(0,0,8)\[log1p\] |
| season | autumn | 4 | 4370 | 38.627 | 47.663 | -11.532 | 1.1064 | 0.54005 | 0.84005 | 77.258 | 121.22 | 170.27 | 191.74 | 0 | MA(0,0,8)\[log1p\] |
| overall | all | 12 | 17473 | 48.979 | 58.612 | -4.271 | 1.2557 | 0.52275 | 0.7804 | 99.085 | 156.9 | 226.87 | 307.51 | 336 | MA(0,0,8)\[log1p\] |
| season | winter | 12 | 4273 | 54.889 | 65.855 | -22.588 | 1.3709 | 0.48631 | 0.7751 | 100.25 | 159.2 | 263.57 | 309.65 | 0 | MA(0,0,8)\[log1p\] |
| season | spring | 12 | 4414 | 47.393 | 55.459 | 9.8235 | 1.0946 | 0.5734 | 0.79973 | 109.62 | 173.69 | 205.01 | 292.89 | 0 | MA(0,0,8)\[log1p\] |
| season | summer | 12 | 4416 | 40.032 | 46.923 | 8.0472 | 1.0224 | 0.61889 | 0.85643 | 98.855 | 156.11 | 166.87 | 220.6 | 336 | MA(0,0,8)\[log1p\] |
| season | autumn | 12 | 4370 | 53.844 | 64.526 | -13.045 | 1.5415 | 0.41007 | 0.68924 | 87.535 | 138.5 | 273.71 | 408.01 | 0 | MA(0,0,8)\[log1p\] |
| overall | all | 24 | 17473 | 48.967 | 58.629 | -4.3343 | 1.2554 | 0.52281 | 0.78063 | 99.085 | 156.9 | 226.99 | 307.72 | 336 | MA(0,0,8)\[log1p\] |
| season | winter | 24 | 4273 | 54.707 | 65.774 | -22.876 | 1.3666 | 0.48888 | 0.77791 | 100.2 | 159.12 | 263.01 | 308.94 | 0 | MA(0,0,8)\[log1p\] |
| season | spring | 24 | 4414 | 47.411 | 55.474 | 9.8399 | 1.095 | 0.57295 | 0.7995 | 109.63 | 173.71 | 205.07 | 292.97 | 0 | MA(0,0,8)\[log1p\] |
| season | summer | 24 | 4416 | 40.113 | 47.044 | 8.0531 | 1.0243 | 0.61685 | 0.85507 | 98.898 | 156.18 | 167.54 | 221.05 | 336 | MA(0,0,8)\[log1p\] |
| season | autumn | 24 | 4370 | 53.872 | 64.568 | -13.039 | 1.5422 | 0.4103 | 0.68902 | 87.531 | 138.49 | 274 | 409.02 | 0 | MA(0,0,8)\[log1p\] |
| overall | all | 48 | 17473 | 49.06 | 58.675 | -4.3837 | 1.2579 | 0.52372 | 0.78092 | 99.085 | 156.9 | 227.03 | 308.75 | 336 | MA(0,0,8)\[log1p\] |
| season | winter | 48 | 4273 | 54.621 | 65.796 | -23.254 | 1.3651 | 0.49099 | 0.77744 | 100.1 | 158.96 | 263.34 | 311.34 | 0 | MA(0,0,8)\[log1p\] |
| season | spring | 48 | 4414 | 47.431 | 55.495 | 9.8727 | 1.0953 | 0.57272 | 0.79882 | 109.65 | 173.74 | 205.17 | 293.51 | 0 | MA(0,0,8)\[log1p\] |
| season | summer | 48 | 4416 | 40.497 | 47.135 | 8.1788 | 1.0341 | 0.61911 | 0.85824 | 98.985 | 156.32 | 166.75 | 220.45 | 336 | MA(0,0,8)\[log1p\] |
| season | autumn | 48 | 4370 | 53.921 | 64.628 | -13.027 | 1.5432 | 0.40984 | 0.6881 | 87.523 | 138.48 | 274.5 | 410.83 | 0 | MA(0,0,8)\[log1p\] |
| overall | all | 1 | 17473 | 7.3242 | 10.984 | 0.19237 | 0.18807 | 0.83506 | 0.94649 | 25.612 | 39.17 | 35.446 | 51.759 | 336 | ARMA(3,0,2) |
| season | winter | 1 | 4273 | 8.8896 | 15.521 | 0.62928 | 0.22685 | 0.85912 | 0.9539 | 32.317 | 49.424 | 43.58 | 64.82 | 336 | ARMA(3,0,2) |
| season | spring | 1 | 4414 | 6.8583 | 9.1111 | 0.34881 | 0.15842 | 0.83394 | 0.9411 | 23.964 | 36.65 | 33.339 | 48.227 | 0 | ARMA(3,0,2) |
| season | summer | 1 | 4416 | 6.6117 | 8.7421 | 0.1222 | 0.16941 | 0.83741 | 0.95018 | 23.18 | 35.451 | 31.695 | 45.919 | 0 | ARMA(3,0,2) |
| season | autumn | 1 | 4370 | 6.9841 | 9.2619 | -0.32196 | 0.19895 | 0.8103 | 0.94096 | 23.178 | 35.448 | 33.411 | 48.456 | 0 | ARMA(3,0,2) |
| overall | all | 4 | 17473 | 17.102 | 22.523 | 0.13897 | 0.43839 | 0.82087 | 0.94117 | 57.32 | 87.664 | 80.667 | 114.07 | 336 | ARMA(3,0,2) |
| season | winter | 4 | 4273 | 17.788 | 24.31 | -0.070317 | 0.44877 | 0.84929 | 0.94688 | 62.341 | 95.342 | 85.33 | 125.03 | 336 | ARMA(3,0,2) |
| season | spring | 4 | 4414 | 17.262 | 22.459 | 1.2895 | 0.39859 | 0.81219 | 0.93679 | 57.396 | 87.78 | 81.447 | 112.64 | 0 | ARMA(3,0,2) |
| season | summer | 4 | 4416 | 15.486 | 19.955 | 0.45759 | 0.39689 | 0.84669 | 0.95969 | 55.616 | 85.057 | 72.338 | 99.547 | 0 | ARMA(3,0,2) |
| season | autumn | 4 | 4370 | 17.901 | 23.208 | -1.1405 | 0.51036 | 0.77574 | 0.92128 | 54.057 | 82.673 | 83.735 | 119.47 | 0 | ARMA(3,0,2) |
| overall | all | 12 | 17473 | 35.046 | 43.009 | -0.065846 | 0.90053 | 0.7891 | 0.94987 | 108.46 | 165.87 | 149.12 | 193.14 | 336 | ARMA(3,0,2) |
| season | winter | 12 | 4273 | 33.71 | 41.79 | -2.1745 | 0.84735 | 0.81676 | 0.956 | 109.18 | 166.98 | 145.59 | 195.44 | 336 | ARMA(3,0,2) |
| season | spring | 12 | 4414 | 35.198 | 43.272 | 4.0787 | 0.81272 | 0.77934 | 0.95605 | 109.64 | 167.67 | 149.94 | 191.23 | 0 | ARMA(3,0,2) |
| season | summer | 12 | 4416 | 31.767 | 39.055 | 1.3727 | 0.81458 | 0.83333 | 0.97237 | 107.52 | 164.43 | 135.66 | 178.29 | 0 | ARMA(3,0,2) |
| season | autumn | 12 | 4370 | 39.513 | 47.496 | -3.6439 | 1.1281 | 0.72723 | 0.91487 | 107.51 | 164.43 | 165.36 | 207.81 | 0 | ARMA(3,0,2) |
| overall | all | 24 | 17473 | 40.165 | 48.89 | -0.42918 | 1.0385 | 0.80782 | 0.95736 | 125.35 | 191.7 | 165.88 | 222.46 | 336 | ARMA(3,0,2) |
| season | winter | 24 | 4273 | 39.759 | 48.41 | -3.8897 | 1.0018 | 0.81559 | 0.96068 | 125.78 | 192.36 | 165.17 | 226.99 | 336 | ARMA(3,0,2) |
| season | spring | 24 | 4414 | 36.637 | 45.093 | 6.1583 | 0.84609 | 0.82465 | 0.97032 | 125.02 | 191.2 | 156.78 | 203.99 | 0 | ARMA(3,0,2) |
| season | summer | 24 | 4416 | 34.714 | 42.419 | 1.7293 | 0.88948 | 0.84534 | 0.97826 | 120.9 | 184.9 | 146.74 | 196.15 | 0 | ARMA(3,0,2) |
| season | autumn | 24 | 4370 | 49.635 | 58.253 | -5.8805 | 1.4194 | 0.74531 | 0.91991 | 129.76 | 198.44 | 195.13 | 263.29 | 0 | ARMA(3,0,2) |
| overall | all | 48 | 17473 | 43.963 | 52.718 | 0.30027 | 1.1355 | 0.81972 | 0.96314 | 136.72 | 209.09 | 176.04 | 242.56 | 336 | ARMA(3,0,2) |
| season | winter | 48 | 4273 | 45.02 | 53.026 | -6.047 | 1.1341 | 0.81512 | 0.97192 | 138.06 | 211.15 | 173.82 | 229.07 | 336 | ARMA(3,0,2) |
| season | spring | 48 | 4414 | 40.871 | 49.346 | 9.5556 | 0.9434 | 0.85433 | 0.98256 | 142.43 | 217.82 | 166.96 | 225.86 | 0 | ARMA(3,0,2) |
| season | summer | 48 | 4416 | 36.263 | 43.241 | 4.0907 | 0.92881 | 0.89697 | 0.99321 | 133.41 | 204.03 | 148.4 | 205.78 | 0 | ARMA(3,0,2) |
| season | autumn | 48 | 4370 | 53.836 | 63.355 | -6.6721 | 1.5398 | 0.71121 | 0.90458 | 132.97 | 203.36 | 215.32 | 309.78 | 0 | ARMA(3,0,2) |
| overall | all | 1 | 17473 | 7.3873 | 11.192 | 0.21802 | 0.18843 | 0.8342 | 0.94637 | 25.54 | 39.059 | 35.176 | 50.804 | 336 | ARIMA(3,1,3) |
| season | winter | 1 | 4273 | 6.7121 | 8.9502 | -0.089392 | 0.16857 | 0.85256 | 0.95343 | 24.147 | 36.929 | 32.544 | 48.076 | 0 | ARIMA(3,1,3) |
| season | spring | 1 | 4414 | 6.8906 | 9.1651 | 0.044851 | 0.15917 | 0.83394 | 0.94314 | 24.13 | 36.903 | 33.552 | 48.496 | 0 | ARIMA(3,1,3) |
| season | summer | 1 | 4416 | 9.1174 | 15.934 | 0.91633 | 0.23173 | 0.83696 | 0.95041 | 31.411 | 48.039 | 42.036 | 59.155 | 336 | ARIMA(3,1,3) |
| season | autumn | 1 | 4370 | 6.8008 | 9.007 | -0.012126 | 0.19364 | 0.81373 | 0.93867 | 22.392 | 34.246 | 32.46 | 47.363 | 0 | ARIMA(3,1,3) |
| overall | all | 4 | 17473 | 16.854 | 22.403 | 0.16641 | 0.43 | 0.82155 | 0.94134 | 57.126 | 87.367 | 79.929 | 113.29 | 336 | ARIMA(3,1,3) |
| season | winter | 4 | 4273 | 16.453 | 21.593 | -0.31735 | 0.41333 | 0.83501 | 0.94571 | 56.652 | 86.642 | 78.221 | 113.55 | 0 | ARIMA(3,1,3) |
| season | spring | 4 | 4414 | 17.364 | 22.755 | 0.15986 | 0.40095 | 0.8097 | 0.93226 | 57.794 | 88.388 | 83.023 | 115.41 | 0 | ARIMA(3,1,3) |
| season | summer | 4 | 4416 | 17.16 | 23.434 | 0.84007 | 0.43796 | 0.84601 | 0.95856 | 61.406 | 93.913 | 79.547 | 109.67 | 336 | ARIMA(3,1,3) |
| season | autumn | 4 | 4370 | 16.42 | 21.745 | -0.034689 | 0.46761 | 0.79565 | 0.92883 | 52.591 | 80.431 | 78.86 | 114.54 | 0 | ARIMA(3,1,3) |
| overall | all | 12 | 17473 | 32.86 | 41.945 | 0.016147 | 0.83707 | 0.80032 | 0.94477 | 107.47 | 164.37 | 149.25 | 200.85 | 336 | ARIMA(3,1,3) |
| season | winter | 12 | 4273 | 33.655 | 42.554 | -0.99191 | 0.84704 | 0.79546 | 0.94243 | 107.04 | 163.71 | 150.29 | 202.98 | 0 | ARIMA(3,1,3) |
| season | spring | 12 | 4414 | 35.608 | 44.833 | 0.54896 | 0.82208 | 0.78342 | 0.94517 | 112.59 | 172.2 | 157.47 | 205.54 | 0 | ARIMA(3,1,3) |
| season | summer | 12 | 4416 | 31.394 | 39.702 | 0.61985 | 0.80236 | 0.83877 | 0.96399 | 110.04 | 168.3 | 140.68 | 188.7 | 336 | ARIMA(3,1,3) |
| season | autumn | 12 | 4370 | 30.79 | 40.509 | -0.1464 | 0.87752 | 0.7833 | 0.92723 | 100.13 | 153.14 | 148.59 | 206.29 | 0 | ARIMA(3,1,3) |
| overall | all | 24 | 17473 | 36.749 | 47.141 | -0.10812 | 0.9388 | 0.8037 | 0.94368 | 122.1 | 186.74 | 169.63 | 232 | 336 | ARIMA(3,1,3) |
| season | winter | 24 | 4273 | 39.619 | 50.535 | -1.4582 | 0.99989 | 0.77744 | 0.92839 | 122.97 | 188.06 | 181.74 | 248.83 | 0 | ARIMA(3,1,3) |
| season | spring | 24 | 4414 | 37.325 | 47.574 | 0.8587 | 0.86182 | 0.81468 | 0.9599 | 131.14 | 200.57 | 170.74 | 223.96 | 0 | ARIMA(3,1,3) |
| season | summer | 24 | 4416 | 34.885 | 43.551 | 0.3961 | 0.89112 | 0.84511 | 0.97034 | 122.68 | 187.62 | 153.44 | 207.9 | 336 | ARIMA(3,1,3) |
| season | autumn | 24 | 4370 | 35.244 | 46.751 | -0.27408 | 1.005 | 0.77643 | 0.91533 | 111.54 | 170.59 | 173.03 | 248.01 | 0 | ARIMA(3,1,3) |
| overall | all | 48 | 17473 | 41.067 | 52.33 | -0.013773 | 1.0502 | 0.84067 | 0.96183 | 149.79 | 229.08 | 190.18 | 254.81 | 336 | ARIMA(3,1,3) |
| season | winter | 48 | 4273 | 43.799 | 55.617 | -2.4662 | 1.1047 | 0.80108 | 0.94992 | 147.29 | 225.26 | 198.92 | 258.48 | 0 | ARIMA(3,1,3) |
| season | spring | 48 | 4414 | 43.155 | 54.047 | 1.3609 | 0.99567 | 0.86747 | 0.97304 | 160.11 | 244.87 | 193.91 | 264.31 | 0 | ARIMA(3,1,3) |
| season | summer | 48 | 4416 | 34.64 | 44.207 | 1.2746 | 0.88321 | 0.90149 | 0.98596 | 152.03 | 232.51 | 171.64 | 237.09 | 336 | ARIMA(3,1,3) |
| season | autumn | 48 | 4370 | 42.78 | 54.766 | -0.30615 | 1.2207 | 0.79085 | 0.93776 | 139.55 | 213.43 | 196.58 | 259.51 | 0 | ARIMA(3,1,3) |
| overall | all | 1 | 17473 | 6.8995 | 9.317 | 0.0087205 | 0.1762 | 0.81549 | 0.93207 | 22.991 | 35.162 | 34.003 | 51.053 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | winter | 1 | 4273 | 6.6902 | 9.1897 | -0.20809 | 0.16809 | 0.83946 | 0.93985 | 23.4 | 35.788 | 33.748 | 51.828 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | spring | 1 | 4414 | 7.2319 | 9.7048 | 0.22871 | 0.16704 | 0.80449 | 0.92456 | 23.407 | 35.797 | 35.372 | 52.441 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | summer | 1 | 4416 | 6.7555 | 8.8637 | 0.11302 | 0.17281 | 0.81861 | 0.94135 | 22.809 | 34.883 | 32.083 | 46.175 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | autumn | 1 | 4370 | 6.9139 | 9.4863 | -0.10688 | 0.19679 | 0.8 | 0.92265 | 22.355 | 34.189 | 34.808 | 53.821 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| overall | all | 4 | 17473 | 14.79 | 19.945 | 0.026226 | 0.37717 | 0.72809 | 0.87083 | 39.066 | 59.746 | 74.661 | 122.52 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | winter | 4 | 4273 | 14.355 | 19.689 | -0.57041 | 0.36065 | 0.75989 | 0.88182 | 39.775 | 60.831 | 73.461 | 123.4 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | spring | 4 | 4414 | 16.108 | 21.339 | 0.62468 | 0.37197 | 0.69325 | 0.84912 | 39.891 | 61.008 | 81.014 | 132.37 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | summer | 4 | 4416 | 13.99 | 18.214 | 0.306 | 0.35769 | 0.74004 | 0.89017 | 38.743 | 59.253 | 66.793 | 99.483 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | autumn | 4 | 4370 | 14.693 | 20.403 | -0.27757 | 0.41827 | 0.72014 | 0.86247 | 37.866 | 57.91 | 77.367 | 135 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| overall | all | 12 | 17473 | 27.691 | 35.644 | 0.076631 | 0.70619 | 0.63738 | 0.82321 | 62.062 | 94.916 | 138.11 | 225.69 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | winter | 12 | 4273 | 27.902 | 35.929 | -1.4468 | 0.70265 | 0.64943 | 0.82682 | 63.291 | 96.795 | 138.99 | 229.08 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | spring | 12 | 4414 | 30.278 | 38.266 | 1.6414 | 0.69927 | 0.59923 | 0.79429 | 63.782 | 97.547 | 151.88 | 247.91 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | summer | 12 | 4416 | 25.506 | 32.38 | 0.82981 | 0.65198 | 0.66757 | 0.85485 | 61.487 | 94.036 | 121.3 | 181.19 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | autumn | 12 | 4370 | 27.081 | 35.765 | -0.77539 | 0.77143 | 0.63364 | 0.81693 | 59.704 | 91.309 | 140.34 | 244.92 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| overall | all | 24 | 17473 | 33.368 | 43.064 | 0.153 | 0.85274 | 0.68723 | 0.85177 | 81.139 | 124.09 | 162.17 | 256.4 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | winter | 24 | 4273 | 36.38 | 46.291 | -2.573 | 0.91756 | 0.64826 | 0.82448 | 82.929 | 126.83 | 178.32 | 280.86 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | spring | 24 | 4414 | 34.345 | 43.83 | 2.9779 | 0.79351 | 0.69937 | 0.86271 | 84.109 | 128.63 | 163.31 | 257.74 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | summer | 24 | 4416 | 29.777 | 38.429 | 1.578 | 0.75993 | 0.72939 | 0.88745 | 80.276 | 122.77 | 139.55 | 202.2 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | autumn | 24 | 4370 | 33.066 | 43.441 | -1.4748 | 0.94297 | 0.67048 | 0.83135 | 77.26 | 118.16 | 168.1 | 285.9 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| overall | all | 48 | 17473 | 38.903 | 50.28 | 0.36129 | 0.99452 | 0.70949 | 0.87335 | 101.45 | 155.15 | 186.37 | 280.97 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | winter | 48 | 4273 | 42.25 | 53.412 | -4.5088 | 1.0638 | 0.68313 | 0.84835 | 103.99 | 159.04 | 201.19 | 293.63 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | spring | 48 | 4414 | 40.701 | 52.796 | 5.0771 | 0.9398 | 0.70571 | 0.88786 | 106.67 | 163.14 | 193.82 | 296.3 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | summer | 48 | 4416 | 32.63 | 42.792 | 3.0213 | 0.83154 | 0.78714 | 0.92323 | 100.21 | 153.26 | 154.81 | 225.42 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| season | autumn | 48 | 4370 | 40.152 | 51.506 | -2.3281 | 1.1467 | 0.66064 | 0.83272 | 94.941 | 145.2 | 196.23 | 309.25 | 0 | SARIMA(1,0,1)x(1,0,0,48) |
| overall | all | 1 | 17473 | 9.0561 | 12.493 | -0.0080124 | 0.23061 | 0.99994 | 1 | 131.48 | 201.08 | 131.48 | 201.08 | 0 | persistence |
| season | winter | 1 | 4273 | 8.443 | 11.971 | -0.078867 | 0.21162 | 1 | 1 | 134.06 | 205.03 | 134.06 | 205.03 | 0 | persistence |
| season | spring | 1 | 4414 | 10.114 | 13.767 | 0.045084 | 0.23348 | 1 | 1 | 143.33 | 219.2 | 143.33 | 219.2 | 0 | persistence |
| season | summer | 1 | 4416 | 8.8684 | 11.789 | 0.00022645 | 0.22708 | 1 | 1 | 130.17 | 199.08 | 130.17 | 199.08 | 0 | persistence |
| season | autumn | 1 | 4370 | 8.7773 | 12.331 | -0.0006865 | 0.24985 | 0.99977 | 1 | 118.3 | 180.93 | 118.3 | 180.93 | 0 | persistence |
| overall | all | 4 | 17473 | 19.976 | 27.002 | -0.017398 | 0.50815 | 0.97282 | 0.9992 | 131.48 | 201.08 | 134.51 | 201.41 | 0 | persistence |
| season | winter | 4 | 4273 | 18.469 | 25.656 | -0.20641 | 0.46308 | 0.97543 | 0.99953 | 134.05 | 205.01 | 136.83 | 205.17 | 0 | persistence |
| season | spring | 4 | 4414 | 22.835 | 30.224 | 0.11328 | 0.52701 | 0.97485 | 1 | 143.33 | 219.21 | 145.77 | 219.21 | 0 | persistence |
| season | summer | 4 | 4416 | 19.457 | 25.395 | 0.0097373 | 0.49805 | 0.98528 | 1 | 130.18 | 199.1 | 131.3 | 199.1 | 0 | persistence |
| season | autumn | 4 | 4370 | 19.088 | 26.406 | 0.0080092 | 0.54337 | 0.95561 | 0.99725 | 118.3 | 180.93 | 124.1 | 182.09 | 0 | persistence |
| overall | all | 12 | 17473 | 37.334 | 47.474 | -0.041092 | 0.94978 | 0.82648 | 0.96452 | 131.48 | 201.08 | 168.74 | 221.69 | 0 | persistence |
| season | winter | 12 | 4273 | 36.44 | 46.63 | -0.4945 | 0.91625 | 0.83361 | 0.97121 | 134.01 | 204.96 | 168.23 | 220.48 | 0 | persistence |
| season | spring | 12 | 4414 | 42.054 | 52.322 | 0.3285 | 0.97074 | 0.81695 | 0.96964 | 143.34 | 219.22 | 182.2 | 234.01 | 0 | persistence |
| season | summer | 12 | 4416 | 36.186 | 45.244 | 0.070426 | 0.92606 | 0.84511 | 0.97396 | 130.21 | 199.15 | 159.65 | 211.09 | 0 | persistence |
| season | autumn | 12 | 4370 | 34.6 | 45.294 | -0.083753 | 0.98538 | 0.8103 | 0.94325 | 118.3 | 180.92 | 164.82 | 221.14 | 0 | persistence |
| overall | all | 24 | 17473 | 39.436 | 50.62 | -0.096835 | 1.0067 | 0.80192 | 0.94409 | 131.48 | 201.08 | 182.32 | 245.95 | 0 | persistence |
| season | winter | 24 | 4273 | 44.457 | 56.287 | -0.85678 | 1.1237 | 0.74795 | 0.923 | 133.96 | 204.88 | 202.86 | 267.17 | 0 | persistence |
| season | spring | 24 | 4414 | 39.534 | 49.887 | 0.6638 | 0.91312 | 0.8362 | 0.96874 | 143.35 | 219.23 | 179.47 | 237.59 | 0 | persistence |
| season | summer | 24 | 4416 | 37.929 | 47.212 | 0.11707 | 0.96928 | 0.82699 | 0.96716 | 130.26 | 199.21 | 165.86 | 217.8 | 0 | persistence |
| season | autumn | 24 | 4370 | 35.951 | 48.797 | -0.33822 | 1.0248 | 0.79474 | 0.91648 | 118.29 | 180.92 | 181.76 | 262.08 | 0 | persistence |
| overall | all | 48 | 17473 | 39.495 | 51.368 | -0.16002 | 1.0101 | 0.80519 | 0.93081 | 131.48 | 201.08 | 186.99 | 257.2 | 0 | persistence |
| season | winter | 48 | 4273 | 42.926 | 54.881 | -1.9415 | 1.083 | 0.76831 | 0.91739 | 133.85 | 204.71 | 199.14 | 260.25 | 0 | persistence |
| season | spring | 48 | 4414 | 41.699 | 53.313 | 1.2759 | 0.9624 | 0.82918 | 0.9556 | 143.37 | 219.27 | 190.01 | 263.28 | 0 | persistence |
| season | summer | 48 | 4416 | 32.367 | 42.642 | 0.30639 | 0.82565 | 0.87998 | 0.96513 | 130.35 | 199.35 | 159.4 | 219.98 | 0 | persistence |
| season | autumn | 48 | 4370 | 41.119 | 53.824 | -0.33982 | 1.1735 | 0.74142 | 0.88421 | 118.29 | 180.9 | 199.92 | 285.69 | 0 | persistence |
| overall | all | 1 | 17473 | 38.822 | 50.643 | -0.27402 | 0.99184 | 0.81034 | 0.93418 | 131.48 | 201.08 | 184.48 | 253.72 | 0 | daily\_naive |
| season | winter | 1 | 4273 | 42.063 | 53.917 | -2.373 | 1.0581 | 0.77791 | 0.92254 | 134.06 | 205.03 | 195.61 | 257.36 | 0 | daily\_naive |
| season | spring | 1 | 4414 | 40.873 | 52.547 | 1.261 | 0.94295 | 0.83666 | 0.95673 | 143.33 | 219.2 | 187.64 | 261.4 | 0 | daily\_naive |
| season | summer | 1 | 4416 | 31.982 | 42.157 | 0.28895 | 0.81639 | 0.88157 | 0.96694 | 130.17 | 199.08 | 158.16 | 218.85 | 0 | daily\_naive |
| season | autumn | 1 | 4370 | 40.492 | 53.173 | -0.34096 | 1.1537 | 0.74348 | 0.8897 | 118.3 | 180.93 | 197.03 | 277.64 | 0 | daily\_naive |
| overall | all | 4 | 17473 | 38.824 | 50.644 | -0.27894 | 0.99211 | 0.81034 | 0.93418 | 131.48 | 201.08 | 184.53 | 253.91 | 0 | daily\_naive |
| season | winter | 4 | 4273 | 42.072 | 53.92 | -2.3932 | 1.0587 | 0.77791 | 0.92254 | 134.05 | 205.01 | 195.66 | 257.57 | 0 | daily\_naive |
| season | spring | 4 | 4414 | 40.873 | 52.547 | 1.261 | 0.9431 | 0.83666 | 0.95673 | 143.33 | 219.21 | 187.68 | 261.56 | 0 | daily\_naive |
| season | summer | 4 | 4416 | 31.982 | 42.157 | 0.28895 | 0.81644 | 0.88157 | 0.96694 | 130.18 | 199.1 | 158.18 | 218.92 | 0 | daily\_naive |
| season | autumn | 4 | 4370 | 40.492 | 53.173 | -0.34096 | 1.154 | 0.74348 | 0.8897 | 118.3 | 180.93 | 197.11 | 277.97 | 0 | daily\_naive |
| overall | all | 12 | 17473 | 38.822 | 50.643 | -0.2857 | 0.99245 | 0.81022 | 0.93413 | 131.48 | 201.08 | 184.63 | 254.26 | 0 | daily\_naive |
| season | winter | 12 | 4273 | 42.065 | 53.918 | -2.4208 | 1.0592 | 0.77744 | 0.92254 | 134.01 | 204.96 | 195.77 | 257.99 | 0 | daily\_naive |
| season | spring | 12 | 4414 | 40.873 | 52.547 | 1.261 | 0.94335 | 0.83666 | 0.95673 | 143.34 | 219.22 | 187.76 | 261.82 | 0 | daily\_naive |
| season | summer | 12 | 4416 | 31.982 | 42.157 | 0.28895 | 0.81647 | 0.88157 | 0.96694 | 130.21 | 199.15 | 158.24 | 219.05 | 0 | daily\_naive |
| season | autumn | 12 | 4370 | 40.492 | 53.173 | -0.34096 | 1.1546 | 0.74348 | 0.88947 | 118.3 | 180.92 | 197.25 | 278.57 | 0 | daily\_naive |
| overall | all | 24 | 17473 | 38.841 | 50.66 | -0.26693 | 0.99326 | 0.80965 | 0.93401 | 131.48 | 201.08 | 184.72 | 254.48 | 0 | daily\_naive |
| season | winter | 24 | 4273 | 42.141 | 53.984 | -2.344 | 1.0621 | 0.77604 | 0.9223 | 133.96 | 204.88 | 195.91 | 258.24 | 0 | daily\_naive |
| season | spring | 24 | 4414 | 40.873 | 52.547 | 1.261 | 0.94341 | 0.8362 | 0.9565 | 143.35 | 219.23 | 187.81 | 261.94 | 0 | daily\_naive |
| season | summer | 24 | 4416 | 31.982 | 42.157 | 0.28895 | 0.81636 | 0.88111 | 0.96694 | 130.26 | 199.21 | 158.29 | 219.15 | 0 | daily\_naive |
| season | autumn | 24 | 4370 | 40.492 | 53.173 | -0.34096 | 1.1551 | 0.74348 | 0.88947 | 118.29 | 180.92 | 197.37 | 278.97 | 0 | daily\_naive |
| overall | all | 48 | 17473 | 47.638 | 60.903 | -0.42849 | 1.2183 | 0.72117 | 0.89475 | 131.48 | 201.08 | 221.58 | 314.48 | 0 | daily\_naive |
| season | winter | 48 | 4273 | 51.077 | 64.95 | -4.1151 | 1.287 | 0.68453 | 0.89141 | 133.85 | 204.71 | 235.7 | 338.51 | 0 | daily\_naive |
| season | spring | 48 | 4414 | 50.416 | 62.99 | 2.1846 | 1.1625 | 0.73403 | 0.91346 | 143.37 | 219.27 | 224.49 | 293.36 | 0 | daily\_naive |
| season | summer | 48 | 4416 | 38.607 | 48.889 | 0.36141 | 0.98604 | 0.80208 | 0.95539 | 130.35 | 199.35 | 172.96 | 220.73 | 0 | daily\_naive |
| season | autumn | 48 | 4370 | 50.595 | 65.445 | -0.26133 | 1.4422 | 0.66224 | 0.81785 | 118.29 | 180.9 | 253.96 | 407.05 | 0 | daily\_naive |
| overall | all | 1 | 17473 | 56.14 | 71.554 | -0.083157 | 1.443 | 0.65392 | 0.82905 | 131.48 | 201.08 | 275.57 | 439.59 | 0 | weekly\_naive |
| season | winter | 1 | 4273 | 66.044 | 82.11 | -1.1821 | 1.6415 | 0.57828 | 0.7627 | 134.06 | 205.03 | 327.37 | 521.62 | 0 | weekly\_naive |
| season | spring | 1 | 4414 | 51.916 | 64.7 | 4.3906 | 1.1985 | 0.72338 | 0.91414 | 143.33 | 219.2 | 228.57 | 312.14 | 0 | weekly\_naive |
| season | summer | 1 | 4416 | 42.037 | 53.846 | -2.3736 | 1.0833 | 0.76381 | 0.91984 | 130.17 | 199.08 | 196.27 | 265.1 | 0 | weekly\_naive |
| season | autumn | 1 | 4370 | 64.973 | 81.983 | -1.2128 | 1.8592 | 0.54668 | 0.71625 | 118.3 | 180.93 | 352.52 | 664.43 | 0 | weekly\_naive |
| overall | all | 4 | 17473 | 56.143 | 71.556 | -0.095404 | 1.4431 | 0.65398 | 0.82905 | 131.48 | 201.08 | 275.57 | 439.62 | 0 | weekly\_naive |
| season | winter | 4 | 4273 | 66.056 | 82.115 | -1.2322 | 1.642 | 0.57828 | 0.7627 | 134.05 | 205.01 | 327.37 | 521.64 | 0 | weekly\_naive |
| season | spring | 4 | 4414 | 51.916 | 64.7 | 4.3906 | 1.1985 | 0.72338 | 0.91414 | 143.33 | 219.21 | 228.57 | 312.18 | 0 | weekly\_naive |
| season | summer | 4 | 4416 | 42.037 | 53.846 | -2.3736 | 1.0832 | 0.76381 | 0.91984 | 130.18 | 199.1 | 196.27 | 265.12 | 0 | weekly\_naive |
| season | autumn | 4 | 4370 | 64.973 | 81.983 | -1.2128 | 1.8592 | 0.54691 | 0.71625 | 118.3 | 180.93 | 352.54 | 664.49 | 0 | weekly\_naive |
| overall | all | 12 | 17473 | 56.142 | 71.555 | -0.13518 | 1.4431 | 0.65381 | 0.82894 | 131.48 | 201.08 | 275.58 | 439.73 | 0 | weekly\_naive |
| season | winter | 12 | 4273 | 66.054 | 82.113 | -1.3948 | 1.6424 | 0.57828 | 0.7627 | 134.01 | 204.96 | 327.36 | 521.7 | 0 | weekly\_naive |
| season | spring | 12 | 4414 | 51.916 | 64.7 | 4.3906 | 1.1984 | 0.72293 | 0.91391 | 143.34 | 219.22 | 228.58 | 312.28 | 0 | weekly\_naive |
| season | summer | 12 | 4416 | 42.037 | 53.846 | -2.3736 | 1.083 | 0.76359 | 0.91984 | 130.21 | 199.15 | 196.27 | 265.17 | 0 | weekly\_naive |
| season | autumn | 12 | 4370 | 64.973 | 81.983 | -1.2128 | 1.8594 | 0.54691 | 0.71602 | 118.3 | 180.92 | 352.58 | 664.7 | 0 | weekly\_naive |
| overall | all | 24 | 17473 | 56.118 | 71.542 | -0.19121 | 1.4427 | 0.65432 | 0.82871 | 131.48 | 201.08 | 275.6 | 439.91 | 0 | weekly\_naive |
| season | winter | 24 | 4273 | 65.954 | 82.066 | -1.6239 | 1.6405 | 0.57992 | 0.7627 | 133.96 | 204.88 | 327.34 | 521.84 | 0 | weekly\_naive |
| season | spring | 24 | 4414 | 51.916 | 64.7 | 4.3906 | 1.1983 | 0.72293 | 0.91391 | 143.35 | 219.23 | 228.59 | 312.37 | 0 | weekly\_naive |
| season | summer | 24 | 4416 | 42.037 | 53.846 | -2.3736 | 1.0827 | 0.76381 | 0.91984 | 130.26 | 199.21 | 196.27 | 265.21 | 0 | weekly\_naive |
| season | autumn | 24 | 4370 | 64.973 | 81.983 | -1.2128 | 1.8598 | 0.54714 | 0.7151 | 118.29 | 180.92 | 352.65 | 665.14 | 0 | weekly\_naive |
| overall | all | 48 | 17473 | 56.098 | 71.531 | -0.24747 | 1.4424 | 0.65467 | 0.82871 | 131.48 | 201.08 | 275.61 | 440.26 | 0 | weekly\_naive |
| season | winter | 48 | 4273 | 65.874 | 82.028 | -1.854 | 1.6396 | 0.58015 | 0.76223 | 133.85 | 204.71 | 327.33 | 522.29 | 0 | weekly\_naive |
| season | spring | 48 | 4414 | 51.916 | 64.7 | 4.3906 | 1.198 | 0.72383 | 0.91368 | 143.37 | 219.27 | 228.55 | 312.42 | 0 | weekly\_naive |
| season | summer | 48 | 4416 | 42.037 | 53.846 | -2.3736 | 1.0819 | 0.76381 | 0.92029 | 130.35 | 199.35 | 196.23 | 265.25 | 0 | weekly\_naive |
| season | autumn | 48 | 4370 | 64.973 | 81.983 | -1.2128 | 1.8605 | 0.54737 | 0.71533 | 118.29 | 180.9 | 352.76 | 666.05 | 0 | weekly\_naive |
| overall | all | 1 | 17473 | 46.536 | 56.346 | 2.6145 | 1.1932 | 0.74813 | 0.93687 | 131.48 | 201.08 | 194.03 | 260.8 | 0 | calendar\_mean |
| season | winter | 1 | 4273 | 51.061 | 61.429 | -13.134 | 1.2774 | 0.70513 | 0.92207 | 134.06 | 205.03 | 212.62 | 272.01 | 0 | calendar\_mean |
| season | spring | 1 | 4414 | 46.613 | 55.896 | 18.307 | 1.0769 | 0.78772 | 0.96285 | 143.33 | 219.2 | 188.85 | 234.88 | 0 | calendar\_mean |
| season | summer | 1 | 4416 | 36.973 | 44.109 | 11.588 | 0.94443 | 0.8562 | 0.99706 | 130.17 | 199.08 | 148.11 | 199.63 | 0 | calendar\_mean |
| season | autumn | 1 | 4370 | 51.698 | 62.31 | -6.9046 | 1.4798 | 0.64096 | 0.8643 | 118.3 | 180.93 | 227.48 | 337.84 | 0 | calendar\_mean |
| overall | all | 4 | 17473 | 46.525 | 56.338 | 2.6036 | 1.1929 | 0.74824 | 0.93687 | 131.48 | 201.08 | 194.02 | 260.79 | 0 | calendar\_mean |
| season | winter | 4 | 4273 | 51.017 | 61.4 | -13.179 | 1.2764 | 0.70559 | 0.92207 | 134.05 | 205.01 | 212.59 | 271.97 | 0 | calendar\_mean |
| season | spring | 4 | 4414 | 46.613 | 55.896 | 18.307 | 1.0768 | 0.78795 | 0.96285 | 143.33 | 219.21 | 188.86 | 234.91 | 0 | calendar\_mean |
| season | summer | 4 | 4416 | 36.973 | 44.109 | 11.588 | 0.94434 | 0.85598 | 0.99706 | 130.18 | 199.1 | 148.12 | 199.64 | 0 | calendar\_mean |
| season | autumn | 4 | 4370 | 51.698 | 62.31 | -6.9046 | 1.4798 | 0.64096 | 0.8643 | 118.3 | 180.93 | 227.47 | 337.8 | 0 | calendar\_mean |
| overall | all | 12 | 17473 | 46.499 | 56.311 | 2.5778 | 1.1923 | 0.74881 | 0.93699 | 131.48 | 201.08 | 193.95 | 260.74 | 0 | calendar\_mean |
| season | winter | 12 | 4273 | 50.911 | 61.3 | -13.284 | 1.274 | 0.70747 | 0.9223 | 134.01 | 204.96 | 212.25 | 271.78 | 0 | calendar\_mean |
| season | spring | 12 | 4414 | 46.613 | 55.896 | 18.307 | 1.0768 | 0.78772 | 0.96262 | 143.34 | 219.22 | 188.88 | 234.96 | 0 | calendar\_mean |
| season | summer | 12 | 4416 | 36.973 | 44.109 | 11.588 | 0.94407 | 0.8562 | 0.99706 | 130.21 | 199.15 | 148.12 | 199.69 | 0 | calendar\_mean |
| season | autumn | 12 | 4370 | 51.698 | 62.31 | -6.9046 | 1.4798 | 0.64142 | 0.86476 | 118.3 | 180.92 | 227.48 | 337.68 | 0 | calendar\_mean |
| overall | all | 24 | 17473 | 46.433 | 56.233 | 2.5116 | 1.1906 | 0.74944 | 0.93745 | 131.48 | 201.08 | 193.62 | 260.35 | 0 | calendar\_mean |
| season | winter | 24 | 4273 | 50.64 | 61.006 | -13.555 | 1.2676 | 0.70981 | 0.92488 | 133.96 | 204.88 | 210.88 | 270.33 | 0 | calendar\_mean |
| season | spring | 24 | 4414 | 46.613 | 55.896 | 18.307 | 1.0768 | 0.78749 | 0.96262 | 143.35 | 219.23 | 188.93 | 235.01 | 0 | calendar\_mean |
| season | summer | 24 | 4416 | 36.973 | 44.109 | 11.588 | 0.94368 | 0.85643 | 0.99706 | 130.26 | 199.21 | 148.12 | 199.75 | 0 | calendar\_mean |
| season | autumn | 24 | 4370 | 51.698 | 62.31 | -6.9046 | 1.4797 | 0.64165 | 0.86407 | 118.29 | 180.92 | 227.47 | 337.42 | 0 | calendar\_mean |
| overall | all | 48 | 17473 | 46.358 | 56.165 | 2.4364 | 1.1885 | 0.75047 | 0.93727 | 131.48 | 201.08 | 193.41 | 260.15 | 0 | calendar\_mean |
| season | winter | 48 | 4273 | 50.333 | 60.749 | -13.863 | 1.2607 | 0.71308 | 0.92511 | 133.85 | 204.71 | 210.06 | 270.03 | 0 | calendar\_mean |
| season | spring | 48 | 4414 | 46.613 | 55.896 | 18.307 | 1.0767 | 0.78772 | 0.96194 | 143.37 | 219.27 | 188.98 | 235.15 | 0 | calendar\_mean |
| season | summer | 48 | 4416 | 36.973 | 44.109 | 11.588 | 0.9429 | 0.85734 | 0.99706 | 130.35 | 199.35 | 148.11 | 199.84 | 0 | calendar\_mean |
| season | autumn | 48 | 4370 | 51.698 | 62.31 | -6.9046 | 1.4792 | 0.64142 | 0.86384 | 118.29 | 180.9 | 227.37 | 336.67 | 0 | calendar\_mean |

Source CSV: `../artifacts/runs/d2dee2d358735d7d/test/forecast_metrics.csv`.

## Reproducibility and claim traceability

- Results manifest: `../artifacts/results.json` (SHA-256 `8cd196dbbe13512f1e09f2c07e285ce4f476bae673184ab8cd56b92fae58d743`).
- Data manifest hash: `f57548d5bc197f884b5b35bb84faaaadcb38b7b46dc3e8c925a150b8ea5a5a1e`.
- Configuration digest: `6f0831112aaed65643e9f88b6d31ac5d31222897d4484c461d9103ac94810ccb`.
- Protocol hash: `b6876f7c8f058f9242eb5852a580384bfa0a1365c76f69a509fa975f8377c68c`.
- Software source hash: `16d9038d1d153c6d68293c5cc8ef0a902381366d5b8ecd993c9cccf03477fda0`.
- Python runtime: `3.13.4`.
- Exporter package versions: `gridshift=1.0.0, numpy=2.5.4, pandas=2.3.3, scipy=1.18.1, statsmodels=0.14.6, reportlab=4.5.1, nbconvert=7.17.2, nbformat=5.11.1, python-pptx=1.0.2`.
- Validation forecast metrics: `C:\Users\viraj\Documents\Codex\2026-10-22\plan-gridshift-a-complete-ats-mini\outputs\GridShift\artifacts\runs\d2dee2d358735d7d\validation\forecast_metrics.csv`.
- Test forecast metrics: `C:\Users\viraj\Documents\Codex\2026-10-22\plan-gridshift-a-complete-ats-mini\outputs\GridShift\artifacts\runs\d2dee2d358735d7d\test\forecast_metrics.csv`.
- Primary and queue summaries: `C:\Users\viraj\Documents\Codex\2026-10-22\plan-gridshift-a-complete-ats-mini\outputs\GridShift\artifacts\runs\d2dee2d358735d7d\test\single_job\primary_summary.csv`; `C:\Users\viraj\Documents\Codex\2026-10-22\plan-gridshift-a-complete-ats-mini\outputs\GridShift\artifacts\runs\d2dee2d358735d7d\test\queue\queue_summary.csv`.
- The notebook reads these files without collecting data or fitting models. The root workflow executes it with `nbconvert` after generation.

## References

- [S1] [Official GB Carbon Intensity API](https://api.carbonintensity.org.uk/)
- [S2] [Official API definitions](https://carbon-intensity.github.io/api-definitions/)
- [S3] [NESO national carbon-intensity dataset](https://www.neso.energy/data-portal/national-carbon-intensity-forecast)
- [S4] [NESO national resource dictionary](https://www.neso.energy/data-portal/national-carbon-intensity-forecast/national_carbon_intensity_forecast)
- [S5] [NESO national carbon-intensity methodology](https://api.neso.energy/dataset/f406810a-1a36-48d2-b542-1dfb1348096e/resource/36638178-e993-4d34-afdc-4ada83993585/download/neso-ci-national-methodology_v2.pdf)
- [S6] [Carbon Intensity API terms](https://github.com/carbon-intensity/terms)
- [S7] [NESO Open Data Licence](https://www.neso.energy/data-portal/neso-open-licence)
- [S8] [NESO historic generation mix and carbon intensity](https://www.neso.energy/data-portal/historic-generation-mix)
- [S9] [Forecasting: Principles and Practice, forecasting toolbox](https://otexts.com/fpp3/toolbox.html)
- [S10] [Forecasting: Principles and Practice, ARIMA](https://otexts.com/fpp3/arima.html)
- [S11] [statsmodels augmented Dickey-Fuller test](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.adfuller.html)
- [S12] [statsmodels SARIMAX](https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAX.html)
- [S13] [statsmodels SARIMAX missing-data example](https://www.statsmodels.org/stable/examples/notebooks/generated/statespace_sarimax_internet.html)
