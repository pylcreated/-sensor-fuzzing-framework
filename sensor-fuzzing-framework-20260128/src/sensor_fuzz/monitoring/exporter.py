"""Enhanced Prometheus exporter with web dashboard."""

from __future__ import annotations

import json
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from prometheus_client import start_http_server, generate_latest, CONTENT_TYPE_LATEST

try:
    from prometheus_client import exposition
except ImportError:
    exposition = None


class DashboardHandler(BaseHTTPRequestHandler):
    """Web dashboard handler for real-time monitoring."""

    def __init__(self, *args, dashboard_data=None, **kwargs):
        """方法说明：执行   init   相关逻辑。"""
        self.dashboard_data = dashboard_data or {}
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        if path == "/":
            self._serve_dashboard()
        elif path == "/api/metrics":
            self._serve_api_metrics()
        elif path == "/api/health":
            self._serve_health_check()
        elif path.startswith("/metrics"):
            self._serve_prometheus_metrics()
        else:
            self._serve_404()

    def _serve_dashboard(self):
        """Serve the main dashboard HTML."""
        html = self._generate_dashboard_html()
        self._send_response(200, "text/html", html)

    def _serve_api_metrics(self):
        """Serve metrics as JSON API."""
        metrics_data = self._collect_metrics_data()
        self._send_response(200, "application/json", json.dumps(metrics_data, indent=2))

    def _serve_health_check(self):
        """Serve health check endpoint."""
        health_data = {
            "status": "healthy",
            "timestamp": time.time(),
            "uptime": self.dashboard_data.get("uptime", 0),
            "version": "1.0.0",
        }
        self._send_response(200, "application/json", json.dumps(health_data))

    def _serve_prometheus_metrics(self):
        """Serve Prometheus metrics."""
        output = generate_latest()
        self._send_response(200, CONTENT_TYPE_LATEST, output.decode("utf-8"))

    def _serve_404(self):
        """Serve 404 error."""
        self._send_response(404, "text/plain", "Not Found")

    def _send_response(self, code: int, content_type: str, content: str):
        """Send HTTP response."""
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(content.encode("utf-8"))

    def _collect_metrics_data(self) -> Dict[str, Any]:
        """Collect current metrics data."""
        return {
            "test_cases": {
                "total": self.dashboard_data.get("test_cases_total", 0),
                "success": self.dashboard_data.get("test_cases_success", 0),
                "failed": self.dashboard_data.get("test_cases_failed", 0),
            },
            "anomalies": {
                "detected": self.dashboard_data.get("anomalies_detected", 0),
                "ai_detected": self.dashboard_data.get("ai_anomalies", 0),
            },
            "performance": {
                "throughput": self.dashboard_data.get("throughput", 0),
                "avg_response_time": self.dashboard_data.get("avg_response_time", 0),
                "cpu_usage": self.dashboard_data.get("cpu_usage", 0),
                "memory_usage": self.dashboard_data.get("memory_usage", 0),
            },
            "ai": {
                "enabled": self.dashboard_data.get("ai_enabled", False),
                "confidence": self.dashboard_data.get("ai_confidence", 0),
                "analysis_time": self.dashboard_data.get("ai_analysis_time", 0),
            },
            "system": {
                "uptime": self.dashboard_data.get("uptime", 0),
                "active_threads": self.dashboard_data.get("active_threads", 0),
                "active_sessions": self.dashboard_data.get("active_sessions", 0),
            },
            "timestamp": time.time(),
        }

    def _generate_dashboard_html(self) -> str:
        """Generate dashboard HTML."""
        return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>工业传感器模糊测试监控面板</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .metric-title {{
            font-size: 14px;
            color: #666;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .metric-value {{
            font-size: 32px;
            font-weight: bold;
            color: #2c3e50;
        }}
        .metric-subtitle {{
            font-size: 12px;
            color: #7f8c8d;
            margin-top: 5px;
        }}
        .status-healthy {{ color: #27ae60; }}
        .status-warning {{ color: #f39c12; }}
        .status-error {{ color: #e74c3c; }}
        .chart-container {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .refresh-btn {{
            background: #3498db;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin-bottom: 20px;
        }}
        .refresh-btn:hover {{
            background: #2980b9;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 工业传感器模糊测试监控面板</h1>
            <p>实时监控测试执行状态和系统性能</p>
            <button class="refresh-btn" onclick="refreshData()">刷新数据</button>
        </div>

        <div class="metrics-grid" id="metrics-grid">
            <!-- Metrics will be populated by JavaScript -->
        </div>

        <div class="chart-container">
            <h3>系统状态概览</h3>
            <div id="system-status">
                <p>正在加载系统状态...</p>
            </div>
        </div>
    </div>

    <script>
        let metricsData = {json.dumps(self._collect_metrics_data())};

        function updateDashboard(data) {{
            metricsData = data;
            const grid = document.getElementById('metrics-grid');

            const metrics = [
                {{
                    title: '测试用例总数',
                    value: data.test_cases.total,
                    subtitle: `成功: ${{data.test_cases.success}} | `
                    `失败: ${{data.test_cases.failed}}`
                }},
                {{
                    title: '检测到的异常',
                    value: data.anomalies.detected,
                    subtitle: `AI检测: ${{data.anomalies.ai_detected}}`
                }},
                {{
                    title: '测试吞吐量',
                    value: data.performance.throughput.toFixed(1),
                    subtitle: '用例/秒'
                }},
                {{
                    title: '平均响应时间',
                    value: (data.performance.avg_response_time * 1000).toFixed(1),
                    subtitle: '毫秒'
                }},
                {{
                    title: 'CPU使用率',
                    value: data.performance.cpu_usage.toFixed(1) + '%',
                    subtitle: '系统负载'
                }},
                {{
                    title: '内存使用',
                    value: (data.performance.memory_usage / 1024 / 1024).toFixed(1),
                    subtitle: 'MB'
                }},
                {{
                    title: '活跃线程',
                    value: data.system.active_threads,
                    subtitle: '并发执行'
                }},
                {{
                    title: '运行时间',
                    value: (data.system.uptime / 3600).toFixed(1),
                    subtitle: '小时'
                }}
            ];

            grid.innerHTML = metrics.map(metric => `
                <div class="metric-card">
                    <div class="metric-title">${{metric.title}}</div>
                    <div class="metric-value">${{metric.value}}</div>
                    <div class="metric-subtitle">${{metric.subtitle}}</div>
                </div>
            `).join('');

            // Update system status
            const statusDiv = document.getElementById('system-status');
            const aiStatus = data.ai.enabled ? '✓ 已启用' : '✗ 未启用';
            const healthClass = data.performance.cpu_usage > 90 ? 'status-error' :
                              data.performance.cpu_usage > 70 ? 'status-warning' :
                              'status-healthy';

            statusDiv.innerHTML = `
                <p><strong>AI状态:</strong> ${{aiStatus}}</p>
                <p><strong>系统健康:</strong> <span class="${{healthClass}}">${{healthClass
                    'status-healthy' ?
                '正常' : healthClass === 'status-warning' ? '警告' : '异常'}}</span></p>
                <p><strong>最后更新:</strong> ${{new Date(data.timestamp * 1000)
                    .toLocaleString('zh-CN')}}</p>
            `;
        }}

        function refreshData() {{
            fetch('/api/metrics')
                .then(response => response.json())
                .then(data => updateDashboard(data))
                .catch(error => console.error('Failed to refresh data:', error));
        }}

        // Initial load
        updateDashboard(metricsData);

        // Auto refresh every 5 seconds
        setInterval(refreshData, 5000);
    </script>
</body>
</html>
        """


class EnhancedMetricsExporter:
    """Enhanced metrics exporter with dashboard."""

    def __init__(
        self,
        port: int = 9000,
        dashboard_port: int = 8080,
        dashboard_host: str = "localhost"
    ):
        """方法说明：执行   init   相关逻辑。"""
        self.port = port
        self.dashboard_port = dashboard_port
        self.dashboard_host = dashboard_host
        self.dashboard_data: Dict[str, Any] = {}
        self._dashboard_server: Optional[HTTPServer] = None
        self._prometheus_thread: Optional[threading.Thread] = None
        self._dashboard_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start both Prometheus and dashboard servers."""
        # Start Prometheus exporter
        self._prometheus_thread = threading.Thread(
            target=start_http_server, args=(self.port,), daemon=True
        )
        self._prometheus_thread.start()

        # Start dashboard server
        def run_dashboard():
            """方法说明：执行 run dashboard 相关逻辑。"""
            def handler_class(*args, **kwargs):
                """方法说明：执行 handler class 相关逻辑。"""
                return DashboardHandler(
                    *args, dashboard_data=self.dashboard_data, **kwargs
                )

            try:
                self._dashboard_server = HTTPServer(
                    (self.dashboard_host, self.dashboard_port), handler_class
                )
                print(
                    f"Dashboard server started on http://{self.dashboard_host}:"
                    f"{self.dashboard_port}"
                )
                self._dashboard_server.serve_forever()
            except Exception as e:
                print(f"Failed to start dashboard server: {e}")

        self._dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
        self._dashboard_thread.start()

    def update_dashboard_data(self, key: str, value: Any) -> None:
        """Update dashboard data."""
        self.dashboard_data[key] = value

    def stop(self) -> None:
        """Stop all servers."""
        if self._dashboard_server:
            self._dashboard_server.shutdown()
            self._dashboard_server.server_close()
        # Prometheus server runs in daemon thread, will stop with main process


# Backward compatibility
def start_exporter(port: int = 9000) -> EnhancedMetricsExporter:
    """Start enhanced metrics exporter with dashboard."""
    exporter = EnhancedMetricsExporter(port=port)
    exporter.start()
    return exporter
