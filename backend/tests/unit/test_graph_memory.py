"""
Unit tests for Graph Memory system.

Tests the knowledge graph storage and retrieval functionality.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import json

from agents.memory.graph_memory import GraphMemory, GraphMemoryTools, Node, Edge


@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client."""
    client = Mock()
    client.table = Mock()
    client.rpc = Mock()
    return client


@pytest.fixture
def mock_openai_embeddings():
    """Create a mock OpenAI embeddings client."""
    embeddings = Mock()
    embeddings.aembed_query = AsyncMock(return_value=[0.1, 0.2, 0.3, 0.4, 0.5])
    return embeddings


@pytest.fixture
def graph_memory(mock_supabase_client, mock_openai_embeddings):
    """Create a GraphMemory instance with mocked dependencies."""
    with patch('agents.memory.graph_memory.create_client', return_value=mock_supabase_client):
        with patch('agents.memory.graph_memory.OpenAIEmbeddings', return_value=mock_openai_embeddings):
            return GraphMemory(
                supabase_url="https://test.supabase.co",
                supabase_key="test_key",
                openai_api_key="test_openai_key"
            )


@pytest.mark.asyncio
async def test_add_node(graph_memory, mock_supabase_client):
    """Test adding a node to the graph memory."""
    # Mock Supabase response
    mock_supabase_client.table.return_value.insert.return_value.execute.return_value.data = [
        {
            'id': 'test-node-id',
            'type': 'feature',
            'content': 'Test feature description',
            'embedding': [0.1, 0.2, 0.3],
            'created_at': '2024-01-01T00:00:00Z',
            'updated_at': None
        }
    ]

    # Test adding a node
    node = await graph_memory.add_node(
        content="Test feature description",
        node_type="feature",
        related_node_ids=["related-id-1", "related-id-2"]
    )

    # Verify the node was created correctly
    assert node.id == "test-node-id"
    assert node.type == "feature"
    assert node.content == "Test feature description"
    assert node.embedding == [0.1, 0.2, 0.3]

    # Verify Supabase was called correctly
    mock_supabase_client.table.assert_called_with('nodes')
    mock_supabase_client.table.return_value.insert.assert_called_once()


@pytest.mark.asyncio
async def test_add_edge(graph_memory, mock_supabase_client):
    """Test adding an edge to the graph memory."""
    # Mock Supabase response
    mock_supabase_client.table.return_value.insert.return_value.execute.return_value.data = [
        {
            'source_id': 'source-id',
            'target_id': 'target-id',
            'relation': 'implements',
            'created_at': '2024-01-01T00:00:00Z'
        }
    ]

    # Test adding an edge
    edge = await graph_memory.add_edge(
        source_id="source-id",
        target_id="target-id",
        relation="implements"
    )

    # Verify the edge was created correctly
    assert edge.source_id == "source-id"
    assert edge.target_id == "target-id"
    assert edge.relation == "implements"

    # Verify Supabase was called correctly
    mock_supabase_client.table.assert_called_with('edges')
    mock_supabase_client.table.return_value.insert.assert_called_once()


@pytest.mark.asyncio
async def test_query_graph(graph_memory, mock_supabase_client):
    """Test querying the graph memory."""
    # Mock Supabase RPC response for vector search
    mock_supabase_client.rpc.return_value.execute.return_value.data = [
        {
            'id': 'result-node-id',
            'type': 'trend',
            'content': 'AI automation trends',
            'similarity': 0.85
        }
    ]

    # Mock neighbor search
    mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {
            'target_id': 'neighbor-id',
            'content': 'Related content',
            'relation': 'related_to',
            'source_id': 'result-node-id'
        }
    ]

    # Test querying the graph
    results = await graph_memory.query_graph(
        question="AI automation trends",
        match_threshold=0.7
    )

    # Verify results
    assert len(results) > 0
    assert results[0]['type'] == 'node'
    assert results[0]['content'] == 'AI automation trends'
    assert results[0]['similarity'] == 0.85

    # Verify RPC was called correctly
    mock_supabase_client.rpc.assert_called_once_with('match_nodes', {
        'query_embedding': [0.1, 0.2, 0.3, 0.4, 0.5],
        'match_threshold': 0.7,
        'max_results': 10
    })


@pytest.mark.asyncio
async def test_get_node(graph_memory, mock_supabase_client):
    """Test getting a specific node by ID."""
    # Mock Supabase response
    mock_supabase_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
        'id': 'test-node-id',
        'type': 'feature',
        'content': 'Test feature',
        'embedding': [0.1, 0.2, 0.3],
        'created_at': '2024-01-01T00:00:00Z'
    }

    # Test getting a node
    node = await graph_memory.get_node('test-node-id')

    # Verify the node
    assert node is not None
    assert node.id == 'test-node-id'
    assert node.type == 'feature'
    assert node.content == 'Test feature'


@pytest.mark.asyncio
async def test_get_node_not_found(graph_memory, mock_supabase_client):
    """Test getting a node that doesn't exist."""
    # Mock Supabase response for not found
    mock_supabase_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.side_effect = Exception("No rows found")

    # Test getting a non-existent node
    node = await graph_memory.get_node('non-existent-id')

    # Verify None is returned
    assert node is None


