"""
Memory/Knowledge Graph related Pydantic models
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator

from .common import BaseResponse, PaginatedResponse


class NodeType(str, Enum):
    """Node type enumeration"""
    CONCEPT = "concept"
    ENTITY = "entity"
    DOCUMENT = "document"
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    EVENT = "event"
    FACT = "fact"
    QUESTION = "question"
    ANSWER = "answer"
    TASK = "task"
    NOTE = "note"
    CUSTOM = "custom"


class EdgeType(str, Enum):
    """Edge type enumeration"""
    RELATED_TO = "related_to"
    PART_OF = "part_of"
    HAS_A = "has_a"
    CONTAINS = "contains"
    DESCRIBES = "describes"
    PRECEDES = "precedes"
    FOLLOWS = "follows"
    CAUSES = "causes"
    ENABLES = "enables"
    REQUIRES = "requires"
    CONTRADICTS = "contradicts"
    SUPPORTS = "supports"
    ANSWERS = "answers"
    ASKS = "asks"
    REFERENCES = "references"
    DEPENDS_ON = "depends_on"
    INFLUENCES = "influences"
    CUSTOM = "custom"


class MemoryNode(BaseModel):
    """Memory node model"""
    id: str = Field(description="Node unique identifier")
    type: NodeType = Field(description="Node type")
    label: str = Field(description="Node label/name")
    content: str = Field(description="Node content/description")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Node properties")
    tags: List[str] = Field(default_factory=list, description="Node tags")
    embedding: Optional[List[float]] = Field(default=None, description="Vector embedding")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    created_by: Optional[str] = Field(default=None, description="Creator identifier")
    version: int = Field(default=1, ge=1, description="Node version")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    visibility: str = Field(default="private", description="Node visibility (public, private, team)")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")


class MemoryEdge(BaseModel):
    """Memory edge model"""
    id: str = Field(description="Edge unique identifier")
    source_id: str = Field(description="Source node ID")
    target_id: str = Field(description="Target node ID")
    type: EdgeType = Field(description="Edge type")
    label: Optional[str] = Field(default=None, description="Edge label")
    weight: float = Field(default=1.0, description="Edge weight/strength")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Edge properties")
    bidirectional: bool = Field(default=False, description="Whether edge is bidirectional")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    created_by: Optional[str] = Field(default=None, description="Creator identifier")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")


class MemoryGraph(BaseModel):
    """Memory graph model"""
    id: str = Field(description="Graph unique identifier")
    name: str = Field(description="Graph name")
    description: Optional[str] = Field(default=None, description="Graph description")
    nodes: Dict[str, MemoryNode] = Field(description="Graph nodes (ID -> Node)")
    edges: List[MemoryEdge] = Field(description="Graph edges")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    created_by: Optional[str] = Field(default=None, description="Creator identifier")
    version: int = Field(default=1, ge=1, description="Graph version")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    is_public: bool = Field(default=False, description="Whether graph is public")
    node_count: int = Field(default=0, description="Number of nodes")
    edge_count: int = Field(default=0, description="Number of edges")

    @validator("node_count", always=True)
    def calculate_node_count(cls, v, values):
        """Calculate node count from nodes dict"""
        if "nodes" in values:
            return len(values["nodes"])
        return v

    @validator("edge_count", always=True)
    def calculate_edge_count(cls, v, values):
        """Calculate edge count from edges list"""
        if "edges" in values:
            return len(values["edges"])
        return v


class MemoryQueryRequest(BaseModel):
    """Memory query request model"""
    query: str = Field(description="Query text or Cypher query")
    query_type: str = Field(default="natural_language", description="Query type (natural_language, cypher, sparql)")
    node_types: Optional[List[NodeType]] = Field(default=None, description="Filter by node types")
    edge_types: Optional[List[EdgeType]] = Field(default=None, description="Filter by edge types")
    tags: Optional[List[str]] = Field(default=None, description="Filter by tags")
    limit: int = Field(default=50, ge=1, le=500, description="Maximum results")
    offset: int = Field(default=0, ge=0, description="Result offset")
    include_embeddings: bool = Field(default=False, description="Include node embeddings")
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Similarity threshold")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Additional filters")
    sort_by: Optional[str] = Field(default=None, description="Sort field")
    sort_order: str = Field(default="desc", description="Sort order")

    @validator("query_type")
    def validate_query_type(cls, v):
        """Validate query type"""
        valid_types = ["natural_language", "cypher", "sparql", "traversal"]
        if v not in valid_types:
            raise ValueError(f"Invalid query type. Must be one of: {valid_types}")
        return v

    @validator("sort_order")
    def validate_sort_order(cls, v):
        """Validate sort order"""
        valid_orders = ["asc", "desc"]
        if v not in valid_orders:
            raise ValueError(f"Invalid sort order. Must be one of: {valid_orders}")
        return v


class MemoryQueryResult(BaseModel):
    """Memory query result model"""
    nodes: List[MemoryNode] = Field(description="Matching nodes")
    edges: List[MemoryEdge] = Field(description="Matching edges")
    paths: List[Dict[str, Any]] = Field(default_factory=list, description="Matching paths")
    total_nodes: int = Field(description="Total matching nodes")
    total_edges: int = Field(description="Total matching edges")
    query_time_ms: float = Field(description="Query execution time in milliseconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Query metadata")


class MemoryQueryResponse(BaseResponse):
    """Memory query response model"""
    result: MemoryQueryResult = Field(description="Query results")


class MemoryCreateRequest(BaseModel):
    """Memory create request model"""
    operation: str = Field(description="Operation type (node, edge, graph)")
    node: Optional[MemoryNode] = Field(default=None, description="Node to create")
    edge: Optional[MemoryEdge] = Field(default=None, description="Edge to create")
    graph: Optional[MemoryGraph] = Field(default=None, description="Graph to create")
    auto_generate_embedding: bool = Field(default=True, description="Auto-generate embedding")
    validate_connections: bool = Field(default=True, description="Validate node connections")

    @validator("operation")
    def validate_operation(cls, v):
        """Validate operation type"""
        valid_operations = ["node", "edge", "graph", "bulk"]
        if v not in valid_operations:
            raise ValueError(f"Invalid operation. Must be one of: {valid_operations}")
        return v

    @validator("node")
    def validate_node_for_operation(cls, v, values):
        """Validate node when operation is 'node'"""
        if values.get("operation") == "node" and v is None:
            raise ValueError("Node is required when operation is 'node'")
        return v

    @validator("edge")
    def validate_edge_for_operation(cls, v, values):
        """Validate edge when operation is 'edge'"""
        if values.get("operation") == "edge" and v is None:
            raise ValueError("Edge is required when operation is 'edge'")
        return v

    @validator("graph")
    def validate_graph_for_operation(cls, v, values):
        """Validate graph when operation is 'graph'"""
        if values.get("operation") == "graph" and v is None:
            raise ValueError("Graph is required when operation is 'graph'")
        return v


class MemoryCreateResponse(BaseResponse):
    """Memory create response model"""
    created_id: str = Field(description="ID of created resource")
    operation: str = Field(description="Operation performed")
    resource_type: str = Field(description="Type of created resource")


class MemoryUpdateRequest(BaseModel):
    """Memory update request model"""
    operation: str = Field(description="Operation type (node, edge, graph)")
    id: str = Field(description="ID of resource to update")
    updates: Dict[str, Any] = Field(description="Updates to apply")
    version: Optional[int] = Field(default=None, description="Expected version")
    auto_update_embedding: bool = Field(default=False, description="Auto-update embedding")

    @validator("operation")
    def validate_operation(cls, v):
        """Validate operation type"""
        valid_operations = ["node", "edge", "graph"]
        if v not in valid_operations:
            raise ValueError(f"Invalid operation. Must be one of: {valid_operations}")
        return v


class MemoryUpdateResponse(BaseResponse):
    """Memory update response model"""
    updated_id: str = Field(description="ID of updated resource")
    operation: str = Field(description="Operation performed")
    new_version: int = Field(description="New version number")


class MemoryDeleteRequest(BaseModel):
    """Memory delete request model"""
    operation: str = Field(description="Operation type (node, edge, graph)")
    id: str = Field(description="ID of resource to delete")
    cascade: bool = Field(default=False, description="Cascade delete for nodes")
    confirm: bool = Field(default=False, description="Confirmation for destructive operations")

    @validator("operation")
    def validate_operation(cls, v):
        """Validate operation type"""
        valid_operations = ["node", "edge", "graph"]
        if v not in valid_operations:
            raise ValueError(f"Invalid operation. Must be one of: {valid_operations}")
        return v

    @validator("confirm")
    def validate_confirmation_for_graph(cls, v, values):
        """Validate confirmation for graph deletion"""
        if values.get("operation") == "graph" and not v:
            raise ValueError("Confirmation required for graph deletion")
        return v


class MemoryDeleteResponse(BaseResponse):
    """Memory delete response model"""
    deleted_id: str = Field(description="ID of deleted resource")
    operation: str = Field(description="Operation performed")
    cascade_count: Optional[int] = Field(default=None, description="Number of cascaded deletions")


class MemoryStats(BaseModel):
    """Memory statistics model"""
    total_nodes: int = Field(description="Total number of nodes")
    total_edges: int = Field(description="Total number of edges")
    node_types: Dict[NodeType, int] = Field(description="Node count by type")
    edge_types: Dict[EdgeType, int] = Field(description="Edge count by type")
    total_embeddings: int = Field(description="Total number of embeddings")
    storage_size_mb: float = Field(description="Storage size in MB")
    last_updated: datetime = Field(description="Last update timestamp")
    graph_count: int = Field(description="Number of graphs")


class MemoryExportRequest(BaseModel):
    """Memory export request model"""
    format: str = Field(default="json", description="Export format")
    include_embeddings: bool = Field(default=False, description="Include embeddings")
    node_types: Optional[List[NodeType]] = Field(default=None, description="Filter by node types")
    edge_types: Optional[List[EdgeType]] = Field(default=None, description="Filter by edge types")
    date_range: Optional[Dict[str, datetime]] = Field(default=None, description="Filter by date range")

    @validator("format")
    def validate_format(cls, v):
        """Validate export format"""
        valid_formats = ["json", "csv", "graphml", "gexf", "cypher"]
        if v not in valid_formats:
            raise ValueError(f"Invalid format. Must be one of: {valid_formats}")
        return v


class MemoryImportRequest(BaseModel):
    """Memory import request model"""
    format: str = Field(description="Import format")
    data: Union[str, Dict[str, Any], List[Dict[str, Any]]] = Field(description="Import data")
    overwrite: bool = Field(default=False, description="Overwrite existing data")
    generate_embeddings: bool = Field(default=False, description="Generate embeddings for imported nodes")
    validate_schema: bool = Field(default=True, description="Validate imported schema")

    @validator("format")
    def validate_format(cls, v):
        """Validate import format"""
        valid_formats = ["json", "csv", "graphml", "gexf", "cypher"]
        if v not in valid_formats:
            raise ValueError(f"Invalid format. Must be one of: {valid_formats}")
        return v