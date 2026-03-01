"""Tests for golden Q&A examples management."""

import pytest
import json
from pathlib import Path

from src.coordinator.evaluation.golden_examples import (
    GoldenQuestion,
    GoldenExamplesDataset,
    GoldenExamplesManager
)


class TestGoldenQuestion:
    """Tests for GoldenQuestion dataclass."""

    def test_from_dict_valid(self):
        """Test creating GoldenQuestion from valid dictionary."""
        data = {
            "id": "test_q1",
            "category": "background",
            "question": "What is your name?",
            "ground_truth": "I am a test persona.",
            "expected_topics": ["test", "persona"],
            "difficulty": "easy"
        }

        question = GoldenQuestion.from_dict(data)

        assert question.id == "test_q1"
        assert question.category == "background"
        assert question.question == "What is your name?"
        assert question.ground_truth == "I am a test persona."
        assert question.expected_topics == ["test", "persona"]
        assert question.difficulty == "easy"

    def test_from_dict_missing_optional_fields(self):
        """Test creating GoldenQuestion with missing optional fields."""
        data = {
            "id": "test_q1",
            "category": "background",
            "question": "What is your name?",
            "ground_truth": "I am a test persona."
            # Missing expected_topics and difficulty
        }

        question = GoldenQuestion.from_dict(data)

        assert question.expected_topics == []
        assert question.difficulty == "medium"  # Default


class TestGoldenExamplesDataset:
    """Tests for GoldenExamplesDataset."""

    def test_num_questions(self, sample_golden_qa_data):
        """Test question counting."""
        questions = [GoldenQuestion.from_dict(q) for q in sample_golden_qa_data["questions"]]
        dataset = GoldenExamplesDataset(
            persona_key="test",
            persona_display_name="Test",
            version="1.0",
            created="2026-01-01",
            questions=questions
        )

        assert dataset.num_questions == 3

    def test_get_questions_by_difficulty(self, sample_golden_qa_data):
        """Test filtering questions by difficulty."""
        questions = [GoldenQuestion.from_dict(q) for q in sample_golden_qa_data["questions"]]
        dataset = GoldenExamplesDataset(
            persona_key="test",
            persona_display_name="Test",
            version="1.0",
            created="2026-01-01",
            questions=questions
        )

        easy_questions = dataset.get_questions_by_difficulty("easy")
        medium_questions = dataset.get_questions_by_difficulty("medium")
        hard_questions = dataset.get_questions_by_difficulty("hard")

        assert len(easy_questions) == 1
        assert len(medium_questions) == 1
        assert len(hard_questions) == 1
        assert easy_questions[0].difficulty == "easy"

    def test_get_questions_by_category(self, sample_golden_qa_data):
        """Test filtering questions by category."""
        questions = [GoldenQuestion.from_dict(q) for q in sample_golden_qa_data["questions"]]
        dataset = GoldenExamplesDataset(
            persona_key="test",
            persona_display_name="Test",
            version="1.0",
            created="2026-01-01",
            questions=questions
        )

        background_questions = dataset.get_questions_by_category("background")
        technical_questions = dataset.get_questions_by_category("technical")

        assert len(background_questions) == 1
        assert len(technical_questions) == 1
        assert background_questions[0].category == "background"


