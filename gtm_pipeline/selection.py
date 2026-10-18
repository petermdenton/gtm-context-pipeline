"""Select saved, assessed companies. This module performs no network operations."""

from collections import Counter
from datetime import date
import re
from urllib.parse import urlsplit


class InputError(ValueError):
    """An input does not meet the toolkit's data contract."""


def require(condition, message):
    if not condition:
        raise InputError(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def integer(value, minimum=1):
    return type(value) is int and value >= minimum


def day(value):
    require(isinstance(value, str), "Dates must be YYYY-MM-DD strings")
    try:
        result = date.fromisoformat(value)
    except ValueError as error:
        raise InputError("Dates must use YYYY-MM-DD") from error
    require(result.isoformat() == value, "Dates must use YYYY-MM-DD")
    return result


def domain(value):
    require(nonempty(value), "Company domain is required")
    value = value.strip().lower().rstrip(".")
    parsed = urlsplit(value if "://" in value else "https://" + value)
    require(parsed.scheme in {"http", "https"} and not parsed.username
            and not parsed.password and parsed.netloc, "Invalid company domain")
    host = (parsed.hostname or "").removeprefix("www.")
    require(len(host) <= 253 and "." in host
            and all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                    for label in host.split(".")), "Invalid company domain")
    return host


def object_version(value, label):
    require(isinstance(value, dict), f"{label} must be an object")
    require(type(value.get("schema_version")) is int and value["schema_version"] == 1,
            f"{label} requires schema_version 1")


def validate_profile(profile):
    object_version(profile, "Profile")
    for field in ("id", "version", "company", "offer", "funnel"):
        require(nonempty(profile.get(field)), f"Profile requires {field}")
    for field in ("evidence_max_age_days", "exclusions_max_age_days"):
        require(integer(profile.get(field)), f"Profile requires positive {field}")
    criteria = profile.get("criteria")
    require(isinstance(criteria, list) and criteria, "Profile requires criteria")
    ids = []
    for item in criteria:
        require(isinstance(item, dict), "Criteria must be objects")
        require(nonempty(item.get("id")) and nonempty(item.get("description")),
                "Each criterion needs id and description")
        require(integer(item.get("weight"), 0), "Criterion weight must be a nonnegative integer")
        require(type(item.get("required")) is bool, "Criterion required must be boolean")
        ids.append(item["id"])
    require(len(ids) == len(set(ids)), "Criterion IDs must be unique")
    require(sum(item["weight"] for item in criteria) == 100, "Criterion weights must total 100")
    require(any(item["required"] for item in criteria), "At least one eligibility criterion must be required")
    return profile


def validate_snapshot(snapshot, profile, as_of):
    object_version(snapshot, "Exclusions")
    require(snapshot.get("funnel") == profile["funnel"], "Exclusions funnel must match profile")
    age = (as_of - day(snapshot.get("as_of"))).days
    coverage = snapshot.get("coverage")
    require(isinstance(coverage, dict), "Exclusions require coverage")
    gaps = []
    for key in ("membership", "customers", "suppression", "holds", "pending_batches"):
        require(coverage.get(key) in {"complete", "partial", "unknown"},
                f"Exclusions coverage requires {key}")
        if coverage[key] != "complete":
            gaps.append(f"{key} coverage is {coverage[key]}")
    if not 0 <= age <= profile["exclusions_max_age_days"]:
        gaps.append("Exclusion snapshot is stale or future-dated")
    records = snapshot.get("records")
    require(isinstance(records, list), "Exclusions records must be a list")
    for record in records:
        require(isinstance(record, dict) and nonempty(record.get("reason")),
                "Every exclusion requires a reason")
        identities(record)
    return gaps


def identities(record):
    aliases = record.get("aliases", [])
    require(isinstance(aliases, list), "Aliases must be a list of domain strings")
    return {domain(record.get("domain")), *(domain(alias) for alias in aliases)}


