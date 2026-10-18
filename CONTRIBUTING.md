# Contributing

Read `AGENTS.md`, the architecture and relevant data contracts before changes.
Use Python 3.11+ and the standard library for the core. Keep company rules in
profiles and provider behavior in adapters. Preserve unrelated working-tree edits.

Use synthetic fixtures for examples and tests. Put real workspaces, captures,
contacts, credentials, source responses and generated runs in ignored `private/`
or `output/`. Never add real customer data to a screenshot or test fixture.

Run `python3 -m unittest discover -s tests -v` before submitting a change. For
Google signature verification, install `.[google]` and run the same suite.
For UI changes, use an isolated synthetic workspace and inspect desktop and mobile
flows. Validate changed skills with an available skill-creator validator, check
relative links and verify documented commands against the CLI.

Explain the problem, resulting behavior, validation and remaining limitations.
Keep drafts, reviewed artifacts and verified external outcomes distinct. This
repository has no open-source license grant yet; agree on contribution terms
with the owner before submitting externally authored work.
