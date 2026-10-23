# Independent locked queue acceptance

Reviewer: `/root/locked_queue_acceptance`, runtime-confirmed
`azure-kmamc/gpt-6-luna`, Max effort. Verdict: PASS for the saved 2025 queue
artifact set. No implementation files were changed.

The reviewer verified frozen identity and all 18 traces, three policies,
136,675 reservations, and 54 annual summaries. Every scheduled cost recomputed
from the normalized half-hour target and declared 0.4 kW IT power with PUE 1.2.
The 17,520-slot test grid is complete and there are no scored-window exclusions.
Matched/unmatched counts and fixed-horizon facility totals matched.

Across both slack settings, pooled counts per policy are 48,078 offered cases.
Earliest and persistence complete 46,127, reject 1,951, and have zero deadline
misses. Calendar mean completes 43,522, rejects 4,556, and has zero misses.
Median waits are one hour and six hours, respectively; p95 waits are eight
hours and twelve hours.

The 42,844-case common completion intersection gives a descriptive modeled
235,260.72 g difference, or 4.816% of baseline 4,885,043.04 g. The selected
policy rejects 2,605 more cases. All 54 comparisons correctly say
`descriptive completion intersection; service differs`. This is not fixed-work
carbon savings. Counts pool separately generated slack scenarios and seeds,
not one real production trace.

For six-hour slack, equal-seed mean matched reductions at loads 0.3, 0.6, and
0.85 are 6.77871%, 4.38559%, and 3.57099%. Selected rejection rates are 2.37301%,
9.70950%, and 17.73731%, versus earliest 0.48518%, 3.66708%, and 9.75836%.

All 54 bootstrap rows cover the 18 scenarios and three declared block sizes,
with 2,000 valid draws and 365 calendar days. Labels, point estimates, and
finite ordered intervals passed the review.

Source inspection confirmed seeded arrivals independent of carbon, only
revealed jobs and committed reservations in simulation, release-time forecast
use, and truth joins afterward. An additional fresh in-memory decision/prefix
check covered 12 traces, 74,694 decisions, and 36 prefix checks without a
mismatch. The reviewer stopped that extra replay at the parent's declared
boundary; acceptance does not claim fresh full replay of the remaining six.

Synthetic idle power is 0.08 kW. Lower fixed-horizon facility cost remains
confounded by rejected work. No actual avoided-emissions or GPU-energy claim
follows.
