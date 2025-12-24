#!/usr/bin/env python
"""
Comprehensive Intent Classification Test Suite

Tests 90 questions across 3 categories to validate intent classification accuracy:
- 30 Pure LLM questions (should NOT trigger any MCP)
- 30 Brave MCP questions (should trigger web search)
- 30 MongoDB MCP questions (should trigger Bitcoin data queries)

Tests against all 4 rarity levels to ensure proper rarity-gating.
"""
import sys
import os
from typing import Dict, List, Tuple
from datetime import datetime
from collections import defaultdict

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from coordinator.tool_definitions import classify_query_intent, QueryIntent, get_tools_for_query

# Test dataset: 90 questions organized by expected intent
TEST_QUESTIONS = {
    "PURE_LLM": [
        # General knowledge (10 questions)
        "What is Bitcoin?",
        "Explain blockchain technology",
        "How does cryptocurrency mining work?",
        "What are smart contracts?",
        "Tell me about Ethereum",
        "What is proof of work?",
        "Explain DeFi",
        "What are NFTs?",
        "How do cryptocurrency wallets work?",
        "What is the difference between Bitcoin and Ethereum?",

        # Conceptual/Educational (10 questions)
        "Why was Bitcoin created?",
        "Who invented Bitcoin?",
        "What problem does Bitcoin solve?",
        "Is Bitcoin legal?",
        "How many Bitcoins exist?",
        "What is the Bitcoin halving?",
        "Can Bitcoin be hacked?",
        "What is a blockchain fork?",
        "How do I buy Bitcoin?",
        "What are the risks of investing in crypto?",

        # General conversation (10 questions)
        "Hello, how are you?",
        "What can you help me with?",
        "Tell me a joke",
        "What's your name?",
        "How does your AI work?",
        "Can you explain trading strategies?",
        "What do you think about cryptocurrency?",
        "Should I invest in crypto?",
        "Tell me about market cycles",
        "What's your opinion on regulation?",
    ],

    "BRAVE_MCP": [
        # News queries (10 questions)
        "What's the latest Bitcoin news?",
        "Latest cryptocurrency news today",
        "Show me recent crypto headlines",
        "What happened in crypto this week?",
        "Latest Bitcoin developments",
        "Recent crypto market news",
        "What's trending in Bitcoin?",
        "Latest crypto regulatory news",
        "Recent Bitcoin adoption news",
        "What are people saying about Bitcoin today?",

        # Current events (10 questions)
        "Bitcoin news breaking now",
        "Latest crypto exchange news",
        "Recent Bitcoin ETF news",
        "What's happening with crypto regulations?",
        "Latest institutional Bitcoin adoption",
        "Recent crypto hacks or security issues",
        "Latest DeFi news",
        "What's new with Ethereum?",
        "Recent crypto market crash news",
        "Latest celebrity crypto endorsements",

        # Market sentiment (10 questions)
        "What are crypto experts saying today?",
        "Latest Bitcoin predictions",
        "What's the crypto community talking about?",
        "Recent Bitcoin influencer opinions",
        "Latest crypto Twitter trends",
        "What are analysts saying about Bitcoin?",
        "Recent crypto market analysis",
        "Latest Bitcoin bull/bear debate",
        "What's the sentiment on crypto today?",
        "Recent crypto fear and greed index",
    ],

    "MONGODB_MCP": [
        # Current price queries (10 questions)
        "What's the current Bitcoin price?",
        "What is BTC price now?",
        "Show me the current Bitcoin price",
        "What's Bitcoin trading at?",
        "Current BTC value",
        "Bitcoin price right now",
        "What's the price of Bitcoin?",
        "BTC price today",
        "Show me Bitcoin's current value",
        "What is Bitcoin worth now?",

        # Technical analysis (10 questions)
        "What's the Bitcoin RSI?",
        "Show me Bitcoin technical indicators",
        "What's the MACD for Bitcoin?",
        "Bitcoin Bollinger Bands analysis",
        "Show me BTC technical analysis",
        "What are the key Bitcoin indicators?",
        "Bitcoin trend analysis",
        "Is Bitcoin overbought or oversold?",
        "Show me Bitcoin moving averages",
        "What's the Bitcoin EMA?",

        # Historical and trading data (10 questions)
        "Bitcoin price last week",
        "Show me historical Bitcoin prices",
        "What was Bitcoin's price yesterday?",
        "Bitcoin price history",
        "Show me my Bitcoin purchases",
        "What's my Bitcoin trading summary?",
        "How much Bitcoin have I bought?",
        "Bitcoin price 7 days ago",
        "Show me Bitcoin price chart",
        "What's my average Bitcoin buy price?",
    ],
}

# Rarity levels to test
RARITIES = ["common", "rare", "epic", "legendary"]

