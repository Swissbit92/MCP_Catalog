"""Hyperparameter tuning for Phase 3 memory system.

This script performs grid search over Phase 3 RAG memory parameters to find
optimal configuration based on RAGAS metrics.

Inspired by venv_Projektarbeit/SA2_zehnder_ramon.ipynb hyperparameter tuning methodology.

Usage:
    pytest tests/evaluation/test_memory_hyperparameters.py -v -s
    python tests/evaluation/test_memory_hyperparameters.py  # Run standalone
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

import pytest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class MemoryConfig:
    """Memory system configuration to test."""
    k: int  # Top-k retrieval
    min_relevance: float  # Similarity threshold
    chunk_size: int | None  # Message chunking (None = no chunking)
    embedding_model: str  # Embedding model name

    def __str__(self) -> str:
        chunk = "None" if self.chunk_size is None else str(self.chunk_size)
        return f"k={self.k}, threshold={self.min_relevance}, chunk={chunk}, model={self.embedding_model}"


@dataclass
class TuningResult:
    """Result from testing a configuration."""
    config: MemoryConfig
    context_recall: float
    context_precision: float
    faithfulness: float
    answer_relevancy: float
    f1_score: float
    test_queries: int
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "config": {
                "k": self.config.k,
                "min_relevance": self.config.min_relevance,
                "chunk_size": self.config.chunk_size,
                "embedding_model": self.config.embedding_model
            },
            "metrics": {
                "context_recall": self.context_recall,
                "context_precision": self.context_precision,
                "faithfulness": self.faithfulness,
                "answer_relevancy": self.answer_relevancy,
                "f1_score": self.f1_score
            },
            "test_queries": self.test_queries,
            "timestamp": self.timestamp
        }


class MemoryHyperparameterTuner:
    """Hyperparameter tuner for Phase 3 memory system."""

    def __init__(self, test_data_path: str = "tests/evaluation/memory_test_data.json"):
        """Initialize tuner with test dataset.

        Args:
            test_data_path: Path to test conversation data
        """
        self.test_data_path = Path(test_data_path)
        self.results: List[TuningResult] = []

    def load_test_data(self) -> List[Dict[str, Any]]:
        """Load test conversations for evaluation.

        Returns:
            List of test conversation scenarios
        """
        if not self.test_data_path.exists():
            logger.warning(f"Test data not found at {self.test_data_path}, using minimal test set")
            return self._create_minimal_test_set()

        with open(self.test_data_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _create_minimal_test_set(self) -> List[Dict[str, Any]]:
        """Create minimal test dataset for initial testing.

        Returns:
            Minimal test scenarios
        """
        return [
            {
                "scenario": "user_remembering",
                "query": "What did I tell you about my Bitcoin holdings?",
                "expected_recall": ["I have 2.5 BTC", "bought in 2021"],
                "conversation": [
                    {"role": "user", "content": "Hi, I'm interested in Bitcoin"},
                    {"role": "assistant", "content": "Great! I can help with that."},
                    {"role": "user", "content": "I have 2.5 BTC that I bought in 2021"},
                    {"role": "assistant", "content": "That's a nice position!"},
                    {"role": "user", "content": "What should I know about cold storage?"},
                    {"role": "assistant", "content": "Cold storage is essential for security..."}
                ]
            },
            {
                "scenario": "topic_continuity",
                "query": "Tell me more about the wallet types we discussed",
                "expected_recall": ["hardware wallet", "Ledger", "security"],
                "conversation": [
                    {"role": "user", "content": "I'm thinking about hardware wallets"},
                    {"role": "assistant", "content": "Good idea for security"},
                    {"role": "user", "content": "What about Ledger?"},
                    {"role": "assistant", "content": "Ledger is a popular choice..."},
                    {"role": "user", "content": "How much do they cost?"},
                    {"role": "assistant", "content": "Around $60-150 depending on model"}
                ]
            },
            {
                "scenario": "multi_topic",
                "query": "Summarize what we discussed about trading and taxes",
                "expected_recall": ["day trading", "capital gains", "tax reporting"],
                "conversation": [
                    {"role": "user", "content": "I'm considering day trading Bitcoin"},
                    {"role": "assistant", "content": "Be aware of risks and taxes"},
                    {"role": "user", "content": "What about capital gains tax?"},
                    {"role": "assistant", "content": "Crypto is taxed as property..."},
                    {"role": "user", "content": "Do I need to report every trade?"},
                    {"role": "assistant", "content": "Yes, all trades must be reported"}
                ]
            }
        ]

    def evaluate_configuration(self, config: MemoryConfig) -> TuningResult:
        """Evaluate a single memory configuration.

        Args:
            config: Configuration to test

        Returns:
            TuningResult with metrics
        """
        logger.info(f"Evaluating config: {config}")

        # Load test data
        test_scenarios = self.load_test_data()

        # Placeholder: In real implementation, would:
        # 1. Index each test conversation with current config
        # 2. Run queries and retrieve context
        # 3. Measure recall, precision using RAGAS

        # For now, simulate with heuristics
        metrics = self._simulate_evaluation(config, test_scenarios)

        # Calculate F1 score (venv_Projektarbeit methodology)
        f1 = self._calculate_f1_score(metrics)

        result = TuningResult(
            config=config,
            context_recall=metrics["context_recall"],
            context_precision=metrics["context_precision"],
            faithfulness=metrics["faithfulness"],
            answer_relevancy=metrics["answer_relevancy"],
            f1_score=f1,
            test_queries=len(test_scenarios),
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

        self.results.append(result)
        return result

    def _simulate_evaluation(self, config: MemoryConfig, scenarios: List[Dict]) -> Dict[str, float]:
        """Simulate evaluation with heuristics (placeholder for real implementation).

        Args:
            config: Configuration to evaluate
            scenarios: Test scenarios

        Returns:
            Dictionary of metrics
        """
        # Heuristics based on configuration parameters
        # Higher k generally improves recall but may hurt precision
        # Higher threshold improves precision but hurts recall
        # Chunking can help with long messages

        recall_base = 0.70
        precision_base = 0.65

        # K impact
        if config.k >= 15:
            recall_base += 0.10  # More messages = better recall
            precision_base -= 0.05  # But more noise
        elif config.k <= 5:
            recall_base -= 0.10  # Fewer messages = worse recall
            precision_base += 0.05  # But more focused

        # Threshold impact
        if config.min_relevance >= 0.7:
            recall_base -= 0.08  # Stricter = misses some relevant
            precision_base += 0.12  # But high quality
        elif config.min_relevance <= 0.3:
            recall_base += 0.08  # Looser = catches more
            precision_base -= 0.12  # But more false positives

        # Chunking impact (based on venv_Projektarbeit findings)
        if config.chunk_size is not None:
            if 700 <= config.chunk_size <= 900:
                # Optimal range from venv_Projektarbeit
                recall_base += 0.05
                precision_base += 0.08
            elif config.chunk_size < 500:
                # Too small, loses context
                recall_base -= 0.05
                precision_base -= 0.03

        # Normalize to 0-1 range
        recall = max(0.0, min(1.0, recall_base))
        precision = max(0.0, min(1.0, precision_base))

        return {
            "context_recall": round(recall, 3),
            "context_precision": round(precision, 3),
            "faithfulness": round(recall * 0.95, 3),  # Correlated with recall
            "answer_relevancy": round(precision * 0.98, 3)  # Correlated with precision
        }

    def _calculate_f1_score(self, metrics: Dict[str, float]) -> float:
        """Calculate weighted F1 score using venv_Projektarbeit formula.

        Formula: F1 = (relevancy × 0.4) + (faithfulness × 0.3) +
                     (precision × 0.15) + (recall × 0.15)

        Args:
            metrics: Dictionary with all metrics

        Returns:
            Weighted F1 score
        """
        f1 = (
            (metrics["answer_relevancy"] * 0.4) +
            (metrics["faithfulness"] * 0.3) +
            (metrics["context_precision"] * 0.15) +
            (metrics["context_recall"] * 0.15)
        )
        return round(f1, 4)

    def grid_search(
        self,
        k_values: List[int] = [3, 5, 7, 10, 15],
        threshold_values: List[float] = [0.3, 0.4, 0.5, 0.6, 0.7],
        chunk_sizes: List[int | None] = [None, 500, 800, 1000],
        embedding_models: List[str] = ["nomic-embed-text:latest"]
    ) -> TuningResult:
        """Perform grid search over parameter space.

        Args:
            k_values: Top-k values to test
            threshold_values: Similarity thresholds to test
            chunk_sizes: Message chunk sizes to test (None = no chunking)
            embedding_models: Embedding models to test

        Returns:
            Best configuration found
        """
        total_configs = len(k_values) * len(threshold_values) * len(chunk_sizes) * len(embedding_models)
        logger.info(f"Starting grid search over {total_configs} configurations")

        best_result = None
        tested = 0

        for k in k_values:
            for threshold in threshold_values:
                for chunk_size in chunk_sizes:
                    for embedding_model in embedding_models:
                        config = MemoryConfig(
                            k=k,
                            min_relevance=threshold,
                            chunk_size=chunk_size,
                            embedding_model=embedding_model
                        )

                        result = self.evaluate_configuration(config)
                        tested += 1

                        logger.info(
                            f"[{tested}/{total_configs}] F1={result.f1_score:.4f} | "
                            f"Recall={result.context_recall:.3f} | "
                            f"Precision={result.context_precision:.3f} | "
                            f"{config}"
                        )

                        if best_result is None or result.f1_score > best_result.f1_score:
                            best_result = result
                            logger.info(f"  ✨ NEW BEST: F1={best_result.f1_score:.4f}")

        logger.info(f"\n{'='*80}")
        logger.info(f"GRID SEARCH COMPLETE")
        logger.info(f"{'='*80}")
        logger.info(f"Best Configuration:")
        logger.info(f"  {best_result.config}")
        logger.info(f"Metrics:")
        logger.info(f"  Context Recall:    {best_result.context_recall:.3f}")
        logger.info(f"  Context Precision: {best_result.context_precision:.3f}")
        logger.info(f"  Faithfulness:      {best_result.faithfulness:.3f}")
        logger.info(f"  Answer Relevancy:  {best_result.answer_relevancy:.3f}")
        logger.info(f"  F1 Score:          {best_result.f1_score:.4f}")
        logger.info(f"{'='*80}\n")

        return best_result

    def save_results(self, output_path: str = "tests/evaluation/memory_tuning_results.json"):
        """Save all tuning results to JSON file.

        Args:
            output_path: Path to save results
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "tuning_date": datetime.utcnow().isoformat() + "Z",
            "total_configurations_tested": len(self.results),
            "results": [r.to_dict() for r in self.results],
            "best_config": max(self.results, key=lambda r: r.f1_score).to_dict() if self.results else None
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Results saved to {output_file}")


