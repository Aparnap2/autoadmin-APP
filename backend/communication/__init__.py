"""
Communication module for AutoAdmin backend
Handles GitHub integration and webhook processing
"""

# from .github_integration import GitHubActionsIntegration
from .webhook_handler import WebhookHandler

__all__ = [
    # 'GitHubActionsIntegration',
    'WebhookHandler'
]