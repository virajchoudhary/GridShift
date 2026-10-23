# Independent frozen scientific source review

Reviewer: `/root/frozen_science_review`, observed runtime
`azure-kmamc/gpt-6-luna` at Max. The returned verdict was FAIL for provenance
acceptance, not for the running experiment or its numerical forecasts.

The review found that the low-level forecast loader accepts absent classical
refit metadata and defaults missing delay metadata. The offline verifier also
allowed missing refit partitions. These are real malformed-input acceptance
gaps, even though generated classical archives contain their cutoff records.

The reviewer recomputed source, protocol, amendment, and dataset hashes against
the freeze. A read-only conditional seasonal forecast check with missing updates
matched direct statsmodels means within 2.84e-14 and variances within 8.88e-16.
The review found the UTC bridge, causal filtering, missing-prefix handling,
catalogue deduplication, overlap energy, and reservation accounting consistent
with the specifications. It did not inspect partial 2025 outcomes.

The root added `verification.forecast_preflight` and
`scripts/run_verified_backtests.py`. This official entry point requires complete
classical cutoff partitions and reconstructs all baseline arrays from frozen
data and configuration before scheduling. The final offline verifier also runs
this check. The frozen numerical source and protocol remain unchanged.

The review additionally noted the internal `synthetic=True` fixture opt-out.
It is an explicit trusted-caller API, not a security boundary. The app and
official entry points do not expose it. The README now states that restriction.
The project does not promise protection against arbitrary malicious Python
callers who can edit code, source attributes, or local artifact bytes.

Correction acceptance requires the fresh `/root/forecast_preflight_recheck`
verdict and the actual preflight receipt. This document does not declare that
acceptance in advance.
