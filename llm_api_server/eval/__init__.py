"""LLM API Server Evaluation Framework.

This module provides a comprehensive evaluation framework for testing LLM API endpoints.
Users can define test cases with validation criteria and generate HTML/JSON reports.

Example usage:
    from llm_api_server.eval import Evaluator, TestCase, HTMLReporter

    # Define test cases
    tests = [
        TestCase(
            question="What is 2+2?",
            description="Basic arithmetic test",
            expected_keywords=["4", "four"],
            min_response_length=10
        ),
        TestCase(
            question="Explain photosynthesis",
            description="Biology knowledge test",
            expected_keywords=["plants", "light", "oxygen"],
            min_response_length=100
        )
    ]

    # Run evaluation
    evaluator = Evaluator(api_url="http://localhost:8000")
    results = evaluator.run_tests(tests)

    # Generate HTML report
    reporter = HTMLReporter()
    reporter.generate(results, "evaluation_report.html")
"""

from .evaluator import Evaluator
from .reporters import ConsoleReporter, HTMLReporter, JSONReporter
from .test_case import TestCase, TestResult
from .validators import validate_response

__all__ = [
    "ConsoleReporter",
    "Evaluator",
    "HTMLReporter",
    "JSONReporter",
    "TestCase",
    "TestResult",
    "validate_response",
]
