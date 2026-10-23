# GridShift deliverables

Original verified workspace directory:
`C:\Users\viraj\Documents\Codex\2026-10-22\plan-gridshift-a-complete-ats-mini\outputs\GridShift`.

All paths below are relative to that directory. Final requirement acceptance
is recorded only in `COMPLETION_CHECKLIST.md` and `artifacts/verification.json`.
In a GitHub clone or extracted full-project ZIP, use the extracted `GridShift`
directory as the project root. Start with `PEER_GUIDE.md`.

| Deliverable | Path |
| --- | --- |
| Peer reading and sharing guide | `PEER_GUIDE.md` |
| Executable dashboard | `app/streamlit_app.py` |
| Research commands and usage | `README.md`, `scripts/run_research.py` |
| Verified backtest runner | `scripts/run_verified_backtests.py` |
| Python package | `src/gridshift/` |
| Locked dependencies | `pyproject.toml`, `uv.lock` |
| Frozen study settings | `configs/study.yaml` |
| Authoritative specifications | `specifications/GRIDSHIFT_PROJECT_PLAN.md`, `specifications/GRIDSHIFT_SOURCE_AUDIT.md` |
| Protocol amendments | `PROTOCOL_AMENDMENTS.md` |
| Source snapshots and normalized target | `data/raw/`, `data/normalized/carbon.parquet` |
| Data manifest and licence | `data/manifest.json`, `DATA_NOTICE.md` |
| Raw reconstruction and missingness | `artifacts/data/` |
| EDA and ATS diagnostics | `artifacts/diagnostics/` |
| Order-search and fitting ledger | `artifacts/runs/d2dee2d358735d7d/selection/` |
| Rolling validation and residuals | `artifacts/runs/d2dee2d358735d7d/validation/` |
| Locked forecast results | `artifacts/runs/d2dee2d358735d7d/test/` |
| Isolated-job backtests | `artifacts/runs/d2dee2d358735d7d/test/single_job/` |
| Shared-GPU reservation backtests | `artifacts/runs/d2dee2d358735d7d/test/queue/` |
| Bounded sensitivities and outage replay | `artifacts/sensitivities/` |
| Protocol freeze | `artifacts/protocol_freeze.json` |
| Verified result input | `artifacts/results.json` |
| Trusted model and prediction fixture | `artifacts/deployment/` |
| Deployment runbook and container specification | `DEPLOYMENT.md`, `Dockerfile` |
| Executed notebook | `notebooks/01_gridshift_study.ipynb` |
| Notebook HTML | `notebooks/01_gridshift_study.html` |
| Final report and editable source | `reports/gridshift_report.pdf`, `reports/gridshift_report.md` |
| Presentation, PDF, and source | `slides/gridshift_presentation.pptx`, `slides/gridshift_presentation.pdf`, `slides/gridshift_presentation.mjs` |
| Rendered report and slides | `reports/gridshift_report_preview/`, `slides/gridshift_presentation_preview/` |
| Academic provenance manifest | `reports/export_manifest.json` |
| Automated tests | `tests/`, `scripts/test_project.py` |
| Test, browser, deployment, and scientific reviews | `artifacts/tests/` |
| Final review attestations | `artifacts/reviews/` |
| Complete requirement audit | `COMPLETION_CHECKLIST.md`, `artifacts/verification.json` |
| Execution decisions | `decisions.tsv` |

The local dashboard is at `http://127.0.0.1:8501`. Restart it with the command
in README when needed. It does not submit GPU jobs.

The 2025 outcomes are modeled intensity-weighted operational CO2 under the
declared energy and workload assumptions. They do not establish measured GPU
energy, net real-world savings, or actual avoided grid emissions. Public
hosting, a container build, and PowerPoint application interoperability have
not been demonstrated.
