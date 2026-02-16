"""
Comprehensive test suite for persona prompt optimization validation.

Tests both baseline (current) and optimized prompt systems across:
- Voice consistency
- First-person adherence
- Multi-message format usage
- Response quality
- Persona differentiation
- Token efficiency
"""

from __future__ import annotations

import sys
import json
import time
import re
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.coordinator.prompt_builder import build_system_prompt
from src.coordinator.persona_loader import get_persona_card
from src.coordinator.llm_client import LC_OllamaClient
from src.coordinator.config import get_ollama_base, get_persona_model


@dataclass
class TestCase:
    """A single test case with prompt and expected characteristics."""
    prompt: str
    test_type: str
    expected_characteristics: List[str]
    persona: str


@dataclass
class TestResult:
    """Results from a single test."""
    test_case: TestCase
    response: str
    passed_checks: List[str]
    failed_checks: List[str]
    metrics: Dict[str, Any]
    score: float


@dataclass
class ComparisonReport:
    """Full comparison between baseline and optimized systems."""
    baseline_results: List[TestResult]
    optimized_results: List[TestResult]
    baseline_metrics: Dict[str, float]
    optimized_metrics: Dict[str, float]
    recommendation: str
    quality_preserved: bool


class PromptOptimizationTester:
    """Test harness for prompt optimization validation."""

    def __init__(self):
        self.llm = LC_OllamaClient(
            base=get_ollama_base(),
            model=get_persona_model(),
            temperature=0.7  # Fixed temperature for consistency
        )

        # Test cases covering different scenarios
        self.test_cases = self._create_test_cases()

    def _create_test_cases(self) -> List[TestCase]:
        """Create comprehensive test cases."""
        return [
            # === First-Person Adherence Tests ===
            TestCase(
                prompt="Tell me about yourself",
                test_type="first_person",
                expected_characteristics=["first_person", "no_third_person", "authentic_voice"],
                persona="eeva"
            ),
            TestCase(
                prompt="What's your background and expertise?",
                test_type="first_person",
                expected_characteristics=["first_person", "no_third_person"],
                persona="eeva"
            ),
            TestCase(
                prompt="Who is Eeva?",
                test_type="first_person_trick",
                expected_characteristics=["first_person", "no_third_person", "stays_in_character"],
                persona="eeva"
            ),
            TestCase(
                prompt="Describe Eeva to me",
                test_type="first_person_trick",
                expected_characteristics=["first_person", "no_third_person", "stays_in_character"],
                persona="eeva"
            ),

            # === Multi-Message Format Tests ===
            TestCase(
                prompt="What's Bitcoin?",
                test_type="multi_message",
                expected_characteristics=["uses_msg_tags", "multiple_messages", "natural_flow"],
                persona="eeva"
            ),
            TestCase(
                prompt="I'm thinking about buying some crypto",
                test_type="multi_message",
                expected_characteristics=["uses_msg_tags", "asks_questions", "shows_curiosity"],
                persona="eeva"
            ),
            TestCase(
                prompt="Had a rough day",
                test_type="multi_message",
                expected_characteristics=["uses_msg_tags", "shows_empathy", "asks_followup"],
                persona="eeva"
            ),

            # === Voice Consistency Tests ===
            TestCase(
                prompt="You're so smart!",
                test_type="voice_consistency",
                expected_characteristics=["deflects_praise", "shows_imposter_syndrome", "uses_humor"],
                persona="eeva"
            ),
            TestCase(
                prompt="Explain proof-of-work mining",
                test_type="voice_consistency",
                expected_characteristics=["uses_metaphors", "technical_accuracy", "friendly_tone"],
                persona="eeva"
            ),
            TestCase(
                prompt="I don't understand what you just said",
                test_type="voice_consistency",
                expected_characteristics=["patient", "asks_clarifying_questions", "no_defensiveness"],
                persona="eeva"
            ),

            # === Psychological Profile Tests ===
            TestCase(
                prompt="What are you good at?",
                test_type="psychological",
                expected_characteristics=["shows_vulnerability", "downplays_expertise", "authentic"],
                persona="eeva"
            ),
            TestCase(
                prompt="What's the weather like?",
                test_type="psychological",
                expected_characteristics=["awkward_with_smalltalk", "redirects_to_tech", "self_aware"],
                persona="eeva"
            ),

            # === Persona Differentiation Tests (Eeva vs Frieren) ===
            TestCase(
                prompt="Tell me about yourself",
                test_type="differentiation",
                expected_characteristics=["distinct_from_frieren", "eeva_specific_traits"],
                persona="eeva"
            ),
            TestCase(
                prompt="Tell me about yourself",
                test_type="differentiation",
                expected_characteristics=["distinct_from_eeva", "frieren_specific_traits"],
                persona="frieren"
            ),

            # === Edge Cases ===
            TestCase(
                prompt="Hi",
                test_type="edge_case",
                expected_characteristics=["brief_response", "welcoming"],
                persona="eeva"
            ),
            TestCase(
                prompt="Thanks",
                test_type="edge_case",
                expected_characteristics=["brief_response", "natural"],
                persona="eeva"
            ),
        ]

    def run_test(self, test_case: TestCase, system_prompt: str) -> TestResult:
        """Run a single test case and evaluate response."""
        # Generate response
        response = self.llm.complete(
            system=system_prompt,
            user_prompt=test_case.prompt
        )

        # Run checks
        passed_checks = []
        failed_checks = []
        metrics = {}

        for characteristic in test_case.expected_characteristics:
            if self._check_characteristic(characteristic, response, test_case):
                passed_checks.append(characteristic)
            else:
                failed_checks.append(characteristic)

        # Calculate metrics
        metrics = self._calculate_metrics(response, test_case)

        # Calculate score
        score = len(passed_checks) / len(test_case.expected_characteristics) if test_case.expected_characteristics else 1.0

        return TestResult(
            test_case=test_case,
            response=response,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            metrics=metrics,
            score=score
        )

    def _check_characteristic(self, characteristic: str, response: str, test_case: TestCase) -> bool:
        """Check if response has expected characteristic."""
        response_lower = response.lower()

        # First-person checks
        if characteristic == "first_person":
            # Should contain first-person pronouns
            first_person_indicators = ["i'm", "i am", "my", "me", "i've", "i have", "i ", " i "]
            return any(indicator in response_lower for indicator in first_person_indicators)

        if characteristic == "no_third_person":
            # Should NOT contain third-person persona references
            persona_name = test_case.persona.lower()
            third_person_patterns = [
                f"{persona_name} is",
                f"{persona_name} has",
                f"{persona_name}'s",
                f"{persona_name} does",
                f"{persona_name} can"
            ]
            return not any(pattern in response_lower for pattern in third_person_patterns)

        if characteristic == "stays_in_character":
            # Should not break the fourth wall
            meta_phrases = ["i'm an ai", "i'm pretending", "as a language model", "i'm simulating"]
            return not any(phrase in response_lower for phrase in meta_phrases)

        # Multi-message checks
        if characteristic == "uses_msg_tags":
            return "<msg>" in response and "</msg>" in response

        if characteristic == "multiple_messages":
            msg_count = response.count("<msg>")
            return msg_count >= 2

        if characteristic == "natural_flow":
            # Messages should be reasonably short (not giant paragraphs in each msg)
            if "<msg>" in response:
                messages = re.findall(r'<msg>(.*?)</msg>', response, re.DOTALL)
                avg_length = sum(len(msg) for msg in messages) / len(messages) if messages else 0
                return avg_length < 300  # Average message under 300 chars
            return True

        # Voice consistency checks
        if characteristic == "deflects_praise":
            deflection_indicators = ["i mean", "just", "anyone", "not really", "i guess"]
            return any(indicator in response_lower for indicator in deflection_indicators)

        if characteristic == "shows_imposter_syndrome":
            imposter_indicators = ["not sure", "probably", "maybe", "i think", "feels like"]
            return any(indicator in response_lower for indicator in imposter_indicators)

        if characteristic == "uses_humor":
            humor_indicators = ["😅", "lol", "haha", "*", "honestly", "😊"]
            return any(indicator in response_lower for indicator in humor_indicators)

        if characteristic == "uses_metaphors":
            # Check for "like" or "think of it as" patterns
            metaphor_indicators = ["like ", "think of it as", "imagine", "it's kind of"]
            return any(indicator in response_lower for indicator in metaphor_indicators)

        if characteristic == "asks_questions":
            return "?" in response

        if characteristic == "shows_curiosity":
            curiosity_indicators = ["what", "how", "why", "are you", "do you"]
            return any(indicator in response_lower for indicator in curiosity_indicators)

        if characteristic == "shows_empathy":
            empathy_indicators = ["sorry", "that sucks", "i hear you", "understand", "feel"]
            return any(indicator in response_lower for indicator in empathy_indicators)

        if characteristic == "asks_followup":
            return "?" in response

        if characteristic == "patient":
            patience_indicators = ["let me", "okay", "sure", "no problem", "that's okay"]
            return any(indicator in response_lower for indicator in patience_indicators)

        if characteristic == "asks_clarifying_questions":
            return "?" in response and any(word in response_lower for word in ["which", "what part", "where", "clarify"])

        # Psychological profile checks
        if characteristic == "shows_vulnerability":
            vulnerability_indicators = ["i struggle", "i'm not", "honestly", "to be fair", "i worry"]
            return any(indicator in response_lower for indicator in vulnerability_indicators)

        if characteristic == "downplays_expertise":
            downplay_indicators = ["just", "only", "i guess", "not really", "anyone could"]
            return any(indicator in response_lower for indicator in downplay_indicators)

        if characteristic == "awkward_with_smalltalk":
            awkward_indicators = ["uh", "um", "honestly", "not really my", "more of a"]
            return any(indicator in response_lower for indicator in awkward_indicators)

        if characteristic == "redirects_to_tech":
            # Should mention tech/crypto in some way
            tech_keywords = ["tech", "crypto", "code", "bitcoin", "data", "algorithm"]
            return any(keyword in response_lower for keyword in tech_keywords)

        if characteristic == "self_aware":
            self_aware_indicators = ["i know", "i realize", "i'm aware", "to be honest"]
            return any(indicator in response_lower for indicator in self_aware_indicators)

        # Persona differentiation
        if characteristic == "eeva_specific_traits":
            eeva_traits = ["crypto", "bitcoin", "physics", "coffee", "diagrams", "notebook"]
            return any(trait in response_lower for trait in eeva_traits)

        if characteristic == "frieren_specific_traits":
            frieren_traits = ["magic", "elf", "himmel", "spell", "journey"]
            return any(trait in response_lower for trait in frieren_traits)

        if characteristic == "distinct_from_eeva":
            # Should not have Eeva-specific patterns
            eeva_traits = ["crypto", "bitcoin", "2 btc", "seed phrase", "coffee"]
            return not any(trait in response_lower for trait in eeva_traits)

        if characteristic == "distinct_from_frieren":
            # Should not have Frieren-specific patterns
            frieren_traits = ["magic", "elf", "himmel", "spell", "journey", "mage"]
            return not any(trait in response_lower for trait in frieren_traits)

        # Edge cases
        if characteristic == "brief_response":
            return len(response) < 200

        if characteristic == "welcoming":
            welcoming_indicators = ["hi", "hey", "hello", "welcome", "!"]
            return any(indicator in response_lower for indicator in welcoming_indicators)

        if characteristic == "natural":
            return len(response) > 0

        if characteristic == "technical_accuracy":
            # Basic check - not spouting nonsense
            return len(response) > 20 and not any(word in response_lower for word in ["sdkfj", "asdf", "###"])

        if characteristic == "friendly_tone":
            friendly_indicators = ["!", "😊", "let me", "sure", "great", "cool"]
            return any(indicator in response for indicator in friendly_indicators)

        if characteristic == "authentic_voice":
            # Not generic corporate speak
            generic_phrases = ["i'm here to help", "how may i assist", "i'd be happy to"]
            return not any(phrase in response_lower for phrase in generic_phrases)

        if characteristic == "no_defensiveness":
            defensive_indicators = ["actually", "but i", "you said", "i told you"]
            return not any(indicator in response_lower for indicator in defensive_indicators)

        # Default pass
        return True

    def _calculate_metrics(self, response: str, test_case: TestCase) -> Dict[str, Any]:
        """Calculate quantitative metrics for response."""
        metrics = {}

        # Length metrics
        metrics["response_length"] = len(response)
        metrics["response_tokens"] = len(response) // 4  # Rough estimate

        # Multi-message metrics
        metrics["msg_tag_count"] = response.count("<msg>")
        metrics["uses_multi_message"] = "<msg>" in response

        # First-person metrics
        first_person_count = sum(response.lower().count(word) for word in ["i'm", "i am", "my", "me"])
        persona_name = test_case.persona.lower()
        third_person_count = sum(response.lower().count(f"{persona_name} {word}") for word in ["is", "has", "does", "can"])
        metrics["first_person_count"] = first_person_count
        metrics["third_person_count"] = third_person_count
        metrics["first_person_ratio"] = first_person_count / max(first_person_count + third_person_count, 1)

        # Question metrics
        metrics["asks_questions"] = "?" in response
        metrics["question_count"] = response.count("?")

        # Emoji usage
        emoji_pattern = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002702-\U000027B0\U000024C2-\U0001F251]')
        metrics["emoji_count"] = len(emoji_pattern.findall(response))

        return metrics

    def run_test_suite(self, prompt_version: str) -> List[TestResult]:
        """Run full test suite with given prompt version."""
        print(f"\n{'='*60}")
        print(f"Running {prompt_version} test suite...")
        print(f"{'='*60}\n")

        results = []

        for i, test_case in enumerate(self.test_cases, 1):
            print(f"[{i}/{len(self.test_cases)}] Testing: {test_case.test_type} - {test_case.prompt[:50]}...")

            # Build system prompt
            system_prompt = build_system_prompt(test_case.persona)

            # Run test
            result = self.run_test(test_case, system_prompt)
            results.append(result)

            # Print result
            status = "[PASS]" if result.score >= 0.8 else "[PARTIAL]" if result.score >= 0.5 else "[FAIL]"
            print(f"  {status} ({result.score:.1%}) - {len(result.passed_checks)}/{len(test_case.expected_characteristics)} checks passed")

            if result.failed_checks:
                print(f"  Failed: {', '.join(result.failed_checks)}")

            # Small delay to avoid overwhelming Ollama
            time.sleep(0.5)

        return results

    def calculate_aggregate_metrics(self, results: List[TestResult]) -> Dict[str, float]:
        """Calculate aggregate metrics across all test results."""
        if not results:
            return {}

        metrics = {
            "overall_score": sum(r.score for r in results) / len(results),
            "pass_rate": sum(1 for r in results if r.score >= 0.8) / len(results),
            "avg_response_length": sum(r.metrics["response_length"] for r in results) / len(results),
            "avg_response_tokens": sum(r.metrics["response_tokens"] for r in results) / len(results),
            "multi_message_usage": sum(1 for r in results if r.metrics["uses_multi_message"]) / len(results),
            "avg_msg_count": sum(r.metrics["msg_tag_count"] for r in results) / len(results),
            "first_person_adherence": sum(r.metrics["first_person_ratio"] for r in results) / len(results),
            "question_rate": sum(1 for r in results if r.metrics["asks_questions"]) / len(results),
            "avg_emoji_count": sum(r.metrics["emoji_count"] for r in results) / len(results),
        }

        # Test type breakdown
        test_types = set(r.test_case.test_type for r in results)
        for test_type in test_types:
            type_results = [r for r in results if r.test_case.test_type == test_type]
            metrics[f"{test_type}_score"] = sum(r.score for r in type_results) / len(type_results)

        return metrics

    def compare_versions(self, baseline_results: List[TestResult], optimized_results: List[TestResult]) -> ComparisonReport:
        """Compare baseline and optimized versions."""
        baseline_metrics = self.calculate_aggregate_metrics(baseline_results)
        optimized_metrics = self.calculate_aggregate_metrics(optimized_results)

        # Quality thresholds
        CRITICAL_METRICS = ["overall_score", "first_person_adherence", "first_person_score", "voice_consistency_score"]
        IMPORTANT_METRICS = ["multi_message_usage", "multi_message_score", "psychological_score"]

        # Check if quality is preserved
        quality_preserved = True
        issues = []

        for metric in CRITICAL_METRICS:
            if metric in baseline_metrics and metric in optimized_metrics:
                baseline_val = baseline_metrics[metric]
                optimized_val = optimized_metrics[metric]
                delta = optimized_val - baseline_val

                # Critical metrics must not degrade by more than 5%
                if delta < -0.05:
                    quality_preserved = False
                    issues.append(f"Critical metric '{metric}' degraded: {baseline_val:.1%} → {optimized_val:.1%} ({delta:+.1%})")

        for metric in IMPORTANT_METRICS:
            if metric in baseline_metrics and metric in optimized_metrics:
                baseline_val = baseline_metrics[metric]
                optimized_val = optimized_metrics[metric]
                delta = optimized_val - baseline_val

                # Important metrics should not degrade by more than 10%
                if delta < -0.10:
                    issues.append(f"Important metric '{metric}' degraded: {baseline_val:.1%} → {optimized_val:.1%} ({delta:+.1%})")

        # Make recommendation
        if quality_preserved and not issues:
            recommendation = "[APPROVE] Optimized version maintains quality. Safe to deploy."
        elif quality_preserved and issues:
            recommendation = f"[CONDITIONAL] Quality preserved but with concerns:\n" + "\n".join(f"  - {issue}" for issue in issues)
        else:
            recommendation = f"[REJECT] Quality degradation detected:\n" + "\n".join(f"  - {issue}" for issue in issues)

        return ComparisonReport(
            baseline_results=baseline_results,
            optimized_results=optimized_results,
            baseline_metrics=baseline_metrics,
            optimized_metrics=optimized_metrics,
            recommendation=recommendation,
            quality_preserved=quality_preserved
        )

    def print_report(self, report: ComparisonReport):
        """Print detailed comparison report."""
        print("\n" + "="*80)
        print("OPTIMIZATION COMPARISON REPORT")
        print("="*80)

        print("\n### AGGREGATE METRICS ###\n")
        print(f"{'Metric':<35} {'Baseline':>12} {'Optimized':>12} {'Delta':>10}")
        print("-" * 80)

        # Sort metrics for consistent display
        all_metrics = sorted(set(report.baseline_metrics.keys()) | set(report.optimized_metrics.keys()))

        for metric in all_metrics:
            baseline_val = report.baseline_metrics.get(metric, 0)
            optimized_val = report.optimized_metrics.get(metric, 0)
            delta = optimized_val - baseline_val

            # Format based on metric type
            if "score" in metric or "rate" in metric or "adherence" in metric or "usage" in metric:
                baseline_str = f"{baseline_val:.1%}"
                optimized_str = f"{optimized_val:.1%}"
                delta_str = f"{delta:+.1%}"
            else:
                baseline_str = f"{baseline_val:.1f}"
                optimized_str = f"{optimized_val:.1f}"
                delta_str = f"{delta:+.1f}"

            # Color code delta
            if delta > 0.01:
                delta_display = f"[+] {delta_str}"
            elif delta < -0.01:
                delta_display = f"[-] {delta_str}"
            else:
                delta_display = f"[=] {delta_str}"

            print(f"{metric:<35} {baseline_str:>12} {optimized_str:>12} {delta_display:>12}")

        print("\n### TEST BREAKDOWN ###\n")

        # Group by test type
        test_types = sorted(set(r.test_case.test_type for r in report.baseline_results))

        for test_type in test_types:
            baseline_type = [r for r in report.baseline_results if r.test_case.test_type == test_type]
            optimized_type = [r for r in report.optimized_results if r.test_case.test_type == test_type]

            baseline_avg = sum(r.score for r in baseline_type) / len(baseline_type)
            optimized_avg = sum(r.score for r in optimized_type) / len(optimized_type)
            delta = optimized_avg - baseline_avg

            status = "[PASS]" if delta >= -0.05 else "[WARN]" if delta >= -0.10 else "[FAIL]"
            print(f"{status} {test_type:<25} Baseline: {baseline_avg:.1%}  Optimized: {optimized_avg:.1%}  Delta: {delta:+.1%}")

        print("\n### RECOMMENDATION ###\n")
        print(report.recommendation)
        print("\n" + "="*80 + "\n")

    def save_detailed_report(self, report: ComparisonReport, filepath: str):
        """Save detailed report to JSON file."""
        report_dict = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "quality_preserved": report.quality_preserved,
                "recommendation": report.recommendation,
            },
            "baseline_metrics": report.baseline_metrics,
            "optimized_metrics": report.optimized_metrics,
            "baseline_results": [
                {
                    "test_type": r.test_case.test_type,
                    "prompt": r.test_case.prompt,
                    "persona": r.test_case.persona,
                    "score": r.score,
                    "passed_checks": r.passed_checks,
                    "failed_checks": r.failed_checks,
                    "metrics": r.metrics,
                    "response_preview": r.response[:200] + "..." if len(r.response) > 200 else r.response
                }
                for r in report.baseline_results
            ],
            "optimized_results": [
                {
                    "test_type": r.test_case.test_type,
                    "prompt": r.test_case.prompt,
                    "persona": r.test_case.persona,
                    "score": r.score,
                    "passed_checks": r.passed_checks,
                    "failed_checks": r.failed_checks,
                    "metrics": r.metrics,
                    "response_preview": r.response[:200] + "..." if len(r.response) > 200 else r.response
                }
                for r in report.optimized_results
            ]
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)

        print(f"[SAVED] Detailed report saved to: {filepath}")


