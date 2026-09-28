from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPO_ROOT / "scripts/validate_rules_guardian.py"
SPEC = importlib.util.spec_from_file_location("validate_rules_guardian", VALIDATOR_PATH)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class RulesGuardianTests(unittest.TestCase):
    def test_repository_foundation_is_valid(self) -> None:
        rule_count, clarification_count = VALIDATOR.validate_repository(REPO_ROOT)
        self.assertGreaterEqual(rule_count, 35)
        self.assertEqual(clarification_count, 12)

    def test_register_is_json_compatible_yaml(self) -> None:
        register_path = REPO_ROOT / "docs/compliance/rules_register.yaml"
        register = json.loads(register_path.read_text(encoding="utf-8"))
        self.assertEqual(register["source"]["revision"], "4.2")
        self.assertEqual(set(register["review_outcomes"]), VALIDATOR.EXPECTED_OUTCOMES)

    def test_duplicate_rule_id_is_rejected(self) -> None:
        register_path = REPO_ROOT / "docs/compliance/rules_register.yaml"
        register = json.loads(register_path.read_text(encoding="utf-8"))
        register["rules"].append(dict(register["rules"][0]))
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "duplicate rule id"):
            VALIDATOR.validate_register(register)

    def test_unknown_clarification_is_rejected(self) -> None:
        register_path = REPO_ROOT / "docs/compliance/rules_register.yaml"
        register = json.loads(register_path.read_text(encoding="utf-8"))
        register["rules"][0]["clarifications"] = ["CLAR-999"]
        with self.assertRaisesRegex(VALIDATOR.ValidationError, "unknown clarification"):
            VALIDATOR.validate_register(register)

    def test_missing_required_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(VALIDATOR.ValidationError, "missing required files"):
                VALIDATOR.validate_required_files(Path(tmp))


if __name__ == "__main__":
    unittest.main()
