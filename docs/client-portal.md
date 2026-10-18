# Machines Among Us client portal

A local, authenticated client workspace organized around goals. The agency brand
is Machines Among Us; machinesamong.us is the intended domain. Nothing in this
implementation provisions DNS, hosts the service, or publishes client data.

## Run the synthetic demo

```sh
python3 -m gtm_pipeline.portal demo
python3 -m gtm_pipeline.portal serve --workspace private/portal-demo --port 8765
```

Open `http://127.0.0.1:8765` and expand **Agency operator access**. Generated
credentials are in `private/portal-demo/demo-login.txt`. The loopback host must
match exactly; `localhost` is not an accepted alias. The demo refuses to overwrite
an existing directory. Use a new private workspace path to create another demo.

The client sees an overview, goal detail pages, performance, pipeline stages,
accounts, evidence inspection, run history and workspace configuration. Saved selection runs and measurement snapshots are read-only. Project targets,
searches, clusters and draft assets can be created by clients and administrators. Agency administrators can provision and revoke
company email domains under Workspace settings. Missing stages are marked as unconnected. Account details are
available only after saved selection runs have been imported.

## Provision another client

```sh
python3 -m gtm_pipeline.portal init \
  --workspace private/clients/example \
  --profile private/example/profile.json \
  --email client@example.test
```

The command prompts for a password. It refuses to overwrite an existing directory.
Client profile rules use the existing input contract. Additional optional profile
fields are `portal_note` and `portal_stages`. Each stage has `name`, `description`,
`status`, `kind` (`profile`, `active`, `planned`), `detail`, and an optional
`metric_group` referencing a saved measurement group. Stage status describes the
connected artifact, not the client's entire business activity.

Generate runs using the workspace's exact copied profile file:

```sh
python3 -m gtm_pipeline next-companies \
  --profile private/clients/example/profile.json \
  --candidates private/example/candidates.json \
  --exclusions private/example/exclusions.json \
  --count 2 --as-of 2026-10-09 \
  --output private/clients/example/runs
```

Use the actual review date for real work. Matching profile IDs, versions, funnel,
profile hash, result hash and run IDs are required for display. Mismatched or
malformed runs are omitted with an unavailable-run notice. Hashes detect changes;
they are not cryptographic signatures. Local operators who can edit the workspace
are trusted. Input file paths are not returned in client manifest views.

`goals.json` has `schema_version: 1`, the workspace's `profile_id`, and a `goals`
array. Each goal has:

- `id`, `title`, `summary` and `owner` strings.
- `status`: `proposed`, `agreed`, `in_progress`, `paused` or `achieved`.
- `target` and `outcome`: descriptions or null for unknown/unagreed values.
- `stages`: stage names; `metric_keys`: keys from the measurement snapshot.
- `next_decision`, `next_step`, `evidence_note`, `success_definition` strings.

Operators edit these files; there is no client goal-editing or approval API yet.
The UI does not infer target attainment from supporting activity counts. Set an
optional IANA `timezone` in private `portal.json` for imported timestamp display;
reporting dates remain literal dates. For example, use America/Los_Angeles when it matches the reporting context.

## Google sign-in and company domains

The optional Google adapter implements the authorization code flow with state,
nonce and PKCE. Google's `google-auth` library verifies signatures, issuer,
audience, issue time and expiry. The adapter additionally checks the nonce,
authorized party and verified email. It requests only `openid email`, stores no
Google access/refresh tokens, and keeps the client secret on the server.

Create a **Web application** OAuth client in a Google Cloud project. Use an
**External** audience to support agency and client organizations. While the
OAuth app is in testing, add the intended test users in Google Cloud. Set the
local authorized redirect URI to exactly:

```text
http://127.0.0.1:8765/auth/google/callback
```

