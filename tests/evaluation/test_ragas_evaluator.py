"""Tests for RAGAS evaluator."""

import pytest

# RAGAS is an optional, evaluation-only dependency (heavy; not installed in the
# default macOS runtime). Its package init can raise ImportError from transitive
# deps (e.g. nltk), so guard with an explicit module-level skip rather than
# importorskip (which doesn't reliably catch deep init failures).
try:
    import ragas  # noqa: F401
except ImportError:
    pytest.skip("ragas/nltk not installed (evaluation-only dependency)", allow_module_level=True)

from datetime import datetime
from src.coordinator.evaluation.ragas_evaluator import (
    PersonaRagasEvaluator,
    RagasResult
)


class TestRagasResult:
    """Tests for RagasResult dataclass."""

    def test_ragas_result_creation(self):
        """Test creating a RagasResult."""
        result = RagasResult(
            persona_key="test",
            persona_display_name="Test Persona",
            faithfulness=0.85,
            answer_relevancy=0.90,
            context_precision=0.80,
            context_recall=0.75,
            f1_score=0.8475,
            questions_evaluated=10,
            timestamp="2026-01-01T00:00:00Z",
            model_name="llama3.1:8b",
            temperature=0.0
        )

        assert result.persona_key == "test"
        assert result.faithfulness == 0.85
        assert result.f1_score == 0.8475
        assert result.questions_evaluated == 10

    def test_ragas_result_to_dict(self):
        """Test converting RagasResult to dictionary."""
        result = RagasResult(
            persona_key="test",
            persona_display_name="Test",
            faithfulness=0.85,
            answer_relevancy=0.90,
            context_precision=0.80,
            context_recall=0.75,
            f1_score=0.8475,
            questions_evaluated=10,
            timestamp="2026-01-01T00:00:00Z"
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["persona_key"] == "test"
        assert result_dict["faithfulness"] == 0.85
        assert result_dict["f1_score"] == 0.8475

    def test_ragas_result_str(self):
        """Test string representation of RagasResult."""
        result = RagasResult(
            persona_key="test",
            persona_display_name="Test Persona",
            faithfulness=0.85,
            answer_relevancy=0.90,
            context_precision=0.80,
            context_recall=0.75,
            f1_score=0.8475,
            questions_evaluated=10,
            timestamp="2026-01-01T00:00:00Z"
        )

        result_str = str(result)

        assert "Test Persona" in result_str
        assert "0.850" in result_str  # Faithfulness formatted
        assert "0.900" in result_str  # Answer relevancy formatted
        assert "0.848" in result_str  # F1 score formatted
        assert "10" in result_str  # Questions evaluated


class TestPersonaRagasEvaluator:
    """Tests for PersonaRagasEvaluator."""

    def test_initialization_with_custom_path(self, temp_golden_qa_file):
        """Test initializing evaluator with custom golden Q&A path."""
        evaluator = PersonaRagasEvaluator(
            persona_key="test_persona",
            golden_qa_path=str(temp_golden_qa_file)
        )

        assert evaluator.persona_key == "test_persona"
        assert evaluator.dataset is not None
        assert evaluator.dataset.num_questions == 3

    def test_initialization_auto_detect(self, temp_golden_qa_dir):
        """Test initializing evaluator with auto-detected path."""
        # This will fail unless we mock or have actual files
        # For now, we'll test the error case
        with pytest.raises(FileNotFoundError):
            PersonaRagasEvaluator("nonexistent_persona")

    def test_initialization_with_model_params(self, temp_golden_qa_file):
        """Test initializing with model parameters."""
        evaluator = PersonaRagasEvaluator(
            persona_key="test",
            golden_qa_path=str(temp_golden_qa_file),
            model_name="llama3.1:8b",
            temperature=0.5
        )

        assert evaluator.model_name == "llama3.1:8b"
        assert evaluator.temperature == 0.5

    @pytest.mark.slow
    def test_evaluate_single_question(self, temp_golden_qa_file):
        """Test evaluating a single Q&A pair."""
        evaluator = PersonaRagasEvaluator(
            persona_key="test",
            golden_qa_path=str(temp_golden_qa_file)
        )

        # Test single question evaluation
        metrics = evaluator.evaluate_single_question(
            question="What is testing?",
            answer="Testing is the process of validating software behavior.",
            ground_truth="Testing is validating that software works correctly.",
            context=["Testing is validating that software works correctly."]
        )

        # Check that all metrics are present
        assert "faithfulness" in metrics
        assert "answer_relevancy" in metrics
        assert "context_precision" in metrics
        assert "context_recall" in metrics

        # Check that metrics are floats between 0 and 1
        for metric_name, value in metrics.items():
            assert isinstance(value, float)
            assert 0.0 <= value <= 1.0, f"{metric_name} should be between 0 and 1"

    @pytest.mark.slow
    def test_evaluate_persona_placeholder_mode(self, temp_golden_qa_file):
        """Test full persona evaluation in placeholder mode."""
        evaluator = PersonaRagasEvaluator(
            persona_key="test",
            golden_qa_path=str(temp_golden_qa_file)
        )

        # Run evaluation (uses ground_truth as placeholder)
        result = evaluator.evaluate_persona()

        # Check result structure
        assert isinstance(result, RagasResult)
        assert result.persona_key == "test"
        assert result.questions_evaluated == 3

        # Check metrics are in valid range
        assert 0.0 <= result.faithfulness <= 1.0
        assert 0.0 <= result.answer_relevancy <= 1.0
        assert 0.0 <= result.context_precision <= 1.0
        assert 0.0 <= result.context_recall <= 1.0
        assert 0.0 <= result.f1_score <= 1.0

        # Check timestamp is valid ISO 8601
        timestamp = datetime.fromisoformat(result.timestamp.replace('Z', '+00:00'))
        assert isinstance(timestamp, datetime)

    @pytest.mark.slow
    def test_evaluate_with_custom_answers(self, temp_golden_qa_file):
        """Test evaluation with custom answers and contexts."""
        evaluator = PersonaRagasEvaluator(
            persona_key="test",
            golden_qa_path=str(temp_golden_qa_file)
        )

        # Provide custom answers
        custom_answers = [
            "I am a test persona focused on quality assurance.",
            "I use systematic approaches with clear validation steps.",
            "I analyze failures, isolate issues, and fix them properly."
        ]

        # Provide custom contexts
        custom_contexts = [
            ["Test persona with expertise in testing"],
            ["Systematic testing with validation"],
            ["Failure analysis and reproduction"]
        ]

        result = evaluator.evaluate_persona(
            answers=custom_answers,
            contexts=custom_contexts
        )

        assert isinstance(result, RagasResult)
        assert result.questions_evaluated == 3

        # Metrics should be reasonable (not perfect since answers differ from ground truth)
        assert 0.0 <= result.faithfulness <= 1.0
        assert 0.0 <= result.answer_relevancy <= 1.0


class TestPersonaRagasEvaluatorRealData:
    """Tests with real golden Q&A files."""

    @pytest.mark.parametrize("persona_key", ["eeva", "gojo"])
    def test_evaluator_initialization_real_personas(self, persona_key):
        """Test initializing evaluator with real persona data."""
        try:
            evaluator = PersonaRagasEvaluator(persona_key)
            assert evaluator.persona_key == persona_key
            assert evaluator.dataset is not None
            assert evaluator.dataset.num_questions >= 10
        except FileNotFoundError:
            pytest.skip(f"Golden Q&A for {persona_key} not found")

    @pytest.mark.slow
    @pytest.mark.parametrize("persona_key", ["eeva", "gojo"])
    def test_placeholder_evaluation_real_personas(self, persona_key):
        """Test placeholder evaluation with real persona data."""
        try:
            evaluator = PersonaRagasEvaluator(persona_key)
            result = evaluator.evaluate_persona()

            # Check result validity
            assert isinstance(result, RagasResult)
            assert result.persona_key == persona_key
            assert result.questions_evaluated >= 10

            # In placeholder mode (ground_truth as both answer and context),
            # we expect high scores since they match perfectly
            assert result.faithfulness >= 0.7, "Placeholder mode should have high faithfulness"
            assert result.answer_relevancy >= 0.7, "Placeholder mode should have high relevancy"

        except FileNotFoundError:
            pytest.skip(f"Golden Q&A for {persona_key} not found")


class TestEvaluatorErrorHandling:
    """Tests for error handling in evaluator."""

    def test_invalid_persona_key(self):
        """Test handling of invalid persona key."""
        with pytest.raises(FileNotFoundError) as exc_info:
            PersonaRagasEvaluator("invalid_persona_that_does_not_exist")

        assert "Golden Q&A file not found" in str(exc_info.value)

    def test_mismatched_answer_length(self, temp_golden_qa_file):
        """Test handling mismatched answer/context lengths."""
        evaluator = PersonaRagasEvaluator(
            persona_key="test",
            golden_qa_path=str(temp_golden_qa_file)
        )

        # Provide wrong number of answers (2 instead of 3)
        with pytest.raises((ValueError, IndexError)):
            evaluator.evaluate_persona(
                answers=["Answer 1", "Answer 2"],  # Only 2 answers for 3 questions
                contexts=[["Context 1"], ["Context 2"], ["Context 3"]]
            )

    def test_empty_answers(self, temp_golden_qa_file):
        """Test handling empty answers list."""
        evaluator = PersonaRagasEvaluator(
            persona_key="test",
            golden_qa_path=str(temp_golden_qa_file)
        )

        # Provide empty answers
        with pytest.raises((ValueError, IndexError)):
            evaluator.evaluate_persona(
                answers=[],
                contexts=[]
            )
