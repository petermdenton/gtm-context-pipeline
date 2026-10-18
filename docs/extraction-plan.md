# Roadmap and implementation boundaries

The current release combines executable local tooling with agent-guided GTM
workflows. Company strategy and production data remain in private workspaces.

## Implemented

- Versioned profiles and deterministic selection from saved reviewed assessments.
- Identity, freshness, exclusion coverage, reserves and hashed run artifacts.
- A local portal with operator sessions, optional Google identity and domain access.
- Persistent project targets and contacts, source receipts and archived records.
- An explicit, bounded Exa search adapter, tested with synthetic responses.
- Explainable local TF-IDF clustering with snapshots and stale-input detection.
- Cluster-linked briefs and creative/page draft text or reference links.
- Eight reusable agent skills with repository-local discovery links.

## Next increments

1. Validate the Exa adapter with an explicitly authorized live request, then add
   provider-neutral discovery and qualification imports. Preserve request limits,
   provenance, unknowns and company-specific criteria.
2. Extend evidence/context/claim contracts and separately reviewed campaign
   memberships. Analytical similarity must remain distinct from approved taxonomy.
3. Add configured creative and page renderers with actual assets and review
   manifests. Publication requires a separate destination adapter and verification.
4. Add provider-specific measurement and read-only CRM adapters, followed by
   explicit pending-batch reconciliation and supported attribution joins.
5. Implement any sending, campaign mutations or schedules as separate capabilities
   with account configuration, authorization, idempotency and observed outcomes.

## Portal production work

The portal is a local prototype, bound to one workspace on `127.0.0.1`. Public
hosting needs a production HTTP service, HTTPS/Secure cookies, tenant routing and
database constraints, identity configuration, invitations, monitoring and backups.
Do not reverse-proxy the current local server onto the internet.

UI upload, live project MCP transport, rendering, publication and delivery are
not implemented. A source receipt or draft record does not prove an external
action occurred. Live provider validation remains separate from offline tests.
