"""Report generators for evaluation results."""

import html
import json
from datetime import datetime
from pathlib import Path

from .test_case import TestResult


class HTMLReporter:
    """Generate HTML reports from evaluation results."""

    def generate(self, results: list[TestResult], output_path: str | Path, title: str = "LLM Evaluation Report"):
        """Generate an HTML report from test results.

        Args:
            results: List of test results
            output_path: Path to write HTML report
            title: Report title
        """
        output_path = Path(output_path)

        # Calculate summary stats
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed
        success_rate = (passed / total * 100) if total > 0 else 0
        total_time = sum(r.response_time for r in results)
        avg_time = total_time / total if total > 0 else 0

        # Generate HTML
        html_content = self._generate_html(
            results=results,
            title=title,
            total=total,
            passed=passed,
            failed=failed,
            success_rate=success_rate,
            total_time=total_time,
            avg_time=avg_time,
        )

        # Write to file
        output_path.write_text(html_content, encoding="utf-8")

    def _generate_html(
        self,
        results: list[TestResult],
        title: str,
        total: int,
        passed: int,
        failed: int,
        success_rate: float,
        total_time: float,
        avg_time: float,
    ) -> str:
        """Generate HTML content for report."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Generate test result rows
        test_rows = []
        for i, result in enumerate(results, 1):
            status_class = "passed" if result.passed else "failed"
            status_icon = "✓" if result.passed else "✗"

            # Build issues/error display
            issues_html = ""
            if result.error:
                issues_html = f'<div class="error">Error: {html.escape(result.error)}</div>'
            elif result.issues:
                issues_list = "".join(f"<li>{html.escape(issue)}</li>" for issue in result.issues)
                issues_html = f'<div class="issues"><ul>{issues_list}</ul></div>'

            # Truncate response for display
            response_display = html.escape(result.response[:500] if result.response else "N/A")
            if result.response and len(result.response) > 500:
                response_display += "..."

            row = f"""
            <tr class="{status_class}">
                <td>{i}</td>
                <td><span class="status-icon">{status_icon}</span></td>
                <td><strong>{html.escape(result.test_case.description)}</strong><br>
                    <span class="question">{html.escape(result.test_case.question)}</span>
                </td>
                <td>{result.response_time:.2f}s</td>
                <td>
                    <div class="response">{response_display}</div>
                    {issues_html}
                </td>
            </tr>
            """
            test_rows.append(row)

        test_rows_html = "\n".join(test_rows)

        # Complete HTML document
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f5f5f5;
            padding: 20px;
            color: #333;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
        }}
        h1 {{
            font-size: 28px;
            margin-bottom: 10px;
        }}
        .timestamp {{
            opacity: 0.9;
            font-size: 14px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #fafafa;
            border-bottom: 1px solid #eee;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 6px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .stat-label {{
            font-size: 12px;
            text-transform: uppercase;
            color: #666;
            font-weight: 600;
            margin-bottom: 8px;
        }}
        .stat-value {{
            font-size: 32px;
            font-weight: bold;
            color: #333;
        }}
        .stat-value.success {{
            color: #10b981;
        }}
        .stat-value.danger {{
            color: #ef4444;
        }}
        .stat-value.info {{
            color: #3b82f6;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        thead {{
            background: #f9fafb;
            border-bottom: 2px solid #e5e7eb;
        }}
        th {{
            padding: 15px;
            text-align: left;
            font-weight: 600;
            font-size: 13px;
            text-transform: uppercase;
            color: #6b7280;
        }}
        td {{
            padding: 15px;
            border-bottom: 1px solid #f3f4f6;
            vertical-align: top;
        }}
        tr.passed {{
            background: #f0fdf4;
        }}
        tr.failed {{
            background: #fef2f2;
        }}
        tr:hover {{
            background: #f9fafb !important;
        }}
        .status-icon {{
            font-size: 18px;
            font-weight: bold;
        }}
        tr.passed .status-icon {{
            color: #10b981;
        }}
        tr.failed .status-icon {{
            color: #ef4444;
        }}
        .question {{
            font-size: 13px;
            color: #6b7280;
            font-style: italic;
        }}
        .response {{
            font-size: 13px;
            line-height: 1.5;
            color: #4b5563;
            background: #f9fafb;
            padding: 10px;
            border-radius: 4px;
            margin-top: 5px;
            max-height: 200px;
            overflow-y: auto;
        }}
        .issues, .error {{
            margin-top: 10px;
            padding: 10px;
            border-radius: 4px;
            font-size: 13px;
        }}
        .issues {{
            background: #fef3c7;
            border-left: 3px solid #f59e0b;
        }}
        .error {{
            background: #fee2e2;
            border-left: 3px solid #ef4444;
            color: #991b1b;
        }}
        .issues ul {{
            margin-left: 20px;
        }}
        .issues li {{
            margin: 5px 0;
            color: #92400e;
        }}
        footer {{
            padding: 20px 30px;
            background: #f9fafb;
            text-align: center;
            font-size: 13px;
            color: #6b7280;
            border-top: 1px solid #e5e7eb;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{html.escape(title)}</h1>
            <div class="timestamp">Generated on {timestamp}</div>
        </header>

        <div class="summary">
            <div class="stat-card">
                <div class="stat-label">Total Tests</div>
                <div class="stat-value info">{total}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Passed</div>
                <div class="stat-value success">{passed}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Failed</div>
                <div class="stat-value danger">{failed}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Success Rate</div>
                <div class="stat-value">{success_rate:.1f}%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Time</div>
                <div class="stat-value">{total_time:.1f}s</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Avg Time</div>
                <div class="stat-value">{avg_time:.2f}s</div>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th style="width: 50px;">#</th>
                    <th style="width: 50px;">Status</th>
                    <th style="width: 30%;">Test</th>
                    <th style="width: 100px;">Time</th>
                    <th>Response & Issues</th>
                </tr>
            </thead>
            <tbody>
                {test_rows_html}
            </tbody>
        </table>

        <footer>
            Generated by LLM API Server Evaluation Framework
        </footer>
    </div>
</body>
</html>"""