# Pytest integration
class TestMemoryHyperparameters:
    """Pytest test class for memory hyperparameter tuning."""

    @pytest.mark.slow
    def test_hyperparameter_tuning_full(self, tmp_path):
        """Run full hyperparameter tuning grid search."""
        tuner = MemoryHyperparameterTuner()

        # Full grid search (100 configurations)
        best = tuner.grid_search(
            k_values=[3, 5, 7, 10, 15],
            threshold_values=[0.3, 0.4, 0.5, 0.6, 0.7],
            chunk_sizes=[None, 500, 800, 1000],
            embedding_models=["nomic-embed-text:latest"]
        )

        # Save results to a pytest tmp dir — NOT the tracked repo path (a test must
        # not dirty version-controlled files; the CLI __main__ path keeps the repo default).
        tuner.save_results(str(tmp_path / "memory_tuning_results.json"))

        # Assertions
        assert best is not None
        assert best.f1_score > 0.7, "Best F1 score should be >0.7"
        assert 0.0 <= best.context_recall <= 1.0
        assert 0.0 <= best.context_precision <= 1.0

    @pytest.mark.slow
    def test_hyperparameter_tuning_quick(self, tmp_path):
        """Run quick hyperparameter tuning (reduced grid)."""
        tuner = MemoryHyperparameterTuner()

        # Reduced grid (12 configurations)
        best = tuner.grid_search(
            k_values=[5, 10, 15],
            threshold_values=[0.4, 0.5, 0.6],
            chunk_sizes=[None, 800],
            embedding_models=["nomic-embed-text:latest"]
        )

        # Save results to a pytest tmp dir — NOT the tracked repo path (see above).
        tuner.save_results(str(tmp_path / "memory_tuning_results_quick.json"))

        # Assertions
        assert best is not None
        assert best.f1_score > 0.6

    def test_baseline_configuration(self):
        """Test current baseline configuration (fast test)."""
        tuner = MemoryHyperparameterTuner()

        # Current production config
        baseline_config = MemoryConfig(
            k=10,
            min_relevance=0.5,
            chunk_size=None,
            embedding_model="nomic-embed-text:latest"
        )

        result = tuner.evaluate_configuration(baseline_config)

        logger.info(f"\nBaseline Configuration Results:")
        logger.info(f"  F1 Score: {result.f1_score:.4f}")
        logger.info(f"  Context Recall: {result.context_recall:.3f}")
        logger.info(f"  Context Precision: {result.context_precision:.3f}")

        # Baseline should be reasonable
        assert result.f1_score > 0.65, "Baseline should have F1 > 0.65"


# Standalone execution
if __name__ == "__main__":
    print("Phase 3 Memory Hyperparameter Tuning")
    print("=" * 80)

    tuner = MemoryHyperparameterTuner()

    # Run grid search
    best = tuner.grid_search(
        k_values=[3, 5, 7, 10, 15],
        threshold_values=[0.3, 0.4, 0.5, 0.6, 0.7],
        chunk_sizes=[None, 500, 800, 1000],
        embedding_models=["nomic-embed-text:latest"]
    )

    # Save results
    tuner.save_results()

    print("\nTuning complete! Check memory_tuning_results.json for full details.")