@pytest.mark.asyncio
async def test_get_nodes_by_type(graph_memory, mock_supabase_client):
    """Test getting nodes by type."""
    # Mock Supabase response
    mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {
            'id': 'trend-1',
            'type': 'trend',
            'content': 'AI trends',
            'created_at': '2024-01-01T00:00:00Z'
        },
        {
            'id': 'trend-2',
            'type': 'trend',
            'content': 'Automation trends',
            'created_at': '2024-01-01T00:00:00Z'
        }
    ]

    # Test getting nodes by type
    nodes = await graph_memory.get_nodes_by_type('trend')

    # Verify results
    assert len(nodes) == 2
    assert all(node.type == 'trend' for node in nodes)
    assert nodes[0].content == 'AI trends'
    assert nodes[1].content == 'Automation trends'


@pytest.mark.asyncio
async def test_get_connected_nodes(graph_memory, mock_supabase_client):
    """Test getting nodes connected to a specific node."""
    # Mock edges response
    mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {'target_id': 'connected-1'},
        {'target_id': 'connected-2'}
    ]

    # Mock nodes response
    mock_supabase_client.table.return_value.select.return_value.in_.return_value.execute.return_value.data = [
        {
            'id': 'connected-1',
            'type': 'feature',
            'content': 'Connected feature 1'
        },
        {
            'id': 'connected-2',
            'type': 'feature',
            'content': 'Connected feature 2'
        }
    ]

    # Test getting connected nodes
    connected_nodes = await graph_memory.get_connected_nodes('source-node-id')

    # Verify results
    assert len(connected_nodes) == 2
    assert connected_nodes[0].id == 'connected-1'
    assert connected_nodes[1].id == 'connected-2'


@pytest.mark.asyncio
async def test_graph_memory_tools_store_memory(graph_memory):
    """Test GraphMemoryTools store_memory functionality."""
    tools = GraphMemoryTools(graph_memory)

    # Mock graph_memory.add_node
    graph_memory.add_node = AsyncMock(return_value=Mock(id="test-memory-id"))

    # Test storing memory
    memory_id = await tools.store_memory(
        content="Test memory content",
        memory_type="insight",
        context="AI automation trends"
    )

    # Verify the memory was stored
    assert memory_id == "test-memory-id"
    graph_memory.add_node.assert_called_once()


@pytest.mark.asyncio
async def test_graph_memory_tools_recall_memory(graph_memory):
    """Test GraphMemoryTools recall_memory functionality."""
    tools = GraphMemoryTools(graph_memory)

    # Mock graph_memory.query_graph
    graph_memory.query_graph = AsyncMock(return_value=[
        {
            'type': 'node',
            'node_type': 'trend',
            'content': 'AI automation trend',
            'similarity': 0.9
        },
        {
            'type': 'neighbor',
            'content': 'Related content',
            'relation': 'implements'
        }
    ])

    # Test recalling memories
    memories = await tools.recall_memory("AI automation", memory_type="trend")

    # Verify the memories were recalled
    assert len(memories) > 0
    assert any("AI automation trend" in memory for memory in memories)
    graph_memory.query_graph.assert_called_once()


@pytest.mark.asyncio
async def test_graph_memory_tools_connect_memories(graph_memory):
    """Test GraphMemoryTools connect_memories functionality."""
    tools = GraphMemoryTools(graph_memory)

    # Mock graph_memory.add_edge
    graph_memory.add_edge = AsyncMock(return_value=True)

    # Test connecting memories
    result = await tools.connect_memories(
        memory_id_1="memory-1",
        memory_id_2="memory-2",
        relation="related_to"
    )

    # Verify the memories were connected
    assert result is True
    graph_memory.add_edge.assert_called_once_with("memory-1", "memory-2", "related_to")


class TestNode:
    """Test the Node dataclass."""

    def test_node_creation(self):
        """Test creating a Node."""
        node = Node(
            id="test-id",
            type="feature",
            content="Test feature content"
        )

        assert node.id == "test-id"
        assert node.type == "feature"
        assert node.content == "Test feature content"
        assert node.embedding is None
        assert node.created_at is None
        assert node.updated_at is None

    def test_node_to_dict(self):
        """Test converting Node to dictionary."""
        node = Node(
            id="test-id",
            type="feature",
            content="Test content",
            embedding=[0.1, 0.2],
            created_at="2024-01-01T00:00:00Z"
        )

        node_dict = node.to_dict()

        expected = {
            'id': 'test-id',
            'type': 'feature',
            'content': 'Test content',
            'embedding': [0.1, 0.2],
            'created_at': '2024-01-01T00:00:00Z',
            'updated_at': None
        }

        assert node_dict == expected


class TestEdge:
    """Test the Edge dataclass."""

    def test_edge_creation(self):
        """Test creating an Edge."""
        edge = Edge(
            source_id="source-id",
            target_id="target-id",
            relation="implements"
        )

        assert edge.source_id == "source-id"
        assert edge.target_id == "target-id"
        assert edge.relation == "implements"
        assert edge.created_at is None

    def test_edge_to_dict(self):
        """Test converting Edge to dictionary."""
        edge = Edge(
            source_id="source-id",
            target_id="target-id",
            relation="implements",
            created_at="2024-01-01T00:00:00Z"
        )

        edge_dict = edge.to_dict()

        expected = {
            'source_id': 'source-id',
            'target_id': 'target-id',
            'relation': 'implements',
            'created_at': '2024-01-01T00:00:00Z'
        }

        assert edge_dict == expected