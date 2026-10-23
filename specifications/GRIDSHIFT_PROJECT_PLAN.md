# GridShift: executable project plan

Carbon-aware GPU workload scheduling with classical time-series forecasts

Version 1.0 | 22 October 2026 | Planning only

ATS is interpreted here as Applied Time Series. Course-specific formatting and marking requirements should be checked against the actual rubric before preparing the final academic package.

## 1. Decision and research question

Build GridShift eventually as a reproducible forecasting study with a scheduling simulator and a professional Streamlit interface. Do not build or deploy the application in this planning phase.

The defensible research question is:

> Under declared job-duration, energy, deadline, and capacity assumptions, do forecasts of NESO's estimated GB carbon intensity reduce the modeled operational CO2 of completed GPU workloads compared with carbon-unaware scheduling and simple forecast baselines?

This is narrower than "AI reduces GPU emissions". Every core job represents a hypothetical workload powered by the GB grid, with national intensity as an explicit proxy. The dataset does not measure GPU energy, represent every datacenter's electricity supply, or establish the marginal grid response to moving a workload. Running the dashboard elsewhere does not make NESO intensity applicable to a GPU outside Great Britain.

Two questions must remain separate:

1. Do classical models forecast carbon intensity better than persistence and seasonal baselines at relevant lead times?
2. Does the forecast produce better feasible workload placements when realized carbon intensity determines the score?

Better MAE is neither necessary nor sufficient for better scheduling. Window ranking, deadline slack, duration, and uncertainty matter.

### Recommended core decisions

| Decision | Proposed choice | Reason or condition |
| --- | --- | --- |
| Geographic target | National Great Britain | Official numerical estimated-actual target is available. No geographic migration. |
| Acquisition | Official national interval API | Explicit interval bounds support auditable scheduling alignment. |
| Target | `intensity.actual` | Estimated realized intensity, never an automatic mixture of actual and forecast. |
| Resolution | 30 minutes | Native source resolution preserves short scheduling opportunities. |
| Forecast outputs | A complete 24-hour path | A scheduler needs all intervals in a job's feasible window, not one endpoint prediction. |
| Reported lead times | 0.5, 2, 6, 12, and 24 hours | Covers immediate through day-ahead placement. |
| Optional horizon | 48 hours | Match the documented official forward range, but treat as secondary. |
| History | 2022-01-01 through 2025-12-31, UTC | Four complete years, subject to a full coverage audit. |
| Development split | 2022-2023 | Training EDA, model design, and computational pilot. |
| Validation split | Calendar year 2024 | Order, transformation, policy, and complexity choices. |
| Locked test split | Calendar year 2025 | Final chronological evaluation after protocol freeze. |
| Main fit window | Preceding 180 days | Balances seasonal examples and changing generation regimes. Test 90 and 365 days only as declared sensitivities. |
| Forecast issue cadence | Each half-hour boundary | Matches decisions and data intervals. |
| Parameter refit | Weekly | Bound the experiment. Update filtering state with eligible observations between refits. |
| Observation delay | 30 minutes beyond interval end | Conservative replay assumption, not a measured NESO latency. Sensitivities: 0 and 60 minutes. |
| Core workload | Known-duration, non-preemptive jobs | No invented checkpointing or hidden energy savings. |
| Execution mode | Recommendation and historical simulation | No real GPU submission or orchestration. |

These are proposed design decisions, not findings. Training-only evidence may justify a documented change before test evaluation. Test performance must not justify changing the protocol.

The source audit in [GRIDSHIFT_SOURCE_AUDIT.md](GRIDSHIFT_SOURCE_AUDIT.md) records official references and live probes. All source IDs below refer to that document.

## 2. Evidence and assumptions

### Verified facts that affect the design

The API supplies half-hour interval boundaries, estimated actual intensity, a separate forecast, and gCO2/kWh units. Its national from/to request limit is 14 days. Use 7-day chunks. Sources: S1, S2, S4.

Live probes found that date requests can select 46 or 50 half-hours on daylight-saving transition days. Explicit UTC range requests included one preceding slot. Normalize interval boundaries before constructing the canonical grid. Do not assume a raw daily response contains 48 UTC intervals.

The inspected historical interfaces lack forecast issue-time fields. Their historical `forecast` values cannot yet support a fair as-issued NESO comparison.

The publisher-linked methodology describes generation-related CO2, rather than a full lifecycle or all-GHG measure. It states that estimates are provided at half-hour period ends. Historical publication delays and revisions remain unresolved. Source: S5.

### Claims the project must reject

| Weak assumption | Replacement |
| --- | --- |
| Official `actual` means directly measured ground truth. | Call it NESO estimated actual. It remains the evaluation target with measurement uncertainty. |
| A historical forecast retrieved now was available then. | Require forecast-vintage evidence or exclude it from scored historical comparisons. |
| The lowest forecast point is the best job start. | Minimize integrated emissions over the entire duration and obey deadlines and capacity. |
| More named model families mean more independent competitors. | AR, MA, and ARMA are nested ARIMA cases. Deduplicate identical effective models. |
| ADF rejection proves a stable forecasting process. | It addresses a unit root under a specified regression. Check seasonality, breaks, variance, and residuals separately. |
| Low AIC proves forecast skill. | Use AIC and BIC for appropriate within-group selection, then chronological out-of-sample evaluation. |
| Hourly averages preserve half-hour scheduling opportunities. | Measure aggregation loss as a sensitivity. Never interpolate hourly forecasts and claim half-hour evidence. |
| A 400 W GPU specification is measured job power. | Treat power as a declared scenario unless telemetry verifies it. |
| Deadline violations can be traded for lower CO2. | Deadlines are hard constraints in the core study. Never count incomplete jobs as emissions saved. |
| A national average-intensity reduction proves avoided grid emissions. | Report a modeled attributional reduction, not a measured or causal grid-emissions claim. |
| A useful application requires a sophisticated model to win. | Deploy a simple baseline or report no scheduling benefit when the evidence supports that outcome. |

### Study hypotheses

- H1: At least one validated classical model reduces forecast loss against the validation-selected strongest simple baseline on the locked test.
- H2: The validation-selected forecast scheduler reduces realized modeled emissions against earliest-feasible execution without increasing deadline misses.
- H3: Its reduction exceeds the scheduler using the validation-selected strongest simple forecast, not merely the carbon-unaware control.
- H4: Benefits vary with duration, slack, load, and the available within-window carbon opportunity.

H2 does not imply H3. A seasonal baseline may supply all useful scheduling information. H2 for the default isolated-job scenario is the primary inferential contrast. H1, H3, H4, other scenarios, and queue outcomes are secondary. Report all declared scenarios, not only successful ones.

## 3. Requirements-to-deliverables mapping

All paths in this section describe the eventual repository. They do not exist as implemented deliverables yet.

