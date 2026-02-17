"""报告生成模块：支持 HTML 渲染与 PDF 导出。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except Exception:  # pragma: no cover - optional dependency path
    Environment = None
    FileSystemLoader = None
    select_autoescape = None

try:  # Optional dependency for PDF output
    from weasyprint import HTML
except Exception:  # pragma: no cover - exercised via ImportError/OSError path
    HTML = None


TEMPLATE_DIR = Path(__file__).parent / "templates"


def render_html(context: Dict[str, Any], template: str = "report.html") -> str:
    """使用模板引擎渲染 HTML 报告。"""
    if Environment is not None and FileSystemLoader is not None:
        env = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=select_autoescape()
        )
        tmpl = env.get_template(template)
        return tmpl.render(**context)

    summary = context.get("summary", "")
    stats = context.get("stats", {})
    findings = context.get("findings", [])
    rows = "".join(
        f"<tr><td>{item.get('id', '')}</td><td>{item.get('category', '')}</td><td>{item.get('severity', '')}</td><td>{item.get('details', '')}</td></tr>"
        for item in findings
    )
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8' /><title>Sensor Fuzz Report</title></head><body>"
        "<h1>Sensor Fuzz Test Report</h1>"
        f"<p>Summary: {summary}</p>"
        "<h2>Statistics</h2>"
        "<ul>"
        f"<li>Test cases: {stats.get('test_cases', 0)}</li>"
        f"<li>Anomalies: {stats.get('anomalies', 0)}</li>"
        f"<li>False positives: {stats.get('false_positives', 0)}</li>"
        "</ul>"
        "<h2>Findings</h2><table>"
        "<tr><th>Case</th><th>Category</th><th>Severity</th><th>Details</th></tr>"
        f"{rows}</table></body></html>"
    )


def export_pdf(html_str: str, output: str | Path) -> Path:
    """将 HTML 内容导出为 PDF 文件。"""
    output_path = Path(output)
    if HTML is None:
        raise ImportError(
            "weasyprint is required for PDF export; install optional report extras"
        )
    HTML(string=html_str).write_pdf(str(output_path))
    return output_path
