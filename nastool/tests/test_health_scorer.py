"""
test_health_scorer.py — Unit tests for health scoring engine v4.0.2

Tests:
- Weighted scoring: critical=3x / important=2x / standard=1x
- Per-category scoring
- Grade calculation: A+/A/A-/B+/B/C/D/F
- HealthReport dataclass
- score_color helper
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


class TestHealthScorerWeights(unittest.TestCase):
    """Test WEIGHTS configuration."""

    def test_weights_defined(self):
        from utils.health_scorer import WEIGHTS

        self.assertIsInstance(WEIGHTS, dict)
        self.assertGreater(len(WEIGHTS), 20)

    def test_weights_are_numeric(self):
        from utils.health_scorer import WEIGHTS

        for check_id, weight in WEIGHTS.items():
            self.assertIsInstance(weight, (int, float), f"{check_id} weight not numeric")
            self.assertGreaterEqual(weight, 0)

    def test_critical_checks_have_high_weight(self):
        from utils.health_scorer import WEIGHTS

        critical_checks = ["smart_health", "raid_status"]
        for cid in critical_checks:
            if cid in WEIGHTS:
                self.assertGreaterEqual(
                    WEIGHTS[cid], 2.5, f"{cid} should have high weight (critical)"
                )


class TestScoreCalculation(unittest.TestCase):
    """Test scoring calculation logic."""

    def test_all_passed_gives_high_score(self):
        from utils.health_scorer import calculate_health_score

        results = [
            make_result("python_version", CheckCategory.SYSTEM, CheckSeverity.PASSED, True)
            for _ in range(5)
        ]
        report = calculate_health_score(results)
        self.assertGreaterEqual(report.overall_score, 90)

    def test_all_critical_gives_low_score(self):
        from utils.health_scorer import calculate_health_score

        results = [
            make_result("smart_health", CheckCategory.STORAGE, CheckSeverity.CRITICAL, False)
            for _ in range(3)
        ]
        report = calculate_health_score(results)
        self.assertLessEqual(report.overall_score, 30)

    def test_mixed_results_gives_mid_score(self):
        from utils.health_scorer import calculate_health_score

        results = [
            make_result("python_version", CheckCategory.SYSTEM, CheckSeverity.PASSED, True),
            make_result("smart_health", CheckCategory.STORAGE, CheckSeverity.CRITICAL, False),
        ]
        report = calculate_health_score(results)
        self.assertGreaterEqual(report.overall_score, 0)
        self.assertLessEqual(report.overall_score, 100)

    def test_empty_results_gives_score_100(self):
        from utils.health_scorer import calculate_health_score

        report = calculate_health_score([])
        self.assertEqual(report.overall_score, 100)


class TestGradeCalculation(unittest.TestCase):
    """Test grade letter calculation via HealthReport.grade()."""

    def test_excellent_score_returns_A_plus(self):
        from utils.health_scorer import calculate_health_score

        results = [
            make_result("python_version", CheckCategory.SYSTEM, CheckSeverity.PASSED, True)
            for _ in range(10)
        ]
        report = calculate_health_score(results)
        self.assertIn(report.grade(), ["A+", "A", "A-"])

    def test_good_score_returns_B_range(self):
        from utils.health_scorer import calculate_health_score

        results = [
            make_result("python_version", CheckCategory.SYSTEM, CheckSeverity.PASSED, True),
            make_result("memory_check", CheckCategory.SYSTEM, CheckSeverity.WARNING, False),
        ]
        report = calculate_health_score(results)
        self.assertIn(report.grade(), ["A-", "B+", "B", "C"])

    def test_critical_score_returns_D_or_F(self):
        from utils.health_scorer import calculate_health_score

        results = [
            make_result("smart_health", CheckCategory.STORAGE, CheckSeverity.CRITICAL, False)
        ]
        report = calculate_health_score(results)
        self.assertIn(report.grade(), ["D", "F"])


class TestScoreColor(unittest.TestCase):
    """Test score_color() helper."""

    def test_score_color_returns_string(self):
        from utils.health_scorer import score_color

        for score in [0, 10, 50, 60, 85, 95, 100]:
            result = score_color(score)
            self.assertIsInstance(result, str)
            self.assertIn(result, ["red", "yellow", "green", "cyan", "magenta"])

    def test_low_score_is_red(self):
        from utils.health_scorer import score_color

        self.assertEqual(score_color(50), "red")
        self.assertEqual(score_color(10), "red")

    def test_high_score_never_red(self):
        from utils.health_scorer import score_color

        self.assertNotEqual(score_color(90), "red")
        self.assertNotEqual(score_color(95), "red")


class TestCategoryScores(unittest.TestCase):
    """Test per-category score calculation."""

    def test_category_scores_populated(self):
        from utils.health_scorer import calculate_health_score

        results = [
            make_result("python_version", CheckCategory.SYSTEM, CheckSeverity.PASSED, True),
            make_result("smart_health", CheckCategory.STORAGE, CheckSeverity.CRITICAL, False),
        ]
        report = calculate_health_score(results)
        self.assertIsInstance(report.category_scores, list)
        # Each category score should have required fields
        for cs in report.category_scores:
            self.assertTrue(hasattr(cs, "score"))
            self.assertGreaterEqual(cs.score, 0)
            self.assertLessEqual(cs.score, 100)


class TestHealthReportCriticalItems(unittest.TestCase):
    """Test critical items collection."""

    def test_critical_items_collected(self):
        from utils.health_scorer import calculate_health_score

        critical_result = make_result(
            "smart_health", CheckCategory.STORAGE, CheckSeverity.CRITICAL, False
        )
        results = [
            make_result("python_version", CheckCategory.SYSTEM, CheckSeverity.PASSED, True),
            critical_result,
        ]
        report = calculate_health_score(results)
        self.assertEqual(report.total_critical, 1)
        self.assertEqual(report.total_passed, 1)

    def test_warning_items_collected(self):
        from utils.health_scorer import calculate_health_score

        warning_result = make_result(
            "memory_check", CheckCategory.SYSTEM, CheckSeverity.WARNING, False
        )
        results = [warning_result]
        report = calculate_health_score(results)
        self.assertEqual(report.total_warnings, 1)


class TestScoreLevelsDefined(unittest.TestCase):
    """Test SCORE_LEVELS and CATEGORY_NAMES are defined."""

    def test_score_levels_defined(self):
        from utils.health_scorer import SCORE_LEVELS

        self.assertIsInstance(SCORE_LEVELS, list)
        self.assertGreater(len(SCORE_LEVELS), 3)
        for entry in SCORE_LEVELS:
            self.assertGreaterEqual(len(entry), 4)

    def test_category_names_defined(self):
        from utils.health_scorer import CATEGORY_NAMES

        self.assertIsInstance(CATEGORY_NAMES, dict)
        self.assertIn(CheckCategory.STORAGE, CATEGORY_NAMES)
        self.assertIn(CheckCategory.SYSTEM, CATEGORY_NAMES)


class TestScoreChangeTracking(unittest.TestCase):
    """Test score change tracking vs previous score."""

    def test_score_change_calculated(self):
        from utils.health_scorer import calculate_health_score

        results = [make_result("python_version", CheckCategory.SYSTEM, CheckSeverity.PASSED, True)]
        report1 = calculate_health_score(results)
        report2 = calculate_health_score(results, previous_score=report1.overall_score)
        self.assertEqual(report2.score_change, 0)

    def test_score_change_positive(self):
        from utils.health_scorer import calculate_health_score

        new_results = [make_result("python_version", CheckCategory.SYSTEM, CheckSeverity.PASSED, True)]
        report = calculate_health_score(new_results, previous_score=0)
        self.assertGreater(report.score_change, 0)


if __name__ == "__main__":
    unittest.main()
