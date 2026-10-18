# Page authoring and verification

Inspect the real destination code before choosing a renderer. This checkout's
`gtm_pipeline/portal_static/` is a client workspace UI, not a campaign page build
system. Its [design system](../../../docs/design-system.md) governs portal edits;
it does not override a client's public brand or make draft records public.

Keep a compact private page manifest with audience/taxonomy version, input ad
and hash, creative ID, supported claims, context/page version, actual path,
asset provenance, CTA targets, review state and experiment reference. Use actual
source hashes; never fabricate an approval or deployed version.

For a new route or variant, trace source, rendering, routing, canonical metadata,
intended navigation, ad destinations and measurement dimensions through the
chosen implementation. Avoid fixed cluster counts and preserve existing routes.
If a registry exists, register the variant's own path and retain legacy canonical
mappings rather than attributing every variant to one URL.

Use the destination's configured measurement provider when tracking is in scope.
Check collectors, event definitions, consent/privacy behavior, attribution and
CTA tracking against its current contract. Public pages need a stated measurement
plan for campaign use; missing ingestion remains a readiness gap. Private review
pages remain access-controlled and outside performance reporting. Do not import
source-project D1 IDs, collectors or historical instrumentation dates.

Verify ad/hero continuity, claim qualifications, actual assets, links, metadata,
responsive behavior and accessible controls. Inspect desktop/mobile output and
use existing meaningful checks. For new tracking, verify labeled QA events in
the appropriate environment and exclude them from performance. Local rendering,
access control and ingestion each need their own evidence when changed.

For authorized publication, inspect destination ownership and current publisher
behavior. Preserve unrelated assets and runtime settings. Record artifact/version,
destination, timestamp, verification and rollback information. A successful upload
without a working destination is not verified publication, and publication is
not a paid launch. Missing publisher support should be reported after completing
the reviewable local artifact.
