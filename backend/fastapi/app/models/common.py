"""
Common Pydantic models used across the application
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field, validator


class SortOrder(str, Enum):
    """Sort order enumeration"""
    ASC = "asc"
    DESC = "desc"


class BaseResponse(BaseModel):
    """Base response model with common fields"""
    success: bool = Field(default=True, description="Operation success status")
    message: Optional[str] = Field(default=None, description="Response message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class ErrorResponse(BaseResponse):
    """Error response model"""
    success: bool = Field(default=False, description="Operation failed")
    error_code: str = Field(description="Error code for programmatic handling")
    error_details: Dict[str, Any] = Field(default_factory=dict, description="Additional error details")


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = Field(description="Service health status")
    version: str = Field(description="Service version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp")
    services: Dict[str, str] = Field(default_factory=dict, description="Individual service statuses")
    uptime_seconds: Optional[float] = Field(default=None, description="Service uptime in seconds")
    memory_usage_mb: Optional[float] = Field(default=None, description="Memory usage in MB")


class MetricsResponse(BaseModel):
    """Metrics response model"""
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Metrics timestamp")
    metrics: Dict[str, Any] = Field(description="Application metrics")
    system_metrics: Dict[str, Any] = Field(default_factory=dict, description="System-level metrics")


class DateRange(BaseModel):
    """Date range model for filtering"""
    start_date: Optional[datetime] = Field(default=None, description="Start date (inclusive)")
    end_date: Optional[datetime] = Field(default=None, description="End date (inclusive)")

    @validator("end_date")
    def validate_date_range(cls, v, values):
        """Validate that end_date is after start_date"""
        if v and "start_date" in values and values["start_date"]:
            if v <= values["start_date"]:
                raise ValueError("end_date must be after start_date")
        return v


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response model"""
    items: List[T] = Field(description="List of items")
    total: int = Field(description="Total number of items")
    page: int = Field(ge=1, description="Current page number")
    page_size: int = Field(ge=1, le=100, description="Number of items per page")
    total_pages: int = Field(description="Total number of pages")
    has_next: bool = Field(description="Whether there are more pages")
    has_prev: bool = Field(description="Whether there are previous pages")

    @validator("total_pages", always=True)
    def calculate_total_pages(cls, v, values):
        """Calculate total pages based on total and page_size"""
        if "total" in values and "page_size" in values:
            total = values["total"]
            page_size = values["page_size"]
            return (total + page_size - 1) // page_size
        return v

    @validator("has_next", always=True)
    def calculate_has_next(cls, v, values):
        """Calculate whether there are more pages"""
        if "page" in values and "total_pages" in values:
            return values["page"] < values["total_pages"]
        return False

    @validator("has_prev", always=True)
    def calculate_has_prev(cls, v, values):
        """Calculate whether there are previous pages"""
        if "page" in values:
            return values["page"] > 1
        return False


class PaginationParams(BaseModel):
    """Pagination parameters for requests"""
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Number of items per page")
    sort_by: Optional[str] = Field(default=None, description="Field to sort by")
    sort_order: SortOrder = Field(default=SortOrder.ASC, description="Sort order")


class FilterParams(BaseModel):
    """Base filter parameters"""
    search: Optional[str] = Field(default=None, description="Search term")
    date_range: Optional[DateRange] = Field(default=None, description="Date range filter")


class CreateResponse(BaseResponse):
    """Response for create operations"""
    id: str = Field(description="Created resource ID")
    resource_type: str = Field(description="Type of created resource")


class UpdateResponse(BaseResponse):
    """Response for update operations"""
    id: str = Field(description="Updated resource ID")
    updated_fields: List[str] = Field(description="List of updated fields")
    resource_type: str = Field(description="Type of updated resource")


class DeleteResponse(BaseResponse):
    """Response for delete operations"""
    id: str = Field(description="Deleted resource ID")
    resource_type: str = Field(description="Type of deleted resource")
    deleted: bool = Field(description="Whether the resource was successfully deleted")


class BulkOperationResponse(BaseResponse):
    """Response for bulk operations"""
    total: int = Field(description="Total number of operations")
    successful: int = Field(description="Number of successful operations")
    failed: int = Field(description="Number of failed operations")
    results: List[Dict[str, Any]] = Field(description="Detailed results for each operation")
    errors: List[str] = Field(default_factory=list, description="List of error messages")


class SearchParams(BaseModel):
    """Search parameters"""
    query: str = Field(description="Search query")
    fields: Optional[List[str]] = Field(default=None, description="Fields to search in")
    fuzzy: bool = Field(default=False, description="Enable fuzzy search")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of results")


class ExportParams(BaseModel):
    """Export parameters"""
    format: str = Field(default="json", description="Export format (json, csv, xlsx)")
    fields: Optional[List[str]] = Field(default=None, description="Fields to include in export")
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Export filters")