| ID | Requirement | Planned implementation and evidence | Completion criterion |
| --- | --- | --- | --- |
| R01 | Official data collection | `src/gridshift/data.py`, immutable raw responses, `data/manifest.json`, source audit | Rebuild the requested UTC series from a frozen manifest. Preserve provenance and licences. |
| R02 | EDA | Notebook section 2, `artifacts/runs/<run_id>/figures/eda_*`, data-quality table | Cover level, distribution, seasonal patterns, changes, extremes, and missingness without test-driven design. |
| R03 | Missing values | Data-quality masks and causal missing-data policy | Preserve raw nulls. Demonstrate that future values cannot influence historical preprocessing. |
| R04 | ADF stationarity testing | Notebook section 3, `artifacts/runs/<run_id>/stationarity.csv` | Record regression, lag rule, statistic, p-value, critical values, sample dates, and qualified interpretation. |
| R05 | Transformations | `forecasting.py` transform state and inverse path | Compare identity and justified transformations on validation. Restore levels, units, and uncertainty correctly. |
| R06 | Seasonal decomposition | STL at period 48; declared weekly diagnostic | Reconstruct the training series and explain trend, seasonality, remainder, and endpoint limitations. |
| R07 | ACF and PACF | Raw, transformed, differenced, and residual plots | Relate lag patterns to candidate orders without treating plots as definitive order estimators. |
| R08 | AR | Named AR specifications, equation and representative fitted example | Explain dependence on past values and map to ARIMA(p,0,0). |
| R09 | MA | Named MA specifications and fitted example | Explain past innovations, not a rolling arithmetic average. Map to ARIMA(0,0,q). |
| R10 | ARMA | Named mixed specifications and fitted example | Explain stationary mixed dynamics and map to ARIMA(p,0,q). |
| R11 | ARIMA | Integrated specifications and inverse-differencing evidence | Show why differencing is or is not needed. Recover multi-step level forecasts. |
| R12 | SARIMA | Daily seasonal specifications and seasonal diagnostics | Use the justified seasonal period and report convergence and residual checks. |
| R13 | Lag selection | Bounded candidate catalogue, ACF/PACF rationale, search ledger | All attempted orders, failures, and selected orders are reproducible. |
| R14 | AIC and BIC | Formula explanation and comparable-group tables | Do not rank incompatible likelihoods, samples, or transformations as one leaderboard. |
| R15 | Scientific forecast comparison | `evaluation.py`, origin-level forecasts and metric tables | Same origins, eligibility rules, target masks, and lead times for all models. |
| R16 | Historical scheduling backtests | `scheduling.py`, `replay.py`, job and decision tables | No future carbon or unknown arrivals in online decisions. Realized estimates score every completed job. |
| R17 | Professional dashboard | `app/streamlit_app.py`, local screenshots, UI tests | Usable research and scheduling views, valid controls, clear uncertainty and failure states. |
| R18 | Reproducible notebook | `notebooks/01_gridshift_study.ipynb`, executed HTML | Restart-and-run-all from the locked environment. Import package logic, not duplicate it. |
| R19 | Report | `reports/gridshift_report.pdf`, editable source, references | Methods, complete outcomes, limitations, and claim-to-evidence references. No fabricated results. |
| R20 | Presentation | `slides/gridshift_presentation.pptx`, PDF, notes | Explain the question, methods, observed outcomes, limits, and demo in 10-12 slides. |
| R21 | Model deployment | Versioned bundle, local prediction path, operational runbook | Reload a trusted artifact and reproduce predictions. Exercise fresh, stale, missing, and incompatible states. |
| R22 | Tests | Unit, integration, scientific-contract, and Streamlit tests | Critical negative cases fail correctly. Offline test suite passes. |
| R23 | Reproducibility | `pyproject.toml`, lockfile, configs, manifests, generated tables | Every headline result resolves to a run, data hash, configuration, and software version. |

The package is incomplete if any syllabus topic appears only in prose without an executed example or a documented data-dependent reason it is inappropriate.

## 4. Data collection and quality protocol

### 4.1 Freeze one target, not a blended series

Collect national interval API data for `[2022-01-01T00:00Z, 2026-01-01T00:00Z)`. This span has 1,461 days and an expected canonical grid of 70,128 half-hour slots. That is an expected grid size, not verified usable coverage.

Use the official portal archive only as a separately identified fallback if the API cannot provide the requested series. First verify timestamp alignment, overlaps, revisions, units, and coverage. Record a protocol amendment before scientific evaluation. Do not merge rows silently.

Keep `actual`, `forecast`, and `index` separately. Never fill missing `actual` with `forecast`. Do not use the target period's `index` or generation mix as a predictor.

### 4.2 Collection behavior

The eventual collector must:

1. Request bounded 7-day UTC chunks with explicit boundaries and timeouts.
2. Respect `Retry-After` for 429 responses. Retry transient failures with bounded backoff and jitter, not permanent schema or authorization errors.
3. Save raw response bytes unchanged with URL, retrieval time, status, response hash, and relevant headers.
4. Validate the JSON schema and parse offset-aware timestamps.
5. Retain complete requested intervals with `from >= start` and `to <= end`.
6. Sort by `from`, detect conflicting duplicates, and compare with the expected UTC grid.
7. Write normalized partitions atomically. A retry must not double-count intervals.
8. Produce a manifest with coverage, schema version, units, source, licence, and all raw hashes.

An identical duplicate may be collapsed with an audit entry. Conflicting versions must be retained in raw storage and resolved through a declared revision policy. Do not average contradictory records.

### 4.3 Canonical observation schema

| Field | Meaning |
| --- | --- |
| `interval_start_utc`, `interval_end_utc` | Half-open 30-minute interval. |
| `actual_gco2_per_kwh` | Nullable estimated-actual target. |
| `provider_forecast_gco2_per_kwh` | Nullable historical provider value. Not an as-issued competitor by default. |
| `provider_index` | Source label retained for display and audit. |
| `retrieved_at_utc`, `raw_hash`, `source_id` | Acquisition provenance. |
| `actual_observed`, `quality_flag` | Original target presence and validation status. |
| `available_at_utc`, `availability_basis` | Verified vintage time when available, otherwise explicitly modeled publication time. |

Zero intensity is a valid value, not missing data. Negative values, infinite values, non-30-minute intervals, and malformed timestamps are errors requiring quarantine or an explained source correction. High but plausible values are not automatically outliers to delete.

### 4.4 Missing-data treatment

Distinguish absent intervals, explicit null actuals, and invalid source records. Plot gap locations and lengths by month and local hour. Record how missingness affects every stage.

- Keep an untouched target series and an observation mask.
- For the primary modeling input, fill only isolated gaps of at most two slots using an observed value from the previous day at the same UTC slot, if available. Otherwise use a past-only last observation within two slots.
- Mark every filled value. The donor must have been available at that point in the replay. Do not recursively conceal long outages with repeated forward fills.
- Keep longer gaps missing for state-space fitting. Baselines use a declared fallback when their required past observation is missing.
- Run ADF and ACF/PACF on declared contiguous observed training segments, or report the effect of the short-gap policy. Do not drop timestamps and compress gaps into false adjacency.
- As a sensitivity, retain all missing observations in state-space models and compare with the short-gap policy.
- Never impute final forecast targets or the realized carbon used to certify a scheduling outcome.

Forecast scores use observed targets, with common masks and counts by horizon. For primary scheduling comparisons, require the entire feasible decision window to have observed realized targets. This prevents each policy from gaining a different missing-data advantage. Select eligible jobs before scoring any policy and report excluded jobs by reason and month.

A complete-case outcome is conditional on coverage. Report a separate operational outage replay and missingness sensitivity. Do not claim excluded periods behaved like retained periods.

Proposed completeness gates are at least 99% observed actual slots overall, at least 95% in each test month, and at least 80% eligible default-scenario releases in each month. These thresholds are study-design choices, not verified dataset properties. If a gate fails, publish the coverage and conditional analyses, but do not label the result a complete-year scheduling assessment. Do not silently move the test period or relax a gate after seeing model outcomes.