Download the Google web client credentials JSON into the ignored client workspace,
for example `private/clients/example/google-oauth.json`. Restrict it to your user
with `chmod 600`. Do not paste its secret into chat or commit it. A Google OAuth
web client is required, not a service-account key.

```sh
python3 -m venv private/portal-runtime
private/portal-runtime/bin/python -m pip install -e '.[google]'
private/portal-runtime/bin/python -m gtm_pipeline.portal serve \
  --workspace private/clients/example --port 8765 \
  --google-credentials private/clients/example/google-oauth.json \
  --google-admin-email owner@gmail.com
```

Use your real agency owner email. The flag can be repeated for additional trusted
agency administrators. Alternatively, persist the exact addresses in a
`google_admin_emails` array in the workspace's private `portal.json`; command-line
values override it. The configured Google email is bound to its Google subject
ID on first successful sign-in. A changed identity cannot claim that same admin
email later. Changing administrators requires a trusted local configuration edit
and server restart; existing sessions are checked against the current policy.

Until credentials are connected, the Google button is disabled and clearly
labeled as awaiting setup. The existing operator email/password remains available
under **Agency operator access**. Existing legacy sessions are invalidated during
the access-schema upgrade because they did not distinguish operator and client
roles. Sign in again with the existing operator credentials.

In **Workspace settings**, the agency operator can add or remove exact company
domains. New workspaces start with no approved domains. Adding a domain grants
all members of that Google Workspace organization access to this one client
workspace, including project editing and explicit Exa searches; this is organization-wide approval, not an individual invitation.
The server checks the verified Google `hd` claim, never merely an email suffix.
An unapproved subdomain is a different organization. Consumer Gmail accounts
cannot enter through a domain rule, but can be explicitly configured agency
administrators. A client's display email can be an alias; Google's verified
organization claim determines membership.

Removing a domain deletes its active client sessions immediately. Re-adding it
does not revive those sessions. Every domain change records the operator and time
in the private SQLite database. Client members cannot read these settings or
change them, even by calling the API directly. Agency administrator grants are
separate from client domains and are not revoked by removing a client domain.

This provisions **email-domain access**, not DNS or custom portal hostnames. Each
local server still serves one configured client; there is no shared cross-client
administration console yet. For another client, initialize a separate workspace,
serve it on a separate port, and register that instance's exact Google callback.
Live Google login requires your own credentials and remains unverified in this distribution. Offline tests cover the real token verifier with locally
signed synthetic tokens as well as callback handling and access policies.

