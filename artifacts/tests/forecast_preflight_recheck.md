# Independent provenance correction acceptance

Reviewer: `/root/forecast_preflight_recheck`, observed runtime
`azure-kmamc/gpt-6-luna`, Max. Verdict: PASS for the README-designated official
backtest workflow.

The reviewer inspected strict classical identity, explicit delay, nonempty
refit partitions, exact eligible cutoffs, and full-origin coverage. It confirmed
that all baseline arrays are reconstructed from frozen data and configuration,
and that preflight precedes both backtests in the official entry point.

AST checks passed on ten relevant files. Scientific source and protocol hashes
still match the original freeze. The app exposes neither a synthetic opt-out
nor the direct backtest loader.

The generic low-level CLI remains a trusted-generated-archive path. This is a
documented limitation rather than a guarantee against arbitrary Python callers.
No partial 2025 outcome, fit, or mutable research artifact was inspected or
changed. Pytest was not rerun by this read-only reviewer.

The root subsequently added separate negative assertions for classical identity
with missing refits and with missing explicit delay. Execution of these tests
and of the real complete-archive preflight remain separate evidence.
