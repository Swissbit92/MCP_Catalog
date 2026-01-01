"""Validate all golden Q&A datasets.

This script validates the golden Q&A examples for Eeva, Frieren, and Gojo,
ensuring they meet quality standards for RAGAS evaluation.
"""

from src.coordinator.evaluation import GoldenExamplesManager

def main():
    """Validate all golden Q&A datasets."""
    manager = GoldenExamplesManager()

    personas = ["eeva", "frieren", "gojo"]

    print("=" * 80)
    print("GOLDEN Q&A VALIDATION REPORT")
    print("=" * 80)
    print()

    all_valid = True

    for persona_key in personas:
        print(f"[*] Validating {persona_key}...")
        print("-" * 80)

        try:
            # Load dataset
            dataset = manager.load_dataset(persona_key)
            print(f"[OK] Loaded: {dataset.num_questions} questions")
            print(f"     Display Name: {dataset.persona_display_name}")
            print(f"     Version: {dataset.version}")
            print(f"     Created: {dataset.created}")

            # Validate dataset
            validation = manager.validate_dataset(dataset)

            print(f"\n[STATS] Statistics:")
            print(f"     Total Questions: {validation['num_questions']}")
            print(f"     Difficulty Distribution:")
            for difficulty, count in validation['difficulty_distribution'].items():
                print(f"        {difficulty.capitalize()}: {count}")
            print(f"     Category Distribution:")
            for category, count in validation['category_distribution'].items():
                print(f"        {category.capitalize()}: {count}")
            print(f"     Avg Ground Truth Length: {validation['avg_ground_truth_length']} chars")

            if validation['is_valid']:
                print(f"\n[OK] VALID: No warnings")
            else:
                print(f"\n[WARN] WARNINGS ({len(validation['warnings'])}):")
                for warning in validation['warnings']:
                    print(f"        - {warning}")
                all_valid = False

        except Exception as e:
            print(f"[ERROR] {e}")
            all_valid = False

        print()

    print("=" * 80)
    if all_valid:
        print("[OK] ALL DATASETS VALID!")
    else:
        print("[WARN] SOME DATASETS HAVE WARNINGS (review above)")
    print("=" * 80)

if __name__ == "__main__":
    main()