def validate_candidates(candidates, profile):
    object_version(candidates, "Candidates")
    require(candidates.get("profile_id") == profile["id"]
            and candidates.get("profile_version") == profile["version"],
            "Candidate assessments must match profile ID and version")
    records = candidates.get("records")
    require(isinstance(records, list), "Candidates records must be a list")
    criteria = {item["id"] for item in profile["criteria"]}
    for record in records:
        require(isinstance(record, dict) and nonempty(record.get("name")),
                "Every candidate requires a name")
        require(nonempty(record.get("origin")), "Every candidate requires an origin")
        identities(record)
        assessments = record.get("assessments")
        require(isinstance(assessments, dict), "Every candidate requires assessments")
        require(set(assessments) <= criteria, "Assessment references an unknown criterion")
        for assessment in assessments.values():
            require(isinstance(assessment, dict), "Assessment must be an object")
            require(assessment.get("verdict") in {"pass", "fail", "unknown"},
                    "Assessment verdict must be pass, fail or unknown")
            require(nonempty(assessment.get("rationale")), "Assessment requires rationale")
            if assessment["verdict"] != "unknown":
                require(nonempty(assessment.get("reviewed_by")), "Assessment requires reviewed_by")
                day(assessment.get("observed_at"))
                source = assessment.get("source_url")
                require(nonempty(source), "Assessment requires source_url")
                parsed = urlsplit(source)
                require(parsed.scheme in {"https", "http"} and parsed.hostname
                        and not parsed.username and not parsed.password,
                        "Assessment source_url must be an HTTP(S) URL without credentials")


def select(profile, candidates, snapshot, requested_n, as_of):
    validate_profile(profile)
    require(integer(requested_n), "Requested count must be a positive integer")
    as_of = day(as_of)
    validate_candidates(candidates, profile)
    gaps = validate_snapshot(snapshot, profile, as_of)

    # Join explicitly supplied aliases transitively, including suppressed domains.
    # Do not guess corporate ownership or collapse arbitrary subdomains.
    parent = {}

    def root(key):
        parent.setdefault(key, key)
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    for record in candidates["records"] + snapshot["records"]:
        keys = sorted(identities(record))
        for key in keys:
            parent[root(key)] = root(keys[0])
    counts = Counter(root(domain(record["domain"])) for record in candidates["records"])
    blocked = {}
    for record in snapshot["records"]:
        blocked.setdefault(root(domain(record["domain"])), []).append(record["reason"])

    eligible, excluded = [], []
    for record in candidates["records"]:
        key = domain(record["domain"])
        group = root(key)
        reasons = list(blocked.get(group, []))
        if counts[group] > 1:
            reasons.append("Duplicate company identity: consolidate assessments before selection")
        score, unknowns = 0, []
        for criterion in profile["criteria"]:
            assessment = record["assessments"].get(criterion["id"], {"verdict": "unknown"})
            verdict = assessment["verdict"]
            if verdict != "unknown":
                age = (as_of - day(assessment["observed_at"])).days
                if not 0 <= age <= profile["evidence_max_age_days"]:
                    verdict = "unknown"
            if verdict == "unknown":
                unknowns.append(criterion["id"])
            if criterion["required"] and verdict != "pass":
                reasons.append(f"Required criterion {criterion['id']}: {verdict}")
            if verdict == "pass":
                score += criterion["weight"]
        row = {**record, "domain": key, "score": score, "unknowns": unknowns,
               "review_status": "draft", "reasons": reasons}
        (excluded if reasons else eligible).append(row)

    eligible.sort(key=lambda row: (-row["score"], row["domain"]))
    for rank, row in enumerate(eligible, 1):
        row["rank"] = rank
    selected = eligible[:requested_n]
    return {"schema_version": 1, "stage": "next-companies", "profile_id": profile["id"],
            "profile_version": profile["version"], "funnel": profile["funnel"],
            "as_of": as_of.isoformat(), "status": "provisional" if gaps else "draft",
            "requested_n": requested_n, "selected_n": len(selected),
            "shortfall": requested_n - len(selected), "coverage_gaps": gaps,
            "exclusion_snapshot_as_of": snapshot["as_of"],
            "selected": selected, "reserves": eligible[requested_n:],
            "excluded": excluded, "reviewed_n": 0, "verified_added_n": 0,
            "discovery_requests": 0, "discovery_cost": 0,
            "next_action": "Review evidence and coverage, then hand off selected companies for research"}
