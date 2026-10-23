# GridShift

Carbon-intensity forecasts and deadline-constrained GPU workload simulations using official NESO Great Britain data.

## Review or share the project

Start with [PEER_GUIDE.md](PEER_GUIDE.md) for the reading order, project results,
presentation files, and local setup. [DELIVERABLES.md](DELIVERABLES.md) lists the
complete evidence package. [RESULTS_SUMMARY.md](RESULTS_SUMMARY.md) contains the
observed results and their limitations.

The repository includes the frozen data and experiments. You do not need to
rerun model selection or download data to review the saved results.

## Run the research

Use Python 3.13 and the provided `uv.lock`.

```powershell
uv sync --frozen
uv run python scripts/run_research.py collect
uv run python scripts/run_research.py audit
uv run python scripts/run_research.py diagnose
uv run python scripts/run_research.py select
uv run python scripts/run_research.py study --stage validation
uv run python scripts/run_research.py backtest --stage validation
uv run python scripts/run_research.py residuals
uv run python scripts/run_research.py queue --stage validation
uv run python scripts/run_research.py sensitivities
uv run python scripts/test_project.py
uv run python scripts/run_research.py freeze
uv run python scripts/run_research.py study --stage test
uv run python scripts/run_verified_backtests.py --stage test
uv run python scripts/run_research.py export
uv run python scripts/test_project.py
uv run python scripts/run_research.py verify
```

The runner restricts BLAS to one thread and uses two fitting processes. Experiments have content-derived directory names. Existing complete forecast files are reused. Test commands require a compatible validation freeze.

The verified-backtest entry point checks complete classical refit provenance and
reconstructs every baseline array from frozen inputs before scheduling. The
lower-level research commands assume trusted generated forecast archives.
`synthetic=True` is an explicit internal fixture opt-out, not an authorization
mechanism for untrusted data. The application never exposes that option.

Re-execute the finished notebook with `uv run python scripts/execute_notebook.py`.
It uses a private kernel bound to the running locked interpreter and writes a
copy under `tmp/notebook_reexecuted`, preserving the exported notebook and HTML.

The dataset is already collected locally. Rebuilding it uses 209 cached compressed source responses when their hashes match. Fresh requests occur only for missing chunks. Statistical evaluation excludes the historical provider `forecast` field because its issue vintage is unverified.

## Run the dashboard

```powershell
uv run streamlit run app/streamlit_app.py --server.address 127.0.0.1 --server.port 8501
```

The default workspace uses frozen historical forecasts. Live refresh requests current official observations only after an explicit command. UI reruns do not train models or mutate research evidence. A stale or missing observation state disables a carbon recommendation.

## Inspect the evidence

The byte-identical authoritative specification copies are in `specifications/`.
`PROTOCOL_AMENDMENTS.md` records development-only numerical and search decisions.
`decisions.tsv` records execution decisions.

- `data/manifest.json` records provenance and raw response hashes.
- `artifacts/data/reconstruction.json` records reconstruction from raw responses.
- `artifacts/diagnostics` contains development-only tables and figures.
- `artifacts/runs/<study_id>` contains order search, validation, and test artifacts.
- `artifacts/protocol_freeze.json` seals model and policy choices.
- `artifacts/results.json` supplies the report, notebook, and presentation numbers.
- `COMPLETION_CHECKLIST.md` records requirement acceptance and remaining limitations.

## Academic deliverables

- `notebooks/01_gridshift_study.ipynb` is the executed offline study.
- `notebooks/01_gridshift_study.html` displays its saved outputs.
- `reports/gridshift_report.pdf` is the 25-page report.
- `reports/gridshift_report.md` is its editable source and extended tables.
- `slides/gridshift_presentation.pptx` contains 12 slides with editable tables,
  charts, embedded figures, and speaker notes.
- `slides/gridshift_presentation.pdf` is a visual companion rendered from the
  validated slides. Its titles are searchable; native editable evidence is in
  the PowerPoint.
- `reports/export_manifest.json` binds the input and generated output hashes.

Academic generation uses the Codex bundled Artifact Tool, Node, Python, and
Poppler paths. To use another installed bundle, set `RUNTIME_NODE`,
`RUNTIME_NODE_MODULES`, `RUNTIME_BIN_DIR`, `RUNTIME_PYTHON`,
`GRIDSHIFT_PRESENTATIONS_SKILL`, and `GRIDSHIFT_PDFTOPPM` to its matching paths.
The Python research, saved notebook, and Streamlit application do not need
Artifact Tool at runtime.

The presentation's PDF uses slide renders because the bundled Artifact Tool
PDF exporter could not resolve its standard-font module. No bundled dependency
was changed. Superseded academic exports are retained under
`artifacts/superseded`; use only the paths above for the final package.

## Scientific boundaries

Jobs are synthetic, non-preemptive counterfactuals powered by the GB grid proxy. Power is allocated IT power in kW and PUE multiplies it once. Costs integrate partial interval overlap in hours.

The primary experiment evaluates independent isolated jobs. Their overlapping releases are correlated counterfactuals, not a runnable combined trace. The queue experiment uses immutable one-GPU reservations and reports service differences.

All costs are modeled intensity-weighted operational CO2. They establish neither measured GPU energy nor actual avoided grid emissions. The replay uses retrospective estimated actuals with an assumed publication delay. Forecast intervals exclude parameter-estimation uncertainty. Net computing overhead and marginal emissions are unmeasured.

A model or scheduler need not improve performance for the project to produce a valid negative result. Software checks, empirical outcomes, and public deployment are separate claims.

## Deployment

The Dockerfile specifies a CPU-only Streamlit process. GitHub publication shares
the source and saved evidence; it does not deploy the application. Public hosting,
GPU execution, paid compute, and container publication remain separate operations.
Container execution has not been demonstrated. See `DEPLOYMENT.md`.