### 4.5 Time and information eligibility

At decision time `o`, admit an observation only if its interval end plus the declared publication delay is no later than `o`.

The primary 30-minute delay excludes the immediately preceding half-hour. Forecast through this unobserved bridge before producing the requested path starting at `o`. Match predictions to timestamps, not an assumed array position.

Use UTC for indexing, splits, durations, and computation. Use `Europe/London` for optional display and calendar diagnostics. Repeated autumn local times must display their offset. A spring local day need not contain 48 slots.

Retrospective estimated actuals may have been revised. Without a vintage archive, call the replay pseudo-real-time with an assumed availability delay. This is an unavoidable limitation, not a claim of perfect historical deployment fidelity.

## 5. Applied time-series methodology

### 5.1 Training EDA

Produce the following on development data:

- Full-series and representative-week plots, rolling means and variances, and month-by-month distributions.
- Histograms, empirical quantiles, zero counts, tails, and flagged extremes.
- Half-hour-by-day heatmaps and weekday-by-local-hour profiles, including daylight-saving boundaries.
- Daily and weekly lag correlations, a periodogram, and daily versus weekly seasonal strength diagnostics.
- Missingness and duplicate audits, including source outages and potential nonrandom missingness.
- Year and season comparisons and documented generation-regime changes where official sources support the interpretation.
- Within-window realized carbon range and oracle opportunity on development data only.

Do not claim daily or weekly seasonality until diagnostics support it. Full test-year plots appear only after the frozen evaluation.

### 5.2 Stationarity and transformations

Start with identity scaling. Examine constant-plus-trend ADF on the raw development segment, then constant-only ADF on plausible transformed stationary candidates. Record `maxlag`, `autolag`, deterministic terms, sample size, test statistic, p-value, critical values, and selected lags.

Use AIC-based ADF autolag with a recorded cap of 48 half-hours, and BIC selection as a sensitivity. The ADF augmentation lag is not the AR model order. A lag cap is a project choice, not a universal rule.

Assess:

1. Original levels.
2. `log1p` if variance and tails justify it.
3. First differences when a stochastic level trend is plausible.
4. Seasonal differences at 48 when seasonal persistence justifies them.
5. Combined differences only when the earlier cases leave a demonstrated problem.

Use KPSS as a complementary check where feasible. Its null differs from ADF's. Report conflicting or inconclusive diagnostics. Structural breaks and deterministic seasonality can undermine a simple unit-root interpretation. A significant p-value is not an instruction to stop checking.

Limit core differencing to `d in {0,1}` and `D in {0,1}`. Do not routinely use both. An exceptional higher order requires a documented training-only justification and is outside the default search.

Fit transformation choices only on eligible training data. Box-Cox is a teaching comparison only when positivity and a justified offset permit it. The offset and lambda must be training-derived. Do not change units through arbitrary min-max scaling.

Back-transform the full path. For nonlinear transforms, distinguish a back-transformed median from an expected value. Scheduling minimizes expected emissions, so use a justified bias adjustment or simulated forecast paths. Reconstruct differenced forecasts with the correct observed anchors.

Record raw negative level forecasts. A nonnegative operational correction must be declared, applied to every affected model, and evaluated separately. Never hide clipping in the chart or describe clipped Gaussian intervals as calibrated.

### 5.3 Decomposition and ACF/PACF

Use additive robust STL at period 48 on development data after the documented gap treatment. Reconstruct the input from trend, seasonal, and remainder terms within numerical tolerance.

Weekly structure at lag 336 is a diagnostic and a declared baseline. Use MSTL for a development-only multi-seasonal illustration if useful. A single SARIMA seasonal period does not model both daily and weekly cycles independently.

Centered decomposition uses future neighbors. It is descriptive only. If a seasonally adjusted model is tested, refit its decomposition within every training window and forecast its components without using future target observations.

Show raw and stationary-candidate ACF/PACF through at least two daily cycles, with a separate view around weekly lags. Explain approximate cutoff patterns and finite-sample uncertainty. Show standardized innovation ACF and Ljung-Box diagnostics for fitted finalists after burn-in, with model degrees of freedom and prespecified lags.

Residual whiteness supports a model's adequacy but does not certify predictive accuracy. Residual normality matters for Gaussian interval validity, not for permission to report a point forecast.

### 5.4 Model catalogue

Let `x_t` be the modeled level after an optional variance transform, and `B` the lag operator.

```text
AR(p):       x_t = c + sum(phi_i * x_(t-i)) + epsilon_t
MA(q):       x_t = mu + epsilon_t + sum(theta_i * epsilon_(t-i))
ARMA(p,q):   combines the AR and MA terms on a stationary series
ARIMA:      phi(B) * (1-B)^d * x_t = c + theta(B) * epsilon_t
SARIMA:     Phi(B^48) * phi(B) * (1-B)^d * (1-B^48)^D * x_t
            = c + Theta(B^48) * theta(B) * epsilon_t
```

Signs depend on the software convention. Explain that convention rather than copying incompatible coefficient notation.

Use the maintained statsmodels state-space implementation, with one adapter and no exogenous covariates in the core. This supports AR, MA, and ARMA restrictions without separate bespoke estimators.

| Family | Bounded proposed search | Required comparison |
| --- | --- | --- |
| Persistence | Last eligible observed level | Essential short-horizon baseline. |
| Daily seasonal naive | Previous-day corresponding slot | Essential daily baseline. |
| Weekly seasonal naive | Previous-week corresponding slot | Essential weekly baseline. |
| Calendar mean | Past-only mean by weekday and slot | Tests whether a predictable calendar pattern supplies the useful information. |
| AR | `p=1..8`, `q=0`, `d=D=0` | Named classical family. Seasonal lag 48 as a separately declared diagnostic alternative, not an accidental AR(48) search. |
| MA | `q=1..8`, `p=0`, `d=D=0` | Distinguish the innovation model from a smoothing average. |
| ARMA | `p,q=1..3`, `d=D=0` | Low-order stationary mixed model. |
| ARIMA | `p,q=0..3`, fixed justified `d` | Include restricted cases and random walk when relevant. |
| SARIMA | `p,q=0..2`, `P,Q=0..1`, fixed justified `d,D`, `m=48` | Daily seasonal classical model. |

ARIMA with `d=0` can duplicate ARMA. An ARMA fitted on first differences is an ARIMA level model after reconstruction. Keep the pedagogical labels, but count each effective specification once in statistical comparisons.

If levels are not a defensible stationary input, the raw AR, MA, and ARMA demonstrations remain labeled restricted or misspecified comparators. Show a stationary-input teaching example and its integrated equivalence. Do not manufacture stationarity to make every family appear suitable for deployment.

Use a constant for stationary models and no deterministic trend for the default integrated models. Drift is a separately specified variant if justified. Never include invalid constant terms under differencing or assume different libraries parameterize drift identically.

Record stationarity and invertibility constraints, likelihood initialization, optimization settings, convergence status, and parameter diagnostics. Keep failed fits in the search ledger. An unconverged model cannot win because its reported AIC looks attractive.

### 5.5 Order selection and computational control

Choose plausible `d`, `D`, seasonal period, and transformations using development diagnostics. For each representation and differencing group, use training likelihood to shortlist orders. Validate the shortlisted models chronologically.

