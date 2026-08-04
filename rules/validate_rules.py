#!/usr/bin/env python3
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE_FILES = [
    ROOT / "source/base.json",
    ROOT / "source/deception_rules.json",
    ROOT / "source/degree_signatures.json",
    ROOT / "source/directional_context_rules.json",
    ROOT / "source/house_rules.json",
]
ALLOWED_CATEGORIES = {
    "Abduction", "Associates", "Children", "Context", "Deception",
    "Degree Signatures", "Disaster", "Domestic", "Family", "Headwinds",
    "Houses", "Public", "Stressors", "Truth", "Violence", "Water",
}
ALLOWED_ROOTS = {
    "case_context", "sect", "planets", "degree_signatures", "moon",
    "aspects", "lots", "fixed_stars", "fixed_stars_list", "house_cusps",
    "house_rulers", "houses", "solar", "solar_phase",
}
OPERATOR_SUFFIX = re.compile(r"(<=|>=|<|>)$")


def fail(message: str) -> None:
    raise ValueError(message)


def validate_path(path: object, rule_id: str) -> None:
    if not isinstance(path, str) or not path or path != path.strip() or len(path) > 240:
        fail(f"{rule_id}: invalid feature path {path!r}")
    parts = path.split(".")
    if any(not part for part in parts) or parts[0] not in ALLOWED_ROOTS:
        fail(f"{rule_id}: unsupported feature path {path!r}")


def validate_comparison(value: object, rule_id: str) -> None:
    if value is None or isinstance(value, dict):
        fail(f"{rule_id}: invalid comparison value")
    if isinstance(value, float) and not math.isfinite(value):
        fail(f"{rule_id}: non-finite comparison value")
    if isinstance(value, str) and not value.strip():
        fail(f"{rule_id}: blank comparison value")
    if isinstance(value, list):
        if not value:
            fail(f"{rule_id}: empty comparison array")
        for child in value:
            validate_comparison(child, rule_id)


def validate_condition(value: object, rule_id: str, depth: int = 0, counter: list[int] | None = None) -> None:
    if counter is None:
        counter = [0]
    counter[0] += 1
    if depth > 16 or counter[0] > 512:
        fail(f"{rule_id}: condition exceeds complexity limits")
    if isinstance(value, bool):
        return
    if isinstance(value, list):
        if not value:
            fail(f"{rule_id}: empty condition group")
        for child in value:
            validate_condition(child, rule_id, depth + 1, counter)
        return
    if not isinstance(value, dict) or not value:
        fail(f"{rule_id}: invalid condition node")

    controls = [key for key in ("all", "any", "not") if key in value]
    if len(controls) > 1 or (controls and len(value) != 1):
        fail(f"{rule_id}: ambiguous condition controls")
    if controls:
        control = controls[0]
        child = value[control]
        if control in ("all", "any") and (not isinstance(child, list) or not child):
            fail(f"{rule_id}: invalid {control} group")
        validate_condition(child, rule_id, depth + 1, counter)
        return

    for key, expected in value.items():
        if not isinstance(key, str):
            fail(f"{rule_id}: condition key is not a string")
        validate_path(OPERATOR_SUFFIX.sub("", key), rule_id)
        validate_comparison(expected, rule_id)


def validate_rule(rule: object) -> None:
    if not isinstance(rule, dict):
        fail("corpus contains a non-object rule")
    rule_id = rule.get("id")
    if not isinstance(rule_id, str) or not rule_id.strip() or len(rule_id) > 120:
        fail(f"invalid rule id {rule_id!r}")
    title = rule.get("title")
    rationale = rule.get("rationale")
    category = rule.get("category")
    weight = rule.get("weight")
    if not isinstance(title, str) or not title.strip() or len(title) > 240:
        fail(f"{rule_id}: invalid title")
    if not isinstance(rationale, str) or not rationale.strip() or len(rationale) > 2000:
        fail(f"{rule_id}: invalid rationale")
    if category not in ALLOWED_CATEGORIES:
        fail(f"{rule_id}: unsupported category {category!r}")
    if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not math.isfinite(weight) or not -100 <= weight <= 100:
        fail(f"{rule_id}: invalid weight")
    evidence = rule.get("evidence")
    if evidence is not None:
        if not isinstance(evidence, list) or not evidence or len(evidence) > 32:
            fail(f"{rule_id}: invalid evidence list")
        if len(evidence) != len(set(evidence)):
            fail(f"{rule_id}: duplicate evidence path")
        for path in evidence:
            validate_path(path, rule_id)
    if "condition" not in rule:
        fail(f"{rule_id}: missing condition")
    validate_condition(rule["condition"], rule_id)


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: validate_rules.py OUTPUT_PATH")
    rules: list[dict] = []
    for path in SOURCE_FILES:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, list) or not value:
            fail(f"{path}: expected a non-empty JSON array")
        rules.extend(value)

    for rule in rules:
        validate_rule(rule)
    ids = [rule["id"] for rule in rules]
    if len(ids) != len(set(ids)):
        fail("duplicate rule IDs")
    expected_ids = set(json.loads((ROOT / "shipped_rule_ids.json").read_text(encoding="utf-8")))
    actual_ids = set(ids)
    if actual_ids != expected_ids or len(ids) != len(expected_ids):
        fail(
            f"corpus must retain shipped IDs; "
            f"missing={sorted(expected_ids - actual_ids)}, unexpected={sorted(actual_ids - expected_ids)}"
        )

    output = Path(sys.argv[1])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(rules, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"validated {len(rules)} rules")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"rule validation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