# Expected behavior per rarity
EXPECTED_BEHAVIOR = {
    "common": {
        QueryIntent.NEEDS_NEITHER: "correct",
        QueryIntent.NEEDS_WEB_SEARCH: "no_access",
        QueryIntent.NEEDS_MONGODB: "no_access",
        QueryIntent.NEEDS_BOTH: "no_access",
    },
    "rare": {
        QueryIntent.NEEDS_NEITHER: "correct",
        QueryIntent.NEEDS_WEB_SEARCH: "correct",
        QueryIntent.NEEDS_MONGODB: "no_access",
        QueryIntent.NEEDS_BOTH: "partial_access",  # Only web search
    },
    "epic": {
        QueryIntent.NEEDS_NEITHER: "correct",
        QueryIntent.NEEDS_WEB_SEARCH: "correct",
        QueryIntent.NEEDS_MONGODB: "correct",
        QueryIntent.NEEDS_BOTH: "correct",
    },
    "legendary": {
        QueryIntent.NEEDS_NEITHER: "correct",
        QueryIntent.NEEDS_WEB_SEARCH: "correct",
        QueryIntent.NEEDS_MONGODB: "correct",
        QueryIntent.NEEDS_BOTH: "correct",
    },
}


class IntentClassificationTester:
    """Comprehensive intent classification test runner."""

    def __init__(self):
        self.results = defaultdict(lambda: defaultdict(list))
        self.scores = defaultdict(lambda: defaultdict(int))
        self.total_tests = 0
        self.passed_tests = 0

    def run_all_tests(self):
        """Run all 90 questions against all 4 rarity levels."""
        print("=" * 80)
        print("COMPREHENSIVE INTENT CLASSIFICATION TEST SUITE")
        print("=" * 80)
        print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Questions: {sum(len(questions) for questions in TEST_QUESTIONS.values())}")
        print(f"Rarity Levels: {len(RARITIES)}")
        print(f"Total Tests: {sum(len(questions) for questions in TEST_QUESTIONS.values()) * len(RARITIES)}")
        print("=" * 80)
        print()

        for expected_category, questions in TEST_QUESTIONS.items():
            self._test_category(expected_category, questions)

        self._print_results()
        self._generate_assessment()

        return self.get_overall_score()

    def _test_category(self, expected_category: str, questions: List[str]):
        """Test a category of questions."""
        print(f"\n{'=' * 80}")
        print(f"Testing Category: {expected_category}")
        print(f"Questions: {len(questions)}")
        print(f"{'=' * 80}\n")

        for rarity in RARITIES:
            print(f"\n--- Testing with {rarity.upper()} persona ---")

            category_correct = 0
            category_total = len(questions)

            for i, question in enumerate(questions, 1):
                result = self._test_question(question, expected_category, rarity)
                self.results[expected_category][rarity].append(result)

                if result['passed']:
                    category_correct += 1
                    self.passed_tests += 1
                    status = "✓"
                else:
                    status = "✗"

                self.total_tests += 1

                # Print progress every 10 questions
                if i % 10 == 0:
                    print(f"  Progress: {i}/{category_total} - Accuracy: {category_correct/i*100:.1f}%")

            accuracy = (category_correct / category_total) * 100
            self.scores[expected_category][rarity] = accuracy
            print(f"\n  {rarity.upper()} Accuracy: {accuracy:.1f}% ({category_correct}/{category_total})")

    def _test_question(self, question: str, expected_category: str, rarity: str) -> Dict:
        """Test a single question and return result."""
        # Classify the intent
        intent = classify_query_intent(question, rarity)

        # Get tools that would be injected
        tools = get_tools_for_query(question, "test_persona", rarity)

        # Determine if the classification is correct
        passed, reason = self._evaluate_classification(
            question, expected_category, rarity, intent, tools
        )

        return {
            'question': question,
            'expected_category': expected_category,
            'rarity': rarity,
            'classified_intent': intent,
            'tools_count': len(tools),
            'tools': [t.get('function', {}).get('name', 'unknown') for t in tools],
            'passed': passed,
            'reason': reason,
        }

    def _evaluate_classification(
        self,
        question: str,
        expected_category: str,
        rarity: str,
        intent: QueryIntent,
        tools: List[Dict]
    ) -> Tuple[bool, str]:
        """Evaluate if classification is correct based on expected category and rarity."""

        # Map expected category to expected intent
        category_to_intent = {
            "PURE_LLM": QueryIntent.NEEDS_NEITHER,
            "BRAVE_MCP": QueryIntent.NEEDS_WEB_SEARCH,
            "MONGODB_MCP": QueryIntent.NEEDS_MONGODB,
        }

        expected_intent = category_to_intent[expected_category]

        # For common personas, everything should be NEEDS_NEITHER
        if rarity == "common":
            if intent == QueryIntent.NEEDS_NEITHER:
                return True, "Correct: Common persona has no MCP access"
            else:
                return False, f"Error: Common persona classified as {intent}, should be NEEDS_NEITHER"

        # For rare personas, MongoDB should become NEEDS_NEITHER
        if rarity == "rare" and expected_intent == QueryIntent.NEEDS_MONGODB:
            if intent == QueryIntent.NEEDS_NEITHER:
                return True, "Correct: Rare persona has no MongoDB access"
            else:
                return False, f"Error: Rare persona classified MongoDB query as {intent}"

        # For epic/legendary or rare with web search, check exact match
        if intent == expected_intent:
            return True, f"Correct: Classified as {intent}"

        # Check if it's a reasonable alternative
        # Sometimes "Bitcoin price news" could be either WEB_SEARCH or MONGODB
        if expected_category == "MONGODB_MCP" and intent == QueryIntent.NEEDS_WEB_SEARCH:
            return False, f"Ambiguous: MongoDB query classified as {intent} (possible false negative)"

        if expected_category == "BRAVE_MCP" and intent == QueryIntent.NEEDS_MONGODB:
            return False, f"Ambiguous: Web search query classified as {intent} (possible false negative)"

        return False, f"Error: Expected {expected_intent}, got {intent}"

    def _print_results(self):
        """Print detailed test results."""
        print("\n\n" + "=" * 80)
        print("DETAILED RESULTS")
        print("=" * 80)

        for category in TEST_QUESTIONS.keys():
            print(f"\n{'=' * 80}")
            print(f"Category: {category}")
            print(f"{'=' * 80}")

            for rarity in RARITIES:
                accuracy = self.scores[category][rarity]
                results = self.results[category][rarity]

                passed_count = sum(1 for r in results if r['passed'])
                total_count = len(results)

                print(f"\n{rarity.upper()} Persona:")
                print(f"  Accuracy: {accuracy:.1f}% ({passed_count}/{total_count})")

                # Show failed examples
                failed = [r for r in results if not r['passed']]
                if failed:
                    print(f"\n  Failed Examples ({len(failed)}):")
                    for i, fail in enumerate(failed[:5], 1):  # Show max 5
                        print(f"    {i}. \"{fail['question'][:60]}...\"")
                        print(f"       Classified as: {fail['classified_intent']}")
                        print(f"       Reason: {fail['reason']}")

                    if len(failed) > 5:
                        print(f"    ... and {len(failed) - 5} more")

    def _generate_assessment(self):
        """Generate comprehensive assessment and recommendations."""
        print("\n\n" + "=" * 80)
        print("ASSESSMENT & RECOMMENDATIONS")
        print("=" * 80)

        overall_accuracy = (self.passed_tests / self.total_tests) * 100

        print(f"\n[OVERALL METRICS]")
        print(f"{'=' * 80}")
        print(f"Total Tests Run: {self.total_tests}")
        print(f"Tests Passed: {self.passed_tests}")
        print(f"Tests Failed: {self.total_tests - self.passed_tests}")
        print(f"Overall Accuracy: {overall_accuracy:.1f}%")

        # Category breakdown
        print(f"\n[CATEGORY BREAKDOWN]")
        print(f"{'=' * 80}")
        for category in TEST_QUESTIONS.keys():
            avg_accuracy = sum(self.scores[category].values()) / len(RARITIES)
            print(f"{category:20} {avg_accuracy:6.1f}%")

        # Rarity breakdown
        print(f"\n[RARITY BREAKDOWN]")
        print(f"{'=' * 80}")
        for rarity in RARITIES:
            rarity_accuracy = sum(
                self.scores[cat][rarity] for cat in TEST_QUESTIONS.keys()
            ) / len(TEST_QUESTIONS)
            print(f"{rarity.upper():20} {rarity_accuracy:6.1f}%")

        # Performance grading
        print(f"\n[PERFORMANCE GRADE]")
        print(f"{'=' * 80}")
        if overall_accuracy >= 95:
            grade = "A+ (Excellent)"
            verdict = "[EXCELLENT] System is production-ready"
        elif overall_accuracy >= 90:
            grade = "A (Very Good)"
            verdict = "[GOOD] Minor improvements needed"
        elif overall_accuracy >= 85:
            grade = "B (Good)"
            verdict = "[ACCEPTABLE] Some improvements recommended"
        elif overall_accuracy >= 80:
            grade = "C (Fair)"
            verdict = "[NEEDS WORK] Significant improvements needed"
        else:
            grade = "D (Poor)"
            verdict = "[POOR] Major improvements required"

        print(f"Grade: {grade}")
        print(f"Verdict: {verdict}")

        # Identify problem areas
        print(f"\n[PROBLEM AREAS]")
        print(f"{'=' * 80}")

        problem_categories = []
        for category in TEST_QUESTIONS.keys():
            avg_accuracy = sum(self.scores[category].values()) / len(RARITIES)
            if avg_accuracy < 85:
                problem_categories.append((category, avg_accuracy))

        if problem_categories:
            for category, accuracy in sorted(problem_categories, key=lambda x: x[1]):
                print(f"[WARNING] {category}: {accuracy:.1f}% accuracy")
                self._analyze_category_failures(category)
        else:
            print("[OK] No major problem areas identified")

        # Recommendations
        print(f"\n[RECOMMENDATIONS]")
        print(f"{'=' * 80}")

        recommendations = self._generate_recommendations(overall_accuracy, problem_categories)
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}")

    def _analyze_category_failures(self, category: str):
        """Analyze why a category is failing."""
        all_failures = []
        for rarity in RARITIES:
            results = self.results[category][rarity]
            all_failures.extend([r for r in results if not r['passed']])

        if not all_failures:
            return

        # Group failures by reason
        reason_groups = defaultdict(list)
        for failure in all_failures:
            reason_groups[failure['reason']].append(failure)

        print(f"\n  Common failure patterns:")
        for reason, failures in sorted(reason_groups.items(), key=lambda x: -len(x[1]))[:3]:
            print(f"    - {reason} ({len(failures)} cases)")
            if failures:
                print(f"      Example: \"{failures[0]['question'][:60]}...\"")

    def _generate_recommendations(self, overall_accuracy: float, problem_categories: List) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        # Overall accuracy recommendations
        if overall_accuracy < 85:
            recommendations.append(
                "CRITICAL: Review keyword lists in tool_definitions.py - accuracy below 85%"
            )

        if overall_accuracy < 90:
            recommendations.append(
                "Add more training examples for ambiguous queries (e.g., 'Bitcoin price news')"
            )

        # Category-specific recommendations
        for category, accuracy in problem_categories:
            if category == "PURE_LLM" and accuracy < 85:
                recommendations.append(
                    f"PURE_LLM ({accuracy:.1f}%): Reduce false positives by tightening keyword matching"
                )

            if category == "BRAVE_MCP" and accuracy < 85:
                recommendations.append(
                    f"BRAVE_MCP ({accuracy:.1f}%): Add more news/current-events keywords"
                )

            if category == "MONGODB_MCP" and accuracy < 85:
                recommendations.append(
                    f"MONGODB_MCP ({accuracy:.1f}%): Add more price/trading/technical keywords"
                )

        # Rarity-specific recommendations
        for rarity in RARITIES:
            rarity_accuracy = sum(
                self.scores[cat][rarity] for cat in TEST_QUESTIONS.keys()
            ) / len(TEST_QUESTIONS)

            if rarity_accuracy < 85:
                recommendations.append(
                    f"{rarity.upper()} persona ({rarity_accuracy:.1f}%): Review rarity-gating logic"
                )

        # False positive/negative analysis
        false_positives = 0
        false_negatives = 0

        for category in TEST_QUESTIONS.keys():
            for rarity in RARITIES:
                results = self.results[category][rarity]
                for result in results:
                    if not result['passed']:
                        if "NEEDS_NEITHER" in str(result['classified_intent']) and category != "PURE_LLM":
                            false_negatives += 1
                        elif category == "PURE_LLM" and "NEEDS_NEITHER" not in str(result['classified_intent']):
                            false_positives += 1

        if false_positives > 10:
            recommendations.append(
                f"HIGH: Reduce false positives ({false_positives} cases) - too many LLM queries triggering MCPs"
            )

        if false_negatives > 10:
            recommendations.append(
                f"HIGH: Reduce false negatives ({false_negatives} cases) - MCP queries not being detected"
            )

        # General improvements
        if not recommendations:
            recommendations.append("✅ System is performing well - consider A/B testing with users")
            recommendations.append("Consider adding query analytics to track real-world performance")

        return recommendations

    def get_overall_score(self) -> float:
        """Get overall accuracy score."""
        return (self.passed_tests / self.total_tests) * 100 if self.total_tests > 0 else 0


def main():
    """Run comprehensive intent classification tests."""
    tester = IntentClassificationTester()
    overall_accuracy = tester.run_all_tests()

    # Exit code based on accuracy
    if overall_accuracy >= 85:
        print("\n✅ Tests passed - System is ready for deployment")
        return 0
    elif overall_accuracy >= 75:
        print("\n⚠️  Tests passed with warnings - Some improvements recommended")
        return 0
    else:
        print("\n❌ Tests failed - Significant improvements needed before deployment")
        return 1


if __name__ == "__main__":
    sys.exit(main())
