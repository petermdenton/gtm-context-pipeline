# Architecture

## Separation of responsibilities

1. **Core:** validates contracts, joins explicit identities, applies configured
   criteria, checks evidence dates and coverage, and records reviewable outputs.
2. **Company workspace:** offer, ICP, seeds, buyer-role hypotheses, exclusions,
   approved claims, campaign taxonomy, brand assets and destination configuration.
3. **Adapters:** normalize data from a provider into core contracts and record
   source provenance. Provider secrets and account IDs stay in private configuration.
4. **Agent/operator workflows:** collect sources, review company fit, distill
   language, develop messaging, review assets and make decisions. These are not
   replaced by a score or treated as unattended automation.

The local selection slice and client portal are implemented. JSON remains the
selection boundary. The portal uses workspace-local SQLite for identity and
project state and presents saved selection outputs from the same core.

## End-to-end stage map

| Stage | Company-specific inputs | Shared responsibility | Current support |
| --- | --- | --- | --- |
| Intake | Offer, seeds, ICP, roles | Versioned targeting brief | Profile subset |
| Discovery | Queries and scope | Bounded requests, normalization, provenance | Explicit project Exa search; live validation pending |
| Qualification | Criteria and exclusions | Evidence validation and deterministic ranking | Local assessments |
| Account evidence | Required attributes | Facts, hypotheses, unknowns | Assessment subset |
| Analytical clustering | Facets and weights | Reusable analytical method | Draft text-similarity components; embedding extraction pending |
| Campaign taxonomy | Reviewed groups and roles | Membership integrity and versioning | Planned |
| Buyer research | Role hypotheses | Dated remit and identity evidence | Planned |
| Research | Source corpus and memberships | Capture manifests and context contracts | Planned |
| Messaging and ads | Claims, brand, persona | Provenance, review and asset manifests | Planned |
| Landing pages | Brand, product assets, CTAs | Rendering and analytics contract | Planned |
| Publication | Destination and platform | Verified deployments and rollback | Planned |
| Campaign operations | Budget, channel, audience | Readiness and separately authorized actions | Planned |
| Measurement | Data sources and outcome definitions | Windows, denominators and unavailable outcomes | Planned |
| Feedback | Reviewed findings | Versioned decisions and new hypotheses | Planned |
| Next-company selection | Requested N and funnel | Exclusions, ranking, reserves and shortfall | Implemented |

## Deliberate boundaries

Analytical clusters and campaign taxonomy remain different artifacts. Taxonomy
size is configurable when that stage is implemented. Campaign selection does
not imply reach, delivery, a person, or buying intent. Publication and paid launch
have different authorization and evidence. A click, signup, meeting and activation
remain distinct outcomes; missing outcome data is null rather than zero.

Runs are local immutable-by-convention snapshots in unique directories, not a
transactional reservation service. The CLI does not lock a shared funnel. Teams
must reconcile pending batches before action until shared reservation support
exists. Input hashes detect changed source files; keep the original input snapshots
available for replay. The core reads each input once, hashing the bytes it parsed.

Explicit aliases are joined transitively. Corporate ownership, mergers and alias
equivalence must be verified upstream. Arbitrary subdomains are not collapsed,
and companies are never joined by display name alone. Conflicting duplicate
records are held rather than resolved by silently choosing a higher score.


## Client presentation boundary

The portal wraps the same saved-run contracts with a server-selected client
workspace. Goals reference related stages and supporting metrics while preserving
unknown targets and outcomes. Client requests cannot select another tenant or
supply filesystem paths. Saved workspace measurement snapshots can be supplied by private source adapters;
client-specific importers and live MCP transport are outside this distribution. See
[client portal](client-portal.md) for isolation, data flow and production gaps.

Workspace access policy lives in `portal_access.py`, with persistent exact-domain
grants, agency roles, hashed sessions, revocation and access-change events. Google
protocol and token verification live in `adapters/google_identity.py`, behind an
optional dependency. Google settings and credentials are private configuration.
Each process still selects one tenant on the server; the browser cannot choose a
workspace. Google access is deny-by-default until explicitly provisioned.

Project state lives in `portal_projects.py`, separately from selection runs and
profile configuration. Stable project IDs, targets, search provenance, cluster
snapshots and draft assets are stored in a private `projects.sqlite3`. Both client
members and administrators can mutate their workspace's projects. Only admins
can provision domains. All project requests resolve inside the server-selected
workspace and enforce the existing session and Origin boundaries.

`adapters/exa_search.py` owns the bounded provider request and normalization;
`project_clustering.py` groups supplied text with deterministic TF-IDF cosine
similarity. Clusters preserve input hashes, source snapshots and pairwise shared
terms. They are draft connected components, not qualified buying intent or
reviewed campaign taxonomy. Draft content refers to a specific cluster version.
Project analytics does not attribute workspace-wide campaign metrics to projects.


Data-source receipts accompany project records: searches preserve normalized
field snapshots and import adapters can atomically save supplied company/contact
records with per-record receipts through `ProjectStore.import_source_records`.
This boundary performs no file upload or MCP network request. Source usage is
independently derived for search, upload and MCP from active records referencing
completed runs or imports. Removed records are archived with their source links
and can be restored; historical receipts remain available but do not imply usage.
Connection configuration and actual imported data remain distinct states.
