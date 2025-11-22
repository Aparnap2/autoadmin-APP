"""
Shared Graph Memory implementation for AutoAdmin agents.

This module provides the core memory system using Firebase as the backend
for storing and retrieving knowledge graph data (nodes and edges).
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from uuid import uuid4

import numpy as np
from langchain_openai import OpenAIEmbeddings
from ..services.firebase_service import FirebaseService


@dataclass
class Node:
    """Represents a node in the knowledge graph."""
    id: str
    type: str  # 'feature', 'file', 'trend', 'metric', 'rule', 'business_rule'
    content: str
    embedding: Optional[List[float]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'type': self.type,
            'content': self.content,
            'embedding': self.embedding,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


@dataclass
class Edge:
    """Represents an edge in the knowledge graph."""
    source_id: str
    target_id: str
    relation: str  # 'impacts', 'depends_on', 'implements', 'blocks', 'related_to'
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'source_id': self.source_id,
            'target_id': self.target_id,
            'relation': self.relation,
            'created_at': self.created_at
        }


logger = logging.getLogger(__name__)


class GraphMemory:
    """
    Shared Graph Memory implementation using Firebase.

    Provides vector similarity search and graph traversal capabilities
    for agent knowledge storage and retrieval.
    """

    def __init__(self, openai_api_key: str):
        """Initialize Graph Memory with Firebase service and embeddings."""
        self.firebase_service = FirebaseService()
        self.embeddings = OpenAIEmbeddings(api_key=openai_api_key)

    async def add_node(
        self,
        content: str,
        node_type: str,
        related_node_ids: Optional[List[str]] = None
    ) -> Node:
        """
        Add a new node to the graph memory.

        Args:
            content: The content of the node
            node_type: Type of node ('feature', 'file', 'trend', etc.)
            related_node_ids: List of related node IDs to create edges with

        Returns:
            Created node object
        """
        try:
            # Generate embedding for the content
            embedding = await self._get_embedding(content)
            node_id = str(uuid4())

            # Create node
            node = Node(
                id=node_id,
                type=node_type,
                content=content,
                embedding=embedding
            )

            # Insert node into Firebase
            node_data = {
                'id': node_id,
                'type': node_type,
                'content': content,
                'embedding': embedding
            }

            created_node = await self.firebase_service.add_node(node_data)
            node_dict = created_node.__dict__.copy()
            node_dict['id'] = created_node.id
            result_node = Node(**node_dict)

            # Create edges to related nodes if provided
            if related_node_ids:
                await self._create_edges(node_id, related_node_ids)

            logger.info(f"Created node {node_id} of type {node_type}")
            return result_node

        except Exception as e:
            logger.error(f"Error adding node: {str(e)}")
            raise

    async def add_edge(self, source_id: str, target_id: str, relation: str) -> Edge:
        """
        Add an edge between two nodes.

        Args:
            source_id: ID of the source node
            target_id: ID of the target node
            relation: Type of relationship

        Returns:
            Created edge object
        """
        try:
            edge_data = {
                'source_id': source_id,
                'target_id': target_id,
                'relation': relation
            }

            created_edge = await self.firebase_service.add_edge(edge_data)
            edge = Edge(source_id=source_id, target_id=target_id, relation=relation)

            logger.info(f"Created edge: {source_id} -> {target_id} ({relation})")
            return edge

        except Exception as e:
            logger.error(f"Error adding edge: {str(e)}")
            raise

    async def query_graph(
        self,
        question: str,
        match_threshold: float = 0.7,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Query the graph using vector similarity search.

        Args:
            question: Query string
            match_threshold: Minimum similarity threshold
            max_results: Maximum number of results

        Returns:
            List of relevant context from the graph
        """
        try:
            # Get embedding for the query
            query_embedding = await self._get_embedding(question)

            # Perform vector similarity search using Firebase service
            result = await self.firebase_service.query_graph(query_embedding, match_threshold)

            if result:
                # Expand context with neighboring nodes
                context = []
                for node in result:
                    context.append({
                        'type': 'node',
                        'content': node.get('content', ''),
                        'node_type': node.get('type', ''),
                        'similarity': node.get('similarity', 0.0)
                    })

                    # Get connected nodes
                    neighbors = await self._get_neighbors(node['id'])
                    context.extend(neighbors)

                logger.info(f"Query returned {len(result)} nodes")
                return context
            else:
                return []

        except Exception as e:
            logger.error(f"Error querying graph: {str(e)}")
            raise

    async def get_node(self, node_id: str) -> Optional[Node]:
        """Get a specific node by ID."""
        try:
            # This would need to be implemented in Firebase service
            # For now, return None as placeholder
            logger.warning(f"get_node not implemented for Firebase: {node_id}")
            return None

        except Exception as e:
            logger.error(f"Error getting node {node_id}: {str(e)}")
            return None

    async def get_nodes_by_type(self, node_type: str) -> List[Node]:
        """Get all nodes of a specific type."""
        try:
            # This would need to be implemented in Firebase service
            # For now, return empty list as placeholder
            logger.warning(f"get_nodes_by_type not implemented for Firebase: {node_type}")
            return []

        except Exception as e:
            logger.error(f"Error getting nodes by type {node_type}: {str(e)}")
            return []

    async def get_connected_nodes(self, node_id: str, relation: Optional[str] = None) -> List[Node]:
        """Get nodes connected to a specific node."""
        try:
            # This would need to be implemented in Firebase service
            # For now, return empty list as placeholder
            logger.warning(f"get_connected_nodes not implemented for Firebase: {node_id}")
            return []

        except Exception as e:
            logger.error(f"Error getting connected nodes for {node_id}: {str(e)}")
            return []

    async def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI."""
        try:
            embedding = await self.embeddings.aembed_query(text)
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            # Return empty embedding if generation fails
            return []

    async def _create_edges(self, source_id: str, target_ids: List[str], relation: str = 'related_to'):
        """Create edges between a source node and multiple target nodes."""
        for target_id in target_ids:
            await self.add_edge(source_id, target_id, relation)
        logger.info(f"Created {len(target_ids)} edges for node {source_id}")

    async def _get_neighbors(self, node_id: str) -> List[Dict[str, Any]]:
        """Get neighboring nodes and their relationships."""
        try:
            # This would need to be implemented in Firebase service
            # For now, return empty list as placeholder
            logger.warning(f"_get_neighbors not implemented for Firebase: {node_id}")
            return []

        except Exception as e:
            logger.error(f"Error getting neighbors for {node_id}: {str(e)}")
            return []


class GraphMemoryTools:
    """
    Tools for agents to interact with the Graph Memory system.

    Provides a clean interface for agents to store and retrieve
    information from the shared knowledge graph.
    """

    def __init__(self, graph_memory: GraphMemory):
        self.graph_memory = graph_memory

    async def store_memory(
        self,
        content: str,
        memory_type: str,
        context: Optional[str] = None
    ) -> str:
        """
        Store information in the graph memory.

        Args:
            content: Information to store
            memory_type: Type of memory ('trend', 'insight', 'task', 'rule', etc.)
            context: Additional context for the memory

        Returns:
            ID of the created memory node
        """
        # Find related nodes if context is provided
        related_node_ids = []
        if context:
            similar_nodes = await self.graph_memory.query_graph(context, match_threshold=0.5, max_results=3)
            related_node_ids = [node.get('id', '') for node in similar_nodes if node.get('id')]

        node = await self.graph_memory.add_node(content, memory_type, related_node_ids)
        return node.id

    async def recall_memory(self, query: str, memory_type: Optional[str] = None) -> List[str]:
        """
        Recall relevant information from the graph memory.

        Args:
            query: Query to search for
            memory_type: Optional filter for memory type

        Returns:
            List of relevant memories
        """
        context = await self.graph_memory.query_graph(query)

        # Filter by memory type if specified
        if memory_type:
            context = [c for c in context if c.get('node_type') == memory_type]

        # Extract content
        memories = []
        for item in context:
            if item['type'] == 'node':
                memories.append(f"[{item['node_type']}] {item['content']}")
            elif item['type'] == 'neighbor':
                memories.append(f"[{item['relation']}] {item['content']}")

        return memories

    async def connect_memories(self, memory_id_1: str, memory_id_2: str, relation: str) -> bool:
        """
        Create a relationship between two memories.

        Args:
            memory_id_1: ID of the first memory
            memory_id_2: ID of the second memory
            relation: Type of relationship

        Returns:
            True if successful, False otherwise
        """
        try:
            await self.graph_memory.add_edge(memory_id_1, memory_id_2, relation)
            return True
        except Exception:
            return False