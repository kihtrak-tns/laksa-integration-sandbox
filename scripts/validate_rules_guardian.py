#!/usr/bin/env python3
"""Deterministically validate the LAKSA Rules Guardian foundation.

The rule register is stored as JSON-compatible YAML so this validator needs
only the Python standard library.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


EXPECTED_OUTCOMES = {
    "COMPLIANT",
    "NON-COMPLIANT",
    "NEEDS ORGANIZER CLARIFICATION",
    "NOT APPLICABLE",
}

VALID_VERIFICATION = {
    "ALIGNED",
    "OPEN_DESIGN",
    "OPEN_EVIDENCE",
    "CLARIFY",
    "CONFLICT",
    "PROCESS",
    "OPTIONAL",
}

VALID_SEVERITY = {"blocking", "advisory"}

REQUIRED_FILES = (
    "AGENTS.md",
    ".agents/skills/laksa-rules-guardian/SKILL.md",
    ".github/pull_request_template.md",
    ".github/workflows/rules-compliance.yml",
    "docs/compliance/source_manifest.json",
    "docs/compliance/rules_register.yaml",
    "docs/compliance/rules_compliance_matrix.md",
    "docs/compliance/organizer_clarifications.md",
    "docs/compliance/architecture_compliance.md",
    "docs/compliance/initial_autonomy_integration_review.md",
    "docs/compliance/visual_start_signal_notes.md",
    "docs/compliance/competition_release_checklist.md",
    "scripts/validate_rules_guardian.py",
    "tests/test_rules_guardian.py",
)

MANDATORY_RULE_IDS = {
    "0.1.1",
    "0.1.2",
    "0.2.4-0.2.4.1",
    "0.2.5-0.2.5.3",
    "1.2-1.2.2.4",
    "1.2.9",
    "2.2.1",
    "2.2.2",
    "2.3",
    "2.4-2.4.1",
    "2.5.1",
    "2.5.2",
    "2.7",
    "3.4.1",
    "3.6.1-3.6.2",
    "3.7.1-3.7.3.3",
    "4.2-4.2.4",
    "5.2-5.2.1",
}

MANDATORY_OPEN_CLARIFICATIONS = {
    "CLAR-001",
    "CLAR-002",
    "CLAR-003",
    "CLAR-004",
}


class ValidationError(Exception):
    """Raised when a deterministic compliance artifact check fails."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot parse {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise ValidationError(f"{path} must contain a top-level object")
    return loaded


def require_nonempty_string(item: dict[str, Any], key: str, context: str) -> None:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{context}: {key} must be a nonempty string")


def require_nonempty_string_list(item: dict[str, Any], key: str, context: str) -> None:
    value = item.get(key)
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(entry, str) or not entry.strip() for entry in value)
    ):
        raise ValidationError(f"{context}: {key} must be a nonempty list of strings")


def validate_required_files(repo_root: Path) -> None:
    missing = [path for path in REQUIRED_FILES if not (repo_root / path).is_file()]
    if missing:
        raise ValidationError("missing required files: " + ", ".join(missing))


def validate_skill(skill_path: Path) -> None:
    content = skill_path.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        raise ValidationError("Rules Guardian SKILL.md lacks YAML frontmatter")
    frontmatter_match = re.match(r"---\n(.*?)\n---\n", content, re.DOTALL)
    if not frontmatter_match:
        raise ValidationError("Rules Guardian SKILL.md has malformed frontmatter")
    frontmatter = frontmatter_match.group(1)
    if "name: laksa-rules-guardian" not in frontmatter:
        raise ValidationError("Rules Guardian skill name is missing or incorrect")
    if "description:" not in frontmatter:
        raise ValidationError("Rules Guardian skill description is missing")

    for outcome in EXPECTED_OUTCOMES:
        if outcome not in content:
            raise ValidationError(f"Rules Guardian skill omits outcome: {outcome}")


def validate_source(manifest: dict[str, Any], register: dict[str, Any]) -> None:
    source = register.get("source")
    if not isinstance(source, dict):
        raise ValidationError("rules register source must be an object")

    for key in ("revision", "revision_date", "sha256"):
        if source.get(key) != manifest.get(key):
            raise ValidationError(f"source mismatch for {key}")

    checksum = manifest.get("sha256")
    if not isinstance(checksum, str) or not re.fullmatch(r"[0-9a-f]{64}", checksum):
        raise ValidationError("source manifest SHA-256 must be 64 lowercase hex characters")

    if manifest.get("redistribution") != "unconfirmed":
        raise ValidationError(
            "redistribution policy changed; perform a reviewed manifest update before publishing sources"
        )