class JSONReporter:
    """Generate JSON reports from evaluation results."""

    def generate(self, results: list[TestResult], output_path: str | Path):
        """Generate a JSON report from test results.

        Args:
            results: List of test results
            output_path: Path to write JSON report
        """
        output_path = Path(output_path)

        # Calculate summary stats
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed
        success_rate = (passed / total * 100) if total > 0 else 0
        total_time = sum(r.response_time for r in results)
        avg_time = total_time / total if total > 0 else 0

        # Build JSON structure
        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "success_rate": success_rate,
                "total_time": total_time,
                "avg_time": avg_time,
            },
            "results": [
                {
                    "test_number": i,
                    "description": r.test_case.description,
                    "question": r.test_case.question,
                    "passed": r.passed,
                    "response_time": r.response_time,
                    "response": r.response,
                    "issues": r.issues,
                    "error": r.error,
                    "metadata": r.test_case.metadata,
                }
                for i, r in enumerate(results, 1)
            ],
        }

        # Write to file
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")


class ConsoleReporter:
    """Generate console output from evaluation results."""

    def generate(self, results: list[TestResult], verbose: bool = False):
        """Print test results to console.

        Args:
            results: List of test results
            verbose: If True, print full responses for all tests
        """
        # Calculate summary stats
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed
        success_rate = (passed / total * 100) if total > 0 else 0
        total_time = sum(r.response_time for r in results)

        print("\n" + "=" * 80)
        print("LLM Evaluation Results")
        print("=" * 80 + "\n")

        # Print individual results
        for i, result in enumerate(results, 1):
            status = "✓ PASSED" if result.passed else "✗ FAILED"
            status_color = "\033[92m" if result.passed else "\033[91m"
            reset = "\033[0m"

            print(f"Test {i}/{total}: {result.test_case.description}")
            print(f'Question: "{result.test_case.question}"')
            print(f"{status_color}{status}{reset} ({result.response_time:.2f}s)")

            if result.error:
                print(f"  Error: {result.error}")
            elif result.issues:
                for issue in result.issues:
                    print(f"  - {issue}")

            if verbose or not result.passed:
                print(f"\nResponse:\n{result.response}\n")

            print()

        # Print summary
        print("=" * 80)
        print("Summary")
        print("=" * 80)
        print(f"Total Tests:  {total}")
        print(f"Passed:       {passed}")
        print(f"Failed:       {failed}")
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"Total Time:   {total_time:.1f}s")
        print()
