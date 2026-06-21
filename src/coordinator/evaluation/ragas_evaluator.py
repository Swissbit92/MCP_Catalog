"""RAGAS evaluator for persona response quality.

Evaluates persona responses using RAGAS (RAG Assessment) metrics:
- Faithfulness: Answer grounded in context
- Answer Relevancy: Answer addresses question
- Context Precision: Retrieved context is relevant
- Context Recall: All relevant context retrieved
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

try:
    from ragas import evaluate
    from ragas.metrics import faithfulness, answer_relevancy, context_recall, context_precision
    from datasets import Dataset
except ImportError as e:
    raise ImportError(
        "RAGAS not installed. Run: pip install ragas==0.2.3"
    ) from e

from .golden_examples import GoldenExamplesManager
from .metrics import calculate_f1_score

logger = logging.getLogger(__name__)


@dataclass
class RagasResult:
    """RAGAS evaluation result for a persona.

    Attributes:
        persona_key: Persona identifier
        persona_display_name: Persona display name
        faithfulness: Faithfulness score (0.0-1.0)
        answer_relevancy: Answer relevancy score (0.0-1.0)
        context_precision: Context precision score (0.0-1.0)
        context_recall: Context recall score (0.0-1.0)
        f1_score: Weighted F1 score (0.0-1.0)
        questions_evaluated: Number of questions evaluated
        timestamp: ISO 8601 timestamp of evaluation
        model_name: LLM model used (e.g., "llama3.1:8b")
        temperature: LLM temperature used
    """
    persona_key: str
    persona_display_name: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float
    f1_score: float
    questions_evaluated: int
    timestamp: str
    model_name: Optional[str] = None
    temperature: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    def __str__(self) -> str:
        """Human-readable string representation."""
        return (
            f"RAGAS Result for {self.persona_display_name} ({self.persona_key})\n"
            f"  Faithfulness:      {self.faithfulness:.3f}\n"
            f"  Answer Relevancy:  {self.answer_relevancy:.3f}\n"
            f"  Context Precision: {self.context_precision:.3f}\n"
            f"  Context Recall:    {self.context_recall:.3f}\n"
            f"  F1 Score:          {self.f1_score:.3f}\n"
            f"  Questions:         {self.questions_evaluated}\n"
            f"  Timestamp:         {self.timestamp}"
        )


class PersonaRagasEvaluator:
    """Evaluate persona response quality using RAGAS metrics.

    Example:
        >>> evaluator = PersonaRagasEvaluator("eeva", "personas/_golden_qa/eeva_golden_qa.json")
        >>> result = evaluator.evaluate_persona()
        >>> print(f"F1 Score: {result.f1_score:.3f}")
        F1 Score: 0.845
    """

    def __init__(
        self,
        persona_key: str,
        golden_qa_path: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.0
    ):
        """Initialize RAGAS evaluator for a persona.

        Args:
            persona_key: Persona identifier (e.g., "eeva")
            golden_qa_path: Path to golden Q&A JSON (auto-detected if None)
            model_name: LLM model to use for generating answers
            temperature: LLM temperature (0.0 for deterministic evaluation)
        """
        self.persona_key = persona_key
        self.model_name = model_name
        self.temperature = temperature

        # Load golden Q&A dataset
        self.manager = GoldenExamplesManager()
        if golden_qa_path:
            # Custom path: load directly
            import json
            with open(golden_qa_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            from .golden_examples import GoldenQuestion, GoldenExamplesDataset
            questions = [GoldenQuestion.from_dict(q) for q in data["questions"]]
            self.dataset = GoldenExamplesDataset(
                persona_key=data["persona_key"],
                persona_display_name=data["persona_display_name"],
                version=data["version"],
                created=data["created"],
                questions=questions
            )
        else:
            # Auto-detect from personas/_golden_qa/{persona_key}_golden_qa.json
            self.dataset = self.manager.load_dataset(persona_key)

        logger.info(
            f"[RAGASEvaluator] Initialized for {self.persona_key} "
            f"with {self.dataset.num_questions} questions"
        )

    def evaluate_persona(
        self,
        answers: Optional[List[str]] = None,
        contexts: Optional[List[List[str]]] = None
    ) -> RagasResult:
        """Run RAGAS evaluation on all golden Q&A examples.

        Args:
            answers: List of generated answers (if None, uses ground_truth as placeholder)
            contexts: List of context lists (if None, uses ground_truth as context)

        Returns:
            RagasResult with all metrics

        Note:
            For now, this is a PLACEHOLDER implementation. Full implementation requires:
            1. Generating actual answers using the persona's LLM
            2. Retrieving actual context from Phase 3 memory system
            3. Running RAGAS evaluation with real data

            Current behavior: Uses ground_truth as both answer and context for testing.
        """
        logger.info(f"[RAGASEvaluator] Starting evaluation for {self.persona_key}...")

        # Prepare evaluation dataset
        questions = [q.question for q in self.dataset.questions]
        ground_truths = [q.ground_truth for q in self.dataset.questions]  # String, not list

        # Placeholder: Use ground truth as answers and contexts if not provided
        if answers is None:
            logger.warning(
                "[RAGASEvaluator] No answers provided, using ground_truth as placeholder"
            )
            answers = [q.ground_truth for q in self.dataset.questions]

        if contexts is None:
            logger.warning(
                "[RAGASEvaluator] No contexts provided, using ground_truth as placeholder"
            )
            contexts = [[q.ground_truth] for q in self.dataset.questions]

        # Create RAGAS dataset
        data = {
            "question": questions,
            "answer": answers,
            "contexts": contexts,
            "ground_truth": ground_truths,  # Should be list of strings, not list of lists
        }
        dataset = Dataset.from_dict(data)

        # Run RAGAS evaluation
        logger.info(f"[RAGASEvaluator] Running RAGAS evaluation on {len(questions)} questions...")
        try:
            result = evaluate(
                dataset=dataset,
                metrics=[
                    context_precision,
                    context_recall,
                    faithfulness,
                    answer_relevancy,
                ],
            )
        except Exception as e:
            logger.error(f"[RAGASEvaluator] RAGAS evaluation failed: {e}")
            raise

        # Extract mean scores
        metrics = {
            "faithfulness": float(result["faithfulness"]),
            "answer_relevancy": float(result["answer_relevancy"]),
            "context_precision": float(result["context_precision"]),
            "context_recall": float(result["context_recall"]),
        }

        # Calculate F1 score
        f1 = calculate_f1_score(metrics)

        # Create result
        ragas_result = RagasResult(
            persona_key=self.persona_key,
            persona_display_name=self.dataset.persona_display_name,
            faithfulness=metrics["faithfulness"],
            answer_relevancy=metrics["answer_relevancy"],
            context_precision=metrics["context_precision"],
            context_recall=metrics["context_recall"],
            f1_score=f1,
            questions_evaluated=len(questions),
            timestamp=datetime.utcnow().isoformat() + "Z",
            model_name=self.model_name,
            temperature=self.temperature,
        )

        logger.info(f"[RAGASEvaluator] Evaluation complete:\n{ragas_result}")

        return ragas_result

    def evaluate_single_question(
        self,
        question: str,
        answer: str,
        ground_truth: str,
        context: Optional[List[str]] = None
    ) -> Dict[str, float]:
        """Evaluate a single Q&A pair (for testing).

        Args:
            question: Question text
            answer: Generated answer
            ground_truth: Expected answer
            context: Retrieved context (defaults to ground_truth)

        Returns:
            Dictionary with individual metrics
        """
        if context is None:
            context = [ground_truth]

        # Create single-item dataset
        data = {
            "question": [question],
            "answer": [answer],
            "contexts": [context],
            "ground_truth": [ground_truth],  # Should be list of strings, not list of lists
        }
        dataset = Dataset.from_dict(data)

        # Evaluate
        result = evaluate(
            dataset=dataset,
            metrics=[
                context_precision,
                context_recall,
                faithfulness,
                answer_relevancy,
            ],
        )

        return {
            "faithfulness": float(result["faithfulness"]),
            "answer_relevancy": float(result["answer_relevancy"]),
            "context_precision": float(result["context_precision"]),
            "context_recall": float(result["context_recall"]),
        }