References: [Google OpenID Connect](https://developers.google.com/identity/openid-connect/openid-connect),
[Google ID token verification](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token).

## Saved measurement snapshots

The portal displays a workspace-local `measurement.json` supplied by a private
source adapter. Client-specific adapters and production snapshots are excluded
from this distribution. There is no bundled generic measurement importer, live
MCP transport, automatic refresh or scheduler.

Inspect `Workspace.measurement` in `gtm_pipeline/portal.py` before integrating a
source. The snapshot must match the workspace profile ID and its SHA-256 hash.
Retain original responses and query provenance privately, with reporting window,
timezone, currency, completeness, filters, metric definitions and retrieval time.
Compute aggregate ratios from summed numerators and denominators. Preserve null
outcomes and distinguish website, advertising, outreach and CRM measurements.
A displayed snapshot does not establish project campaign attribution.

## Isolation and production boundary

Each server process is permanently bound to one workspace and one session database. The local credential is an agency
operator credential; Google client identities can edit projects in their assigned workspace. Requests
cannot select another client, provide a filesystem path or execute arbitrary SQL.
Project mutations use bounded, authenticated endpoints; all POST requests enforce Origin. Optional Google sign-in contacts only Google identity
endpoints, exchanging an authorization code and verifying its ID token. Separate instances require separate ports and distinct
credentials. Other tenants' tokens are invalid. This is process-level workspace
isolation, not an operating-system sandbox against a privileged local operator.

Passwords use salted PBKDF2-HMAC-SHA256 with 600,000 iterations. Random session
secrets are stored as SHA-256 hashes, expire after eight hours, and are revoked on
logout. Login attempts are limited to ten per five minutes per workspace. Login, logout and domain changes enforce the exact request Origin; session cookies
are HttpOnly and SameSite Strict. A separate ten-minute HttpOnly SameSite Lax cookie
binds the Google callback to the browser that initiated it. Its server-side flow
is single-use, with a nonce and PKCE verifier. Client data responses are no-store. Static assets are allowlisted; file
paths are never web routes. Cookies omit Secure only because this server binds
exclusively to plain HTTP on 127.0.0.1.

This standard-library server is a local prototype. Do not reverse-proxy it onto
the internet. Production work still includes a production HTTP service, deployment of the Google identity
configuration, HTTPS/Secure cookies, tenant routing and database constraints for
a shared service, individual invitations, operational monitoring and backups.
Domain changes already have a workspace-local audit trail; this is not a complete
production security audit system. Domain ownership alone is not deployment configuration.

## Validation

Run `python3 -m unittest discover -s tests -v`. Portal tests exercise authentication,
logout and expiry, cross-workspace token rejection, request boundaries, path
rejection, run integrity, mismatched goals/measurement, rate limiting, unknown
metric preservation and provisioning safety. The UI is also checked in the browser. To include the real Google signature
verification tests, run `private/portal-runtime/bin/python -m unittest discover -s tests -v`
after installing the optional dependency. The stdlib suite skips those two tests;
all remaining callback and access tests run without Google libraries or network calls.



## Codex-style product direction

The default interface uses a compact workspace sidebar, contextual search prompt,
goals presented as tasks, and focused goal detail views. The design is a Machines
Among Us product study, not an OpenAI product or a native Codex integration.
`?design=classic#overview` opens the original agency dashboard; `?design=codex`
explicitly selects the default design. Both use the same authenticated workspace.

The prompt searches saved goals and metrics. Quick actions retrieve recorded next
decisions, campaign results, and missing evidence. It is deterministic local search,
not a connected model, and does not trigger external actions. Goal selection opens
its target, outcome, owner, workstreams, and evidence. Search results retain the
reporting window and relevant source caveats.

## Sidebar projects

An optional workspace-local `projects.json` supplies the expandable **Projects**
section in the sidebar. It has `schema_version: 1`, the matching `profile_id`,
and a `projects` array of objects with nonempty `title` strings. The section starts
expanded and retains its open or closed state while navigating within the page.
Project cards and sidebar entries open a project workspace with six tabs and
persisted target/search counts. They do not imply qualification or campaign progress. Client-specific names remain in the private workspace.

The primary sidebar sections are Projects, Cluster briefs, Creative, Landing pages,
and Analytics. Analytics uses the existing measurement snapshot. The global Creative and Landing pages libraries currently show empty states.
Their project tabs store scoped draft content and reference links. Global named
brief collections are not automatically mapped into project clusters. The agency brand link opens the goals overview.

Cluster briefs uses a two-column card collection (one column on phones). Its
workspace-local `cluster-briefs.json` has `schema_version: 1`, matching `profile_id`,
and a `briefs` array of objects with nonempty `title` strings. Configured empty collections remain explicitly empty. Cards display the absence of brief content instead
of inventing timestamps or completed research. Opening a card shows its empty
brief; pins are presentation preferences for the current page session only.

Workspace settings lists **Connected ad accounts** from an optional `ad_accounts`
array in private `portal.json`. Each entry has `provider`, `account_id` and an HTTPS
`url`. These are account links, not a claim that an OAuth/API integration has been
verified. Only those three fields are exposed to the authenticated client. Links
open externally; no campaigns are edited and no new provider permissions are granted.

The **Projects** sidebar label opens `#projects`, a card homepage using the same
layout as Cluster briefs. The separate chevron toggles the sidebar list without
navigating. Both card titles and sidebar project names open the Targets tab.
Project pins are independent of brief pins and last for the current page session.


## Project workspaces and Exa

Projects are seeded once per unique title from private `projects.json`, assigned
stable IDs and saved in private `projects.sqlite3`. Renaming or removing a seed
file entry does not delete an existing project. Routes use
`#project/<id>/<tab>` for Targets, Clusters, Cluster briefs, Creative, Landing pages
and Analytics. Both client members and agency admins can add/edit targets, run
searches and clustering, and save drafts. Each action records its actor and time.
Domain grants remain administrator-only. Data survives browser and server restarts.

The Targets tab accepts company name, website, description, sector, tags and notes.
Websites are normalized by case and leading `www`; exact domains deduplicate
within a project. Subdomains, subsidiaries and aliases are not automatically
merged. New targets remain unreviewed. This discovery list does not apply the
separate selection engine's eligibility/exclusion rules or enroll anyone.

To enable Exa, provide `EXA_API_KEY` in the server environment, or put the key in
`exa-api-key.txt` inside the private client workspace and restrict it with
`chmod 600`. A `--exa-key-file` argument selects another private file. Restart the
server after configuring the key. Never put the key in browser code or chat.
Without an Exa key, the search controls show that setup is required. Live provider behavior and billing have not been validated.

A submitted search calls the fixed HTTPS Exa endpoint using company category,
auto search, highlights and moderation, requesting 1 through 100 results. It
sends the query and settings, not the project's target list. Each project permits
20 search attempts per hour and 1,000 targets. There are no automatic retries or
redirects. Operation IDs prevent repeated submissions from repeating a paid call;
concurrent searches in a project are blocked. Interrupted runs become unknown on
the next attempt after two minutes; check provider usage before rerunning them.
Counts are request limits, not a dollar budget. User-initiated searches may incur
provider charges, as disclosed in the search form.

Search history retains parameters, timestamps, actor, request/input and response
hashes, provider request ID, result counts, additions, duplicates, omissions and
provider-reported cost data when available. Raw responses stay in the private
SQLite document and are omitted from the client API. Reruns use exact original
parameters; duplicate domains append source evidence without replacing manual
assessments. Directory results from recognized company-profile aggregators and
invalid websites are held out with reasons. Exa results are unreviewed evidence.
See [Exa search API](https://exa.ai/docs/reference/search) for the provider contract.

Clustering is an explicit local action with no paid call. TF-IDF cosine similarity
connects targets at a 0.24 threshold using descriptions, sectors, tags and notes.
Connected components can contain members that are only indirectly related;
shared terms and pairwise edges are inspectable. Missing or unrelated evidence
stays ungrouped. Each run preserves its inputs, sources, method and hash. Changes
to targets or their sources flag prior runs as stale; rerunning creates a new
version. This does not reproduce an embedding/facet algorithm.

Cluster briefs show each cluster's source pack, including descriptions, notes,
search excerpts, source links and dates. Saved briefs link to a specific cluster
snapshot. Creative and landing-page tabs accept draft text and reference links,
optionally linked to a cluster. These are draft records, without publishing or
asset generation. Editing/deleting saved draft assets is not implemented yet.
Analytics shows project activity counts and a clear unconnected state for campaign
metrics. Workspace-wide measurement remains separate and is not attributed here.

Offline project tests cover persistence, duplicate domains, exact reruns,
idempotency, failures, source retention, stable clustering, stale snapshots,
cluster/asset scope, and client editing with administrator-only domain control.
Browser validation uses a separate synthetic workspace and simulated provider;
no synthetic targets or searches are added to the client workspace.


### Search configuration dropdown

Each project has a **Data Sources** configuration control beside its title,
accessible from all six tabs. Its **Access Searches** section contains search history and metadata,
an inline query editor, maximum results, and actions to rerun saved settings or
edit them as a new query. Search execution and permissions use the same project
API. The targets table keeps manual entry as its primary page action.

The dropdown closes on Escape or outside click. Unsubmitted query drafts remain
project-specific in page memory while navigating and are cleared by page reload
or sign-out. The query editor is usable before Exa setup, while Run remains
disabled. Saved reruns use read-only original settings until Edit as new query is
selected. Browser checks used simulated searches in an isolated test workspace.


### Company and contact targets

The Targets page has Companies and Contacts tabs with independent counts and
manual entry forms. Company discovery and text clustering continue to use company
targets. Contacts are separate project records with name, company, role, optional
email/profile URL and notes. Both client members and admins can add or edit them;
source history preserves actor, timestamps and previous values. New records are
unreviewed. No contact search, enrichment or sending is performed.

Contacts remain in the same private project database. Older project documents
read as an empty contact list without replacing their existing company data.
Email and profile URL duplicates are rejected within a project, while names alone
are not treated as identity. Each project allows up to 1,000 contacts. Homepage
and analytics target counts include both kinds; company clustering and its hashes
remain separate from contact changes. Target-tab selection is kept per project
until page reload or sign-out.


The Data Sources dropdown groups three expandable sections: **Access Searches**,
**Data Upload**, and **MCP Connection**. The existing Exa editor and history live
under Access Searches. Data Upload and MCP Connection currently show explicitly
unavailable/unconnected panels; this UI change does not implement file imports
or a live project MCP transport. An existing workspace measurement snapshot is
identified separately and never presented as a project source connection.


### Data source provenance and usage

Data Sources shows independent system-controlled status indicators. One, two or
all three sources may show a green check and "In use". The server derives usage
from current project records that retain references to completed searches or
imports. Historical receipts alone do not mark a source in use; a connection setting, opened
section, failed run or successful empty search does not mark it used. All source
sections may be expanded together. Workspace-wide analytics never marks a project
MCP source as used.

Removing the last active record linked to a source changes its status to a muted
"Not in use". Remove from project archives the full record and its source links;
it does not erase audit receipts. Removed records can be restored from the target
list, which restores source usage too. Restoration rejects identity conflicts
rather than replacing an existing record. History labels removed contributions.

Search history shows the initiating account email, full timestamp with timezone,
status, added/existing/omitted counts, and each contributed record. New search runs
persist field snapshots, source excerpts, record IDs and addition/evidence-update
actions. Later edits do not rewrite these receipts. Older runs without field
receipts retain source excerpts and show a clearly labeled current company name.
Raw provider responses remain private. Manual additions/edits also appear in an
activity log; new manual changes include field snapshots in their source history.

`ProjectStore.import_source_records` is a local adapter boundary for supplied
company/contact records with `kind` upload or mcp, a display label, actor and
operation ID. Validation precedes import; records, source references and receipt
commit together. An identical operation ID is not imported twice. It preserves
manual fields when adding evidence to an existing domain/contact. Conflicting
contact identities require review. Source receipts retain timestamps, field
snapshots, input hashes, file or server display names and per-record outcomes.
They remain private and scoped to the selected workspace and project.

Upload history displays file, initiating account, timestamp and contributions.
MCP history displays the server name, importing account, import timestamp and
contributions. An import timestamp is not represented as a verified connection
establishment time. No UI upload endpoint, MCP connector or connection event is
fabricated by this storage boundary. Those integrations remain unimplemented;
actual connection logs must be written when a future connector establishes them.
Offline and browser tests use clearly synthetic receipts, without modifying the
client data or contacting providers.

### Sequences navigation

The workspace sidebar opens Sequences at `#sequences`. It represents the order
of ads an audience sees across platforms over time, including the timing between
steps. Its landing page is currently an empty state; sequence editing and ad
delivery are not implemented. The former workspace `#creative` link remains an
alias. Individual project Creative tabs still store draft assets.
