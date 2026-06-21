"""Golden Q&A examples management for RAGAS evaluation.

Loads and validates golden question-answer pairs from JSON files.
"""

from __future__ import annotations

import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class GoldenQuestion:
    """A single golden Q&A example for evaluation.

    Attributes:
        id: Unique identifier (e.g., "eeva_q1")
        category: Question category (e.g., "background", "technical")
        question: The question text
        ground_truth: The expected answer (reference for evaluation)
        expected_topics: List of topics that should appear in answer
        difficulty: Question difficulty (easy, medium, hard)
    """
    id: str
    category: str
    question: str
    ground_truth: str
    expected_topics: List[str]
    difficulty: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> GoldenQuestion:
        """Create GoldenQuestion from dictionary.

        Args:
            data: Dictionary with question data

        Returns:
            GoldenQuestion instance
        """
        return cls(
            id=data["id"],
            category=data["category"],
            question=data["question"],
            ground_truth=data["ground_truth"],
            expected_topics=data.get("expected_topics", []),
            difficulty=data.get("difficulty", "medium")
        )


@dataclass
class GoldenExamplesDataset:
    """Complete golden Q&A dataset for a persona.

    Attributes:
        persona_key: Persona identifier (e.g., "eeva")
        persona_display_name: Persona display name (e.g., "Eeva")
        version: Dataset version (e.g., "1.0")
        created: Creation date
        questions: List of GoldenQuestion instances
    """
    persona_key: str
    persona_display_name: str
    version: str
    created: str
    questions: List[GoldenQuestion]

    @property
    def num_questions(self) -> int:
        """Total number of questions in dataset."""
        return len(self.questions)

    def get_questions_by_difficulty(self, difficulty: str) -> List[GoldenQuestion]:
        """Filter questions by difficulty.

        Args:
            difficulty: Difficulty level (easy, medium, hard)

        Returns:
            List of questions with specified difficulty
        """
        return [q for q in self.questions if q.difficulty == difficulty]

    def get_questions_by_category(self, category: str) -> List[GoldenQuestion]:
        """Filter questions by category.

        Args:
            category: Category name (e.g., "technical", "background")

        Returns:
            List of questions in specified category
        """
        return [q for q in self.questions if q.category == category]


class GoldenExamplesManager:
    """Manager for loading and validating golden Q&A examples."""

    def __init__(self, base_path: Optional[str] = None):
        """Initialize golden examples manager.

        Args:
            base_path: Base directory for golden Q&A files
                      (default: personas/_golden_qa/)
        """
        if base_path is None:
            base_path = "personas/_golden_qa"
        self.base_path = Path(base_path)

    def load_dataset(self, persona_key: str) -> GoldenExamplesDataset:
        """Load golden Q&A dataset for a persona.

        Args:
            persona_key: Persona identifier (e.g., "eeva")

        Returns:
            GoldenExamplesDataset instance

        Raises:
            FileNotFoundError: If golden Q&A file doesn't exist
            ValueError: If JSON is invalid or missing required fields
        """
        file_path = self.base_path / f"{persona_key}_golden_qa.json"

        if not file_path.exists():
            raise FileNotFoundError(
                f"Golden Q&A file not found: {file_path}\n"
                f"Create it using the template in {self.base_path}/README.md"
            )

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {file_path}: {e}")

        # Validate required fields
        required_fields = ["persona_key", "persona_display_name", "version", "created", "questions"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise ValueError(f"Missing required fields in {file_path}: {missing_fields}")

        # Parse questions
        questions = []
        for i, q_data in enumerate(data["questions"]):
            try:
                questions.append(GoldenQuestion.from_dict(q_data))
            except KeyError as e:
                raise ValueError(
                    f"Invalid question #{i+1} in {file_path}: missing field {e}"
                )

        dataset = GoldenExamplesDataset(
            persona_key=data["persona_key"],
            persona_display_name=data["persona_display_name"],
            version=data["version"],
            created=data["created"],
            questions=questions
        )

        logger.info(
            f"[GoldenExamples] Loaded {dataset.num_questions} questions for {persona_key} "
            f"(version {dataset.version})"
        )

        return dataset

    def validate_dataset(self, dataset: GoldenExamplesDataset) -> Dict[str, Any]:
        """Validate golden Q&A dataset quality.

        Checks:
        - Minimum number of questions (10)
        - Diversity of difficulty levels
        - Diversity of categories
        - Ground truth length (should be substantial)

        Args:
            dataset: GoldenExamplesDataset to validate

        Returns:
            Dictionary with validation results and warnings
        """
        warnings = []
        stats = {
            "num_questions": dataset.num_questions,
            "difficulty_distribution": {},
            "category_distribution": {},
            "avg_ground_truth_length": 0,
        }

        # Count difficulty distribution
        for difficulty in ["easy", "medium", "hard"]:
            count = len(dataset.get_questions_by_difficulty(difficulty))
            stats["difficulty_distribution"][difficulty] = count

        # Count category distribution
        categories = set(q.category for q in dataset.questions)
        for category in categories:
            count = len(dataset.get_questions_by_category(category))
            stats["category_distribution"][category] = count

        # Calculate average ground truth length
        total_length = sum(len(q.ground_truth) for q in dataset.questions)
        stats["avg_ground_truth_length"] = total_length // dataset.num_questions if dataset.num_questions > 0 else 0

        # Validation rules
        if dataset.num_questions < 10:
            warnings.append(f"Only {dataset.num_questions} questions (minimum 10 recommended)")

        if stats["difficulty_distribution"]["easy"] == 0:
            warnings.append("No easy questions (should have 3+ for baseline)")

        if stats["difficulty_distribution"]["hard"] == 0:
            warnings.append("No hard questions (should have 3+ for testing limits)")

        if len(categories) < 2:
            warnings.append("Only 1 category (should have 2+ for diversity)")

        if stats["avg_ground_truth_length"] < 50:
            warnings.append("Ground truth answers are very short (avg < 50 chars)")

        stats["warnings"] = warnings
        stats["is_valid"] = len(warnings) == 0

        return stats

    def list_available_datasets(self) -> List[str]:
        """List all available golden Q&A datasets.

        Returns:
            List of persona keys with golden Q&A files
        """
        if not self.base_path.exists():
            return []

        datasets = []
        for file_path in self.base_path.glob("*_golden_qa.json"):
            persona_key = file_path.stem.replace("_golden_qa", "")
            datasets.append(persona_key)

        return sorted(datasets)