```text
AIC  = -2 * log_likelihood + 2 * k
BIC  = -2 * log_likelihood + k * log(n_effective)
AICc = AIC + 2*k*(k+1)/(n_effective-k-1), when the denominator is valid
```

Count all estimated parameters, including variance and deterministic terms. Record the package's effective-sample and burn-in conventions.

Do not compare IC numbers across transformed targets, different observation masks, different windows, incompatible likelihood conventions, or different differencing groups. Use validation loss to compare those choices. Do not compare AutoReg conditional likelihood directly with a differently sampled state-space likelihood.

Use the first UTC half-hour of each validation month as the 12 selection anchors. At each anchor, fit the declared catalogue using only the preceding eligible 180-day history. Rank converged candidates within each comparable family, representation, and differencing group by AICc and BIC. Aggregate within-anchor ranks, not absolute IC values across different windows. Retain at most three distinct orders per group overall, using median AICc rank first, median BIC rank second, then lower parameter count. Candidates must converge at at least 10 of the 12 anchors to qualify. Keep the remaining attempts and failures in the ledger. Evaluate the resulting fixed shortlist across the full validation year with weekly refits and half-hour state updates.

Before the full validation run, execute a training-only CPU and memory pilot. Seasonal period 48 may be expensive. Record fit counts, machine, runtime, peak memory, convergence, and the chosen numerical iteration cap. Bound the catalogue rather than launching an unconstrained automatic search.

If half-hourly computation is impractical, amend the protocol before test evaluation to use hourly models with seasonal period 24 and hourly job boundaries. Explicitly narrow the short-job claim. Do not upsample hourly forecasts and present the result as a half-hourly model.

For a planned hourly sensitivity, form an hourly target only when both original half-hours are observed, using their duration-weighted mean. Compare whole-hour jobs on the same hourly start grid under both model resolutions, with realized costs still derived from the original half-hours. Separately compare half-hour versus hourly oracle start grids to quantify the opportunity lost to coarser scheduling. Do not mix those two changes into a single unexplained resolution comparison.

Weekly seasonal SARIMA with period 336, deep learning, external weather models, and multivariate model searches are outside the default scope.

## 6. Forecast evaluation and uncertainty

### 6.1 Chronological evaluation

Use the proposed development, validation, and test years from section 1. A year may serve as evaluation data at one origin and later become past training data at a later origin. That is legitimate walk-forward operation.

Do not shuffle rows or use random train/test splits. Never fit transformations or decomposition on the full dataset before splitting.

At each origin:

1. Determine the eligible history from the availability rule.
2. Fit or update the model using only that history.
3. Produce the entire future path on the canonical target grid.
4. Persist the forecast before the evaluator reads future targets.
5. Score observed targets afterward.

When a parameter refit is weekly, use filtering updates rather than full-sample smoothing that conditions old state estimates on later observations. Do not reuse a final model artifact to fabricate earlier forecasts.

The primary output path has 48 future half-hours. Report endpoint lead times `h={1,4,12,24,48}` and cumulative path metrics. The optional 48-hour path has 96 slots.

Stop origins early enough that every target lies within its evaluation partition. At the validation boundary, do not score validation-origin forecasts against the locked test year. At the test end, exclude origins whose full path or job window extends beyond collected truth.

### 6.2 Metrics

Report MAE, RMSE, mean error, and daily-seasonal MASE in original gCO2/kWh, by lead time and season. The MASE scale uses only the origin's training data and observed valid seasonal pairs. Report an undefined scale rather than divide by zero.

Avoid MAPE as the main metric because low or zero carbon-intensity targets make percentage errors unstable.

Also report:

- MAE of integrated predicted emissions over candidate job windows.
- Rank agreement between predicted and realized candidate-window costs.
- Realized regret of the forecast-chosen start relative to the oracle start.
- Forecast failures, fallback frequency, and the number of scored targets per horizon.

Compute a common-origin comparison for model skill and a separate end-to-end result including fallback behavior. Otherwise a model could improve its score by failing on difficult periods.

### 6.3 Model and policy selection

Produce one validation-selected order per named effective family. Select a forecast champion by mean validation MAE across the declared lead times, with equal horizon weights.

Separately select a deployment model-policy pair by validation scheduling performance on the primary scenario, subject to feasibility and operational checks. Restrict the choice to the validated family finalists and simple baselines. Report when the forecast champion and scheduling choice differ.

Choose the strongest simple forecast baseline on validation only. Freeze both selections before looking at test scores. Ties within 1% validation loss favor the simpler model and lower operational cost. The 1% rule is a prespecified simplicity choice, not a statistical significance threshold.

The final test may reveal a different winner. Report that observation without silently changing the deployment candidate. Any post-test revision needs a new untouched evaluation period.

### 6.4 Intervals and inference

Produce 80% and 95% predictive intervals. Evaluate empirical coverage, interval width, and an interval score by lead time. State when Gaussian assumptions fail.

For job-cost uncertainty, use joint simulated forecast paths or a justified residual block procedure. Sum each simulated path's energy-weighted costs. Marginal interval widths cannot be added as if serial errors were independent.

For comparisons, calculate paired loss and savings differences on the same eligible cases. Aggregate or resample time blocks so overlapping forecast horizons and adjacent scheduling windows are not treated as independent observations.

Use a paired moving-block bootstrap with a 7-day primary block and 2,000 resamples. Report sensitivity to 3-day and 14-day blocks. The block length must be checked against development and validation dependence, then frozen. Resample the time axis first, not every job as an independent sample. For a queue simulation, retain contiguous episode or block totals and boundary treatment.

Use one declared primary scheduling contrast for inference. Treat model-family and scenario comparisons as secondary, with a multiplicity correction or explicitly descriptive intervals. Do not select a favorable p-value from many horizons and workloads.

Report effect size, uncertainty, complete sample counts, and failures. Statistical significance does not establish practical value.

## 7. Historical scheduling backtests

### 7.1 Energy and emissions accounting

For a job with interval-overlap energy `e_jk` in kWh and realized intensity `y_k`:

```text
Realized job CO2 in grams: C_j(s) = sum_k e_jk(s) * y_k
Predicted job CO2:         C_hat_j(s | o) = sum_k e_jk(s) * y_hat_k|o
Facility job energy:      e_jk = PUE * GPU_and_allocated_host_power_kW * overlap_hours
Savings in grams:         sum(C_baseline) - sum(C_policy)
Savings percentage:       100 * savings_grams / sum(C_baseline), if denominator > 0
```

Use duration overlap, not a count of touched slots. Convert watts to kW and minutes to hours explicitly. Do not multiply by PUE if energy is already facility-level.

For the core, fixed job energy is independent of start time. Power and PUE scenarios scale absolute CO2 but often cannot change start ranking or percentage savings. That is an algebraic property, not evidence of robustness to real variable energy.

Use explicitly synthetic parameters. Suggested illustrative default: 0.4 kW combined allocated IT power, PUE 1.2, known constant-power duration. This is not a measured GPU or whole-server profile. Sensitivities use 0.2 and 0.8 kW, PUE 1.0 and 1.5, and a declared nonconstant profile.

Primary accounting excludes idle capacity outside job execution and embodied hardware emissions. A secondary fixed-horizon facility scenario includes idle power for every policy on the same wall-clock horizon. Report which boundary each result uses.

