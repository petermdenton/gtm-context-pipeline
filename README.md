# GTM Context Pipeline

An evidence-based GTM workflow toolkit with a local project portal and eight
agent skills. Turn company context and reviewed evidence into target selections,
draft clusters, briefs and reviewable next steps.

Python 3.11+ runs the core without third-party dependencies. All included company
fixtures are fictional and synthetic. Client data stays in ignored workspaces.

## Run the synthetic example

```sh
git clone https://github.com/petermdenton/gtm-context-pipeline.git
cd gtm-context-pipeline
python3 -m gtm_pipeline validate --profile examples/warehouse-software/profile.json
python3 -m gtm_pipeline next-companies \
  --profile examples/warehouse-software/profile.json \
  --candidates examples/warehouse-software/candidates.json \
  --exclusions examples/warehouse-software/exclusions.json \
  --count 2 --as-of 2026-10-09
```

The fixed date makes the demo reproducible. Real runs should use their actual
review date and current evidence. Try `examples/model-evaluation/` for a second
fictional business using the same selection engine.

Each run writes JSON results, a readable Markdown report and a SHA-256 manifest
to ignored `output/runs/`. Results include selections, reserves, exclusions,
unknowns, coverage gaps and shortfalls. Scores rank supplied assessments; they
are not probabilities of purchase. The engine validates evidence records but
does not browse their URLs or establish that the assessments are true.

## Open the local portal

```sh
python3 -m gtm_pipeline.portal demo
python3 -m gtm_pipeline.portal serve --workspace private/portal-demo
```

Open <http://127.0.0.1:8765>. Expand **Agency operator access** and use the generated
credentials in `private/portal-demo/demo-login.txt`. The demo command creates a
new workspace and refuses to overwrite an existing one. Use `--workspace` with
a new private directory when creating another demo.

The portal includes project targets, company/contact records, source receipts,
draft text clustering, cluster briefs, creative/page drafts and saved measurement
views. It binds to one workspace on loopback. It is a local prototype and must
not be exposed as a public login service.

## What works today

| Capability | Status |
| --- | --- |
| Profile validation and saved-company selection | Implemented; evidence freshness, identity, exclusions and run hashes |
| Local project portal | Implemented; persistent targets, contacts, source receipts and draft content |
| Company discovery | Optional Exa adapter; private API key required; offline-tested, live paid validation pending |
| Clustering | Local TF-IDF similarity; draft analytical groups, not approved campaign memberships |
| Identity and access | Local operator login; optional Google sign-in and exact-domain grants; offline-tested |
| Measurement | Saved workspace snapshots; client-specific importers are external |
| Research, outreach and campaign workflows | Eight agent skills; execution depends on available authorized tools |
| Rendering, publication, CRM writes, sending and scheduling | Not implemented by this toolkit |

Exa requests occur only after explicit search submission and may incur provider
charges. Google sign-in requires your own OAuth configuration and the optional
`google` dependency. See [portal setup](docs/client-portal.md).

## Use the skills

The eight workflows live under `skills/`, with relative discovery links in
`.agents/skills/`. Use [the routing table](AGENTS.md#skill-routing) to choose a
stage. Start with [gtm-pipeline](skills/gtm-pipeline/SKILL.md) for a multi-stage
request or saved handoff. Agents that do not discover repository skills can
read the relevant `SKILL.md` directly.

Skills guide judgment, evidence collection, review and handoffs. They do not
install integrations or execute external actions by themselves. Recorded-workflow
discovery is optional and requires a separately installed discovery skill.

## Adapt it to your business

Copy a fictional example into ignored `private/<company>/`, then replace its
profile, reviewed candidate assessments and exclusions using the
[input contracts](docs/contracts.md). Version profiles when criteria change.
Keep approved claims, research, contacts, credentials and production data private.
Required unknown or stale evidence blocks selection; incomplete exclusion
coverage makes a batch provisional. Include prior pending selections and recheck
membership before making live additions.

## Development

A [GitHub Actions template](docs/github-actions.yml) runs the suite on Python 3.11
and 3.14. To enable it, copy it to `.github/workflows/tests.yml` and push using a
GitHub login authorized to manage workflows. CI is not enabled in this initial
publication because the publishing credential lacks that permission.

```sh
python3 -m unittest discover -s tests -v
```

Optional installation: `python3 -m pip install -e .`, which exposes the `gtm`
command. For Google identity verification, install `python3 -m pip install -e
'.[google]'` in a virtual environment. The standard-library suite skips two
optional Google signature tests when that dependency is absent.

See [architecture](docs/architecture.md), [roadmap](docs/extraction-plan.md),
[design system](docs/design-system.md), [contributing](CONTRIBUTING.md) and
[release provenance](docs/provenance.json). This distribution does not currently
include an open-source license grant.
