# Implementation checkpoint

The current user authorization supersedes the planning-only restriction in the original specifications. Preserve those source documents unchanged.

## Execution sequence

1. Implement and test UTC, interval, energy, and single-job contracts.
2. Collect and hash official interval data. Audit completeness without inspecting test performance.
3. Execute development diagnostics and a training-only seasonal fit pilot.
4. Execute bounded monthly order selection and full rolling validation.
5. Independently verify the single-job implementation and historical validation experiment.
6. Implement and verify shared-capacity reservations.
7. Freeze validation-selected orders, policies, source hashes, and numerical settings.
8. Run locked 2025 forecasting and both scheduling experiments.
9. Build and exercise Streamlit, model loading, notebook, report, and slides.
10. Audit all 23 requirements against actual artifacts and tests.

## Throughput and boundaries

Use two initial independent writer lanes, forecasting and single-job scheduling. The parent owns domain contracts, data, integration, execution, and final acceptance. Academic and UI lanes start after the core is verified. No public deployment, real GPU execution, paid compute, commit, or push is authorized.

Keep raw collection and compact forecast matrices below a recorded storage budget. Reuse weekly fixed-parameter forward-filter states; never use full-sample smoothing or final fitted parameters to reconstruct earlier forecasts. Numerical or search changes require training-only evidence and a protocol amendment before test access.

No result is certified by this checkpoint. The completion audit records actual evidence and remaining gaps.
