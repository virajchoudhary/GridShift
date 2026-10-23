# Independent locked isolated-job acceptance

Reviewer: `/root/locked_primary_acceptance`, runtime-confirmed
`azure-kmamc/gpt-6-luna`, Max effort. Parent retained final acceptance.

Verdict: PASS for the isolated-job experiment. The reviewer changed no files,
ran no models or experiment replay, and did not inspect queue contents.

The reviewer recomputed the protocol, normalized-data, and scientific-source
hashes, all 860 frozen validation-artifact hashes, and all nine forecast archive
hashes. They matched the frozen records and strict test preflight receipt.

All 734,076 decisions across 21 scenarios were scheduled and feasible. There
were 147 exclusions, seven late releases per scenario, because the complete
48-slot path crossed the test boundary. No case was excluded for missing truth.

The default comparison contains 2,913 jobs. At 0.4 kW IT power and PUE 1.2,
each two-hour job uses a modeled 0.96 facility kWh. Independent recomputation
matched every policy's energy-weighted emissions; maximum per-decision
difference was 1.14e-13 g.

Earliest execution totals 361,306.56 g. Frozen calendar mean totals 316,453.92 g.
The difference is 44,852.64 g, or 12.414012%, averaging 15.397405 g per case.
The independently reproduced 2,000-resample seven-day paired bootstrap gives
10.951237%-13.828262% and 13.662495-17.092451 g per case.

Full-year selected and oracle minima matched all 2,913 default cases. A
deterministic 128-job sample matched every forecast and oracle minimum,
including tie handling, and 26,880 candidate rows.

These are correlated isolated counterfactuals, not a runnable combined trace.
The result is modeled intensity-weighted operational CO2, not measured GPU
energy, verified net savings, or actual avoided grid emissions. Calendar mean
remains selected; test outcomes do not promote SARIMA.
