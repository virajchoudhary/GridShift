# Review and share GridShift

GridShift studies whether short-term forecasts of Great Britain's carbon
intensity improve deadline-constrained GPU workload scheduling. It combines
official NESO data, classical time-series experiments, scheduling simulations,
and a local Streamlit dashboard.

## Read these files first

| Order | File | Purpose |
| --- | --- | --- |
| 1 | [RESULTS_SUMMARY.md](RESULTS_SUMMARY.md) | Observed findings and scientific limits. |
| 2 | [Report PDF](reports/gridshift_report.pdf) | The complete 25-page research report. |
| 3 | [Presentation PDF](slides/gridshift_presentation.pdf) | The 12-slide visual overview. |
| 4 | [PowerPoint](slides/gridshift_presentation.pptx) | Editable slides with speaker notes and backup equations. |
| 5 | [Notebook HTML](notebooks/01_gridshift_study.html) | Executed analysis, tables, and figures without Python setup. |
| 6 | [Completion checklist](COMPLETION_CHECKLIST.md) | Acceptance evidence for all 23 requirements. |

The editable report is `reports/gridshift_report.md`. The executable notebook
is `notebooks/01_gridshift_study.ipynb`. `DELIVERABLES.md` lists the remaining
source, data, diagnostics, manifests, and experiment tables.

## Understand the findings

The development period is 2022-2023, validation is 2024, and the locked test is
2025. The target is NESO estimated actual carbon intensity at 30-minute UTC
resolution. All 17,520 half-hours in the test year are observed.

The frozen SARIMA forecast has common mean endpoint MAE of 24.453 gCO2/kWh,
compared with 29.122 for persistence. That is a 16.033% reduction. This metric
averages leads of 0.5, 2, 6, 12, and 24 hours on common no-fallback origins.

Calendar mean, not SARIMA, is the validation-selected deployment scheduler.
For 2,913 isolated two-hour jobs with ten hours of slack, calendar mean reduces
modeled operational CO2 by 12.414% against earliest execution. Its paired
seven-day block-bootstrap 95% interval is 10.951%-13.828%. Completed work is
identical and there are no deadline misses.

Across 18 shared-GPU traces, calendar mean reduces modeled cost by 4.816% on
the common completion intersection. It also rejects 9.476% of offered jobs,
compared with 4.058% for earliest execution. This is a service tradeoff, not
fixed-work savings.

Power, PUE, durations, and arrivals are synthetic. Publication delay is assumed,
historical vintages are unverified, and predictive intervals can under-cover.
These results do not establish measured GPU energy, verified net savings, or
actual avoided grid emissions. Do not describe the project as a production GPU
scheduler or claim that classical deployment adds proven scheduling value.

## Run the saved dashboard

Use the full project archive or an authorized GitHub clone. The smaller review
archive contains documents only and cannot run the application.

Install Python 3.13 and `uv`. From the project root, run:

```powershell
uv sync --frozen
uv run streamlit run app/streamlit_app.py --server.address 127.0.0.1 --server.port 8501
```

Open `http://127.0.0.1:8501`. The initial view uses frozen historical results.
No GPU, paid compute, model training, or live API request is required for that
view. Live refresh is a separate explicit action.

For checks, run:

```powershell
uv run pytest
uv run python scripts/verify_deployment.py
uv run python scripts/run_research.py verify
```

The last command writes local verification outputs. To re-execute the notebook
without modifying the supplied notebook, run:

```powershell
uv run python scripts/execute_notebook.py
```

Full experiment commands are documented in `README.md`. Do not retune models
on 2025 or overwrite the frozen accepted experiment with new choices. The
academic exporter uses the original Codex document runtime; reading the saved
PDFs, HTML, and PowerPoint does not need that runtime.

## Choose a sharing package

`GridShift_Peer_Review_2026-10-23.zip` contains this guide, the results summary,
report sources and PDF, presentation sources and PDF, the executed notebook
and HTML, specifications, protocol amendments, data attribution, and key review
receipts. Send this archive to peers who need to read or present the project.

`GridShift_Full_Project_2026-10-23.zip` contains the application, package, tests,
locked dependencies, frozen NESO snapshots, experiment artifacts, and documents.
Send this larger archive to peers who need to run or reproduce the project.

Both archives have a file-level SHA-256 manifest. Local virtual environments,
caches, temporary files, credentials, and build distributions are excluded.
The full archive retains superseded research evidence; use the final paths in
`DELIVERABLES.md` for the accepted report and presentation.

The GitHub repository is private by default. A repository link alone does not
give peers access. Repository invitations are a separate action; a ZIP can be
sent directly. Do not send credentials or a local virtual environment.

Some retained provenance and review receipts contain original workspace paths
and internal reviewer identifiers. They document the original execution, not
paths peers must recreate. Frozen scientific files retain their original bytes.

## A short message to accompany the review archive

> GridShift is our carbon-aware GPU scheduling mini-project using official NESO
> Great Britain data and classical time-series forecasting. The archive includes
> the report, slides, executed notebook, results, and requirement audit. Start
> with PEER_GUIDE.md or RESULTS_SUMMARY.md. SARIMA improves forecast MAE, while
> the validation-selected calendar-mean scheduler shows modeled isolated-job
> timing benefit. Shared-GPU contention introduces a rejection tradeoff. All
> emissions are modeled, not measured or actual avoided grid emissions.
