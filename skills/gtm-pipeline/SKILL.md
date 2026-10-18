---
name: gtm-pipeline
description: Coordinate multi-stage GTM work and feedback handoffs in GTM Pipeline, from company profiles and discovery through research, content, measurement and the next batch. Use for end-to-end requests or resuming a saved run; route single-stage tasks to the matching local skill.
---

# GTM Pipeline

Read checkout `AGENTS.md`, `README.md`, `docs/architecture.md` and
`docs/extraction-plan.md`. Use current code and `docs/client-portal.md` to resolve
implementation status. The source project's scripts and services are not local
dependencies. All checkout paths are relative to the GTM Pipeline root.

Resolve the client workspace, requested stages, company profile/version, source
snapshots, desired artifact and established external-action scope. Resume the
last verified handoff and reuse valid saved evidence. Supplied seeds and the
client's offer govern targeting; do not substitute a fixed industry or ICP.

For a multi-stage run, read [stage handoffs](references/closed-loop.md). Keep
run records under ignored `output/gtm-loop/<run-id>/` or the existing private
workspace. Run workflow discovery at each new task/site boundary as described
in `AGENTS.md`; record the selected path/hash and observed outcome privately.

Route only the relevant work:

| Requested work | Skill | Local support |
| --- | --- | --- |
| Next N eligible companies | [gtm-next-companies](../gtm-next-companies/SKILL.md) | Saved-assessment CLI, exclusions, reserves and shortfall |
| Seeds, accounts and clusters | [gtm-clusters](../gtm-clusters/SKILL.md) | Portal targets, explicit Exa search and local draft similarity clusters |
| Research, messaging and creatives | [gtm-campaign-authoring](../gtm-campaign-authoring/SKILL.md) | Agent work and portal draft storage; no asset generator |
| Buyers and email preparation | [gtm-outreach](../gtm-outreach/SKILL.md) | Agent research/drafts and contact storage; no CRM/mail integration |
| Ad-aligned destination | [gtm-ad-page](../gtm-ad-page/SKILL.md) | Draft storage; renderer/publisher not implemented |
| Measurement | [gtm-analytics](../gtm-analytics/SKILL.md) | Saved snapshots; provider-specific import, no live generic transport |
| Readiness and campaign feedback | [gtm-campaign-operations](../gtm-campaign-operations/SKILL.md) | Agent review; platform execution and scheduling not implemented |

Finish supported local work and use available external tools when the request
authorizes them. A missing toolkit adapter need not prevent a reviewable draft
or a supported tool action. If implementation is requested, use the repository's
profile/core/adapter separation and test the new behavior before relying on it.
Never invent a CLI or claim the source repository's tooling ran here.

Keep fit, similarity, engagement, identity confidence and exclusion coverage
separate. Selection is draft, analytical clusters are not approved campaigns,
and neither proves reach or buying intent. Preserve review, publication,
targeting, delivery and product outcomes as distinct states.

Report artifacts, hashes/versions, evidence gaps, checks and the next supported
stage. Updating these skills or describing a loop does not authorize research
spend, publication, platform changes, sending or recurring execution.
