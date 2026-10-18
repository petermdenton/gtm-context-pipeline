# Selection and review contract

The authoritative schema is [docs/contracts.md](../../../docs/contracts.md)
and executable validation is in `gtm_pipeline/selection.py`. Keep company rules
in the profile; do not copy another company's workload vocabulary or scores.

Pin raw input bytes and retain snapshots for replay. A changed criterion or
weight requires a new profile version and matching reassessments. Each pass/fail
assessment needs rationale, reviewer, source URL and observation date. That
date is not automatically a publication date. The engine checks structure and
age; an upstream reviewer must inspect the source and conclusion.

Identity normalization joins explicit aliases transitively. Verify alias
equivalence upstream; ownership and display-name similarity are insufficient.
Conflicting duplicate candidate identities are held for consolidation. Every
known exclusion wins, including an alias of a selected domain.

Required failures or unknown/stale/future evidence block selection. Optional
unknowns remain visible and contribute no score; they are not negative facts.
Eligible companies sort by descending weighted score, then normalized domain.
There is no inferred budget, campaign quota or calibrated purchase probability.

The exclusion snapshot must match the profile funnel and report each coverage
dimension honestly: membership, customers, suppression, holds, pending batches.
An empty record list means no known exclusions only after actual source checks.
Missing/partial/stale coverage makes all selections provisional while retaining
every known exclusion. Do not reactivate a hold without a sourced review.

Before a selection handoff, reconcile:

- Unique selected identities, no overlap with reserves/exclusions or known
  pending batches, and all required criteria supported at the review date.
- `selected_n <= requested_n` and `shortfall = requested_n - selected_n`.
- Original assessments, effective unknowns, coverage dates and source hashes.
- `reviewed_n` and `verified_added_n` remain zero in CLI output. Later reviews
  and additions belong in linked records with evidence and timestamps.

Keep the CLI manifest intact; it pins the JSON result. Do not annotate it after
the fact without producing a new version and consistent hashes. Reruns create
new directories and do not reconcile previous pending batches automatically.
Recheck membership before any live insertion; concurrent reservations are not
implemented. An explicit shortfall is a valid result, never a reason to include
suppressed, duplicate or unsupported accounts.
