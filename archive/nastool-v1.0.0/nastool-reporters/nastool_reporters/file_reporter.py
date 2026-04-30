"""
File Reporter Module for nastool

Export diagnostic results to JSON or HTML files.

Usage:
    from reporters.file_reporter import FileReporter

    reporter = FileReporter()
    reporter.save_json(results, "report.json")
    reporter.save_html(results, "report.html")
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from nastool_core.checks import CheckResult, CheckSeverity

# String-to-enum cache for robustness
_SEVERITY_CACHE = {_s.value: _s for _s in CheckSeverity}


def _norm_severity(sev) -> CheckSeverity:
    """Normalize severity: accept enum, string (case-insensitive), or 'INFO'/'passed'."""
    if isinstance(sev, CheckSeverity):
        return sev
    if isinstance(sev, str):
        s = sev.strip().lower()
        # Try exact value match first (CheckSeverity.INFO.value = 'info')
        if s in _SEVERITY_CACHE:
            return _SEVERITY_CACHE[s]
        # Try name match (CheckSeverity.WARNING.name = 'WARNING')
        for _e in CheckSeverity:
            if _e.name.lower() == s:
                return _e
    # Default fallback
    return CheckSeverity.INFO


class FileReporter:
    """
    Export diagnostic results to various file formats.

    Supports:
    - JSON: Machine-readable, suitable for CI/CD
    - HTML: Human-readable report with styling

    Example:
        reporter = FileReporter()
        reporter.save_json(results, "diagnostic_report.json")
        reporter.save_html(results, "diagnostic_report.html")
    """

    def __init__(self, device_info: Optional[Dict[str, Any]] = None):
        """
        Initialize file reporter.

        Args:
            device_info: Optional device information to include in report
        """
        self.device_info = device_info or {}
        self.timestamp = datetime.now().isoformat()

    def save_report(
        self,
        results: list,
        output_path: str,
        format: str = "json",
    ) -> str:
        """Dispatch to save_json or save_html based on format."""
        if format == "json":
            return self.save_json(results, output_path)
        elif format == "html":
            return self.save_html(results, output_path)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def save_json(
        self, results: List[CheckResult], output_path: str, include_details: bool = True
    ) -> str:
        """
        Save results to JSON file.

        Args:
            results: List of check results
            output_path: Output file path
            include_details: Whether to include detailed information

        Returns:
            Absolute path to saved file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build report structure
        report = {
            "meta": {
                "version": "3.0.4",
                "timestamp": self.timestamp,
                "tool": "nastool",
            },
            "device": self.device_info,
            "summary": self._build_summary(results),
            "checks": [],
        }

        # Add check results
        for result in results:
            sev = _norm_severity(result.severity)
            check_data = {
                "id": result.check_id,
                "category": str(result.category) if isinstance(result.category, str) else result.category.name,
                "severity": sev.name,
"passed": sev == CheckSeverity.PASSED,
                "message": result.message,
            }

            if include_details and result.details:
                check_data["details"] = result.details

            report["checks"].append(check_data)

        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return str(output_path.absolute())

    def save_html(
        self, results: List[CheckResult], output_path: str, title: str = "nastool Diagnostic Report"
    ) -> str:
        """
        Save results to HTML file with styling.

        Args:
            results: List of check results
            output_path: Output file path
            title: Report title

        Returns:
            Absolute path to saved file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        summary = self._build_summary(results)

        # Build HTML
        html = self._build_html_template(title, summary, results)

        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        return str(output_path.absolute())

    def _build_summary(self, results: List[CheckResult]) -> Dict[str, Any]:
        """Build summary statistics"""
        total = len(results)
        if total == 0:
            return {
                "total": 0,
                "passed": 0,
                "warnings": 0,
                "critical": 0,
                "skipped": 0,
                "score": 0,
            }

        counts = {
            CheckSeverity.PASSED: 0,
            CheckSeverity.WARNING: 0,
            CheckSeverity.CRITICAL: 0,
            CheckSeverity.INFO: 0,
        }

        for result in results:
            counts[_norm_severity(result.severity)] += 1

        # Calculate health score
        ok_weight = 100
        warn_weight = 50
        crit_weight = 0

        score = (
            counts[CheckSeverity.PASSED] * ok_weight
            + counts[CheckSeverity.WARNING] * warn_weight
            + counts[CheckSeverity.CRITICAL] * crit_weight
        ) / total

        return {
            "total": total,
            "passed": counts[CheckSeverity.PASSED],
            "warnings": counts[CheckSeverity.WARNING],
            "critical": counts[CheckSeverity.CRITICAL],
            "skipped": counts[CheckSeverity.INFO],
            "score": int(score),
        }

    def _build_html_template(
        self, title: str, summary: Dict[str, Any], results: List[CheckResult]
    ) -> str:
        """Build complete HTML report"""

        # Determine status color
        if summary["score"] >= 90:
            status_color = "#10b981"
            status_text = "Excellent"
        elif summary["score"] >= 70:
            status_color = "#84cc16"
            status_text = "Good"
        elif summary["score"] >= 50:
            status_color = "#f59e0b"
            status_text = "Warning"
        else:
            status_color = "#ef4444"
            status_text = "Critical"

        # Build check rows
        check_rows = []
        for result in results:
            sev = _norm_severity(result.severity)
            severity_colors = {
                CheckSeverity.PASSED: "#10b981",
                CheckSeverity.WARNING: "#f59e0b",
                CheckSeverity.CRITICAL: "#ef4444",
                CheckSeverity.INFO: "#6b7280",
            }
            severity_icons = {
                CheckSeverity.PASSED: "[OK]",
                CheckSeverity.WARNING: "[!]",
                CheckSeverity.CRITICAL: "[X]",
                CheckSeverity.INFO: "⏭",
            }

            color = severity_colors[sev]
            icon = severity_icons[sev]

            row = f"""
            <tr>
                <td><span style="color: {color};">{icon}</span></td>
                <td>{str(result.category)}</td>
                <td><code>{result.check_id}</code></td>
                <td>{result.message}</td>
            </tr>
            """
            check_rows.append(row)

        # Complete HTML template
        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f3f4f6;
            color: #1f2937;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            padding: 2rem;
        }}
        .header {{
            background: linear-gradient(135deg, #3b82f6, #8b5cf6);
            color: white;
            padding: 2rem;
            border-radius: 1rem;
            margin-bottom: 2rem;
        }}
        .header h1 {{
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }}
        .header .subtitle {{
            opacity: 0.9;
        }}
        .score-card {{
            background: white;
            padding: 2rem;
            border-radius: 1rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
            text-align: center;
        }}
        .score {{
            font-size: 4rem;
            font-weight: bold;
            color: {status_color};
        }}
        .score-label {{
            color: #6b7280;
            font-size: 1rem;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .stat {{
            background: white;
            padding: 1.5rem;
            border-radius: 0.5rem;
            text-align: center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .stat-value {{
            font-size: 2rem;
            font-weight: bold;
        }}
        .stat-label {{
            color: #6b7280;
            font-size: 0.875rem;
        }}
        .checks-table {{
            background: white;
            border-radius: 1rem;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th {{
            background: #f9fafb;
            padding: 1rem;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #e5e7eb;
        }}
        td {{
            padding: 1rem;
            border-bottom: 1px solid #e5e7eb;
        }}
        tr:last-child td {{
            border-bottom: none;
        }}
        code {{
            background: #f3f4f6;
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            font-family: 'Menlo', 'Monaco', monospace;
            font-size: 0.875rem;
        }}
        .footer {{
            text-align: center;
            color: #6b7280;
            margin-top: 2rem;
            font-size: 0.875rem;
        }}
        .ok {{ color: #10b981; }}
        .warning {{ color: #f59e0b; }}
        .critical {{ color: #ef4444; }}
        .skipped {{ color: #6b7280; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🍓 {title}</h1>
            <p class="subtitle">Generated: {self.timestamp}</p>
        </div>
        
        <div class="score-card">
            <div class="score">{summary["score"]}/100</div>
            <div class="score-label">{status_text}</div>
        </div>
        
        <div class="stats">
            <div class="stat">
                <div class="stat-value">{summary["total"]}</div>
                <div class="stat-label">Total Checks</div>
            </div>
            <div class="stat">
                <div class="stat-value ok">{summary["passed"]}</div>
                <div class="stat-label">Passed</div>
            </div>
            <div class="stat">
                <div class="stat-value warning">{summary["warnings"]}</div>
                <div class="stat-label">Warnings</div>
            </div>
            <div class="stat">
                <div class="stat-value critical">{summary["critical"]}</div>
                <div class="stat-label">Critical</div>
            </div>
        </div>
        
        <div class="checks-table">
            <table>
                <thead>
                    <tr>
                        <th>Status</th>
                        <th>Category</th>
                        <th>Check ID</th>
                        <th>Message</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(check_rows)}
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>Generated by nastool v3.0.4</p>
        </div>
    </div>
</body>
</html>
        """

        return html


def save_report(
    results: List[CheckResult],
    output_path: str,
    format: str = "json",
    device_info: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Convenience function to save report.

    Args:
        results: List of check results
        output_path: Output file path
        format: Output format (json or html)
        device_info: Optional device information

    Returns:
        Absolute path to saved file
    """
    reporter = FileReporter(device_info=device_info)

    if format == "json":
        return reporter.save_json(results, output_path)
    elif format == "html":
        return reporter.save_html(results, output_path)
    else:
        raise ValueError(f"Unsupported format: {format}")
