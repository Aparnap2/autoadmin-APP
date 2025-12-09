"""
File management related Pydantic models
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator

from .common import BaseResponse, PaginatedResponse


class FileType(str, Enum):
    """File type enumeration"""
    DOCUMENT = "document"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    ARCHIVE = "archive"
    DATA = "data"
    CODE = "code"
    TEXT = "text"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    PDF = "pdf"
    OTHER = "other"


class FileStatus(str, Enum):
    """File status enumeration"""
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DELETED = "deleted"
    CORRUPTED = "corrupted"


class FileMetadata(BaseModel):
    """File metadata model"""
    id: str = Field(description="File ID")
    filename: str = Field(description="Original filename")
    display_name: Optional[str] = Field(default=None, description="Display name")
    file_type: FileType = Field(description="File type")
    mime_type: str = Field(description="MIME type")
    size_bytes: int = Field(ge=0, description="File size in bytes")
    size_human: str = Field(description="Human-readable file size")
    checksum: Optional[str] = Field(default=None, description="File checksum (SHA-256)")
    storage_path: str = Field(description="Storage path")
    public_url: Optional[str] = Field(default=None, description="Public URL")
    download_url: Optional[str] = Field(default=None, description="Download URL")
    thumbnail_url: Optional[str] = Field(default=None, description="Thumbnail URL")
    status: FileStatus = Field(default=FileStatus.UPLOADING, description="File status")
    uploaded_by: Optional[str] = Field(default=None, description="Uploader identifier")
    team: Optional[str] = Field(default=None, description="Team identifier")
    tags: List[str] = Field(default_factory=list, description="File tags")
    description: Optional[str] = Field(default=None, description="File description")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    expires_at: Optional[datetime] = Field(default=None, description="Expiration timestamp")
    download_count: int = Field(default=0, ge=0, description="Download count")
    last_downloaded_at: Optional[datetime] = Field(default=None, description="Last download timestamp")
    is_public: bool = Field(default=False, description="Whether file is publicly accessible")
    is_encrypted: bool = Field(default=False, description="Whether file is encrypted")
    encryption_key_id: Optional[str] = Field(default=None, description="Encryption key ID")
    virus_scan_status: Optional[str] = Field(default=None, description="Virus scan status")
    processing_status: Optional[str] = Field(default=None, description="Processing status")
    extracted_text: Optional[str] = Field(default=None, description="Extracted text content")
    extracted_metadata: Dict[str, Any] = Field(default_factory=dict, description="Extracted metadata")


class FileUploadRequest(BaseModel):
    """File upload request model"""
    filename: str = Field(description="File name")
    file_type: Optional[FileType] = Field(default=None, description="File type")
    mime_type: Optional[str] = Field(default=None, description="MIME type")
    display_name: Optional[str] = Field(default=None, description="Display name")
    description: Optional[str] = Field(default=None, description="File description")
    tags: List[str] = Field(default_factory=list, description="File tags")
    team: Optional[str] = Field(default=None, description="Team identifier")
    is_public: bool = Field(default=False, description="Whether file should be public")
    encrypt: bool = Field(default=False, description="Whether to encrypt file")
    expires_at: Optional[datetime] = Field(default=None, description="Expiration timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    auto_extract_text: bool = Field(default=True, description="Auto-extract text content")
    generate_thumbnail: bool = Field(default=True, description="Generate thumbnail")
    virus_scan: bool = Field(default=True, description="Perform virus scan")

    @validator("filename")
    def validate_filename(cls, v):
        """Validate filename"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Filename cannot be empty")
        if len(v) > 255:
            raise ValueError("Filename too long (max 255 characters)")
        # Check for invalid characters
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
        if any(char in v for char in invalid_chars):
            raise ValueError(f"Filename contains invalid characters: {invalid_chars}")
        return v.strip()


class FileUploadResponse(BaseResponse):
    """File upload response model"""
    upload_url: str = Field(description="Presigned upload URL")
    file_id: str = Field(description="File ID")
    upload_id: str = Field(description="Upload ID")
    expires_at: datetime = Field(description="Upload URL expiration")
    max_file_size: int = Field(description="Maximum file size in bytes")
    allowed_types: List[str] = Field(description="Allowed file types")
    metadata: FileMetadata = Field(description="File metadata")


class FileDownloadRequest(BaseModel):
    """File download request model"""
    file_id: str = Field(description="File ID")
    version: Optional[int] = Field(default=None, description="File version")
    download_as: Optional[str] = Field(default=None, description="Download as filename")
    range_header: Optional[str] = Field(default=None, description="Range header for partial downloads")
    thumbnail: bool = Field(default=False, description="Download thumbnail instead of full file")
    expiration_seconds: int = Field(default=3600, ge=60, le=86400, description="URL expiration in seconds")


