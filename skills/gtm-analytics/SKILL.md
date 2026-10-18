---
name: gtm-analytics
description: Produce read-only GTM traffic, engagement, advertising and outreach reports from saved snapshots or an available authorized data connector. Use for measurement and attribution questions in GTM Pipeline, preserving windows, denominators and unknown outcomes.
---

# GTM analytics

Read checkout `AGENTS.md` and [measurement guidance](references/measurement.md).
Resolve the client/workspace, requested channels/pages/projects, reporting window,
timezone and source. Prefer saved data that fits the question; disclose its age.

The portal reads workspace `measurement.json` snapshots. Client-specific
measurement importers are outside this distribution. Inspect `Workspace.measurement`
in `gtm_pipeline/portal.py` and the private source adapter before preparing a
snapshot. No generic measurement importer, live MCP transport or Cloudflare D1
report helper is bundled here.

For live reporting, use an available authorized read-only connector/API and its
current schema guidance. Read provider context before SQL when required. Query
aggregates and only the relevant dimensions. Readout scope does not authorize
schema changes, customer/contact exports, account changes or new credentials.
If access is missing, finish analysis of permitted snapshots and identify the
exact freshness or coverage gap.

Compute CTR, CPC, CPM, reply and other rates from summed numerators/denominators,
not averages of row percentages. Label units and currency; do not combine
incompatible cohorts or currencies. Keep unavailable denominators/results null.
Respect source-specific bot/QA exclusions, privacy constraints and event semantics.

Distinguish page views, sessions, browsers and people; click events from views
with a click; and platform engagement from CRM/product outcomes. A CTA click does
not verify a signup, meeting or activation. Historical tracking gaps and suppressed
values are unknown, not zero. Anonymous activity cannot identify a buyer/company.

Workspace aggregates are not project campaign attribution. Join reports only
at supported dimensions with adequate source evidence. Do not assign company
engagement to a specific adset from matching names or addition dates alone.

Save aggregate outputs and query/source provenance privately, with window,
filters, coverage, freshness, definitions and input hashes. Report observed
results and limitations, not unsupported intent or causal lift. Route reviewed
message findings to authoring/pages, and fit/outcome evidence to operations and
outreach. Reporting does not mutate campaigns or schedule the next run.
