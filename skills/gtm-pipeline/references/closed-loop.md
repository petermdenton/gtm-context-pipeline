# Stage handoffs and feedback

Resume at the requested stage. Counts, taxonomy, channels, geography, review
cadence and budgets come from the client/request rather than the source project.
This map describes agent work; only the capabilities marked as implemented in
the checkout are executable toolkit features.

| Stage | Owner | Reviewable handoff |
| --- | --- | --- |
| Intake | `gtm-clusters` | Versioned profile, resolved seeds, exclusions, claims and role hypotheses |
| Discovery and qualification | `gtm-clusters` | Dated sources, search provenance, reviewed assessments and unknowns |
| Company selection | `gtm-next-companies` | Ranked batch, reserves, exclusions, coverage and shortfall |
| Clusters and memberships | `gtm-clusters` | Draft analytical groups and separately reviewed membership proposals |
| Company-content research | `gtm-campaign-authoring` | Capture manifest, coverage, excerpts, source dates and hashes |
| Messaging and creative assets | `gtm-campaign-authoring` | Buyer/stage hypothesis, claim references, copy and actual exports if requested |
| Destinations | `gtm-ad-page` | Brief or implemented page, actual route, versions, tracking and verification |
| Campaign readiness/actions | `gtm-campaign-operations` | Concrete targeting delta, scope, settings and verified action results |
| Measurement | `gtm-analytics` | Aggregate results, windows, denominators, filters and unavailable outcomes |
| Buyer research and follow-up | `gtm-outreach` | Team/remit evidence, drafts and separately verified external outcomes |
| Feedback | `gtm-campaign-operations` | Reviewed fit/message findings and a versioned next-batch hypothesis |

Selection can begin before any campaign. An incremental batch may reuse valid
contexts, creative assets and destinations. New evidence changes the affected
artifacts, not every cluster automatically. New campaign categories need
coordinated definitions, membership, content, destination and measurement support.

## Persist the handoff

Use the existing private run, or a unique `output/gtm-loop/<run-id>/`. Check Git
ignore coverage before storing client material. Keep a small agent-authored
handoff plus links; this is not an implemented import schema or scheduler.

Record run/parent IDs, scope, owner, timestamps, input paths/hashes, profile and
taxonomy versions, source windows and coverage, artifact versions, review status,
completed stages and next action. Preserve exact local selection manifests;
store later reviews as linked records instead of editing hashed results.

An account handoff carries canonical domain, verified aliases/provider IDs when
known, seed/query origin, independent fit evidence, unknowns, exclusion coverage,
proposed membership/version and its review decision. A campaign handoff carries
exact destination IDs, approved delta, preserved settings, creative/page versions
and observed readback. Keep external identifiers private.

Record authorization already established for research spending, publication,
targeting changes, launch, CRM writes and sending. Reuse it without asking again;
finish independent work before requesting a missing material input or scope.

For each new task/site, include `workflow_lookup` with query, site, decision,
selected ID/path/hash when used and observed outcome. A discovered workflow or
opened page is not a completed campaign action.

For a treatment, preserve audience, hypothesis, owner, variable being changed,
creative/page/context versions, metric, denominator and observation window in a
private experiment record. There is no experiment-creation CLI here. Reuse an
existing experiment and do not call UTMs alone random assignment.

## Close the loop

Join results only at supported identities and dimensions. Targeting readback
proves an addition, not delivery; aggregate web traffic does not identify buyers.
Missing outcome coverage remains unavailable. Distinguish no delivery from
delivery without a recorded response. Preserve uncertainty and negative findings.

Return fit findings to clusters, message findings to authoring/pages and verified
replies or outcomes to outreach. Record why a profile/query/message changes and
retain the old version. Compare cohorts with exposure and timing differences
disclosed; observational differences do not establish causal lift.

Recurring work requires an actual configured scheduler and validated tool access.
These files do not implement unattended execution. Report separately what local
code ran, what the agent reviewed and what an external service verified.
