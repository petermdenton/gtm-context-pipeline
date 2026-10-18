# Input contracts, schema version 1

The executable validation is in `gtm_pipeline/selection.py`. The two example
directories are complete fixtures. Unknown extra fields are preserved where
appropriate for future metadata; unsupported schema versions fail.

## Profile

Required fields: `schema_version`, `id`, `version`, `company`, `offer`, `funnel`,
positive `evidence_max_age_days` and `exclusions_max_age_days`, and `criteria`.
Each criterion has a unique `id`, description, nonnegative integer `weight`,
and boolean `required`. Weights total 100. Required criteria must pass to select
an account; optional criteria contribute ranking weight only when they pass.
At least one criterion must be required so that eligibility always needs evidence.

Treat profile versions as immutable. Candidate `profile_id` and `profile_version`
must match. The manifest additionally pins the exact profile bytes by SHA-256.

## Candidates

Envelope: `schema_version`, `profile_id`, `profile_version`, and `records`.
Each company has `name`, `domain`, optional domain `aliases`, `origin` identifying
its source run or seed, and `assessments` keyed by criterion ID.

Each assessment contains `verdict` (`pass`, `fail`, `unknown`) and `rationale`.
A pass or fail additionally requires `reviewed_by`, an HTTP(S) `source_url`, and
`observed_at` in YYYY-MM-DD format. That date is the observation date, not a claim
about when a webpage was published. Source content and the conclusion must be
reviewed upstream; this command validates structure and freshness only.

Missing, explicitly unknown, stale or future-dated assessments are unknown at
selection time. Stale source assessments remain in the output, alongside the
effective `unknowns` list. Optional unknowns add no score but are not interpreted
as negative facts. Required unknowns or failures block selection.

## Exclusions

Envelope: `schema_version`, matching `funnel`, `as_of` date, `coverage`, and
`records`. Coverage requires `membership`, `customers`, `suppression`, `holds`
and `pending_batches`, each `complete`, `partial` or `unknown`.
Every record has a domain, optional aliases and a nonempty reason. Every listed
company is excluded. Importers must map all applicable lifecycle and suppression
states into this combined exclusion list before claiming complete coverage.

Future/stale snapshots and partial/unknown coverage are explicit provisional
conditions. The engine still excludes every known blocked identity.

## Result and manifest

The result contains selected, reserve and excluded records; profile/funnel/date;
requested/selected counts and shortfall; coverage gaps; effective unknowns and
draft review status. `reviewed_n` and `verified_added_n` remain zero because the
command performs neither review nor enrollment. Ties sort by normalized domain.
The manifest pins each input path/hash and the full JSON output hash.

Private records belong under ignored `private/` and generated runs under ignored
`output/`. A custom `--output` path is supported; the caller owns its privacy and
Git ignore configuration. Do not put real contacts or account snapshots in examples.
