"""Persona evaluation module using RAGAS framework.

This module provides quantifiable quality metrics for persona responses:
- Faithfulness: Is the answer grounded in retrieved context?
- Answer Relevancy: Does the answer address the question?
- Context Precision: Is retrieved context relevant?
- Context Recall: Was all relevant context retrieved?

Usage:
    from src.coordinator.evaluation import PersonaRagasEvaluator, RagasResult

    evaluator = PersonaRagasEvaluator("eeva", "personas/_golden_qa/eeva_golden_qa.json")
    result = evaluator.evaluate_persona()
    print(f"F1 Score: {result.f1_score}")
"""

from .ragas_evaluator import PersonaRagasEvaluator, RagasResult
from .golden_examples import GoldenExamplesManager, GoldenQuestion
from .metrics import calculate_f1_score, calculate_weighted_score

__all__ = [
    "PersonaRagasEvaluator",
    "RagasResult",
    "GoldenExamplesManager",
    "GoldenQuestion",
    "calculate_f1_score",
    "calculate_weighted_score",
]
