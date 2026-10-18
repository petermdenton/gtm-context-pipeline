---
name: gtm-clusters
description: Develop company-specific profiles, seed hypotheses, discovery evidence and draft clusters in GTM Pipeline. Use for account research, qualification, analytical grouping and reviewed campaign-membership proposals. Route next-N saved-company selection to gtm-next-companies.
---

# Accounts and clusters

Read checkout `AGENTS.md`, `docs/contracts.md`, `docs/architecture.md` and the
project-workspace sections of `docs/client-portal.md`. Resolve the client/project,
profile/version, seeds, exclusions and requested output before changing data.
Read [seed discovery](references/seed-discovery.md) for expansion or membership
work. Follow the workflow-discovery rule before a new stage or website task.

Distinguish these current capabilities:

- Profiles and reviewed assessments use the selection contract. Review verdicts
  against the client's criteria; the core does not verify claims by browsing.
- Portal company/contact targets and source receipts are persistent private
  records. Search results and manual targets start unreviewed.
- `gtm_pipeline/adapters/exa_search.py` supports explicit bounded portal searches
  with provenance and deduplication. It is offline-tested; live paid validation
  is pending. There is no local copy of the source project's discovery CLI.
- `gtm_pipeline/project_clustering.py` uses deterministic TF-IDF cosine edges
  and connected components over supplied text. It makes no embedding request.
  Members can be linked indirectly; inspect pairwise evidence and outliers.

For requested discovery, reuse saved evidence, then plan queries from the client's
offer and seeds. Confirm provider access, request limits and established paid
scope before running a search. Requests are not qualified-company counts or
dollar caps. Preserve query/input/response hashes, omissions, cost when reported
and the distinction between failed, unknown and completed operations.

Research accounts on dated primary sources. Retain unresolved company identity,
fit, scale, need and buyer gates. Normalize reviewed assessments into the input
contract deliberately; no Exa-to-qualified-candidate adapter is implemented.
Use [gtm-next-companies](../gtm-next-companies/SKILL.md) for eligible next-N ranking.

For analytical grouping, pin inputs and method, inspect missing/ungrouped records
and keep snapshots/version hashes. Changed targets or source evidence make prior
portal clusters stale. Do not present similarity components as approved taxonomy.

For campaign membership, use the client's reviewed taxonomy or propose a version
with definitions, inclusions, exclusions, roles and message hypotheses. Propose
one primary membership per selected company when routing is needed, with source,
rationale, alternatives and review status. Keep holds outside active counts.
There is no fixed cluster count or automatic reviewed-membership classifier.

Buyer titles are hypotheses until current identity/remit is evidenced. Route
people research to [gtm-outreach](../gtm-outreach/SKILL.md). Keep contacts private.
Deliver pinned inputs, methodology, evidence/unknowns, membership deltas, counts
and the next review step. Downstream assets or platform settings change only
when included in the user's requested scope.