class FileDownloadResponse(BaseResponse):
    """File download response model"""
    download_url: str = Field(description="Presigned download URL")
    file_id: str = Field(description="File ID")
    filename: str = Field(description="Filename")
    size_bytes: int = Field(description="File size in bytes")
    mime_type: str = Field(description="MIME type")
    expires_at: datetime = Field(description="Download URL expiration")
    metadata: FileMetadata = Field(description="File metadata")


class FileListResponse(PaginatedResponse[FileMetadata]):
    """Paginated file list response"""
    pass


class FileDeleteRequest(BaseModel):
    """File delete request model"""
    file_id: str = Field(description="File ID")
    permanent: bool = Field(default=False, description="Permanent deletion (vs soft delete)")
    confirm: bool = Field(default=False, description="Confirmation required for permanent deletion")

    @validator("confirm")
    def validate_confirmation_for_permanent(cls, v, values):
        """Validate confirmation for permanent deletion"""
        if values.get("permanent") and not v:
            raise ValueError("Confirmation required for permanent deletion")
        return v


class FileDeleteResponse(BaseResponse):
    """File delete response model"""
    file_id: str = Field(description="Deleted file ID")
    deleted: bool = Field(description="Whether file was deleted")
    permanent: bool = Field(description="Whether deletion was permanent")


class FileUpdateRequest(BaseModel):
    """File update request model"""
    file_id: str = Field(description="File ID")
    display_name: Optional[str] = Field(default=None, description="New display name")
    description: Optional[str] = Field(default=None, description="New description")
    tags: Optional[List[str]] = Field(default=None, description="New tags")
    is_public: Optional[bool] = Field(default=None, description="Public status")
    expires_at: Optional[datetime] = Field(default=None, description="New expiration timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata updates")


class FileUpdateResponse(BaseResponse):
    """File update response model"""
    file_id: str = Field(description="Updated file ID")
    updated_fields: List[str] = Field(description="Updated fields")
    metadata: FileMetadata = Field(description="Updated file metadata")


class FileSearchRequest(BaseModel):
    """File search request model"""
    query: Optional[str] = Field(default=None, description="Search query")
    file_types: Optional[List[FileType]] = Field(default=None, description="Filter by file types")
    tags: Optional[List[str]] = Field(default=None, description="Filter by tags")
    team: Optional[str] = Field(default=None, description="Filter by team")
    uploaded_by: Optional[str] = Field(default=None, description="Filter by uploader")
    status: Optional[FileStatus] = Field(default=None, description="Filter by status")
    size_min: Optional[int] = Field(default=None, ge=0, description="Minimum file size")
    size_max: Optional[int] = Field(default=None, ge=0, description="Maximum file size")
    date_from: Optional[datetime] = Field(default=None, description="Filter from date")
    date_to: Optional[datetime] = Field(default=None, description="Filter to date")
    has_text_content: Optional[bool] = Field(default=None, description="Filter by extracted text presence")
    include_deleted: bool = Field(default=False, description="Include deleted files")


class FileProcessingRequest(BaseModel):
    """File processing request model"""
    file_id: str = Field(description="File ID")
    operations: List[str] = Field(description="Processing operations")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Processing parameters")
    notify_on_complete: bool = Field(default=False, description="Notify when processing completes")
    webhook_url: Optional[str] = Field(default=None, description="Webhook URL for notifications")


class FileProcessingResponse(BaseResponse):
    """File processing response model"""
    processing_id: str = Field(description="Processing job ID")
    file_id: str = Field(description="File ID")
    operations: List[str] = Field(description="Requested operations")
    estimated_time: Optional[int] = Field(default=None, description="Estimated processing time in seconds")


class FileStats(BaseModel):
    """File statistics model"""
    total_files: int = Field(description="Total files")
    total_size_bytes: int = Field(description="Total storage used in bytes")
    total_size_human: str = Field(description="Total storage used (human readable)")
    files_by_type: Dict[FileType, int] = Field(description="Files by type")
    files_by_status: Dict[FileStatus, int] = Field(description="Files by status")
    average_file_size: float = Field(description="Average file size in bytes")
    largest_file: Optional[Dict[str, Any]] = Field(default=None, description="Largest file info")
    storage_quota: Optional[int] = Field(default=None, description="Storage quota in bytes")
    storage_used_percentage: float = Field(description="Storage used percentage")
    upload_count_today: int = Field(description="Uploads today")
    download_count_today: int = Field(description="Downloads today")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Stats timestamp")