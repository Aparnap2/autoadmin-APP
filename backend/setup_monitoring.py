#!/usr/bin/env python3
"""
AutoAdmin Monitoring System Setup Script

This script helps configure and test the comprehensive monitoring system
for the AutoAdmin application.
"""

import asyncio
import os
import sys
import json
from datetime import datetime
from typing import Dict, Any

# Import monitoring components
from monitoring import (
    metrics_collector,
    health_checker,
    alert_manager,
    error_tracker,
    ServiceComponent,
    LogLevel
)
from monitoring.integration import initialize_monitoring
from monitoring.logger import get_logger
from monitoring.dashboard import create_all_dashboards

logger = get_logger("setup_monitoring")


class MonitoringSetup:
    """Monitoring system setup and configuration utility"""

    def __init__(self):
        self.config = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """Load monitoring configuration from environment and defaults"""
        config = {
            "environment": os.getenv("ENVIRONMENT", "development"),
            "database": {
                "connection_string": os.getenv("DATABASE_URL")
            },
            "redis": {
                "host": os.getenv("REDIS_HOST", "localhost"),
                "port": int(os.getenv("REDIS_PORT", "6379")),
                "password": os.getenv("REDIS_PASSWORD"),
                "db": int(os.getenv("REDIS_DB", "0"))
            },
            "qdrant": {
                "url": os.getenv("QDRANT_URL"),
                "api_key": os.getenv("QDRANT_API_KEY")
            },
            "metrics_collection_interval": int(os.getenv("METRICS_INTERVAL", "15")),
            "alert_evaluation_interval": int(os.getenv("ALERT_INTERVAL", "60")),
            "metrics_retention_hours": int(os.getenv("METRICS_RETENTION", "24")),
            "health_check_path": os.getenv("HEALTH_CHECK_PATH", "/")
        }

        return config

    async def setup_monitoring(self):
        """Set up the complete monitoring system"""
        print("🚀 Setting up AutoAdmin Monitoring System...")
        print(f"📊 Environment: {self.config['environment']}")

        try:
            # Initialize monitoring system
            print("⚙️  Initializing monitoring components...")
            await initialize_monitoring(self.config)

            print("✅ Monitoring system initialized successfully!")
            return True

        except Exception as e:
            print(f"❌ Failed to initialize monitoring system: {e}")
            logger.error("Monitoring setup failed", component=ServiceComponent.MONITORING, error=e)
            return False

    async def test_components(self):
        """Test all monitoring components"""
        print("\n🧪 Testing Monitoring Components...")

        # Test metrics collection
        await self.test_metrics()

        # Test health checks
        await self.test_health_checks()

        # Test error tracking
        await self.test_error_tracking()

        # Test alerting (if configured)
        await self.test_alerting()

        print("✅ All component tests completed!")

    async def test_metrics(self):
        """Test metrics collection"""
        print("📈 Testing metrics collection...")

        # Test different metric types
        metrics_collector.increment("test_counter", 1, {"test": "setup"})
        metrics_collector.gauge("test_gauge", 42.0, {"test": "setup"})
        metrics_collector.timer("test_timer", 150.5, {"test": "setup"})
        metrics_collector.meter("test_meter", 3, {"test": "setup"})

        # Get metrics summary
        summary = metrics_collector.get_metrics_summary()
        print(f"   ✓ Metrics registered: {len(summary.get('metrics', {}))}")

        # Test system metrics
        metrics_collector.collect_system_metrics()
        print(f"   ✓ System metrics collected")

    async def test_health_checks(self):
        """Test health check system"""
        print("🏥 Testing health checks...")

        # Test system health
        system_health = await health_checker.get_system_health()
        print(f"   ✓ Overall health: {system_health.status.value}")
        print(f"   ✓ Components checked: {len(system_health.components)}")

        # Test specific health checks
        for check_name in health_checker.health_checks.keys():
            try:
                result = await health_checker.check_component_health(check_name)
                print(f"   ✓ {check_name}: {result.status.value} ({result.response_time_ms:.1f}ms)")
            except Exception as e:
                print(f"   ❌ {check_name}: Failed - {e}")

    async def test_error_tracking(self):
        """Test error tracking system"""
        print("🐛 Testing error tracking...")

        try:
            # Generate a test error
            raise ValueError("This is a test error for monitoring setup")
        except Exception as e:
            # Track the error
            from monitoring.error_tracking import ErrorContext, ErrorSeverity, ErrorCategory
            context = ErrorContext(
                component=ServiceComponent.MONITORING,
                custom_data={"setup_test": True}
            )

            error_id = await error_tracker.track_error(
                e,
                context=context,
                severity=ErrorSeverity.LOW,
                category=ErrorCategory.VALIDATION
            )

            print(f"   ✓ Error tracked: {error_id}")

            # Get error statistics
            stats = error_tracker.get_error_statistics(hours=1)
            print(f"   ✓ Error reports: {stats['total_reports']}")
            print(f"   ✓ Error occurrences: {stats['total_occurrences']}")

    async def test_alerting(self):
        """Test alerting system"""
        print("🚨 Testing alerting system...")

        # Get alert statistics
        stats = alert_manager.get_alert_statistics()
        print(f"   ✓ Alert rules registered: {len(alert_manager.alert_rules)}")
        print(f"   ✓ Notification channels: {len(alert_manager.notification_channels)}")
        print(f"   ✓ Active alerts: {stats['active_alerts']}")

        # Test alert evaluation (if we have metrics)
        try:
            metrics_summary = metrics_collector.get_metrics_summary()
            await alert_manager.evaluate_alert_rules(metrics_summary, {})
            print("   ✓ Alert rules evaluated")
        except Exception as e:
            print(f"   ⚠️  Alert evaluation test failed: {e}")

    def generate_dashboards(self):
        """Generate monitoring dashboards"""
        print("\n📊 Generating Monitoring Dashboards...")

        dashboards = create_all_dashboards()

        # Create dashboard directory
        dashboard_dir = "monitoring_dashboards"
        os.makedirs(dashboard_dir, exist_ok=True)

        for name, dashboard in dashboards.items():
            filename = f"{dashboard_dir}/{name.lower().replace(' ', '_')}.json"

            with open(filename, 'w') as f:
                json.dump(dashboard, f, indent=2, default=str)

            print(f"   ✓ Generated: {filename}")

        return dashboard_dir

    def generate_env_file(self):
        """Generate environment configuration file"""
        print("\n📝 Generating Environment Configuration...")

        env_file = "monitoring.env"

        with open(env_file, 'w') as f:
            f.write("# AutoAdmin Monitoring Configuration\n")
            f.write(f"# Generated on {datetime.utcnow().isoformat()}\n\n")

            f.write("# Environment\n")
            f.write(f"ENVIRONMENT={self.config['environment']}\n\n")

            f.write("# Metrics Configuration\n")
            f.write(f"METRICS_INTERVAL={self.config['metrics_collection_interval']}\n")
            f.write(f"METRICS_RETENTION={self.config['metrics_retention_hours']}\n\n")

            f.write("# Alerting Configuration\n")
            f.write(f"ALERT_INTERVAL={self.config['alert_evaluation_interval']}\n\n")

            f.write("# Database Configuration\n")
            if self.config['database']['connection_string']:
                f.write(f"DATABASE_URL={self.config['database']['connection_string']}\n")
            f.write("\n")

            f.write("# Redis Configuration\n")
            f.write(f"REDIS_HOST={self.config['redis']['host']}\n")
            f.write(f"REDIS_PORT={self.config['redis']['port']}\n")
            if self.config['redis']['password']:
                f.write(f"REDIS_PASSWORD={self.config['redis']['password']}\n")
            f.write(f"REDIS_DB={self.config['redis']['db']}\n\n")

            f.write("# Vector Database Configuration\n")
            if self.config['qdrant']['url']:
                f.write(f"QDRANT_URL={self.config['qdrant']['url']}\n")
            if self.config['qdrant']['api_key']:
                f.write(f"QDRANT_API_KEY={self.config['qdrant']['api_key']}\n")
            f.write("\n")

            f.write("# Email Alerting\n")
            f.write("# ALERT_EMAIL_SMTP_HOST=smtp.gmail.com\n")
            f.write("# ALERT_EMAIL_SMTP_PORT=587\n")
            f.write("# ALERT_EMAIL_USERNAME=your-email@gmail.com\n")
            f.write("# ALERT_EMAIL_PASSWORD=your-password\n")
            f.write("# ALERT_EMAIL_FROM=your-email@gmail.com\n")
            f.write("# ALERT_EMAIL_TO=admin@company.com\n\n")

            f.write("# Slack Alerting\n")
            f.write("# ALERT_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...\n\n")

            f.write("# PagerDuty Alerting\n")
            f.write("# ALERT_PAGERDUTY_INTEGRATION_KEY=your-integration-key\n\n")

            f.write("# Webhook Alerting\n")
            f.write("# ALERT_WEBHOOK_URL=https://your-webhook.com/alerts\n")
            f.write("# ALERT_WEBHOOK_TOKEN=your-token\n\n")

            f.write("# Sentry Error Tracking\n")
            f.write("# SENTRY_DSN=https://your-sentry-dsn\n")

        print(f"   ✓ Generated: {env_file}")
        return env_file

    def print_next_steps(self):
        """Print next steps for using the monitoring system"""
        print("\n🎯 Next Steps:")
        print("1. Configure environment variables using monitoring.env")
        print("2. Set up notification channels (email, Slack, PagerDuty)")
        print("3. Deploy the application with monitoring enabled")
        print("4. Access monitoring endpoints:")
        print("   - Health: http://localhost:8000/health")
        print("   - Metrics: http://localhost:8000/monitoring/metrics")
        print("   - Alerts: http://localhost:8000/monitoring/alerts")
        print("   - Dashboard: http://localhost:8000/monitoring/status")
        print("5. View generated dashboards in the monitoring_dashboards/ directory")
        print("6. Integrate with external tools:")
        print("   - Prometheus: http://localhost:8000/monitoring/metrics?format=prometheus")
        print("   - Grafana: Import dashboard configurations")
        print("   - ELK Stack: Configure to ingest structured logs")

    async def run_setup(self):
        """Run the complete setup process"""
        print("=" * 60)
        print("🔧 AutoAdmin Monitoring System Setup")
        print("=" * 60)

        # Setup monitoring system
        if not await self.setup_monitoring():
            return False

        # Test components
        await self.test_components()

        # Generate dashboards
        dashboard_dir = self.generate_dashboards()

        # Generate environment file
        env_file = self.generate_env_file()

        # Print monitoring summary
        await self.print_monitoring_summary()

        # Print next steps
        self.print_next_steps()

        print("\n✅ Monitoring system setup completed successfully!")
        return True

    async def print_monitoring_summary(self):
        """Print a summary of the configured monitoring system"""
        print("\n📋 Monitoring System Summary:")

        # Metrics summary
        metrics_summary = metrics_collector.get_metrics_summary()
        print(f"📈 Metrics:")
        print(f"   - Total metrics: {len(metrics_summary.get('metrics', {}))}")
        print(f"   - Collection interval: {self.config['metrics_collection_interval']}s")
        print(f"   - Retention: {self.config['metrics_retention_hours']}h")

        # Health checks summary
        print(f"🏥 Health Checks:")
        print(f"   - Total checks: {len(health_checker.health_checks)}")
        print(f"   - Components: {list(health_checker.health_checks.keys())}")

        # Alerting summary
        alert_stats = alert_manager.get_alert_statistics()
        print(f"🚨 Alerting:")
        print(f"   - Alert rules: {len(alert_manager.alert_rules)}")
        print(f"   - Notification channels: {len(alert_manager.notification_channels)}")
        print(f"   - Active alerts: {alert_stats['active_alerts']}")

        # Error tracking summary
        error_stats = error_tracker.get_error_statistics(hours=24)
        print(f"🐛 Error Tracking:")
        print(f"   - Error reports: {error_stats['total_reports']}")
        print(f"   - Error occurrences: {error_stats['total_occurrences']}")


async def main():
    """Main setup script entry point"""
    setup = MonitoringSetup()

    try:
        success = await setup.run_setup()
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n⚠️  Setup interrupted by user")
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        logger.error("Setup script failed", component=ServiceComponent.MONITORING, error=e)
        sys.exit(1)


if __name__ == "__main__":
    # Check for required dependencies
    try:
        import psutil
        import aiohttp
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please install required dependencies:")
        print("pip install psutil aiohttp")
        sys.exit(1)

    # Run setup
    asyncio.run(main())