Forecasting and scheduler computation also use energy. Log runtime and estimate the break-even overhead where measurement is unavailable. Report operational scheduling estimates separately from a complete net-emissions claim.

### 7.2 Primary experiment: isolated feasible jobs

This experiment isolates the value of temporal placement without queueing confounders. Each release represents an independent counterfactual job on an otherwise available GPU. The cases are not one simultaneous workload trace.

Let release be `r`, duration `L`, slack `S`, and hard deadline `d=r+L+S`. Feasible grid starts satisfy:

```text
s >= r
s + L <= d
every occupied interval is available
the forecast covers every occupied interval
```

At release time, choose the feasible start with minimum integrated predicted cost. Resolve exact ties by earliest start. Commit that choice once. Primary jobs do not repeatedly postpone themselves when newer forecasts arrive.

Default scenario: a 2-hour job with 10 hours of slack, hence a deadline 12 hours after release. Test a duration grid of 0.5, 1, 2, and 4 hours and slack grid of 0, 2, 6, 12, and 20 hours. All windows fit the 24-hour core horizon.

Use releases every 3 hours across the evaluation year. Label overlapping cases as correlated counterfactuals. Weight seasons explicitly and bootstrap calendar blocks. Do not present these cases as a schedulable combined trace.

Compare exactly the same jobs under:

| Policy | Information and purpose |
| --- | --- |
| Earliest feasible | Execute at release. Carbon-unaware primary control. |
| Seeded random feasible | Diagnostic showing the opportunity distribution. Not the primary comparator. |
| Calendar-mean schedule | Past-only predictable timing without a complex model. |
| Daily and weekly seasonal-naive schedules | Test the value of cheap forecasts. |
| Validation-selected classical schedules | Translate forecast paths to identical optimization rules. |
| Carbon oracle | Use realized future intensity with the same job constraints. Unattainable opportunity bound, never a deployable policy. |
| NESO schedule, conditional | Include only when issue-stamped historical forecasts are independently verified. Otherwise prospective display only. |

Record release, decision time, duration, deadline, information cutoff, candidate costs, chosen start, forecast ID, policy, fallback reason, realized grams, and oracle regret.

### 7.3 Secondary core experiment: shared GPU capacity

Run a bounded one-GPU queue replay to test whether isolated-job benefits survive contention. Capacity is one job at a time. Jobs are non-preemptive, and their declared duration and profile are known.

Generate synthetic arrivals independently of the carbon series. Freeze the trace specification before test scoring. Use durations of 1, 2, and 4 hours with probabilities 0.5, 0.3, and 0.2, respectively. Expected duration is 1.9 hours. Use nominal offered loads of 0.3, 0.6, and 0.85, with seeds 1729, 2718, and 31415 for each load. Default slack is 6 hours beyond duration. A separately declared 12-hour-slack scenario tests flexibility.

For Poisson arrivals, set `lambda = offered_load / expected_duration_hours`. Snap release times upward to the half-hour grid and report the actual post-discretization offered load. Nominal load below one does not guarantee deadline feasibility.

Replay a continuous trace with a 48-hour warm-up before the test year. Score only test-year releases whose entire feasible window ends within the test year. Stop arrivals at least 24 hours before the end and drain accepted jobs. Warm-up jobs affect reservations but do not enter test savings totals. Use the same warm-up, horizon, and trace for every policy. If truth is missing, apply the common feasible-window eligibility rule before policy scoring and report exclusions. Do not reset capacity at each reported monthly boundary.

Keep every offered job in the queue replay even if its later outcome cannot be scored because of missing truth. Apply future completeness masks only in the evaluator after decisions exist. Removing jobs based on future data availability would change reservations and give the remaining decisions information unavailable at arrival.

Use a reservation policy at arrival:

1. Reveal only newly arrived jobs and previously committed reservations.
2. Find all duration-length free runs before the job deadline.
3. Compare earliest-feasible reservation with forecast-minimum-cost reservation.
4. Keep prior accepted reservations immutable.
5. Reject infeasible requests with an explicit reason. Never erase them.

This policy is deliberately simple and reproducible. It is not globally optimal and cannot guarantee service for unknown future arrivals.

Compare earliest-feasible reservation, the validation-selected strongest simple-forecast reservation, and the locked deployment model-policy reservation. Report deadline misses and rejection rates on the same offered trace. Compare CO2 for jobs completed by all compared policies, and report each policy's total completed work, energy, emissions, and unmatched jobs separately. A lower total caused by rejecting work is not a carbon saving.

The completion intersection is a post-policy subset and can itself be selective. Its emissions comparison is descriptive when accepted sets differ. A whole-trace fixed-work savings claim requires the same offered jobs to complete under every compared policy. Otherwise report the emissions-service tradeoff and unmatched workload explicitly, with no claim that the queue test establishes H2.

Optional small-batch offline optimization uses OR-Tools CP-SAT, with all known jobs, capacity, and deadlines. Distinguish a carbon-only oracle with online arrival knowledge from a full-trace oracle that also sees future arrivals. Use exact or certified bounds only when solver status supports them.

A rolling reoptimization policy, multi-GPU placement, heterogeneous hardware, and preemption are extensions. They are not needed to answer the primary question.

### 7.4 Scheduling metrics and research conclusions

Report aggregate grams, aggregate percentage savings, median and tail waiting time, completion and rejection rates, deadline misses, fallback rates, and regret against the oracle. Include per-month results and every declared duration/slack scenario.

Calculate opportunity captured only when the earliest-feasible-to-oracle gap is positive and at least 1% of earliest-feasible emissions. This prespecified reporting threshold avoids unstable ratios. Always report the absolute gap and the number of excluded ratio cases. When opportunity is zero, report it directly.

Prespecify a practical threshold of 5% aggregate savings for the primary scenario. This is a project decision threshold, not a predicted result. Show sensitivity to thresholds of 2% and 10%.

| Outcome | Allowed conclusion |
| --- | --- |
| Positive paired savings interval against earliest execution, zero primary deadline misses | Evidence of modeled scheduling benefit under the declared assumptions. |
| Also improves against the strongest validation-selected simple forecast | Evidence that the classical forecasting choice adds scheduling value beyond that baseline. |
| Savings interval overlaps zero | Inconclusive benefit. Report estimate and uncertainty. |
| Negative savings | The tested policy increases modeled emissions. |
| Lower CO2 because jobs were rejected or unfinished | No valid fixed-workload savings claim. |
| Benefit exists only with large slack, isolated jobs, or high oracle opportunity | Narrow the conclusion to those conditions. |
| Net overhead is unmeasured or historical vintages are absent | No verified net-real-world or fully as-issued deployment claim. |

In the primary known-duration isolated setting, every accepted job must meet its deadline by construction. Queue rejection and duration-error stress tests require their own service metrics.

## 8. Implementation architecture

### 8.1 Chosen shape

Use one Python package with pure scheduling logic, a trusted forecast adapter, immutable run artifacts, and a thin Streamlit client. The notebook and dashboard call the same package.

Knowledge ownership matters more than splitting every pipeline step into a separate module:

