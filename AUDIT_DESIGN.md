# Final requirement acceptance

The offline verifier checks executable evidence. Separate root and independent
review attestations assess scientific completeness, interpretation, and visual
quality for R02-R14, R17, R19, and R20.

Run `verification.review_basis(root, config)` after final exports and browser
checks. Inspect the actual files in that basis. Submit explicit per-requirement
verdicts with `verification.record_review`, using the inspected basis hash,
reviewer identity, role, findings, and limitations. Run the verifier again to
merge those records into `COMPLETION_CHECKLIST.md`.

The basis includes current source, specifications, frozen study identity,
experiment tables, deployment, academic outputs, browser evidence, and test
receipts. Review files and generated verification outputs are excluded to avoid
a hash cycle. A changed basis invalidates an earlier attestation.

Two independent Azure Luna Max design candidates recommended actor-separated
records. The cross-judge selected candidate B's separate review category, with
candidate A's evidence basis and machine-pass rule. Both candidates and the
cross-judge used the same model family. There was no provider diversity.

Passing reviews cannot override failed or missing executable evidence. Valid
negative scientific outcomes can pass. Reviewer IDs are declared attestations,
not authenticated identities. Cryptographic signing would require a separate
key-management design and is outside this project.

The browser receipt binds the current UI source and screenshot bytes. Layout
and scientific claims still require direct inspection. No attestation claims
actual avoided emissions or public deployment.
