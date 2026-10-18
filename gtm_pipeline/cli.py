"""Small CLI boundary with pinned inputs and isolated run artifacts."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from uuid import uuid4

from . import __version__
from .selection import InputError, select, validate_profile


def load(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return json.loads(raw), {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}


def write_run(result, inputs, output):
    # Unique directories prevent reruns from replacing previous decisions.
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex
    target = Path(output) / run_id
    target.mkdir(parents=True, exist_ok=False, mode=0o700)
    result["run_id"] = run_id
    encoded = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    (target / "next-companies.json").write_text(encoded, encoding="utf-8")
    manifest = {"schema_version": 1, "toolkit_version": __version__, "run_id": run_id,
                "created_at": datetime.now(timezone.utc).isoformat(), "inputs": inputs,
                "output_sha256": hashlib.sha256(encoded.encode()).hexdigest(),
                "execution": "local-saved-evidence", "external_actions": [],
                "status": result["status"]}
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    lines = ["# Next companies", "", f"Status: {result['status']}. "
             f"Selected {result['selected_n']} of {result['requested_n']}; shortfall {result['shortfall']}.",
             "", f"Profile: {result['profile_id']} / {result['profile_version']}. "
             f"Funnel: {result['funnel']}. As of: {result['as_of']}.", "",
             "Scores are weighted reviewed criteria, not purchase intent probabilities.",
             "No companies have been reserved, enrolled or sent messages.", ""]
    for section in ("selected", "reserves", "excluded"):
        lines.extend([f"## {section.title()}", ""])
        for row in result[section]:
            lines.append(f"- {row['name']} ({row['domain']}): {row['score']}/100. "
                         + "; ".join(row["reasons"]))
        if not result[section]:
            lines.append("None.")
        lines.append("")
    lines.extend(["## Coverage gaps", ""] + [f"- {gap}" for gap in result["coverage_gaps"]])
    if not result["coverage_gaps"]:
        lines.append("None reported by the supplied snapshot; review is still required.")
    lines.extend(["", "Full assessment evidence and unknowns are in next-companies.json.", ""])
    (target / "next-companies.md").write_text("\n".join(lines), encoding="utf-8")
    return target.resolve()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Local, configurable GTM toolkit")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="Validate a company profile")
    validate.add_argument("--profile", required=True)
    batch = commands.add_parser("next-companies", help="Rank saved, reviewed company assessments")
    for field in ("profile", "candidates", "exclusions", "as-of"):
        batch.add_argument("--" + field, required=True)
    batch.add_argument("--count", type=int, required=True)
    batch.add_argument("--output", default="output/runs")
    args = parser.parse_args(argv)
    try:
        profile, profile_ref = load(args.profile)
        if args.command == "validate":
            validate_profile(profile)
            print(f"Valid profile: {profile['id']} / {profile['version']}")
            return 0
        candidates, candidates_ref = load(args.candidates)
        exclusions, exclusions_ref = load(args.exclusions)
        result = select(profile, candidates, exclusions, args.count, args.as_of)
        target = write_run(result, {"profile": profile_ref, "candidates": candidates_ref,
                                   "exclusions": exclusions_ref}, args.output)
        print(json.dumps({"output": str(target), "status": result["status"],
                          "selected_n": result["selected_n"], "shortfall": result["shortfall"]}))
        return 0
    except (InputError, OSError, ValueError, TypeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
