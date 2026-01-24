"""Custom metrics for RAGAS evaluation.

Provides weighted F1 score calculation and threshold validation based on
venv_Projektarbeit methodology.
"""

from typing import Dict


def calculate_f1_score(metrics: Dict[str, float]) -> float:
    """Calculate weighted F1 score from RAGAS metrics.

    Uses the same weighting as venv_Projektarbeit/SA2_zehnder_ramon.ipynb:
    - Answer Relevancy: 40%
    - Faithfulness: 30%
    - Context Precision: 15%
    - Context Recall: 15%

    Args:
        metrics: Dictionary with keys: answer_relevancy, faithfulness,
                context_precision, context_recall

    Returns:
        Weighted F1 score (0.0 to 1.0)

    Example:
        >>> metrics = {
        ...     "answer_relevancy": 0.90,
        ...     "faithfulness": 0.85,
        ...     "context_precision": 0.80,
        ...     "context_recall": 0.75
        ... }
        >>> calculate_f1_score(metrics)
        0.845
    """
    answer_relevancy = metrics.get("answer_relevancy", 0.0)
    faithfulness = metrics.get("faithfulness", 0.0)
    context_precision = metrics.get("context_precision", 0.0)
    context_recall = metrics.get("context_recall", 0.0)

    f1 = (
        (answer_relevancy * 0.4) +
        (faithfulness * 0.3) +
        (context_precision * 0.15) +
        (context_recall * 0.15)
    )

    return round(f1, 4)


def calculate_weighted_score(
    answer_relevancy: float,
    faithfulness: float,
    context_precision: float,
    context_recall: float
) -> float:
    """Calculate weighted score from individual metrics.

    Alternative API to calculate_f1_score for clearer function signatures.

    Args:
        answer_relevancy: Answer relevancy score (0.0 to 1.0)
        faithfulness: Faithfulness score (0.0 to 1.0)
        context_precision: Context precision score (0.0 to 1.0)
        context_recall: Context recall score (0.0 to 1.0)

    Returns:
        Weighted F1 score (0.0 to 1.0)
    """
    return calculate_f1_score({
        "answer_relevancy": answer_relevancy,
        "faithfulness": faithfulness,
        "context_precision": context_precision,
        "context_recall": context_recall,
    })


def check_regression(
    current_metrics: Dict[str, float],
    baseline_metrics: Dict[str, float],
    hard_threshold: float = 0.10,
    warning_threshold: float = 0.05
) -> Dict[str, str]:
    """Check if current metrics represent a regression from baseline.

    Args:
        current_metrics: Current evaluation metrics
        baseline_metrics: Baseline metrics to compare against
        hard_threshold: Threshold for hard failure (default: 10% drop)
        warning_threshold: Threshold for warning (default: 5% drop)

    Returns:
        Dictionary with status for each metric:
        - "pass": Within 5% of baseline or better
        - "warning": 5-10% drop from baseline
        - "fail": >10% drop from baseline

    Example:
        >>> current = {"faithfulness": 0.80, "answer_relevancy": 0.85}
        >>> baseline = {"faithfulness": 0.90, "answer_relevancy": 0.88}
        >>> check_regression(current, baseline)
        {'faithfulness': 'fail', 'answer_relevancy': 'pass'}
    """
    results = {}

    for metric_name in ["faithfulness", "answer_relevancy", "context_precision", "context_recall", "f1_score"]:
        current_value = current_metrics.get(metric_name, 0.0)
        baseline_value = baseline_metrics.get(metric_name, 0.0)

        if baseline_value == 0.0:
            results[metric_name] = "pass"  # No baseline to compare
            continue

        drop_pct = (baseline_value - current_value) / baseline_value

        if drop_pct > hard_threshold:
            results[metric_name] = "fail"
        elif drop_pct > warning_threshold:
            results[metric_name] = "warning"
        else:
            results[metric_name] = "pass"

    return results