| Module | Owns | Does not own |
| --- | --- | --- |
| `data.py` | Official acquisition, interval interpretation, provenance, quality masks, and as-of history views | Model order or scheduling policy. |
| `forecasting.py` | Model catalogue, fitted transform state, parameter fits, causal state updates, path forecasts, artifact compatibility | Realized future targets or workload execution. |
| `scheduling.py` | Job contracts, candidate windows, reservations, integrated predicted cost, tie-breaking | API calls or future truth. |
| `replay.py` | Clock, information revelation, policies, and persisted decisions | Statistical interpretation of final results. |
| `evaluation.py` | Target joins, metrics, paired blocks, exclusions, and evidence tables | Online decisions. |
| `artifacts.py` | Atomic run storage, hashes, bundle compatibility, and result lookup | Model mathematics or policy choices. |
| `cli.py` | Thin command entry points into package operations | A second implementation of collection, forecasting, or simulation. |
| `app/streamlit_app.py` | Controls, visualizations, session-local scenarios, and result display | Training on each rerun or duplicated scientific calculations. |

### 8.2 Caller usage before types

Proposed commands below are an implementation contract. They are not available or tested in this planning phase.

```powershell
uv sync --frozen
uv run gridshift collect --config configs/study.yaml
uv run gridshift audit --manifest data/manifest.json
uv run gridshift study --config configs/study.yaml --stage validation
uv run gridshift freeze --config configs/study.yaml
uv run gridshift study --config configs/study.yaml --stage test
uv run gridshift backtest --config configs/study.yaml --stage test
uv run gridshift export --run-id <verified-run-id>
uv run jupyter nbconvert --execute --to html notebooks/01_gridshift_study.ipynb
uv run pytest
uv run streamlit run app/streamlit_app.py
```

The CLI must reject a test run if no compatible frozen validation protocol exists. A rerun with the same inputs uses the same content-derived experiment identity or produces an explicitly separate attempt, never overwrites accepted evidence.

Proposed library call sites:

```python
# Notebook: fit and evaluate without reimplementing the package.
run = study(protocol=validated_protocol, dataset=frozen_dataset)

# Live recommendation: only an as-of view reaches the forecaster.
history = dataset.as_of(decision_time, availability_policy)
path = forecaster.predict(history, start=decision_time, slots=48)
decision = recommend(job, path, reservations)

# Historical replay: future truth is available only to the evaluator.
decisions = replay(policy, released_jobs, forecast_store, protocol)
scores = evaluate(decisions, realized_series, evaluation_spec)
```

### 8.3 Domain types and interfaces

These are design signatures, not executable source:

```text
UtcInterval(start, end)
  Offset-aware, positive duration, grid-aligned.

ObservedHistory(intervals, values, observed_mask, cutoff, dataset_hash)
  No observation's modeled or verified availability exceeds cutoff.

ForecastPath(issued_at, target_intervals, expected_intensity,
             predictive_distribution, model_id, training_cutoff,
             source_hash, availability_basis, status)
  Ordered complete target grid, original units, no future target observations.

GpuJob(id, released_at, duration, deadline, energy_profile, scenario_id)
  Positive duration, deadline >= release + duration, declared accounting boundary.

ReservationCalendar(capacity, committed_intervals)
  Only accepted reservations occupy capacity. All mutations have one replay owner.

Decision = Scheduled(start, finish, forecast_id, predicted_grams)
         | Infeasible(reason)
         | Unavailable(reason)
  Rejection is not a zero-emission completed job.

FittedBundle(model_spec, parameters, transform_state, train_end,
             data_hash, protocol_hash, library_versions, interval_grid)
  Trusted local artifact with explicit compatibility checks.

fit(history, model_spec) -> FittedBundle
predict(bundle, history, request) -> ForecastPath | ForecastFailure
recommend(job, path, calendar) -> Decision
replay(policy, arrivals, forecast_store, protocol) -> DecisionTable
evaluate(decisions, truth, evaluation_spec) -> EvidenceTables
```

Use typed Python dataclasses and enums, with boundary validation for timestamps, units, arrays, and configuration. Avoid passing raw API dictionaries into the scheduler.

A forecaster receives only an `ObservedHistory`. A scheduler receives only a `ForecastPath`, the current job, and revealed reservations. Neither can access the full truth series. The evaluator owns that series. This separation makes hindsight leakage harder to introduce.

Store simulation paths separately from the compact point-forecast table when their size requires it. Do not force the dashboard to load every historical model state.

### 8.4 Planned repository

```text
gridshift/
  README.md
  pyproject.toml
  uv.lock
  configs/
    study.yaml
    workloads.yaml
    deployment.yaml
  src/gridshift/
    data.py
    forecasting.py
    scheduling.py
    replay.py
    evaluation.py
    artifacts.py
    cli.py
  app/streamlit_app.py
  notebooks/01_gridshift_study.ipynb
  tests/
    fixtures/
    test_data.py
    test_forecasting.py
    test_information_boundaries.py
    test_scheduling.py
    test_replay.py
    test_artifacts.py
    test_app.py
  data/
    raw/
    normalized/
    manifest.json
  artifacts/runs/<run_id>/
    protocol.json
    quality.json
    stationarity.csv
    fits.parquet
    forecasts.parquet
    jobs.parquet
    decisions.parquet
    metrics.parquet
    figures/
  models/<model_id>/
  reports/
  slides/
```

Use pandas, NumPy, SciPy, statsmodels, Matplotlib or Plotly, Streamlit, PyArrow, pytest, and nbconvert. Use Hypothesis for temporal properties if useful. OR-Tools is needed only for the optional optimizer. Pin versions after a compatible local environment is verified.

No database, message broker, Kubernetes, GPU dependency, or separate REST service is required. Forecasting runs on CPU. Frozen Parquet and JSON files are sufficient for this project.

### 8.5 Alternatives and accepted tradeoffs

An artifact-first package keeps the scientific state inspectable and lets the notebook, CLI, and dashboard share calculations. Its interface hides API normalization, model-state handling, and replay eligibility without requiring callers to coordinate those internals.

A Streamlit-first notebook-style application is faster to start but exposes experiment state through UI callbacks. It encourages duplicated calculations, accidental refitting, and session-dependent results. Reject that shape.

A continuously running forecast service with a queue database and background workers separates live operations well but adds deployment, concurrency, and persistence work unrelated to the research question. Keep it as a future operational architecture, not this mini-project's default.

Accept offline artifact generation in exchange for reproducible evaluation and a responsive dashboard. Accept a simple reservation scheduler in exchange for traceable decisions. Do not confuse those choices with proven global optimality.

### 8.6 Synthesis record

Two independent read-only candidates used the configured Azure Luna Max worker role. This is independent analysis within one model family, not model or provider diversity. The parent retained source verification, design decisions, and final acceptance.

Candidate A preferred an artifact-first runner over a public stage-by-stage analysis library. Candidate B preferred a compact DataFrame-oriented research package over a ports-and-adapters service design. The chosen base combines the artifact-first runner with small validated boundary types. It avoids exposing cleaning, differencing, and future-truth joins as operations the dashboard must coordinate.

Adopted from Candidate A: shared result artifacts for academic outputs and explicit rejection of work-dropping savings. Adopted from Candidate B: one scientific package for notebook and dashboard, and a distinction between known-job and full-arrival-foresight oracles.

Both candidates proposed the portal archive and a longer default history. The final plan instead uses the explicit-interval API and four recent complete years, because portal boundary semantics still need a crosswalk and the extra older history is not required for the rolling-window study. Candidate A's short-horizon emphasis is extended to a 24-hour path to cover the proposed deadline windows. An additional 2026 replication remains outside the core.

