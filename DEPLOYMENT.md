# Local deployment runbook

## Start a trusted instance

1. Install the locked environment with `uv sync --frozen`.
2. Run `uv run pytest`.
3. Verify `artifacts/protocol_freeze.json` and the dataset manifest.
4. Start the dashboard with the command in `README.md`.
5. Inspect the issue timestamp, observation cutoff, and model identifier before using a recommendation.

The application loads only project-produced JSON, NPZ, and Parquet artifacts. It has no model upload or pickle deserialization control.

After the research export builds the bundle, run its offline prediction check:

```powershell
uv run python scripts/verify_deployment.py
```

For a current official-observation probe, add `--network`. This requests seven
days of observations and verifies trusted inference and a feasible synthetic
recommendation. It does not collect forecast vintages, execute a GPU workload,
or score realized savings. The receipt is `artifacts/tests/deployment_runtime.json`.

## Handle failures

Missing result artifacts leave historical result views unavailable. They do not cause fabricated results.

An incompatible schema, altered checksum, or mismatched library version blocks trusted inference. Restore the matching artifacts and locked environment. Do not bypass version checks.

Missing or stale observations disable live carbon recommendations. Historical results remain readable. Earliest feasible scheduling is an operational fallback only when release, duration, deadline, and capacity are known. A fallback carries no carbon-saving claim.

An API failure must leave the cached historical evidence unchanged. Retry live refresh separately. Do not train a replacement model in a UI callback.

## Promote or roll back

Fit and evaluate model changes offline. A new representation or policy requires a new validation protocol and an untouched evaluation period. The 2025 test cannot serve as a new tuning set.

Restore a complete trusted bundle with its protocol, hashes, and environment to roll back. Copying only model parameters is insufficient.

## Container boundary

The Dockerfile is a packaging specification. A successful local Streamlit run does not prove a container build or public deployment. Container execution needs a separate verified build. Public hosting and external access require authorization.

The process uses CPU forecasting. It does not connect to a GPU queue, Slurm, Kubernetes, or a cloud compute provider.
