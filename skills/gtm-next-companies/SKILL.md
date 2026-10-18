---
name: gtm-next-companies
description: Select the next N eligible companies for a configured funnel from saved, reviewed assessments in GTM Pipeline. Use for initial batches or replenishment with identity checks, exclusions, evidence freshness, reserves and explicit shortfalls. This workflow does not use the browser or enroll companies.
---

# Select the next companies

Read checkout `AGENTS.md`, [the input contract](../../docs/contracts.md) and
[selection guidance](references/selection.md). Run commands from the checkout
root. The implemented selector is `gtm_pipeline/cli.py`; it performs no network
requests and does not establish the truth of supplied assessments.

Resolve requested N, company profile/version, funnel, reviewed candidate file,
dated exclusion snapshot, review date and private output destination. Reuse
session inputs. Ask for N or the target business only if execution needs an
unresolved choice; inspect available evidence in the meantime. Use the profile's
funnel, not an assumed company-wide scope.

Read saved evidence first. Exclusions must cover membership, customers,
suppression, holds and previous pending batches. Missing/stale coverage is
provisional, not proof that a company is net-new. Do not fabricate complete
coverage or fill required unknowns to reach N.

Use the actual commands, replacing placeholders with reviewed private files and
the real review date:

```sh
python3 -m gtm_pipeline validate --profile private/<client>/profile.json
python3 -m gtm_pipeline next-companies \
  --profile private/<client>/profile.json \
  --candidates private/<client>/candidates.json \
  --exclusions private/<client>/exclusions.json \
  --count <N> --as-of <YYYY-MM-DD> --output output/runs
```

For an offline, explicitly synthetic smoke check, use all three files from
`examples/warehouse-software/`, `--count 2` and `--as-of 2026-10-09`. The fixed
date belongs to the fixture; never use it to make live evidence appear current.

Inspect the generated `next-companies.json`, `next-companies.md` and
`manifest.json`. Reconcile requested/selected counts, reserves, exclusions,
unknowns, coverage gaps and input/output hashes. Scores sum configured weights
for passing reviewed criteria and break ties by domain; they are not intent.

If saved evidence is insufficient, deliver the shortfall and a concrete research
plan. Route requested discovery to [gtm-clusters](../gtm-clusters/SKILL.md) as a
separate stage. Do not open tabs, extract browser credentials or silently use
the portal's paid search within this browser-free selection workflow. A supplied
API/export may refresh evidence within scope; no CRM connector is bundled here.

Outputs remain draft or provisional. Record later review separately, preserve
the hashed run and include pending selections in subsequent exclusion snapshots.
The CLI neither reserves accounts nor writes to a funnel. Hand off to research,
outreach or operations according to the request and report actual additions
separately from selections.
