"""
Monitoring dashboard templates and visualization components
"""

import json
from typing import Dict, Any, List
from datetime import datetime, timedelta


class DashboardTemplate:
    """Base dashboard template"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.widgets = []

    def add_widget(self, widget: Dict[str, Any]):
        """Add a widget to the dashboard"""
        self.widgets.append(widget)

    def to_dict(self) -> Dict[str, Any]:
        """Convert dashboard to dictionary"""
        return {
            "name": self.name,
            "description": self.description,
            "widgets": self.widgets,
            "created_at": datetime.utcnow().isoformat()
        }


class MonitoringDashboards:
    """Pre-configured monitoring dashboards"""

    @staticmethod
    def system_overview_dashboard() -> Dict[str, Any]:
        """System overview dashboard"""
        dashboard = DashboardTemplate(
            "System Overview",
            "High-level system health and performance metrics"
        )

        # System Status Widget
        dashboard.add_widget({
            "id": "system_status",
            "type": "status_panel",
            "title": "System Status",
            "grid_position": {"x": 0, "y": 0, "w": 12, "h": 4},
            "data_source": "/monitoring/health/detailed",
            "refresh_interval": 30,
            "display": {
                "show_uptime": True,
                "show_component_count": True,
                "show_recommendations": True
            }
        })

        # CPU Usage Widget
        dashboard.add_widget({
            "id": "cpu_usage",
            "type": "timeseries_chart",
            "title": "CPU Usage (%)",
            "grid_position": {"x": 0, "y": 4, "w": 6, "h": 6},
            "data_source": "/monitoring/metrics/history",
            "metric_name": "system_cpu_percent",
            "time_range": "1h",
            "refresh_interval": 15,
            "display": {
                "line_color": "#3B82F6",
                "fill_area": True,
                "show_grid": True,
                "y_axis_max": 100
            }
        })

        # Memory Usage Widget
        dashboard.add_widget({
            "id": "memory_usage",
            "type": "timeseries_chart",
            "title": "Memory Usage (%)",
            "grid_position": {"x": 6, "y": 4, "w": 6, "h": 6},
            "data_source": "/monitoring/metrics/history",
            "metric_name": "system_memory_percent",
            "time_range": "1h",
            "refresh_interval": 15,
            "display": {
                "line_color": "#10B981",
                "fill_area": True,
                "show_grid": True,
                "y_axis_max": 100
            }
        })

        # Disk Usage Widget
        dashboard.add_widget({
            "id": "disk_usage",
            "type": "gauge_chart",
            "title": "Disk Usage",
            "grid_position": {"x": 0, "y": 10, "w": 6, "h": 4},
            "data_source": "/monitoring/metrics",
            "metric_name": "system_disk_percent",
            "refresh_interval": 60,
            "display": {
                "thresholds": [
                    {"value": 70, "color": "#10B981"},
                    {"value": 85, "color": "#F59E0B"},
                    {"value": 95, "color": "#EF4444"}
                ]
            }
        })

        # Active Alerts Widget
        dashboard.add_widget({
            "id": "active_alerts",
            "type": "alerts_list",
            "title": "Active Alerts",
            "grid_position": {"x": 6, "y": 10, "w": 6, "h": 4},
            "data_source": "/monitoring/alerts",
            "refresh_interval": 30,
            "display": {
                "max_items": 5,
                "show_severity": True,
                "show_timestamp": True,
                "color_by_severity": True
            }
        })

        # HTTP Requests Widget
        dashboard.add_widget({
            "id": "http_requests",
            "type": "timeseries_chart",
            "title": "HTTP Requests (per minute)",
            "grid_position": {"x": 0, "y": 14, "w": 6, "h": 6},
            "data_source": "/monitoring/metrics/history",
            "metric_name": "http_requests_total",
            "time_range": "1h",
            "refresh_interval": 15,
            "display": {
                "line_color": "#8B5CF6",
                "fill_area": False,
                "show_grid": True,
                "aggregation": "rate"
            }
        })

        # Response Time Widget
        dashboard.add_widget({
            "id": "response_time",
            "type": "timeseries_chart",
            "title": "Average Response Time (ms)",
            "grid_position": {"x": 6, "y": 14, "w": 6, "h": 6},
            "data_source": "/monitoring/metrics/history",
            "metric_name": "http_request_duration_ms_avg",
            "time_range": "1h",
            "refresh_interval": 15,
            "display": {
                "line_color": "#F59E0B",
                "fill_area": False,
                "show_grid": True,
                "show_percentiles": ["p50", "p95", "p99"]
            }
        })

        return dashboard.to_dict()

    @staticmethod
    def agents_dashboard() -> Dict[str, Any]:
        """Agent-specific monitoring dashboard"""
        dashboard = DashboardTemplate(
            "Agent Monitoring",
            "Comprehensive view of agent performance and health"
        )

        # Agent Status Overview
        dashboard.add_widget({
            "id": "agent_status_overview",
            "type": "status_grid",
            "title": "Agent Status",
            "grid_position": {"x": 0, "y": 0, "w": 12, "h": 6},
            "data_source": "/monitoring/metrics",
            "metrics": ["agents_active_count", "agents_total_count"],
            "refresh_interval": 30,
            "display": {
                "show_agent_types": True,
                "show_task_count": True,
                "color_by_status": True
            }
        })

        # Task Execution Time
        dashboard.add_widget({
            "id": "task_execution_time",
            "type": "histogram_chart",
            "title": "Task Execution Time Distribution",
            "grid_position": {"x": 0, "y": 6, "w": 6, "h": 8},
            "data_source": "/monitoring/metrics/history",
            "metric_name": "agent_task_duration_ms",
            "time_range": "24h",
            "refresh_interval": 60,
            "display": {
                "show_percentiles": True,
                "bucket_size": 100,
                "log_scale": True
            }
        })

        # Task Completion Rate
        dashboard.add_widget({
            "id": "task_completion_rate",
            "type": "pie_chart",
            "title": "Task Status Distribution",
            "grid_position": {"x": 6, "y": 6, "w": 6, "h": 4},
            "data_source": "/monitoring/metrics",
            "metrics": ["tasks_completed_total", "tasks_failed_total", "tasks_pending_count"],
            "refresh_interval": 30,
            "display": {
                "colors": {
                    "completed": "#10B981",
                    "failed": "#EF4444",
                    "pending": "#F59E0B"
                }
            }
        })

        # Agent Task Load
        dashboard.add_widget({
            "id": "agent_task_load",
            "type": "bar_chart",
            "title": "Current Task Load by Agent",
            "grid_position": {"x": 6, "y": 10, "w": 6, "h": 4},
            "data_source": "/monitoring/metrics",
            "refresh_interval": 30,
            "display": {
                "horizontal_bars": True,
                "show_thresholds": True,
                "color_by_utilization": True
            }
        })

        # Agent Health Timeline
        dashboard.add_widget({
            "id": "agent_health_timeline",
            "type": "gantt_chart",
            "title": "Agent Activity Timeline",
            "grid_position": {"x": 0, "y": 14, "w": 12, "h": 6},
            "data_source": "/monitoring/health/components",
            "time_range": "6h",
            "refresh_interval": 60,
            "display": {
                "group_by": "agent_type",
                "color_by_status": True,
                "show_durations": True
            }
        })

        return dashboard.to_dict()

    @staticmethod
    def performance_dashboard() -> Dict[str, Any]:
        """Performance monitoring dashboard"""
        dashboard = DashboardTemplate(
            "Performance Monitoring",
            "Detailed performance metrics and bottlenecks"
        )

        # Response Time Percentiles
        dashboard.add_widget({
            "id": "response_time_percentiles",
            "type": "timeseries_chart",
            "title": "Response Time Percentiles (ms)",
            "grid_position": {"x": 0, "y": 0, "w": 12, "h": 8},
            "data_source": "/monitoring/metrics/history",
            "metrics": [
                "http_request_duration_ms_p50",
                "http_request_duration_ms_p95",
                "http_request_duration_ms_p99"
            ],
            "time_range": "1h",
            "refresh_interval": 15,
            "display": {
                "multi_series": True,
                "colors": {
                    "p50": "#10B981",
                    "p95": "#F59E0B",
                    "p99": "#EF4444"
                },
                "legend": True,
                "show_grid": True
            }
        })

        # Request Rate by Endpoint
        dashboard.add_widget({
            "id": "request_rate_by_endpoint",
            "type": "heatmap_chart",
            "title": "Request Rate by Endpoint",
            "grid_position": {"x": 0, "y": 8, "w": 6, "h": 6},
            "data_source": "/monitoring/metrics/history",
            "metric_name": "http_requests_total",
            "time_range": "24h",
            "refresh_interval": 60,
            "display": {
                "x_axis": "time",
                "y_axis": "endpoint",
                "color_scale": "viridis"
            }
        })

        # Error Rate by Endpoint
        dashboard.add_widget({
            "id": "error_rate_by_endpoint",
            "type": "bar_chart",
            "title": "Error Rate by Endpoint (%)",
            "grid_position": {"x": 6, "y": 8, "w": 6, "h": 6},
            "data_source": "/monitoring/metrics",
            "refresh_interval": 30,
            "display": {
                "sort_by": "value",
                "show_thresholds": True,
                "threshold_value": 5
            }
        })

        # Database Performance
        dashboard.add_widget({
            "id": "database_performance",
            "type": "timeseries_chart",
            "title": "Database Query Duration (ms)",
            "grid_position": {"x": 0, "y": 14, "w": 6, "h": 6},
            "data_source": "/monitoring/metrics/history",
            "metric_name": "database_query_duration_ms_avg",
            "time_range": "1h",
            "refresh_interval": 15,
            "display": {
                "line_color": "#6366F1",
                "fill_area": False,
                "show_grid": True
            }
        })

        # Cache Performance
        dashboard.add_widget({
            "id": "cache_performance",
            "type": "gauge_chart",
            "title": "Cache Hit Rate (%)",
            "grid_position": {"x": 6, "y": 14, "w": 6, "h": 6},
            "data_source": "/monitoring/metrics",
            "metric_name": "cache_hit_rate",
            "refresh_interval": 30,
            "display": {
                "thresholds": [
                    {"value": 80, "color": "#10B981"},
                    {"value": 60, "color": "#F59E0B"},
                    {"value": 40, "color": "#EF4444"}
                ],
                "show_value": True
            }
        })

        return dashboard.to_dict()

    @staticmethod
    def alerts_dashboard() -> Dict[str, Any]:
        """Alert management dashboard"""
        dashboard = DashboardTemplate(
            "Alert Management",
            "Active alerts, history, and alerting statistics"
        )

        # Alert Statistics
        dashboard.add_widget({
            "id": "alert_statistics",
            "type": "statistics_grid",
            "title": "Alert Statistics",
            "grid_position": {"x": 0, "y": 0, "w": 12, "h": 4},
            "data_source": "/monitoring/alerts/statistics",
            "refresh_interval": 30,
            "display": {
                "metrics": [
                    "active_alerts",
                    "total_alerts",
                    "last_24_hours.total",
                    "last_24_hours.by_severity"
                ]
            }
        })

        # Active Alerts List
        dashboard.add_widget({
            "id": "active_alerts_list",
            "type": "alerts_table",
            "title": "Active Alerts",
            "grid_position": {"x": 0, "y": 4, "w": 8, "h": 8},
            "data_source": "/monitoring/alerts",
            "refresh_interval": 30,
            "display": {
                "columns": [
                    "severity",
                    "rule_name",
                    "component",
                    "message",
                    "timestamp",
                    "consecutive_failures"
                ],
                "sortable": True,
                "filterable": True,
                "actions": ["acknowledge", "suppress"]
            }
        })

        # Alert Timeline
        dashboard.add_widget({
            "id": "alert_timeline",
            "type": "timeline_chart",
            "title": "Alert Timeline (Last 24 Hours)",
            "grid_position": {"x": 8, "y": 4, "w": 4, "h": 8},
            "data_source": "/monitoring/alerts",
            "time_range": "24h",
            "refresh_interval": 60,
            "display": {
                "group_by_severity": True,
                "show_resolutions": True,
                "interactive": True
            }
        })

        # Alert History by Severity
        dashboard.add_widget({
            "id": "alert_history_by_severity",
            "type": "stacked_area_chart",
            "title": "Alert History by Severity",
            "grid_position": {"x": 0, "y": 12, "w": 6, "h": 6},
            "data_source": "/monitoring/alerts",
            "time_range": "7d",
            "refresh_interval": 300,
            "display": {
                "colors": {
                    "critical": "#EF4444",
                    "error": "#F59E0B",
                    "warning": "#10B981",
                    "info": "#6B7280"
                }
            }
        })

        # Top Alert Sources
        dashboard.add_widget({
            "id": "top_alert_sources",
            "type": "horizontal_bar_chart",
            "title": "Top Alert Sources (Last 7 Days)",
            "grid_position": {"x": 6, "y": 12, "w": 6, "h": 6},
            "data_source": "/monitoring/alerts",
            "time_range": "7d",
            "refresh_interval": 300,
            "display": {
                "max_items": 10,
                "show_count": True,
                "show_percentage": True
            }
        })

        return dashboard.to_dict()

    @staticmethod
    def infrastructure_dashboard() -> Dict[str, Any]:
        """Infrastructure monitoring dashboard"""
        dashboard = DashboardTemplate(
            "Infrastructure Monitoring",
            "System resources and external dependencies"
        )

        # System Resources Overview
        dashboard.add_widget({
            "id": "system_resources_overview",
            "type": "resource_grid",
            "title": "System Resources",
            "grid_position": {"x": 0, "y": 0, "w": 12, "h": 6},
            "data_source": "/monitoring/health/detailed",
            "refresh_interval": 30,
            "display": {
                "resources": [
                    "cpu",
                    "memory",
                    "disk",
                    "network"
                ]
            }
        })

        # External Services Status
        dashboard.add_widget({
            "id": "external_services_status",
            "type": "service_status_grid",
            "title": "External Services Status",
            "grid_position": {"x": 0, "y": 6, "w": 6, "h": 6},
            "data_source": "/monitoring/health/detailed",
            "refresh_interval": 60,
            "display": {
                "services": [
                    "database",
                    "redis",
                    "qdrant",
                    "external_apis"
                ]
            }
        })

        # Network I/O
        dashboard.add_widget({
            "id": "network_io",
            "type": "timeseries_chart",
            "title": "Network I/O (MB/s)",
            "grid_position": {"x": 6, "y": 6, "w": 6, "h": 6},
            "data_source": "/monitoring/metrics/history",
            "metrics": [
                "system_network_bytes_sent",
                "system_network_bytes_recv"
            ],
            "time_range": "1h",
            "refresh_interval": 15,
            "display": {
                "multi_series": True,
                "unit_conversion": "bytes_to_mb",
                "colors": {
                    "sent": "#3B82F6",
                    "received": "#10B981"
                }
            }
        })

        # Database Connections
        dashboard.add_widget({
            "id": "database_connections",
            "type": "gauge_chart",
            "title": "Database Connections",
            "grid_position": {"x": 0, "y": 12, "w": 6, "h": 4},
            "data_source": "/monitoring/metrics",
            "metric_name": "database_connections_active",
            "refresh_interval": 30,
            "display": {
                "show_value": True,
                "show_percentage": True,
                "thresholds": [
                    {"value": 50, "color": "#10B981"},
                    {"value": 80, "color": "#F59E0B"},
                    {"value": 95, "color": "#EF4444"}
                ]
            }
        })

        # Uptime Timeline
        dashboard.add_widget({
            "id": "uptime_timeline",
            "type": "status_timeline",
            "title": "Component Uptime (Last 7 Days)",
            "grid_position": {"x": 6, "y": 12, "w": 6, "h": 4},
            "data_source": "/monitoring/health/components",
            "time_range": "7d",
            "refresh_interval": 300,
            "display": {
                "group_by": "component_type",
                "show_percentage": True
            }
        })

        return dashboard.to_dict()

    @staticmethod
    def get_all_dashboards() -> List[Dict[str, Any]]:
        """Get all pre-configured dashboards"""
        return [
            MonitoringDashboards.system_overview_dashboard(),
            MonitoringDashboards.agents_dashboard(),
            MonitoringDashboards.performance_dashboard(),
            MonitoringDashboards.alerts_dashboard(),
            MonitoringDashboards.infrastructure_dashboard()
        ]


class DashboardRenderer:
    """Dashboard HTML/JavaScript renderer"""

    @staticmethod
    def render_dashboard_html(dashboard: Dict[str, Any]) -> str:
        """Render dashboard as HTML page"""
        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{dashboard['name']} - AutoAdmin Monitoring</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f8fafc; }}
        .header {{ background: white; border-bottom: 1px solid #e2e8f0; padding: 1rem 2rem; }}
        .header h1 {{ color: #1e293b; font-size: 1.5rem; }}
        .header p {{ color: #64748b; margin-top: 0.5rem; }}
        .dashboard {{ padding: 2rem; }}
        .widget-grid {{ display: grid; grid-template-columns: repeat(12, 1fr); gap: 1rem; }}
        .widget {{ background: white; border-radius: 8px; border: 1px solid #e2e8f0; padding: 1rem; }}
        .widget-title {{ font-size: 0.875rem; font-weight: 600; color: #374151; margin-bottom: 1rem; }}
        .refresh-info {{ text-align: center; color: #6b7280; font-size: 0.75rem; margin-top: 2rem; }}
        .status-healthy {{ color: #10b981; }}
        .status-degraded {{ color: #f59e0b; }}
        .status-unhealthy {{ color: #ef4444; }}
        .metric-value {{ font-size: 2rem; font-weight: bold; color: #1e293b; }}
        .metric-label {{ color: #6b7280; font-size: 0.875rem; }}
        @media (max-width: 768px) {{ .dashboard {{ padding: 1rem; }} .widget-grid {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{dashboard['name']}</h1>
        <p>{dashboard['description']}</p>
    </div>
    <div class="dashboard">
        <div class="widget-grid" id="widget-grid">
            <!-- Widgets will be rendered here -->
        </div>
    </div>
    <div class="refresh-info">
        Last updated: <span id="last-updated">Never</span> | Auto-refresh: 30s
    </div>

    <script>
        const dashboard = {json.dumps(dashboard)};

        function renderWidgets() {{
            const grid = document.getElementById('widget-grid');
            grid.innerHTML = '';

            dashboard.widgets.forEach(widget => {{
                const widgetEl = document.createElement('div');
                widgetEl.className = 'widget';
                widgetEl.style.gridColumn = `span ${{widget.grid_position.w}}`;
                widgetEl.style.gridRow = `span ${{widget.grid_position.h}}`;

                widgetEl.innerHTML = `
                    <div class="widget-title">${{widget.title}}</div>
                    <div id="widget-${{widget.id}}">Loading...</div>
                `;

                grid.appendChild(widgetEl);

                // Load widget data
                loadWidgetData(widget);
            }});
        }}

        async function loadWidgetData(widget) {{
            try {{
                const response = await axios.get(widget.data_source);
                const data = response.data;

                const container = document.getElementById(`widget-${{widget.id}}`);

                switch(widget.type) {{
                    case 'status_panel':
                        renderStatusPanel(container, data);
                        break;
                    case 'timeseries_chart':
                        renderTimeSeriesChart(container, widget, data);
                        break;
                    case 'gauge_chart':
                        renderGaugeChart(container, widget, data);
                        break;
                    case 'alerts_list':
                        renderAlertsList(container, data);
                        break;
                    default:
                        container.innerHTML = JSON.stringify(data, null, 2);
                }}
            }} catch (error) {{
                const container = document.getElementById(`widget-${{widget.id}}`);
                container.innerHTML = `<div style="color: #ef4444;">Error loading data: ${{error.message}}</div>`;
            }}
        }}

        function renderStatusPanel(container, data) {{
            const statusClass = data.status === 'healthy' ? 'status-healthy' :
                              data.status === 'degraded' ? 'status-degraded' : 'status-unhealthy';

            container.innerHTML = `
                <div style="text-align: center;">
                    <div class="metric-value ${{statusClass}}">${{data.status.toUpperCase()}}</div>
                    <div class="metric-label">Overall Status</div>
                    <div style="margin-top: 1rem;">
                        <div>Components: ${{data.summary.healthy_components}}/${{data.summary.total_components}} healthy</div>
                        <div>Uptime: ${{Math.floor(data.uptime_seconds / 3600)}}h ${{Math.floor((data.uptime_seconds % 3600) / 60)}}m</div>
                    </div>
                </div>
            `;
        }}

        function renderTimeSeriesChart(container, widget, data) {{
            container.innerHTML = '<canvas></canvas>';
            const canvas = container.querySelector('canvas');

            // Simplified chart rendering - in production, use proper chart configuration
            new Chart(canvas, {{
                type: 'line',
                data: {{
                    labels: ['Now'], // Simplified for demo
                    datasets: [{{
                        label: widget.title,
                        data: [data[widget.metric_name] || 0],
                        borderColor: widget.display.line_color || '#3B82F6',
                        fill: widget.display.fill_area || false
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false
                }}
            }});
        }}

        function renderGaugeChart(container, widget, data) {{
            const value = data[widget.metric_name] || 0;
            container.innerHTML = `
                <div style="text-align: center;">
                    <div class="metric-value">${{value.toFixed(1)}}%</div>
                    <div class="metric-label">${{widget.title}}</div>
                </div>
            `;
        }}

        function renderAlertsList(container, data) {{
            if (!data.alerts || data.alerts.length === 0) {{
                container.innerHTML = '<div style="color: #10b981;">No active alerts</div>';
                return;
            }}

            const alertsHtml = data.alerts.slice(0, 5).map(alert => `
                <div style="margin-bottom: 0.5rem; padding: 0.5rem; border-left: 3px solid #${{
                    alert.severity === 'critical' ? 'ef4444' :
                    alert.severity === 'error' ? 'f59e0b' :
                    alert.severity === 'warning' ? '10b981' : '6b7280'
                }}; background: #f9fafb;">
                    <div style="font-weight: 600; color: #1e293b;">${{alert.rule_name}}</div>
                    <div style="font-size: 0.875rem; color: #6b7280;">${{alert.message}}</div>
                    <div style="font-size: 0.75rem; color: #9ca3af;">${{new Date(alert.timestamp).toLocaleString()}}</div>
                </div>
            `).join('');

            container.innerHTML = alertsHtml;
        }}

        function updateLastUpdated() {{
            document.getElementById('last-updated').textContent = new Date().toLocaleString();
        }}

        // Initial render
        renderWidgets();
        updateLastUpdated();

        // Auto-refresh every 30 seconds
        setInterval(() => {{
            renderWidgets();
            updateLastUpdated();
        }}, 30000);
    </script>
</body>
</html>
        """

    @staticmethod
    def export_dashboard_config(dashboard: Dict[str, Any], format: str = "json") -> str:
        """Export dashboard configuration in specified format"""
        if format == "json":
            return json.dumps(dashboard, indent=2)
        elif format == "grafana":
            # Convert to Grafana dashboard format
            return MonitoringDashboards._convert_to_grafana(dashboard)
        else:
            raise ValueError(f"Unsupported format: {format}")

    @staticmethod
    def _convert_to_grafana(dashboard: Dict[str, Any]) -> str:
        """Convert dashboard to Grafana format"""
        # This is a simplified conversion - in production, implement full Grafana JSON schema
        grafana_dashboard = {
            "dashboard": {
                "id": None,
                "title": dashboard["name"],
                "tags": ["autoadmin"],
                "timezone": "browser",
                "panels": [],
                "time": {
                    "from": "now-1h",
                    "to": "now"
                },
                "refresh": "30s"
            }
        }

        # Convert widgets to Grafana panels
        for widget in dashboard["widgets"]:
            panel = {
                "id": len(grafana_dashboard["dashboard"]["panels"]) + 1,
                "title": widget["title"],
                "type": MonitoringDashboards._convert_widget_type_to_grafana(widget["type"]),
                "gridPos": {
                    "x": widget["grid_position"]["x"],
                    "y": widget["grid_position"]["y"],
                    "w": widget["grid_position"]["w"],
                    "h": widget["grid_position"]["h"]
                },
                "targets": [
                    {
                        "expr": widget.get("metric_name", "up"),
                        "legendFormat": "{{__name__}}"
                    }
                ]
            }
            grafana_dashboard["dashboard"]["panels"].append(panel)

        return json.dumps(grafana_dashboard, indent=2)

    @staticmethod
    def _convert_widget_type_to_grafana(widget_type: str) -> str:
        """Convert widget type to Grafana panel type"""
        type_mapping = {
            "timeseries_chart": "timeseries",
            "gauge_chart": "stat",
            "status_panel": "stat",
            "alerts_list": "table",
            "bar_chart": "barchart",
            "pie_chart": "piechart",
            "heatmap_chart": "heatmap"
        }
        return type_mapping.get(widget_type, "stat")


# Create all dashboards
def create_all_dashboards() -> Dict[str, Dict[str, Any]]:
    """Create all monitoring dashboards"""
    dashboards = MonitoringDashboards.get_all_dashboards()
    return {dashboard["name"]: dashboard for dashboard in dashboards}