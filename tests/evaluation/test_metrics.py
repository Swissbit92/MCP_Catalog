"""Tests for RAGAS metrics calculations."""

import pytest
from src.coordinator.evaluation.metrics import (
    calculate_f1_score,
    calculate_weighted_score,
    check_regression
)


class TestCalculateF1Score:
    """Tests for F1 score calculation."""

    def test_perfect_scores(self):
        """Test F1 score with perfect metrics."""
        metrics = {
            "answer_relevancy": 1.0,
            "faithfulness": 1.0,
            "context_precision": 1.0,
            "context_recall": 1.0
        }

        f1 = calculate_f1_score(metrics)

        assert f1 == 1.0

    def test_zero_scores(self):
        """Test F1 score with zero metrics."""
        metrics = {
            "answer_relevancy": 0.0,
            "faithfulness": 0.0,
            "context_precision": 0.0,
            "context_recall": 0.0
        }

        f1 = calculate_f1_score(metrics)

        assert f1 == 0.0

    def test_sample_scores(self, sample_ragas_metrics):
        """Test F1 score with realistic metrics."""
        # answer_relevancy=0.90, faithfulness=0.85, precision=0.80, recall=0.75
        # F1 = (0.90 * 0.4) + (0.85 * 0.3) + (0.80 * 0.15) + (0.75 * 0.15)
        # F1 = 0.36 + 0.255 + 0.12 + 0.1125 = 0.8475

        f1 = calculate_f1_score(sample_ragas_metrics)

        assert f1 == 0.8475

    def test_weighted_formula(self):
        """Test that F1 formula uses correct weights."""
        metrics = {
            "answer_relevancy": 1.0,  # 40% weight
            "faithfulness": 0.0,
            "context_precision": 0.0,
            "context_recall": 0.0
        }

        f1 = calculate_f1_score(metrics)

        assert f1 == 0.4  # Only relevancy contributes

    def test_missing_metrics(self):
        """Test F1 score with missing metrics (defaults to 0)."""
        metrics = {
            "answer_relevancy": 0.9
            # Missing other metrics
        }

        f1 = calculate_f1_score(metrics)

        # Only relevancy contributes: 0.9 * 0.4 = 0.36
        assert f1 == 0.36

    def test_rounding(self):
        """Test that F1 score is rounded to 4 decimal places."""
        metrics = {
            "answer_relevancy": 0.12345,
            "faithfulness": 0.67890,
            "context_precision": 0.11111,
            "context_recall": 0.22222
        }

        f1 = calculate_f1_score(metrics)

        # Check it's rounded to 4 decimals
        assert len(str(f1).split('.')[-1]) <= 4


class TestCalculateWeightedScore:
    """Tests for alternative weighted score API."""

    def test_equivalent_to_f1_score(self, sample_ragas_metrics):
        """Test that weighted_score matches calculate_f1_score."""
        f1_result = calculate_f1_score(sample_ragas_metrics)

        weighted_result = calculate_weighted_score(
            answer_relevancy=sample_ragas_metrics["answer_relevancy"],
            faithfulness=sample_ragas_metrics["faithfulness"],
            context_precision=sample_ragas_metrics["context_precision"],
            context_recall=sample_ragas_metrics["context_recall"]
        )

        assert f1_result == weighted_result

    def test_direct_parameters(self):
        """Test weighted score with direct parameters."""
        score = calculate_weighted_score(
            answer_relevancy=0.9,
            faithfulness=0.8,
            context_precision=0.7,
            context_recall=0.6
        )

        # Manual calculation: (0.9*0.4) + (0.8*0.3) + (0.7*0.15) + (0.6*0.15)
        # = 0.36 + 0.24 + 0.105 + 0.09 = 0.795
        assert score == 0.795