The source claims were checked against official material and direct root API probes. Candidate statements are not experimental evidence. A separate read-only verification pass inspected both saved documents and found no blocking or major defects in requirements coverage, information boundaries, scheduling methodology, architecture, or scope.

## 9. Dashboard, deployment, and academic outputs

### 9.1 Streamlit dashboard

The first screen is the scheduling workspace, not a landing page. Use a restrained light interface, compact controls, readable tables, and consistent units. Carbon severity may use color, but never color alone. Reserve prominent text for the project name and current decision.

Provide five views:

| View | Content and actions |
| --- | --- |
| Schedule | Release, duration, deadline, power, PUE, model, recommended start, feasible alternatives, integrated expected CO2, uncertainty, and timeline. |
| Forecasts | Estimated actual history, forecast path, issue time, last eligible observation, uncertainty bands, and baseline comparison. |
| Model comparison | Validation and test results clearly separated, lead-time metrics, selected orders, AIC/BIC comparable groups, residual diagnostics, failures. |
| Backtests | Frozen scenario filters, savings, service metrics, regret, month and slack comparisons, and decision-table download. |
| Data and evidence | Coverage, missingness, source licence, retrieval time, data hash, protocol, bundle version, and citations. |

Use numeric inputs and datetime controls for workloads, a model selector, scenario filters, a refresh command, and downloads. Do not add arbitrary free-text code, artifact upload, or model execution.

Test states include loading, no feasible slot, missing forecast coverage, stale observations, API failure, incompatible model bundle, unknown actual outcome, and zero opportunity. Clearly separate simulated historical results from live predicted recommendations.

A live prediction is not a realized saving. Show predicted differences with uncertainty, not a success badge or guaranteed percentage reduction.

### 9.2 Local model deployment

Deployment means packaging and loading a validated trusted model inside the local Streamlit application. It does not mean GPU job execution or public hosting.

The bundle includes parameters, model order, transform state, training cutoff, data and protocol hashes, seasonal period, required library versions, and bundle schema. Load only project-produced trusted artifacts. Do not deserialize untrusted pickle uploads.

At startup, verify bundle compatibility and forecast reproducibility on a held-out fixture. Cache the bundle and immutable artifacts by hash. UI reruns must not trigger model training or rewrite evidence.

Update live observations with explicit timeouts and bounded retries. When the last observed interval is more than two hours old, mark the input stale and disable the carbon recommendation by default. The user may still view historical results. For missing coverage or model failure, recommend earliest feasible execution only when its feasibility is known, label the fallback, and make no carbon-saving claim.

Evaluate retraining offline. Promote a new model only through a new versioned validation result. Keep rollback to the last trusted bundle.

An optional prospective collector may record 7-14 days of issue-stamped NESO forecasts after separate authorization. That supports a small genuine as-issued comparison, not a replacement for the year-long test.

Public Streamlit hosting, authentication, continuous jobs, remote infrastructure, and paid compute require separate approval. No external publication is authorized by this plan.

### 9.3 Reproducible notebook

Use one executed notebook with these sections:

1. Question, scope, units, source, and frozen configuration.
2. Collection audit, missingness, and training EDA.
3. ADF, transformations, differencing, decomposition, and ACF/PACF.
4. AR, MA, ARMA, ARIMA, and SARIMA explanations and fitted examples.
5. Lag selection, comparable AIC/BIC tables, convergence, and residual diagnostics.
6. Chronological forecast comparisons and predictive uncertainty.
7. Primary and queue scheduling backtests.
8. Sensitivities, negative outcomes, limitations, and deployment demonstration.

The notebook imports the package and reads frozen artifacts. It must execute offline once the documented dataset is present. Explain which command performs fresh acquisition. Save an HTML export and the exact environment and run IDs.

### 9.4 Report and presentation

Plan a 15-25 page report excluding appendices, adjusted to the course rubric. Include an abstract, question, literature and data, quality audit, time-series methods, evaluation, scheduling formulation, observed results, deployment, limitations, conclusion, and references.

Generate tables and figures from accepted artifacts. Every claim must point to a figure, table, or run. Include unsuccessful models, null outcomes, incomplete coverage, and protocol amendments. Keep proposed thresholds distinct from observed results.

Use 10-12 presentation slides: problem, scope, data, diagnostics, models, validation design, scheduler, forecast outcomes, scheduling outcomes, dashboard, limitations, and conclusion. Include speaker notes and a backup slide for equations and failure cases.

Until experiments run, outcome sections remain labeled "Not evaluated". Do not insert illustrative savings into result charts.

## 10. Tests and acceptance gates

Tests verify implementation contracts, not that the preferred model wins.

### 10.1 Required executable checks

| Area | Positive case | Negative or adversarial case |
| --- | --- | --- |
| API contract | Valid response produces an ordered normalized series. | 429, timeout, HTML body, malformed schema, null fields, and partial response. |
| Boundaries | Explicit UTC day becomes exactly 48 expected grid slots. | Raw preceding interval and overlapping chunks cannot add an extra slot. |
| Daylight saving | 46-slot and 50-slot civil-day responses preserve valid UTC timestamps. | Naive local timestamps and ambiguous repeated times are rejected or resolved explicitly. |
| Quality | Zero values remain observed. Identical duplicates are audited. | Conflicting duplicates, negative values, NaN-as-zero, and irregular intervals cannot pass silently. |
| Missing data | Past-only donor or short forward fill is marked. | Changing future values cannot change a historical fill. Long outages are not disguised. |
| Information boundary | Eligibility follows interval end plus delay. | Mutation of all post-cutoff truth leaves the forecast and decision unchanged. |
| Forecast alignment | Correct 48-slot path starts at the requested origin. | The delayed unobserved bridge cannot cause an off-by-one horizon. |
| Transform | Differencing and identity inverse paths reconstruct known levels. | Wrong anchors, incompatible state, log-median-as-mean, and invalid Box-Cox inputs. |
| Classical models | Known synthetic AR and seasonal fixtures exercise each supported family. | Unconverged fits, invalid trends, unsupported orders, and nonfinite predictions cannot win selection. |
| Metrics | Hand-computed fixture matches MAE, RMSE, MASE, and CO2. | Zero MASE or savings denominators return explicit undefined values. |
| Energy integration | A constant-intensity job matches analytical kWh times gCO2/kWh. | Watts interpreted as kW, PUE applied twice, or whole slots counted for partial overlap. |
| Scheduling | Two known windows choose the lower integrated cost. | The lowest single point with a dirty remainder must lose. |
| Feasibility | Release, duration, hard deadline, and reservations all hold. | Too-long jobs, incomplete forecasts, and overlapping reservations return failure. |
| Flat carbon | Earliest feasible tie-breaking is deterministic. | Arbitrary delay cannot appear as a carbon improvement. |
| Oracle | Small cases agree with exhaustive enumeration. | An online forecast policy cannot use the oracle's future intensity. |
| Queue replay | Identical seeded arrivals reach each policy. | Unknown future arrivals cannot affect an earlier reservation. Rejections remain in totals. |
| Work equivalence | Same completed work supports paired emissions comparison. | Dropped work cannot count as savings. |
| Statistical blocks | Paired time-block resamples keep policies aligned. | IID job resampling cannot be the default for overlapping windows. |
| Artifacts | Trusted compatible bundle reloads within tolerance. | Wrong library version, protocol hash, corrupted file, and untrusted artifact fail closed. |
| Reproducibility | Offline run and notebook regenerate accepted tables. | Different seeds or data revisions cannot overwrite the same accepted run unnoticed. |
| Dashboard | Controls update recommendation and evidence consistently. | Stale data, infeasible job, API failure, missing results, and mobile layout remain readable. |