def validate_register(register: dict[str, Any]) -> tuple[int, int]:
    if register.get("schema_version") != 1:
        raise ValidationError("unsupported rules-register schema_version")

    outcomes = register.get("review_outcomes")
    if not isinstance(outcomes, list) or set(outcomes) != EXPECTED_OUTCOMES:
        raise ValidationError("review_outcomes must contain exactly the four approved outcomes")

    verification_states = register.get("verification_states")
    if not isinstance(verification_states, list) or set(verification_states) != VALID_VERIFICATION:
        raise ValidationError("verification_states do not match the approved set")

    clarifications = register.get("clarifications")
    if not isinstance(clarifications, list):
        raise ValidationError("clarifications must be a list")

    clarification_ids: set[str] = set()
    clarification_status: dict[str, str] = {}
    for entry in clarifications:
        if not isinstance(entry, dict):
            raise ValidationError("each clarification must be an object")
        require_nonempty_string(entry, "id", "clarification")
        cid = entry["id"]
        if cid in clarification_ids:
            raise ValidationError(f"duplicate clarification id: {cid}")
        clarification_ids.add(cid)
        if entry.get("priority") not in {"P0", "P1", "P2"}:
            raise ValidationError(f"{cid}: invalid priority")
        if entry.get("status") not in {"OPEN", "CLOSED"}:
            raise ValidationError(f"{cid}: invalid status")
        clarification_status[cid] = entry["status"]

    missing_p0 = MANDATORY_OPEN_CLARIFICATIONS - clarification_ids
    if missing_p0:
        raise ValidationError("missing mandatory clarifications: " + ", ".join(sorted(missing_p0)))
    incorrectly_closed = {
        cid
        for cid in MANDATORY_OPEN_CLARIFICATIONS
        if clarification_status.get(cid) != "OPEN"
    }
    if incorrectly_closed:
        raise ValidationError(
            "P0 clarifications cannot close without a reviewed source update: "
            + ", ".join(sorted(incorrectly_closed))
        )

    rules = register.get("rules")
    if not isinstance(rules, list) or not rules:
        raise ValidationError("rules must be a nonempty list")

    rule_ids: set[str] = set()
    for rule in rules:
        if not isinstance(rule, dict):
            raise ValidationError("each rule must be an object")
        require_nonempty_string(rule, "id", "rule")
        rid = rule["id"]
        if rid in rule_ids:
            raise ValidationError(f"duplicate rule id: {rid}")
        rule_ids.add(rid)
        require_nonempty_string(rule, "category", rid)
        require_nonempty_string(rule, "statement", rid)
        require_nonempty_string_list(rule, "applies_to", rid)
        require_nonempty_string_list(rule, "evidence", rid)
        if rule.get("severity") not in VALID_SEVERITY:
            raise ValidationError(f"{rid}: invalid severity")
        if rule.get("verification") not in VALID_VERIFICATION:
            raise ValidationError(f"{rid}: invalid verification state")
        refs = rule.get("clarifications", [])
        if not isinstance(refs, list) or any(ref not in clarification_ids for ref in refs):
            raise ValidationError(f"{rid}: unknown clarification reference")

    missing_rules = MANDATORY_RULE_IDS - rule_ids
    if missing_rules:
        raise ValidationError("missing mandatory rule entries: " + ", ".join(sorted(missing_rules)))

    return len(rules), len(clarifications)


def validate_repository(repo_root: Path) -> tuple[int, int]:
    repo_root = repo_root.resolve()
    validate_required_files(repo_root)
    manifest = load_json(repo_root / "docs/compliance/source_manifest.json")
    register = load_json(repo_root / "docs/compliance/rules_register.yaml")
    validate_source(manifest, register)
    counts = validate_register(register)
    validate_skill(repo_root / ".agents/skills/laksa-rules-guardian/SKILL.md")
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()

    try:
        rules_count, clarifications_count = validate_repository(args.repo_root)
    except (ValidationError, OSError) as exc:
        print(f"Rules Guardian validation FAILED: {exc}", file=sys.stderr)
        return 1

    print(
        "Rules Guardian validation PASSED: "
        f"{rules_count} rule groups, {clarifications_count} clarifications"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