class TestCheckRegression:
    """Tests for regression detection."""

    def test_no_regression(self, baseline_metrics):
        """Test when metrics are maintained (no regression)."""
        current_metrics = baseline_metrics.copy()

        results = check_regression(current_metrics, baseline_metrics)

        for metric, status in results.items():
            assert status == "pass", f"{metric} should pass"

    def test_hard_failure_regression(self, baseline_metrics, regressed_metrics):
        """Test detection of hard failure (>10% drop)."""
        results = check_regression(regressed_metrics, baseline_metrics)

        # Faithfulness dropped 11.8% (0.85 -> 0.75)
        assert results["faithfulness"] == "fail"

        # Context recall dropped 12.5% (0.80 -> 0.70)
        assert results["context_recall"] == "fail"

    def test_warning_regression(self, baseline_metrics, warning_metrics):
        """Test detection of warning level regression (5-10% drop)."""
        results = check_regression(warning_metrics, baseline_metrics)

        # Faithfulness dropped ~5.9% (0.85 -> 0.80)
        assert results["faithfulness"] == "warning"

        # Answer relevancy dropped 5.6% (0.90 -> 0.85)
        assert results["answer_relevancy"] == "warning"

    def test_improvement(self, baseline_metrics):
        """Test that improvements are detected as pass."""
        improved_metrics = {
            "faithfulness": 0.95,  # Improved from 0.85
            "answer_relevancy": 0.95,  # Improved from 0.90
            "context_precision": 0.90,  # Improved from 0.80
            "context_recall": 0.90,  # Improved from 0.80
            "f1_score": 0.930
        }

        results = check_regression(improved_metrics, baseline_metrics)

        for metric, status in results.items():
            assert status == "pass", f"{metric} should pass (improvement)"

    def test_custom_thresholds(self, baseline_metrics):
        """Test custom regression thresholds."""
        # 8% drop
        current_metrics = {
            "faithfulness": 0.78,  # 8.2% drop from 0.85
            "answer_relevancy": 0.85,
            "context_precision": 0.80,
            "context_recall": 0.80,
            "f1_score": 0.815
        }

        # With default thresholds (5%, 10%), this is a warning
        results_default = check_regression(current_metrics, baseline_metrics)
        assert results_default["faithfulness"] == "warning"

        # With custom thresholds (7%, 15%), this is a warning
        results_custom = check_regression(
            current_metrics,
            baseline_metrics,
            hard_threshold=0.15,
            warning_threshold=0.07
        )
        assert results_custom["faithfulness"] == "warning"

        # With stricter thresholds (6%, 8%), this is a fail
        results_strict = check_regression(
            current_metrics,
            baseline_metrics,
            hard_threshold=0.08,
            warning_threshold=0.06
        )
        assert results_strict["faithfulness"] == "fail"

    def test_no_baseline(self):
        """Test regression check when no baseline exists."""
        current_metrics = {
            "faithfulness": 0.85,
            "answer_relevancy": 0.90,
            "context_precision": 0.80,
            "context_recall": 0.75,
            "f1_score": 0.845
        }

        baseline_metrics = {
            "faithfulness": 0.0,  # No baseline
            "answer_relevancy": 0.0,
            "context_precision": 0.0,
            "context_recall": 0.0,
            "f1_score": 0.0
        }

        results = check_regression(current_metrics, baseline_metrics)

        # All should pass when baseline is 0
        for metric, status in results.items():
            assert status == "pass", f"{metric} should pass (no baseline)"

    def test_edge_case_exact_threshold(self, baseline_metrics):
        """Test exact threshold boundaries."""
        # Exactly 10% drop (hard threshold boundary)
        current_metrics = {
            "faithfulness": 0.765,  # Exactly 10% drop from 0.85
            "answer_relevancy": 0.81,   # Exactly 10% drop from 0.90
            "context_precision": 0.80,
            "context_recall": 0.80,
            "f1_score": 0.800
        }

        results = check_regression(current_metrics, baseline_metrics)

        # At exactly 10%, should be "fail" (>10% means strictly greater)
        # But at 10% exactly, it's not > 10%, so should be "warning"
        # Let's verify the logic
        drop_faithfulness = (0.85 - 0.765) / 0.85  # ≈ 0.1 (exactly 10%)
        assert abs(drop_faithfulness - 0.10) < 0.0001  # Floating point tolerance

        # Since 0.10 is not > 0.10, it should be warning (5% < drop <= 10%)
        assert results["faithfulness"] == "warning"


class TestMetricsIntegration:
    """Integration tests for metrics module."""

    def test_full_evaluation_workflow(self):
        """Test complete workflow: calculate F1 and check regression."""
        # Baseline evaluation
        baseline_metrics = {
            "answer_relevancy": 0.90,
            "faithfulness": 0.85,
            "context_precision": 0.80,
            "context_recall": 0.80
        }
        baseline_f1 = calculate_f1_score(baseline_metrics)
        baseline_metrics["f1_score"] = baseline_f1

        # Current evaluation (slightly worse)
        current_metrics = {
            "answer_relevancy": 0.88,  # 2.2% drop
            "faithfulness": 0.82,  # 3.5% drop
            "context_precision": 0.78,  # 2.5% drop
            "context_recall": 0.79  # 1.25% drop
        }
        current_f1 = calculate_f1_score(current_metrics)
        current_metrics["f1_score"] = current_f1

        # Check regression
        results = check_regression(current_metrics, baseline_metrics)

        # All metrics should pass (< 5% drop)
        assert all(status == "pass" for status in results.values())

        # F1 score should be lower but not significantly
        assert current_f1 < baseline_f1
        assert (baseline_f1 - current_f1) / baseline_f1 < 0.05  # Less than 5% drop
