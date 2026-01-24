"""Pytest fixtures for RAGAS evaluation tests."""

import pytest
import json
import tempfile
from pathlib import Path
from typing import Dict, Any


@pytest.fixture
def sample_golden_qa_data() -> Dict[str, Any]:
    """Sample golden Q&A dataset for testing."""
    return {
        "persona_key": "test_persona",
        "persona_display_name": "Test Persona",
        "version": "1.0",
        "created": "2026-01-01",
        "questions": [
            {
                "id": "test_q1",
                "category": "background",
                "question": "What is your background?",
                "ground_truth": "I am a test persona with expertise in testing.",
                "expected_topics": ["test", "persona", "expertise"],
                "difficulty": "easy"
            },
            {
                "id": "test_q2",
                "category": "technical",
                "question": "How do you approach testing?",
                "ground_truth": "I approach testing systematically with clear test cases and validation.",
                "expected_topics": ["testing", "validation", "systematic"],
                "difficulty": "medium"
            },
            {
                "id": "test_q3",
                "category": "scenario",
                "question": "A test is failing. What do you do?",
                "ground_truth": "I analyze the failure, isolate the issue, reproduce it consistently, and then fix it with proper validation.",
                "expected_topics": ["debugging", "failure analysis", "reproduction", "validation"],
                "difficulty": "hard"
            }
        ]
    }


@pytest.fixture
def temp_golden_qa_file(sample_golden_qa_data, tmp_path) -> Path:
    """Create a temporary golden Q&A JSON file."""
    file_path = tmp_path / "test_persona_golden_qa.json"
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(sample_golden_qa_data, f, indent=2)
    return file_path


@pytest.fixture
def temp_golden_qa_dir(sample_golden_qa_data, tmp_path) -> Path:
    """Create a temporary directory with golden Q&A files."""
    golden_qa_dir = tmp_path / "_golden_qa"
    golden_qa_dir.mkdir()

    # Create test_persona file
    file_path = golden_qa_dir / "test_persona_golden_qa.json"
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(sample_golden_qa_data, f, indent=2)

    return golden_qa_dir


@pytest.fixture
def invalid_golden_qa_data() -> Dict[str, Any]:
    """Invalid golden Q&A dataset missing required fields."""
    return {
        "persona_key": "invalid_persona",
        # Missing persona_display_name, version, created
        "questions": [
            {
                "id": "invalid_q1",
                "question": "Test question?",
                # Missing category, ground_truth, expected_topics, difficulty
            }
        ]
    }


@pytest.fixture
def low_quality_golden_qa_data() -> Dict[str, Any]:
    """Low quality golden Q&A dataset (triggers warnings)."""
    return {
        "persona_key": "low_quality",
        "persona_display_name": "Low Quality Persona",
        "version": "1.0",
        "created": "2026-01-01",
        "questions": [
            {
                "id": "lq_q1",
                "category": "test",
                "question": "Test?",
                "ground_truth": "Yes.",  # Too short
                "expected_topics": ["test"],
                "difficulty": "easy"
            },
            {
                "id": "lq_q2",
                "category": "test",  # Only 1 category
                "question": "Another test?",
                "ground_truth": "No.",  # Too short
                "expected_topics": ["test"],
                "difficulty": "easy"  # No medium or hard questions
            }
        ]  # Only 2 questions (should have 10+)
    }


@pytest.fixture
def sample_ragas_metrics() -> Dict[str, float]:
    """Sample RAGAS metrics for testing."""
    return {
        "faithfulness": 0.85,
        "answer_relevancy": 0.90,
        "context_precision": 0.80,
        "context_recall": 0.75
    }


@pytest.fixture
def baseline_metrics() -> Dict[str, float]:
    """Baseline metrics for regression testing."""
    return {
        "faithfulness": 0.85,
        "answer_relevancy": 0.90,
        "context_precision": 0.80,
        "context_recall": 0.80,
        "f1_score": 0.850
    }


@pytest.fixture
def regressed_metrics() -> Dict[str, float]:
    """Metrics showing regression (>10% drop)."""
    return {
        "faithfulness": 0.75,  # 11.8% drop
        "answer_relevancy": 0.85,  # 5.6% drop
        "context_precision": 0.75,  # 6.25% drop
        "context_recall": 0.70,  # 12.5% drop
        "f1_score": 0.770  # Calculated
    }


@pytest.fixture
def warning_metrics() -> Dict[str, float]:
    """Metrics showing warning level regression (5-10% drop)."""
    return {
        "faithfulness": 0.80,  # 5.9% drop
        "answer_relevancy": 0.85,  # 5.6% drop
        "context_precision": 0.76,  # 5% drop
        "context_recall": 0.78,  # 2.5% drop
        "f1_score": 0.810  # Calculated
    }


def pytest_addoption(parser):
    """Add custom pytest command-line options."""
    parser.addoption(
        "--persona",
        action="store",
        default=None,
        help="Run tests for a specific persona (e.g., 'eeva')"
    )
    parser.addoption(
        "--threshold",
        action="store",
        type=float,
        default=0.80,
        help="F1 score threshold for quality tests (default: 0.80)"
    )
    parser.addoption(
        "--skip-slow",
        action="store_true",
        default=False,
        help="Skip slow integration tests"
    )
