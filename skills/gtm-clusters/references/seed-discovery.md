# Seed discovery and campaign assignment

Resolve supplied seeds to canonical domains and professional company identities.
Record why each is relevant, the client's proposed contribution, dated evidence,
fit hypotheses and open gates. No fixed seed count or industry is assumed.
For feedback seeds, retain engagement type, exposure, window, identity confidence
and outcome coverage; an engager's similarity is not a candidate's buying intent.

Search saved reviewed candidates and project evidence before paid expansion.
Separate already-targeted accounts, eligible prospects, customers/suppressions,
holds and identity gaps. The portal's target list is not a complete exclusion
snapshot. Preserve previous searches and the reasons for any reconsideration.

Translate seeds into explicit workflow queries, inclusions, geography and scale
constraints. Keep search parameters separate from the selection profile schema.
The local Exa adapter is called by project search, not `scripts/exa_discover.py`.
Inspect [portal search behavior](../../../docs/client-portal.md#project-workspaces-and-exa)
before execution. Keep credentials private, report actual costs where available,
and stop at authorized scope. An uncertain request result needs reconciliation
before a paid retry; an operation ID is not proof the provider completed it.

Provider results are discovery evidence. Verify the candidate's own offer/work
and map that evidence to profile criteria. Preserve origin run/seed, query,
source dates, unknowns and independent exclusions. A project's domain dedupe
does not verify corporate aliases, eligibility or CRM membership. Contact
research requires current professional evidence, not an assumed buyer title.

For a new grouping, use the current local text method and review its connected
components. Missing or unrelated descriptions remain ungrouped. Embedding/facet
clustering from the source repository is not implemented here. Do not invent
cached vectors or claim TF-IDF reproduces their results.

For an incremental batch, compare each company's evidence with the current
reviewed campaign definitions. Do not inherit a seed's membership automatically
or recluster the whole universe for every addition. Each proposal carries company
key, taxonomy version, primary membership or null, evidence, rationale, alternatives
and `proposed`, `reviewed` or `hold` status. Record the reviewer or approved rule.

Preserve the old taxonomy and write a versioned membership delta. Reconcile
primary assignments, holds and counts. Existing categories can reuse compatible
assets; new categories need explicit downstream support. Operations must resolve
real platform destinations before applying a membership, because a cluster label
is not a live campaign ID.
