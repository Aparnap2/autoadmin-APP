"""
Webhook-related Pydantic models
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator

from .common import BaseResponse, PaginatedResponse


class WebhookEventType(str, Enum):
    """Webhook event type enumeration"""
    GITHUB_PUSH = "github_push"
    GITHUB_PULL_REQUEST = "github_pull_request"
    GITHUB_ISSUE = "github_issue"
    HUBSPOT_CONTACT_CREATED = "hubspot_contact_created"
    HUBSPOT_DEAL_CREATED = "hubspot_deal_created"
    CUSTOM = "custom"


class WebhookStatus(str, Enum):
    """Webhook status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PENDING = "pending"


class WebhookEvent(BaseModel):
    """Webhook event model"""
    id: str = Field(description="Event ID")
    type: WebhookEventType = Field(description="Event type")
    source: str = Field(description="Event source")
    payload: Dict[str, Any] = Field(description="Event payload")
    headers: Dict[str, str] = Field(default_factory=dict, description="Event headers")
    signature: Optional[str] = Field(default=None, description="Event signature")
    timestamp: datetime = Field(description="Event timestamp")
    processed: bool = Field(default=False, description="Whether event has been processed")
    processing_attempts: int = Field(default=0, description="Number of processing attempts")
    error_message: Optional[str] = Field(default=None, description="Processing error message")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    processed_at: Optional[datetime] = Field(default=None, description="Processing timestamp")


class WebhookConfig(BaseModel):
    """Webhook configuration model"""
    id: str = Field(description="Config ID")
    name: str = Field(description="Config name")
    url: str = Field(description="Webhook URL")
    event_types: List[WebhookEventType] = Field(description="Supported event types")
    secret: Optional[str] = Field(default=None, description="Webhook secret")
    status: WebhookStatus = Field(default=WebhookStatus.ACTIVE, description="Webhook status")
    retry_count: int = Field(default=3, ge=0, le=10, description="Retry count")
    timeout_seconds: int = Field(default=30, ge=1, description="Timeout in seconds")
    headers: Dict[str, str] = Field(default_factory=dict, description="Additional headers")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Event filters")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    created_by: Optional[str] = Field(default=None, description="Creator identifier")
    description: Optional[str] = Field(default=None, description="Config description")


class GitHubEvent(BaseModel):
    """GitHub-specific event model"""
    event_type: str = Field(description="GitHub event type")
    action: Optional[str] = Field(default=None, description="Event action")
    repository: Dict[str, Any] = Field(description="Repository information")
    sender: Dict[str, Any] = Field(description="Sender information")
    payload: Dict[str, Any] = Field(description="Full event payload")
    timestamp: datetime = Field(description="Event timestamp")
    commit_hash: Optional[str] = Field(default=None, description="Commit hash")
    branch: Optional[str] = Field(default=None, description="Branch name")
    pull_request_number: Optional[int] = Field(default=None, description="Pull request number")
    issue_number: Optional[int] = Field(default=None, description="Issue number")


class HubSpotEvent(BaseModel):
    """HubSpot-specific event model"""
    event_type: str = Field(description="HubSpot event type")
    object_type: str = Field(description="Object type (contact, deal, company)")
    object_id: str = Field(description="Object ID")
    change_source: Optional[str] = Field(default=None, description="Change source")
    property_changes: List[Dict[str, Any]] = Field(default_factory=list, description="Property changes")
    payload: Dict[str, Any] = Field(description="Full event payload")
    timestamp: datetime = Field(description="Event timestamp")


class CustomEvent(BaseModel):
    """Custom webhook event model"""
    event_type: str = Field(description="Custom event type")
    source: str = Field(description="Event source")
    payload: Dict[str, Any] = Field(description="Event payload")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Event metadata")
    timestamp: datetime = Field(description="Event timestamp")


class WebhookPayload(BaseModel):
    """Generic webhook payload model"""
    event: WebhookEvent = Field(description="Webhook event")
    raw_payload: Dict[str, Any] = Field(description="Raw payload data")
    headers: Dict[str, str] = Field(default_factory=dict, description="Request headers")
    query_params: Dict[str, str] = Field(default_factory=dict, description="Query parameters")
    source_ip: Optional[str] = Field(default=None, description="Source IP address")
    user_agent: Optional[str] = Field(default=None, description="User agent")


class WebhookResponse(BaseResponse):
    """Webhook processing response model"""
    event_id: str = Field(description="Processed event ID")
    processed: bool = Field(description="Whether event was processed")
    action_taken: Optional[str] = Field(default=None, description="Action taken")
    processing_time_ms: float = Field(description="Processing time in milliseconds")


class WebhookSubscription(BaseModel):
    """Webhook subscription model"""
    id: str = Field(description="Subscription ID")
    webhook_config_id: str = Field(description="Webhook config ID")
    subscriber_url: str = Field(description="Subscriber URL")
    event_types: List[WebhookEventType] = Field(description="Subscribed event types")
    status: WebhookStatus = Field(default=WebhookStatus.ACTIVE, description="Subscription status")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Event filters")
    retry_count: int = Field(default=3, ge=0, description="Retry count")
    timeout_seconds: int = Field(default=30, ge=1, description="Timeout in seconds")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    last_delivery: Optional[datetime] = Field(default=None, description="Last successful delivery")
    delivery_count: int = Field(default=0, description="Total delivery count")
    failure_count: int = Field(default=0, description="Failure count")


class WebhookDeliveryAttempt(BaseModel):
    """Webhook delivery attempt model"""
    id: str = Field(description="Attempt ID")
    subscription_id: str = Field(description="Subscription ID")
    event_id: str = Field(description="Event ID")
    status: str = Field(description="Delivery status (success, failure, pending)")
    response_code: Optional[int] = Field(default=None, description="HTTP response code")
    response_body: Optional[str] = Field(default=None, description="Response body")
    error_message: Optional[str] = Field(default=None, description="Error message")
    attempt_number: int = Field(ge=1, description="Attempt number")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Attempt timestamp")
    duration_ms: float = Field(description="Attempt duration in milliseconds")


class WebhookStats(BaseModel):
    """Webhook statistics model"""
    total_events: int = Field(description="Total events received")
    events_by_type: Dict[WebhookEventType, int] = Field(description="Events by type")
    successful_deliveries: int = Field(description="Successful deliveries")
    failed_deliveries: int = Field(description="Failed deliveries")
    average_delivery_time: float = Field(description="Average delivery time in milliseconds")
    active_subscriptions: int = Field(description="Active subscriptions")
    active_webhooks: int = Field(description="Active webhook configs")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Stats timestamp")