# Sources, metrics and reporting

For saved portal data, inspect the matching private profile and
`measurement.json`, including source mode, reporting window and import time.
Imported-at is not refreshed-at. Preserve original snapshots and their hashes.
An available ad-account link or MCP settings panel does not prove a live connection.

Client-specific measurement importers are outside this distribution. A source
adapter must match the provider's actual schema and semantics, preserve complete
responses and input hashes, and emit a snapshot matching the workspace profile.
Inspect `Workspace.measurement` in `gtm_pipeline/portal.py` for the display
boundary. Keep prior snapshots when replacing `measurement.json`. Compute rates
upstream with SUM/SUM aggregation and explicit units. Similar field names alone
do not make two providers compatible.

For an available live connector, inspect context/schema and complete pagination
before claiming coverage. Keep query text, parameters, selected dimensions,
retrieval time, response completeness and source window. Apply documented bot,
QA, consent and suppression semantics. Do not copy another client's historical
tracking-start date or hardcoded filters into a generic report.

Use these interpretation checks where the source supports them:

- CTR = clicks / impressions, CPC = spend / clicks, CPM = 1000 * spend /
  impressions. Define outreach denominators explicitly. Zero denominator means
  unavailable rate, not measured zero. State fraction versus percent units.
- If visible time is a cumulative heartbeat, use its maximum per view rather
  than summing it. Do not apply that rule to incremental-duration events blindly.
- Do not sum unique counts across sources/windows without a supported identity
  join. Cohort definitions and attribution windows must agree before comparison.
- Rolling-window changes are net changes, not necessarily new daily activity.
  Replies attributed to send date differ from replies grouped by event date.
- Missing revenue, meetings or activation remain unavailable until their owning
  systems provide evidence. An empty import does not verify zero spend.

The handoff includes scope, exact window/timezone, currency, filters, source age,
coverage, numerator/denominator, supported dimensions and observational limits.
Keep website, platform and CRM/product evidence separate unless a documented
join connects them. Project-local target counts do not attribute workspace-wide
campaign results to that project.
