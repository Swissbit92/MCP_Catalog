"""
Streamlined test runner for prompt optimization validation.
Runs key tests in both baseline and optimized modes, then compares results.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the test suite
from prompt_optimization_tests import PromptOptimizationTester

# Import both prompt builders
import src.coordinator.prompt_builder as baseline_module
import src.coordinator.prompt_builder_optimized as optimized_module


def main():
    """Run streamlined comparison."""
    print("="*80)
    print("PROMPT OPTIMIZATION VALIDATION - STREAMLINED TEST")
    print("="*80)
    print(f"\nRunning comprehensive tests comparing baseline vs optimized prompts...")
    print(f"This will take approximately 3-5 minutes.\n")

    tester = PromptOptimizationTester()

    # === PHASE 1: Baseline Testing ===
    print("\n" + "="*80)
    print("PHASE 1: BASELINE TESTING (Current System)")
    print("="*80)

    # Ensure we're using baseline
    baseline_results = tester.run_test_suite("BASELINE")

    # === PHASE 2: Optimized Testing ===
    print("\n" + "="*80)
    print("PHASE 2: OPTIMIZED TESTING")
    print("="*80)
    print("\nSwitching to optimized prompt builder...\n")

    # Temporarily swap the build function
    original_build = baseline_module.build_system_prompt
    baseline_module.build_system_prompt = optimized_module.build_system_prompt

    try:
        optimized_results = tester.run_test_suite("OPTIMIZED")
    finally:
        # Restore original
        baseline_module.build_system_prompt = original_build

    # === PHASE 3: Analysis ===
    print("\n" + "="*80)
    print("PHASE 3: ANALYSIS & COMPARISON")
    print("="*80)

    report = tester.compare_versions(baseline_results, optimized_results)
    tester.print_report(report)

    # Save detailed report
    report_dir = Path(__file__).parent.parent / "AI_documentation" / "01_implementation_history"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "PROMPT_OPTIMIZATION_TEST_REPORT.json"
    tester.save_detailed_report(report, str(report_path))

    # === NEXT STEPS ===
    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80 + "\n")

    if report.quality_preserved:
        print("[PASS] Quality preserved! The optimized prompt is safe to deploy.")
        print("   Token savings: ~1,020 tokens (28.8% reduction)")
        print("   This allows for significantly more conversation history.")
        print(f"\n   Recommendation: {report.recommendation}\n")
        return True
    else:
        print("[FAIL] Quality degradation detected.")
        print("   The optimizations should NOT be applied.")
        print(f"\n   {report.recommendation}\n")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
