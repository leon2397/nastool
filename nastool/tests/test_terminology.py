"""
test_terminology.py — Unit tests for terminology translation layer v4.0.2

Tests the "common person" terminology translation:
- TERMINOLOGY dict (33 check terms → human-readable)
- translate_result() → friendly_title/friendly_short/friendly_message/...
- translate_category(), translate_risk()
- generate_suggestions()
- CATEGORY_NAMES, SEVERITY_LABELS, RISK_LABELS
"""

import unittest
from checks.base import CheckResult, CheckSeverity, CheckCategory


def make_result(check_id, category, severity, passed):
    return CheckResult(
        check_id=check_id,
        category=category,
        severity=severity,
        passed=passed,
        title="Test",
        current="current",
        expected="expected",
        message="test message",
    )


class TestTERMINOLOGYDict(unittest.TestCase):
    """Test TERMINOLOGY dict covers key checks."""

    def test_terminology_defined(self):
        from utils.terminology import TERMINOLOGY

        self.assertIsInstance(TERMINOLOGY, dict)
        self.assertGreater(len(TERMINOLOGY), 20)

    def test_critical_check_ids_have_translations(self):
        from utils.terminology import TERMINOLOGY

        critical_ids = ["smart_health", "raid_status", "cpu_temperature", "storage_disk"]
        for cid in critical_ids:
            self.assertIn(cid, TERMINOLOGY, f"Critical check {cid} missing from TERMINOLOGY")

    def test_all_terminology_entries_have_required_fields(self):
        from utils.terminology import TERMINOLOGY

        required_fields = {"title", "short", "why", "risk_low", "risk_high"}
        for check_id, trans in TERMINOLOGY.items():
            for field in required_fields:
                self.assertIn(
                    field, trans,
                    f"Check {check_id} missing '{field}'. Keys: {list(trans.keys())}"
                )

    def test_translation_titles_are_non_empty_strings(self):
        from utils.terminology import TERMINOLOGY

        for check_id, trans in TERMINOLOGY.items():
            self.assertIsInstance(trans["title"], str)
            self.assertGreater(len(trans["title"]), 0)
            self.assertIsInstance(trans["short"], str)
            self.assertIsInstance(trans["why"], str)

    def test_translation_risk_fields_are_non_empty(self):
        from utils.terminology import TERMINOLOGY

        for check_id, trans in TERMINOLOGY.items():
            self.assertIsInstance(trans["risk_low"], str)
            self.assertIsInstance(trans["risk_high"], str)
            self.assertGreater(len(trans["risk_low"]), 0)
            self.assertGreater(len(trans["risk_high"]), 0)


class TestTranslateFunctions(unittest.TestCase):
    """Test translate_result(), translate_category(), translate_risk()."""

    def test_translate_category_all_categories(self):
        from utils.terminology import translate_category

        cats = list(CheckCategory)
        for cat in cats:
            result = translate_category(cat)
            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)

    def test_translate_result_returns_translation(self):
        from utils.terminology import translate_result

        result = make_result("smart_health", CheckCategory.STORAGE, CheckSeverity.CRITICAL, False)
        trans = translate_result(result)
        self.assertIsInstance(trans, dict)
        self.assertIn("friendly_title", trans)
        self.assertIn("friendly_short", trans)
        self.assertIn("friendly_message", trans)
        self.assertIn("current", trans)
        self.assertIn("expected", trans)

    def test_translate_result_unknown_check_id(self):
        from utils.terminology import translate_result

        result = make_result("unknown_check_xyz", CheckCategory.SYSTEM, CheckSeverity.INFO, True)
        trans = translate_result(result)
        self.assertIsInstance(trans, dict)

    def test_translate_risk_all_levels(self):
        from utils.terminology import translate_risk

        for risk in ["low", "medium", "high"]:
            result = translate_risk(risk)
            # RISK_LABELS values are (emoji_label, description) tuples
            self.assertIsInstance(result, (str, tuple))
            if isinstance(result, tuple):
                self.assertGreaterEqual(len(result), 2)


class TestSeverityLabels(unittest.TestCase):
    """Test SEVERITY_LABELS dictionary."""

    def test_severity_labels_defined(self):
        from utils.terminology import SEVERITY_LABELS

        self.assertIsInstance(SEVERITY_LABELS, dict)
        self.assertIn(CheckSeverity.CRITICAL, SEVERITY_LABELS)
        self.assertIn(CheckSeverity.WARNING, SEVERITY_LABELS)
        self.assertIn(CheckSeverity.INFO, SEVERITY_LABELS)
        self.assertIn(CheckSeverity.PASSED, SEVERITY_LABELS)

    def test_severity_labels_are_non_empty(self):
        from utils.terminology import SEVERITY_LABELS

        for sev, label in SEVERITY_LABELS.items():
            self.assertIsInstance(label, (str, tuple))


class TestGenerateSuggestions(unittest.TestCase):
    """Test suggestion generation from results."""

    def test_generate_suggestions_returns_list(self):
        from utils.terminology import generate_suggestions

        results = [
            make_result("smart_health", CheckCategory.STORAGE, CheckSeverity.CRITICAL, False),
        ]
        suggestions = generate_suggestions(results)
        self.assertIsInstance(suggestions, list)

    def test_generate_suggestions_empty_input(self):
        from utils.terminology import generate_suggestions

        suggestions = generate_suggestions([])
        self.assertIsInstance(suggestions, list)


class TestScoreUrgency(unittest.TestCase):
    """Test score_urgency() helper."""

    def test_score_urgency_returns_value(self):
        from utils.terminology import score_urgency

        result = make_result("smart_health", CheckCategory.STORAGE, CheckSeverity.CRITICAL, False)
        urgency = score_urgency(result)
        # Returns 'now' (str) for critical, 'soon' for warning, etc.
        self.assertIsInstance(urgency, str)


class TestCategoryShortNames(unittest.TestCase):
    """Test CATEGORY_SHORT names."""

    def test_category_short_defined(self):
        from utils.terminology import CATEGORY_SHORT

        self.assertIsInstance(CATEGORY_SHORT, dict)
        self.assertIn(CheckCategory.STORAGE, CATEGORY_SHORT)
        self.assertIn(CheckCategory.SYSTEM, CATEGORY_SHORT)


class TestTerminologyExports(unittest.TestCase):
    """Test module-level exports are all available."""

    def test_all_public_exports_available(self):
        from utils.terminology import (
            translate_result,
            translate_category,
            translate_risk,
            generate_suggestions,
            score_urgency,
            CATEGORY_NAMES,
            CATEGORY_SHORT,
            TERMINOLOGY,
            SEVERITY_LABELS,
            RISK_LABELS,
        )

        self.assertTrue(callable(translate_result))
        self.assertTrue(callable(translate_category))
        self.assertTrue(callable(translate_risk))
        self.assertTrue(callable(generate_suggestions))
        self.assertTrue(callable(score_urgency))
        self.assertIsInstance(TERMINOLOGY, dict)
        self.assertIsInstance(CATEGORY_NAMES, dict)


if __name__ == "__main__":
    unittest.main()
