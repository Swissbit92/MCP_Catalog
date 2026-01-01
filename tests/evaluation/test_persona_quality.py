"""Integration tests for persona quality using RAGAS.

These tests evaluate the actual quality of persona responses using RAGAS metrics.
They are designed to be run in CI/CD to detect regression in persona quality.

Usage:
    # Run all personas
    pytest tests/evaluation/test_persona_quality.py -v

    # Run specific persona
    pytest tests/evaluation/test_persona_quality.py --persona=eeva -v

    # Set custom threshold
    pytest tests/evaluation/test_persona_quality.py --threshold=0.85 -v

    # Skip slow tests
    pytest tests/evaluation/test_persona_quality.py --skip-slow -v
"""

import pytest
import json
from pathlib import Path
from src.coordinator.evaluation import PersonaRagasEvaluator, GoldenExamplesManager
from src.coordinator.evaluation.metrics import check_regression


# Baseline metrics file (to be created after first successful run)
BASELINE_FILE = Path("tests/evaluation/baseline_metrics.json")


def load_baseline_metrics():
    """Load baseline metrics from file if it exists."""
    if BASELINE_FILE.exists():
        with open(BASELINE_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_baseline_metrics(baselines):
    """Save baseline metrics to file."""
    BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(BASELINE_FILE, 'w') as f:
        json.dump(baselines, f, indent=2)


class TestPersonaQuality:
    """Integration tests for persona quality evaluation."""

    @pytest.fixture
    def personas_to_test(self, request):
        """Get list of personas to test based on CLI args."""
        persona_arg = request.config.getoption("--persona")
        if persona_arg:
            return [persona_arg]

        # Default: test all personas
        manager = GoldenExamplesManager()
        available = manager.list_available_datasets()

        if not available:
            pytest.skip("No golden Q&A datasets found")

        return available

    @pytest.fixture
    def quality_threshold(self, request):
        """Get quality threshold from CLI args."""
        return request.config.getoption("--threshold")

    @pytest.mark.slow
    def test_persona_baseline_quality(self, personas_to_test, quality_threshold, request):
        """Test that personas meet minimum quality thresholds.

        This test runs RAGAS evaluation in placeholder mode (using ground_truth
        as both answer and context) to verify the golden Q&A datasets are
        well-formed and produce reasonable scores.
        """
        if request.config.getoption("--skip-slow"):
            pytest.skip("Skipping slow integration test")

        results = {}

        for persona_key in personas_to_test:
            print(f"\n[*] Evaluating {persona_key}...")

            try:
                # Initialize evaluator
                evaluator = PersonaRagasEvaluator(persona_key)

                # Run evaluation (placeholder mode)
                result = evaluator.evaluate_persona()

                # Store results
                results[persona_key] = {
                    "faithfulness": result.faithfulness,
                    "answer_relevancy": result.answer_relevancy,
                    "context_precision": result.context_precision,
                    "context_recall": result.context_recall,
                    "f1_score": result.f1_score,
                    "questions_evaluated": result.questions_evaluated
                }

                print(f"    Faithfulness:      {result.faithfulness:.3f}")
                print(f"    Answer Relevancy:  {result.answer_relevancy:.3f}")
                print(f"    Context Precision: {result.context_precision:.3f}")
                print(f"    Context Recall:    {result.context_recall:.3f}")
                print(f"    F1 Score:          {result.f1_score:.3f}")

                # Check against threshold
                assert result.f1_score >= quality_threshold, (
                    f"{persona_key} F1 score ({result.f1_score:.3f}) below threshold ({quality_threshold})"
                )

                # In placeholder mode, we expect high scores
                assert result.faithfulness >= 0.7, (
                    f"{persona_key} faithfulness ({result.faithfulness:.3f}) unexpectedly low"
                )
                assert result.answer_relevancy >= 0.7, (
                    f"{persona_key} answer relevancy ({result.answer_relevancy:.3f}) unexpectedly low"
                )

            except FileNotFoundError:
                pytest.skip(f"Golden Q&A for {persona_key} not found")

        # Save results as new baseline if this is first run
        if results and not BASELINE_FILE.exists():
            print(f"\n[*] Saving baseline metrics to {BASELINE_FILE}")
            save_baseline_metrics(results)

    @pytest.mark.slow
    def test_persona_regression_detection(self, personas_to_test, request):
        """Test for quality regression compared to baseline.

        This test compares current evaluation results against saved baseline
        metrics and fails if quality drops significantly (>5% for warnings,
        >10% for hard failures).
        """
        if request.config.getoption("--skip-slow"):
            pytest.skip("Skipping slow integration test")

        baselines = load_baseline_metrics()

        if not baselines:
            pytest.skip("No baseline metrics found. Run test_persona_baseline_quality first.")

        for persona_key in personas_to_test:
            if persona_key not in baselines:
                print(f"\n[SKIP] No baseline for {persona_key}, skipping regression test")
                continue

            print(f"\n[*] Checking regression for {persona_key}...")

            try:
                # Run current evaluation
                evaluator = PersonaRagasEvaluator(persona_key)
                result = evaluator.evaluate_persona()

                current_metrics = {
                    "faithfulness": result.faithfulness,
                    "answer_relevancy": result.answer_relevancy,
                    "context_precision": result.context_precision,
                    "context_recall": result.context_recall,
                    "f1_score": result.f1_score
                }

                baseline_metrics = baselines[persona_key]

                # Check for regression
                regression_results = check_regression(current_metrics, baseline_metrics)

                # Print results
                for metric, status in regression_results.items():
                    current = current_metrics[metric]
                    baseline = baseline_metrics[metric]
                    change_pct = ((current - baseline) / baseline * 100) if baseline > 0 else 0

                    status_emoji = {
                        "pass": "[OK]",
                        "warning": "[WARN]",
                        "fail": "[FAIL]"
                    }[status]

                    print(f"    {metric:20s} {status_emoji} {current:.3f} vs {baseline:.3f} ({change_pct:+.1f}%)")

                # Fail if any metric has hard failure
                failed_metrics = [m for m, s in regression_results.items() if s == "fail"]
                if failed_metrics:
                    pytest.fail(
                        f"{persona_key} has regressed metrics: {', '.join(failed_metrics)}"
                    )

                # Warn if any metric has warning (but don't fail)
                warning_metrics = [m for m, s in regression_results.items() if s == "warning"]
                if warning_metrics:
                    print(f"    [WARN] Some metrics show minor regression: {', '.join(warning_metrics)}")

            except FileNotFoundError:
                pytest.skip(f"Golden Q&A for {persona_key} not found")


class TestGoldenQAQuality:
    """Tests for golden Q&A dataset quality."""

    def test_all_personas_have_minimum_questions(self):
        """Test that all personas have at least 10 questions."""
        manager = GoldenExamplesManager()
        available = manager.list_available_datasets()

        if not available:
            pytest.skip("No golden Q&A datasets found")

        for persona_key in available:
            dataset = manager.load_dataset(persona_key)
            assert dataset.num_questions >= 10, (
                f"{persona_key} has only {dataset.num_questions} questions (minimum: 10)"
            )

    def test_all_personas_have_difficulty_distribution(self):
        """Test that all personas have proper difficulty distribution."""
        manager = GoldenExamplesManager()
        available = manager.list_available_datasets()

        if not available:
            pytest.skip("No golden Q&A datasets found")

        for persona_key in available:
            dataset = manager.load_dataset(persona_key)
            validation = manager.validate_dataset(dataset)

            # Check difficulty distribution
            easy = validation["difficulty_distribution"].get("easy", 0)
            medium = validation["difficulty_distribution"].get("medium", 0)
            hard = validation["difficulty_distribution"].get("hard", 0)

            assert easy >= 3, f"{persona_key} has only {easy} easy questions (minimum: 3)"
            assert medium >= 3, f"{persona_key} has only {medium} medium questions (minimum: 3)"
            assert hard >= 3, f"{persona_key} has only {hard} hard questions (minimum: 3)"

    def test_all_personas_have_category_diversity(self):
        """Test that all personas have multiple categories."""
        manager = GoldenExamplesManager()
        available = manager.list_available_datasets()

        if not available:
            pytest.skip("No golden Q&A datasets found")

        for persona_key in available:
            dataset = manager.load_dataset(persona_key)
            validation = manager.validate_dataset(dataset)

            num_categories = len(validation["category_distribution"])
            assert num_categories >= 2, (
                f"{persona_key} has only {num_categories} category (minimum: 2)"
            )

    def test_all_personas_have_substantial_ground_truths(self):
        """Test that ground truth answers are substantial."""
        manager = GoldenExamplesManager()
        available = manager.list_available_datasets()

        if not available:
            pytest.skip("No golden Q&A datasets found")

        for persona_key in available:
            dataset = manager.load_dataset(persona_key)
            validation = manager.validate_dataset(dataset)

            avg_length = validation["avg_ground_truth_length"]
            assert avg_length >= 50, (
                f"{persona_key} ground truths are too short (avg: {avg_length} chars, minimum: 50)"
            )


class TestEvaluationConsistency:
    """Tests for evaluation consistency and reproducibility."""

    @pytest.mark.slow
    def test_evaluation_reproducibility(self, request):
        """Test that evaluation produces consistent results across runs."""
        if request.config.getoption("--skip-slow"):
            pytest.skip("Skipping slow integration test")

        persona_key = "eeva"  # Use eeva as test case

        try:
            evaluator = PersonaRagasEvaluator(persona_key)

            # Run evaluation twice
            result1 = evaluator.evaluate_persona()
            result2 = evaluator.evaluate_persona()

            # Results should be identical (placeholder mode is deterministic)
            assert result1.faithfulness == result2.faithfulness
            assert result1.answer_relevancy == result2.answer_relevancy
            assert result1.context_precision == result2.context_precision
            assert result1.context_recall == result2.context_recall
            assert result1.f1_score == result2.f1_score

        except FileNotFoundError:
            pytest.skip(f"Golden Q&A for {persona_key} not found")


class TestCLIOptions:
    """Tests for CLI option handling."""

    def test_persona_filter(self, request):
        """Test --persona CLI option."""
        persona_arg = request.config.getoption("--persona")

        if persona_arg:
            # Verify the specified persona exists
            manager = GoldenExamplesManager()
            available = manager.list_available_datasets()

            if persona_arg not in available:
                pytest.skip(f"Persona '{persona_arg}' not found")

            print(f"Testing persona: {persona_arg}")

    def test_threshold_option(self, request):
        """Test --threshold CLI option."""
        threshold = request.config.getoption("--threshold")

        assert 0.0 <= threshold <= 1.0, "Threshold should be between 0 and 1"
        print(f"Using quality threshold: {threshold}")