def main():
    """Run comparison tests."""
    print("="*80)
    print("PERSONA PROMPT OPTIMIZATION VALIDATION SUITE")
    print("="*80)
    print("\nThis test suite will compare baseline and optimized prompt systems.")
    print("Testing voice consistency, first-person adherence, and response quality.")
    print("\n[NOTE] This will take several minutes as we test multiple scenarios.")
    print("\nPress Ctrl+C to cancel, or wait 5 seconds to begin...")

    try:
        time.sleep(5)
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        return

    tester = PromptOptimizationTester()

    # Run baseline tests
    print("\n" + "="*80)
    print("PHASE 1: BASELINE TESTING (Current System)")
    print("="*80)
    baseline_results = tester.run_test_suite("BASELINE")

    # Switch to optimized version
    print("\n" + "="*80)
    print("PHASE 2: OPTIMIZED TESTING")
    print("="*80)
    print("\nSwitching to optimized prompt builder...")

    # Import optimized version (we'll create this next)
    import src.coordinator.prompt_builder_optimized as optimized_builder

    # Temporarily replace the build function
    original_build = src.coordinator.prompt_builder.build_system_prompt
    src.coordinator.prompt_builder.build_system_prompt = optimized_builder.build_system_prompt

    try:
        optimized_results = tester.run_test_suite("OPTIMIZED")
    finally:
        # Restore original
        src.coordinator.prompt_builder.build_system_prompt = original_build

    # Compare results
    print("\n" + "="*80)
    print("PHASE 3: ANALYSIS & COMPARISON")
    print("="*80)

    report = tester.compare_versions(baseline_results, optimized_results)
    tester.print_report(report)

    # Save detailed report
    report_dir = Path(__file__).parent / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "PROMPT_OPTIMIZATION_TEST_REPORT.json"
    tester.save_detailed_report(report, str(report_path))

    print("\n### NEXT STEPS ###\n")
    if report.quality_preserved:
        print("[PASS] Quality preserved. You can safely apply the optimizations.")
        print("   Run: python tests/apply_optimization.py")
    else:
        print("[FAIL] Quality degradation detected. Optimizations should not be applied.")
        print("   Reverting to baseline system (no changes needed).")

    return report


if __name__ == "__main__":
    main()