Use Streamlit `AppTest` for control and state behavior. Use browser screenshots for layout at desktop and mobile widths in the eventual implementation. Unit tests alone do not establish a usable interface.

### 10.2 Scientific acceptance gates

| Gate | Required evidence | Failure action |
| --- | --- | --- |
| G0: Planning | Requirements map, primary sources, methodology, architecture, and scope | Resolve planning defects before implementation. |
| G1: Data | Complete acquisition audit, hashes, licence, null and duplicate ledger | Do not train on an unexplained blended or malformed target. |
| G2: Diagnostics | Executed development EDA, stationarity and seasonal analysis | Amend representations with a documented training-only reason. |
| G3: Validation | All required families and baselines, comparable selection, failure ledger | Keep simple fallback. Do not force a complex winner. |
| G4: Protocol freeze | Sealed configuration, model and policy choices, exclusions, metrics, seeds | Test command refuses unsealed or incompatible protocol. |
| G5: Forecast test | Locked chronological results with counts, uncertainty, and fallbacks | Report failure, null skill, or limited horizons honestly. |
| G6: Scheduling | Feasible fixed-work comparisons, realized target scores, oracle and uncertainty | No savings claim from incomplete work or hindsight decisions. |
| G7: Deployment | Bundle reload, live-path state handling, local dashboard user-path tests | Historical analysis can complete while deployment remains incomplete. |
| G8: Academic package | Executed notebook, report, slides, tests, and claim traceability | Do not mark the project complete from the dashboard alone. |

A negative scientific answer can pass G5 and G6. A broken simulator or leaking comparison cannot.

## 11. Implementation sequence and boundaries

### 11.1 Ordered work packages

Effort estimates are planning estimates for one developer, not commitments.

| Package | Work and output | Dependency | Estimate |
| --- | --- | --- | --- |
| W1 | Environment, domain contracts, source collector, raw manifest, interval fixtures | Approved build scope | 2 days |
| W2 | Coverage audit, missing-data policy, training EDA, notebook foundation | W1 | 2 days |
| W3 | ADF, transformations, decomposition, ACF/PACF, model demonstrations | W2 | 2-3 days |
| W4 | Bounded search, fit pilot, validation forecasts, uncertainty, failures | W3 | 3-4 days |
| W5 | Primary scheduler, energy integration, controls, oracle, adversarial tests | W1; validation for selection | 2 days |
| W6 | Queue replay, service accounting, sensitivity configuration | W5 | 1-2 days |
| W7 | Freeze protocol, run untouched test, paired inference, generated evidence | W4-W6 | 2-3 days |
| W8 | Trusted bundle, local deployment, Streamlit views and user-path tests | W7 | 2-3 days |
| W9 | Executed notebook, report, slides, reproducibility and final review | W7-W8 | 2-3 days |

Budget roughly 18-24 working days plus actual experiment runtime and course-review time. Preserve W1-W7 rigor if time is tight. Reduce extensions and visual extras before weakening evaluation.

At every package, retain a runnable tested state and evidence for its gate. Do not build the dashboard first and retrofit a scientific comparison afterward.

W5 can begin after W1 using synthetic carbon fixtures while W4 runs. Its final scientific comparison still waits for validation-selected forecasts. W7 is the only package allowed to evaluate locked test outcomes.

### 11.2 Hard core scope

Official national NESO data, half-hourly univariate classical forecasting, all requested ATS topics, chronological comparisons, isolated and one-GPU reservation backtests, modeled operational CO2, local trusted model deployment, Streamlit dashboard, notebook, report, slides, and tests.

### 11.3 Optional work after the core

Hourly aggregation sensitivity, 48-hour forecasts, prospective issue-stamped official forecast comparison, a small offline CP-SAT oracle, variable energy profiles, duration-error stress tests, and a limited telemetry demonstration.

Optional work must not delay the core or replace a required syllabus item. Describe every additional comparison before examining its test outcome.

### 11.4 Explicit exclusions

- Real GPU scheduling, Slurm submission, Kubernetes integration, or cloud job execution.
- Paid compute, external deployment, public hosting, publication, or repository pushes.
- Deep learning, reinforcement learning, weather-driven forecasting, or broad AutoML.
- Spatial migration, regional observed-target assumptions, electricity-price optimization, or demand-response control.
- Full lifecycle CO2e, embodied-carbon allocation, marginal-emissions estimation, or official carbon-accounting certification.
- A proof of optimal online multi-job scheduling or guaranteed feasibility for unknown future arrivals.
- Invented measurements, savings, statistical significance, or claims of a best model before evaluation.

### 11.5 Risks and stop conditions

| Risk | Mitigation | Stop or limit condition |
| --- | --- | --- |
| Incomplete or revised source data | Frozen raw snapshots, quality masks, source-specific provenance | Unexplained coverage or target definition blocks scientific runs. |
| Future leakage | As-of types, strict module access, mutation tests | Any affected forecast or decision invalidates the run. |
| Weak baseline | Persistence, daily, weekly, and calendar controls | No added-model-value claim without beating the declared simple comparator. |
| Nonstationarity and structural change | Rolling windows, seasonal and year diagnostics | Narrow conclusions if one regime drives the effect. |
| Seasonal model cost | Training-only pilot and bounded catalogue | Amend resolution before test, not after an inconvenient result. |
| Poorly calibrated uncertainty | Coverage diagnostics and joint path simulation | No risk-aware guarantee from unvalidated intervals. |
| Selection over many scenarios | One primary contrast, frozen secondary set, block inference | No cherry-picked best-case conclusion. |
| Unrealistic energy or queue assumptions | Synthetic labels, service accounting, explicit boundaries | No measured-GPU or production claim without new evidence. |
| API outage or stale state | Offline artifacts, availability flags, earliest-feasible fallback | Disable live carbon recommendation when input is stale or incomplete. |
| Scope expansion | Complete required deliverables before optional infrastructure | New external, sensitive, or irreversible work needs separate authorization. |

### 11.6 What is authorized now

This phase authorizes source investigation and planning documents only. It does not authorize building the application, collecting the full experimental dataset, training models, running scheduling experiments, creating public deliverables, or operating GPU resources.

The next implementation step, after build authorization, is W1: establish interval and information contracts, then implement the collector against the verified boundary fixtures.

## 12. Current status

G0 planning acceptance: **PASS**. The plan and source audit are complete planning deliverables. Structure checks confirmed 23 distinct requirements, nine acceptance gates, nine work packages, balanced code fences, and the 70,128-slot expected UTC grid calculation. Independent read-only review found no blocking or major defects.

No application, full dataset collection, model training, scheduling experiment, notebook, report, presentation, or deployment was implemented in this phase. No implementation tests were run. Full data completeness, stationarity, selected orders, forecast skill, scheduling benefit, and deployed application behavior are all **NOT EVALUATED**.

Success for GridShift means a complete, reproducible, scientifically honest project. It does not require a complex model to beat a simple baseline or a scheduler to save carbon.
