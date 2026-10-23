# GridShift source audit

Audit date: 22 October 2026. This is a planning investigation, not an experimental-results document.

## 1. What was checked

The investigation used first-party NESO pages, the official Carbon Intensity API documentation, live read-only API requests, the publisher-linked methodology PDF, statsmodels documentation, and the authors' forecasting textbook.

No complete research dataset was downloaded. No forecasting model, scheduling experiment, notebook, dashboard, or application was built or run. Small API responses establish availability and schema behavior only. They do not establish complete coverage, stationarity, forecast accuracy, or scheduling savings.

## 2. Source register

| ID | Source | Use in the plan |
| --- | --- | --- |
| S1 | [Official GB Carbon Intensity API](https://api.carbonintensity.org.uk/) | Publisher, available national endpoints, forward forecast endpoint, API licence link. |
| S2 | [Official API definitions](https://carbon-intensity.github.io/api-definitions/) | Interval schema, estimated actual versus forecast, units, UTC timestamps, request limits. |
| S3 | [NESO national carbon-intensity dataset](https://www.neso.energy/data-portal/national-carbon-intensity-forecast) | Official alternative archive and dataset-specific licence metadata. |
| S4 | [NESO national resource dictionary](https://www.neso.energy/data-portal/national-carbon-intensity-forecast/national_carbon_intensity_forecast) | Meaning of `datetime`, `actual`, `forecast`, and `index`. |
| S5 | [Publisher-linked methodology PDF](https://api.neso.energy/dataset/f406810a-1a36-48d2-b542-1dfb1348096e/resource/36638178-e993-4d34-afdc-4ada83993585/download/neso-ci-national-methodology_v2.pdf) | Emissions boundary and timing of estimates. |
| S6 | [API terms](https://github.com/carbon-intensity/terms) | CC BY 4.0, attribution, rate limiting, availability limitations, and no implied endorsement. |
| S7 | [NESO Open Data Licence](https://www.neso.energy/data-portal/neso-open-licence) | Separate licence for associated portal datasets. |
| S8 | [Historic generation mix and carbon intensity](https://www.neso.energy/data-portal/historic-generation-mix) | Why a longer, publisher-cleaned archive is not an interchangeable raw target. |
| S9 | [Forecasting: Principles and Practice, forecasting toolbox](https://otexts.com/fpp3/toolbox.html) | Rolling-origin evaluation, multi-step errors, baselines, and uncertainty. |
| S10 | [Forecasting: Principles and Practice, ARIMA](https://otexts.com/fpp3/arima.html) | Differencing, ARIMA families, order selection, and information-criterion comparisons. |
| S11 | [statsmodels ADF documentation](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.adfuller.html) | Null hypothesis, deterministic terms, lag selection, and returned diagnostic fields. |
| S12 | [statsmodels SARIMAX documentation](https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAX.html) | Seasonal model specification and state-space implementation. |
| S13 | [statsmodels model selection and missing-data example](https://www.statsmodels.org/stable/examples/notebooks/generated/statespace_sarimax_internet.html) | Missing observations in state-space models and failed model fits. |

The `stable` statsmodels website is mutable. The eventual project must cite and lock the installed release, not infer its version from this audit.

## 3. Verified source facts

### Official series and units

NESO owns the official GB API. The national response contains explicit `from` and `to` boundaries, an estimated `actual`, a separate `forecast`, and a categorical `index`. The numerical intensity unit is gCO2/kWh. The national from/to endpoint documents a maximum request span of 14 days. The statistics endpoints document 30 days. Use 7-day collection chunks as a conservative project choice, not as an asserted service limit. Sources: S1, S2, S4.

### Emissions and availability boundary

The publisher-linked PDF has three pages and an issue date of May 2024. It describes electricity-generation CO2 estimates, not a complete lifecycle or all-GHG inventory. Its method includes imports and losses and states that estimates arrive at the end of half-hour periods. It also describes embedded-generation visibility limitations and forecasts up to 48 hours ahead. A publication statement is not a measured latency guarantee. Sources: S2, S5.

The PDF was downloaded for read-only inspection. SHA-256:

```text
85da2e8977fc369bdd43eca613b7f0ffe8a6374afc1ae39d0228e7ccb4188594
```

The linked file uses regional wording in parts of the document despite appearing under the national dataset. Its GB formula and national API schema support the national study. Do not use its regional discussion as evidence that regional `actual` observations are available.

### Historical forecast provenance

The ordinary API response and inspected portal schema do not contain a forecast issue timestamp or an archive of all revisions. Therefore, this audit cannot establish the lead time or original availability of a historical `forecast` value.

This is a limit of the inspected interfaces, not proof that NESO has no forecast-vintage archive anywhere. A later archived-forecast comparison requires evidence of issue time, target time, revision identity, and historical availability.

### Licensing

The API terms link CC BY 4.0. The associated national portal dataset lists the NESO Open Data Licence. Preserve the licence of the chosen acquisition channel and the attribution record. The portal licence requests the statement "Supported by National Energy SO Open Data". Neither channel authorizes implied NESO endorsement or unrestricted logo use. Sources: S3, S6, S7.

### Longer alternative archive

The historic generation-mix page states that data begin in 2009, that seasonal decomposition corrects missing or irregular observations, and that cleansing can revise the data. It is useful context, but it must not silently replace or fill gaps in the API target. That would change both provenance and the missing-data experiment. Source: S8.

## 4. Live API spot checks

Requests below succeeded on 22 October 2026. Counts describe raw responses, before normalization.

| Request | Raw intervals | First `from` | Last `to` | Null `actual` |
| --- | ---: | --- | --- | ---: |
| `/intensity/date/2017-09-26` | 48 | 2017-09-25T23:00Z | 2017-09-26T23:00Z | 0 |
| `/intensity/date/2022-01-01` | 48 | 2022-01-01T00:00Z | 2022-01-02T00:00Z | 0 |
| `/intensity/date/2023-07-01` | 48 | 2023-06-30T23:00Z | 2023-07-01T23:00Z | 0 |
| `/intensity/date/2024-03-31` | 46 | 2024-03-31T00:00Z | 2024-03-31T23:00Z | 0 |
| `/intensity/date/2024-10-27` | 50 | 2024-10-26T23:00Z | 2024-10-28T00:00Z | 0 |
| `/intensity/date/2025-07-01` | 48 | 2025-06-30T23:00Z | 2025-07-01T23:00Z | 0 |

All six responses had unique `from` values and non-null `forecast` values. These small samples say nothing about unqueried dates.

The date endpoint behaves like civil-day selection in these samples. UTC response timestamps do not imply a UTC date window. The 46-slot and 50-slot responses are expected civil-day lengths around daylight-saving changes, not automatically missing or duplicate data.

Explicit UTC range checks:

| Request | Raw intervals | First `from` | Last `to` |
| --- | ---: | --- | --- |
| `/intensity/2025-01-01T00:00Z/2025-01-02T00:00Z` | 49 | 2024-12-31T23:30Z | 2025-01-02T00:00Z |
| `/intensity/2024-03-31T00:00Z/2024-04-01T00:00Z` | 49 | 2024-03-30T23:30Z | 2024-04-01T00:00Z |
| `/intensity/2024-10-27T00:00Z/2024-10-28T00:00Z` | 49 | 2024-10-26T23:30Z | 2024-10-28T00:00Z |

For these requests, retain intervals satisfying `from >= requested_start` and `to <= requested_end`. This yields 48 half-hours per complete UTC day. Adjacent chunks need the same boundary rule before deduplication.

The January range included a preceding interval with `actual=51` and ended with an interval with `actual=67`. These are source-response examples, not experimental outcomes.

## 5. Portal schema probe

The following read-only request succeeded:

```text
https://api.neso.energy/api/3/action/datastore_search?resource_id=0e5fde43-2de7-4fb4-833d-c7bca3b658b0&limit=2&sort=datetime%20asc
```

The reported total was 155,839 rows at retrieval time. This is mutable archive metadata, not the number of usable observations in GridShift.

Returned field IDs were `_id`, `datetime`, `forecast`, `actual`, and `index`. The first two sorted timestamps were `2018-01-01T00:00:00` and `2018-01-01T00:30:00`. Neither record contained forecast-vintage metadata.

The API supplied earlier spot-check data than the beginning of this portal resource. Do not claim identical coverage or silently combine the channels. Portal `datetime` start-versus-end interpretation must be checked against overlapping API intervals before any substitution.

## 6. Unresolved facts and next evidence

| Unknown | Consequence | Required next evidence |
| --- | --- | --- |
| Full 2022-2025 coverage and all gap patterns | The proposed split is provisional. | Complete frozen collection, UTC-grid audit, and monthly coverage table. |
| Actual publication latency and revision history | Historical replay is pseudo-real-time, not a perfect as-of reconstruction. | Timestamped prospective snapshots or a verified vintage archive. |
| Historical NESO forecast issue times | No fair scored historical NESO competitor yet. | Issue-stamped archived forecasts. |
| Stability, daily seasonality, and weekly effects | No differencing order or model can be declared best. | Training-only EDA and diagnostics. |
| Practical seasonal-fit cost | No runtime promise for the full experiment. | Small training-only fit pilot with recorded machine and software. |
| GPU energy and job-duration profiles | Workload emissions remain modeled. | Optional authorized telemetry with a documented measurement boundary. |
| Forecast skill and scheduling benefit | The research question remains unanswered. | Frozen validation protocol and untouched chronological test. |

## 7. Investigation limitations

The first sandboxed HTTP request failed DNS resolution. Approved read-only requests then succeeded. An initial PDF text extraction encountered the Windows output encoding; UTF-8 extraction succeeded. These are tool-environment issues, not evidence of NESO downtime or malformed data.

Some NESO web pages required JavaScript for their embedded explorer. The independent API requests supplied the schema checks. The audit did not infer service uptime from the presence of a web page.

Small spot checks deliberately stop short of a completeness audit or any scientific certification. Recheck mutable endpoints, licences, and metadata at the eventual data freeze.