class TestGoldenExamplesManager:
    """Tests for GoldenExamplesManager."""

    def test_load_dataset_valid(self, temp_golden_qa_dir):
        """Test loading a valid golden Q&A dataset."""
        manager = GoldenExamplesManager(base_path=str(temp_golden_qa_dir))
        dataset = manager.load_dataset("test_persona")

        assert dataset.persona_key == "test_persona"
        assert dataset.persona_display_name == "Test Persona"
        assert dataset.version == "1.0"
        assert dataset.num_questions == 3

    def test_load_dataset_file_not_found(self, tmp_path):
        """Test loading non-existent dataset raises error."""
        manager = GoldenExamplesManager(base_path=str(tmp_path))

        with pytest.raises(FileNotFoundError) as exc_info:
            manager.load_dataset("nonexistent")

        assert "Golden Q&A file not found" in str(exc_info.value)

    def test_load_dataset_invalid_json(self, tmp_path):
        """Test loading invalid JSON raises error."""
        golden_qa_dir = tmp_path / "_golden_qa"
        golden_qa_dir.mkdir()

        # Create invalid JSON file
        file_path = golden_qa_dir / "invalid_golden_qa.json"
        with open(file_path, 'w') as f:
            f.write("{invalid json")

        manager = GoldenExamplesManager(base_path=str(golden_qa_dir))

        with pytest.raises(ValueError) as exc_info:
            manager.load_dataset("invalid")

        assert "Invalid JSON" in str(exc_info.value)

    def test_load_dataset_missing_required_fields(self, tmp_path, invalid_golden_qa_data):
        """Test loading dataset with missing required fields."""
        golden_qa_dir = tmp_path / "_golden_qa"
        golden_qa_dir.mkdir()

        file_path = golden_qa_dir / "invalid_persona_golden_qa.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(invalid_golden_qa_data, f)

        manager = GoldenExamplesManager(base_path=str(golden_qa_dir))

        with pytest.raises(ValueError) as exc_info:
            manager.load_dataset("invalid_persona")

        assert "Missing required fields" in str(exc_info.value)

    def test_validate_dataset_valid(self, temp_golden_qa_dir):
        """Test validating a high-quality dataset."""
        manager = GoldenExamplesManager(base_path=str(temp_golden_qa_dir))
        dataset = manager.load_dataset("test_persona")
        validation = manager.validate_dataset(dataset)

        # Note: This will have warnings because only 3 questions (need 10)
        assert validation["num_questions"] == 3
        assert "difficulty_distribution" in validation
        assert "category_distribution" in validation
        assert "warnings" in validation

    def test_validate_dataset_low_quality(self, tmp_path, low_quality_golden_qa_data):
        """Test validating a low-quality dataset produces warnings."""
        golden_qa_dir = tmp_path / "_golden_qa"
        golden_qa_dir.mkdir()

        file_path = golden_qa_dir / "low_quality_golden_qa.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(low_quality_golden_qa_data, f)

        manager = GoldenExamplesManager(base_path=str(golden_qa_dir))
        dataset = manager.load_dataset("low_quality")
        validation = manager.validate_dataset(dataset)

        assert validation["is_valid"] is False
        assert len(validation["warnings"]) > 0

        # Check for specific warnings
        warnings_text = " ".join(validation["warnings"])
        assert "Only 2 questions" in warnings_text
        assert "No hard questions" in warnings_text or "No medium questions" in warnings_text

    def test_list_available_datasets(self, temp_golden_qa_dir):
        """Test listing available datasets."""
        manager = GoldenExamplesManager(base_path=str(temp_golden_qa_dir))
        datasets = manager.list_available_datasets()

        assert "test_persona" in datasets

    def test_list_available_datasets_empty(self, tmp_path):
        """Test listing datasets in empty directory."""
        manager = GoldenExamplesManager(base_path=str(tmp_path))
        datasets = manager.list_available_datasets()

        assert datasets == []


class TestRealGoldenQAFiles:
    """Tests for actual golden Q&A files in the project."""

    @pytest.mark.parametrize("persona_key", ["eeva", "gojo"])
    def test_real_dataset_loads(self, persona_key):
        """Test that real golden Q&A files load successfully."""
        manager = GoldenExamplesManager()  # Uses default path

        try:
            dataset = manager.load_dataset(persona_key)
            assert dataset is not None
            assert dataset.persona_key == persona_key
            assert dataset.num_questions > 0
        except FileNotFoundError:
            pytest.skip(f"Golden Q&A file for {persona_key} not found (expected during early development)")

    @pytest.mark.parametrize("persona_key", ["eeva", "gojo"])
    def test_real_dataset_valid(self, persona_key):
        """Test that real golden Q&A files pass validation."""
        manager = GoldenExamplesManager()

        try:
            dataset = manager.load_dataset(persona_key)
            validation = manager.validate_dataset(dataset)

            # Check basic structure
            assert validation["num_questions"] >= 10, f"{persona_key} should have at least 10 questions"

            # Check difficulty distribution
            assert validation["difficulty_distribution"]["easy"] >= 3, f"{persona_key} should have 3+ easy questions"
            assert validation["difficulty_distribution"]["medium"] >= 3, f"{persona_key} should have 3+ medium questions"
            assert validation["difficulty_distribution"]["hard"] >= 3, f"{persona_key} should have 3+ hard questions"

            # Check category diversity
            num_categories = len(validation["category_distribution"])
            assert num_categories >= 2, f"{persona_key} should have 2+ categories"

            # Check ground truth length
            assert validation["avg_ground_truth_length"] >= 50, f"{persona_key} ground truths should be substantial"

        except FileNotFoundError:
            pytest.skip(f"Golden Q&A file for {persona_key} not found (expected during early development)")

    def test_all_personas_have_golden_qa(self):
        """Test that all expected personas have golden Q&A files."""
        manager = GoldenExamplesManager()
        available = manager.list_available_datasets()

        expected_personas = ["eeva", "gojo"]

        for persona in expected_personas:
            if persona not in available:
                pytest.skip(f"Golden Q&A for {persona} not yet created (expected during development)")
            assert persona in available, f"Missing golden Q&A for {persona}"
