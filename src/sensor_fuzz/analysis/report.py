"""报告生成模块：支持 HTML 渲染与 PDF 导出。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from jinja2 import Environment, FileSystemLoader, select_autoescape

try:  # Optional dependency for PDF output
    from weasyprint import HTML
except Exception:  # pragma: no cover - exercised via ImportError/OSError path
    HTML = None


TEMPLATE_DIR = Path(__file__).parent / "templates"


def render_html(context: Dict[str, Any], template: str = "report.html") -> str:
    """使用模板引擎渲染 HTML 报告。"""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=select_autoescape()
    )
    tmpl = env.get_template(template)
    return tmpl.render(**context)


def export_pdf(html_str: str, output: str | Path) -> Path:
    """将 HTML 内容导出为 PDF 文件。"""
    output_path = Path(output)
    if HTML is None:
        raise ImportError(
            "weasyprint is required for PDF export; install optional report extras"
        )
    HTML(string=html_str).write_pdf(str(output_path))
    return output_path
