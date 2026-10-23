# Independent locked forecast acceptance

Reviewer: `/root/locked_forecast_review`, runtime-confirmed
`azure-kmamc/gpt-6-luna`, Max effort. Verdict: R15 PASS.

The reviewer independently recomputed all nine models' endpoint losses from
saved arrays and frozen truth, with maximum metric delta zero. All models have
17,473 issue origins and complete 48-slot paths. The common no-fallback
intersection has 16,465 origins. The protocol, scientific source, normalized
data, finalist specifications, and archive checksums match their frozen records.

Common mean endpoint MAE in gCO2/kWh is 24.452878466 for frozen SARIMA and
29.122004251 for validation-selected persistence. The arithmetic mean covers
leads 0.5, 2, 6, 12, and 24 hours. End-to-end means including fallbacks are
24.330379 and 29.059601, respectively.

MA log1p, ARMA, and ARIMA each have one 336-origin fallback block. The recorded
causes are an unconverged August MA fit, an unconverged July ARIMA fit, and a
December ARMA LU decomposition error. Fallbacks use daily seasonal naive.

Calibration qualifies the result. At 24 hours, SARIMA empirical coverage is
70.6% and 87.0% for nominal 80% and 95% intervals. Parameter-estimation
uncertainty is excluded. These are marginal intervals, not joint job-cost
guarantees.

The test result does not change the frozen calendar-mean deployment choice.
No scheduling review, fitting, experimental rerun, or file edit was performed
by this reviewer. Parent acceptance uses actual files and final checks.
