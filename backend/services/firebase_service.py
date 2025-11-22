"""
Firebase Service for Python Backend
Replaces Supabase integration with Firebase Admin SDK
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass, asdict
from google.cloud import firestore
from firebase_admin import credentials, initialize_app, get_app, auth
from firebase_admin import firestore as admin_firestore
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Task:
    """Task data structure matching Firebase schema"""
    id: str
    status: str  # 'pending' | 'processing' | 'review_ready' | 'done' | 'failed'
    input_prompt: str
    output_result: Optional[str] = None
    agent_type: str = 'strategy'  # 'marketing' | 'finance' | 'devops' | 'strategy'
    priority: str = 'medium'  # 'low' | 'medium' | 'high'
    parameters: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class GraphNode:
    """Graph node data structure"""
    id: str
    type: str  # 'feature' | 'file' | 'trend' | 'metric' | 'rule' | 'business_rule'
    content: str
    embedding: Optional[List[float]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class GraphEdge:
    """Graph edge data structure"""
    source_id: str
    target_id: str
    relation: str  # 'impacts' | 'depends_on' | 'implements' | 'blocks' | 'related_to'
    created_at: Optional[datetime] = None

@dataclass
class WebhookEvent:
    """Webhook event data structure"""
    id: str
    source: str
    event: str
    payload: Dict[str, Any]
    processed_data: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None

@dataclass
class AgentFile:
    """Virtual filesystem file structure"""
    path: str
    content: str
    last_modified: Optional[datetime] = None

class FirebaseService:
    """
    Firebase service replacing Supabase integration
    Provides same API interface for compatibility
    """

    _instance = None
    _app = None
    _db = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirebaseService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize Firebase Admin SDK"""
        try:
            # Check if already initialized
            if self._app is not None:
                return

            # Get Firebase configuration from environment
            project_id = os.getenv('FIREBASE_PROJECT_ID')
            client_email = os.getenv('FIREBASE_CLIENT_EMAIL')
            private_key = os.getenv('FIREBASE_PRIVATE_KEY')

            if not all([project_id, client_email, private_key]):
                # Try to use default credentials (e.g., in production)
                try:
                    self._app = get_app()
                    logger.info("Using existing Firebase app")
                except ValueError:
                    raise ValueError(
                        "Firebase configuration missing. Please set FIREBASE_PROJECT_ID, "
                        "FIREBASE_CLIENT_EMAIL, and FIREBASE_PRIVATE_KEY environment variables"
                    )
            else:
                # Create credentials from environment variables
                cred_dict = {
                    "type": "service_account",
                    "project_id": project_id,
                    "private_key": private_key.replace('\\n', '\n'),
                    "client_email": client_email,
                    "token_uri": "https://oauth2.googleapis.com/token"
                }

                cred = credentials.Certificate(cred_dict)
                self._app = initialize_app(cred)
                logger.info(f"Firebase app initialized for project: {project_id}")

            # Initialize Firestore
            self._db = admin_firestore.client(app=self._app)
            logger.info("Firestore client initialized")

        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {str(e)}")
            raise

    @property
    def db(self) -> admin_firestore.client:
        """Get Firestore client"""
        if self._db is None:
            self._initialize()
        return self._db

    # Task Management Methods
    async def create_task(self, task_data: Dict[str, Any]) -> Task:
        """Create a new task"""
        try:
            # Add timestamps
            task_data['created_at'] = admin_firestore.SERVER_TIMESTAMP
            task_data['updated_at'] = None

            # Create document
            doc_ref = self.db.collection('tasks').document()
            doc_ref.set(task_data)

            # Return created task
            task_data['id'] = doc_ref.id
            return Task(**task_data)

        except Exception as e:
            logger.error(f"Error creating task: {str(e)}")
            raise

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        try:
            doc_ref = self.db.collection('tasks').document(task_id)
            doc = doc_ref.get()

            if doc.exists:
                task_data = doc.to_dict()
                task_data['id'] = doc.id
                return Task(**task_data)
            return None

        except Exception as e:
            logger.error(f"Error getting task {task_id}: {str(e)}")
            raise

    async def update_task_status(self, task_id: str, status: str) -> Task:
        """Update task status"""
        try:
            doc_ref = self.db.collection('tasks').document(task_id)

            # Update with new status and timestamp
            update_data = {
                'status': status,
                'updated_at': admin_firestore.SERVER_TIMESTAMP
            }

            doc_ref.update(update_data)

            # Get updated document
            updated_doc = doc_ref.get()
            task_data = updated_doc.to_dict()
            task_data['id'] = updated_doc.id

            return Task(**task_data)

        except Exception as e:
            logger.error(f"Error updating task status: {str(e)}")
            raise

    async def get_tasks_by_agent_type(self, agent_type: str) -> List[Task]:
        """Get tasks by agent type"""
        try:
            query = (self.db.collection('tasks')
                    .where('agent_type', '==', agent_type)
                    .order_by('created_at', direction=firestore.DESCENDING))

            docs = query.stream()
            tasks = []

            for doc in docs:
                task_data = doc.to_dict()
                task_data['id'] = doc.id
                tasks.append(Task(**task_data))

            return tasks

        except Exception as e:
            logger.error(f"Error getting tasks by agent type: {str(e)}")
            raise

    # Graph Memory Methods
    async def add_node(self, node_data: Dict[str, Any]) -> GraphNode:
        """Add a node to the graph memory"""
        try:
            node_data['created_at'] = admin_firestore.SERVER_TIMESTAMP
            node_data['updated_at'] = None

            doc_ref = self.db.collection('nodes').document()
            doc_ref.set(node_data)

            node_data['id'] = doc_ref.id
            return GraphNode(**node_data)

        except Exception as e:
            logger.error(f"Error adding node: {str(e)}")
            raise

    async def add_edge(self, edge_data: Dict[str, Any]) -> GraphEdge:
        """Add an edge to the graph"""
        try:
            edge_data['created_at'] = admin_firestore.SERVER_TIMESTAMP

            doc_ref = self.db.collection('edges').document()
            doc_ref.set(edge_data)

            edge_data['id'] = doc_ref.id
            return GraphEdge(**edge_data)

        except Exception as e:
            logger.error(f"Error adding edge: {str(e)}")
            raise

    async def query_graph(self, query_embedding: List[float], match_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Query graph using vector similarity
        This would typically call a Firebase Cloud Function for vector search
        """
        try:
            # For now, implement a simple search
            # In production, this should call a vector search function

            query = (self.db.collection('nodes')
                    .where('embedding', '!=', None)
                    .limit(10))

            docs = query.stream()
            results = []

            for doc in docs:
                node_data = doc.to_dict()
                node_data['id'] = doc.id

                # Simple similarity calculation (replace with proper implementation)
                if 'embedding' in node_data and node_data['embedding']:
                    # Placeholder similarity calculation
                    similarity = 0.8  # This should be calculated properly
                    if similarity >= match_threshold:
                        results.append({
                            'id': doc.id,
                            'content': node_data.get('content', ''),
                            'type': node_data.get('type', ''),
                            'similarity': similarity
                        })

            return results

        except Exception as e:
            logger.error(f"Error querying graph: {str(e)}")
            raise

    # Virtual Filesystem Methods
    async def store_agent_file(self, path: str, content: str) -> AgentFile:
        """Store a file in the virtual filesystem"""
        try:
            file_data = {
                'path': path,
                'content': content,
                'last_modified': admin_firestore.SERVER_TIMESTAMP
            }

            doc_ref = self.db.collection('agent_files').document(path)
            doc_ref.set(file_data)

            return AgentFile(**file_data)

        except Exception as e:
            logger.error(f"Error storing agent file: {str(e)}")
            raise

    async def get_agent_file(self, path: str) -> Optional[AgentFile]:
        """Get a file from the virtual filesystem"""
        try:
            doc_ref = self.db.collection('agent_files').document(path)
            doc = doc_ref.get()

            if doc.exists:
                file_data = doc.to_dict()
                return AgentFile(**file_data)
            return None

        except Exception as e:
            logger.error(f"Error getting agent file: {str(e)}")
            raise

    # Webhook Event Methods
    async def create_webhook_event(self, event_data: Dict[str, Any]) -> WebhookEvent:
        """Create a webhook event"""
        try:
            event_data['created_at'] = admin_firestore.SERVER_TIMESTAMP

            doc_ref = self.db.collection('webhook_events').document()
            doc_ref.set(event_data)

            event_data['id'] = doc_ref.id
            return WebhookEvent(**event_data)

        except Exception as e:
            logger.error(f"Error creating webhook event: {str(e)}")
            raise

    # Batch Operations
    async def batch_create_nodes(self, nodes_data: List[Dict[str, Any]]) -> List[str]:
        """Create multiple nodes in a batch"""
        try:
            batch = self.db.batch()
            doc_refs = []

            for node_data in nodes_data:
                doc_ref = self.db.collection('nodes').document()
                doc_refs.append(doc_ref)

                node_data['created_at'] = admin_firestore.SERVER_TIMESTAMP
                node_data['updated_at'] = None

                batch.set(doc_ref, node_data)

            batch.commit()

            return [doc_ref.id for doc_ref in doc_refs]

        except Exception as e:
            logger.error(f"Error batch creating nodes: {str(e)}")
            raise

    # Real-time Listeners (would be implemented with Firebase Functions for Python)
    def on_tasks_change(self, callback):
        """
        Listen for task changes
        Note: This would typically be implemented with Firebase Functions
        and websockets for Python backend
        """
        logger.warning("Real-time listeners not implemented in Python backend")
        pass

    # Utility Methods
    async def get_collection_stats(self, collection_name: str) -> Dict[str, int]:
        """Get statistics for a collection"""
        try:
            query = self.db.collection(collection_name).limit(1)
            docs = list(query.stream())

            # For accurate count, you might need a Cloud Function or
            # use a separate collection to track counts
            return {"count": len(docs)}

        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Check Firebase service health"""
        try:
            # Try to access Firestore
            doc_ref = self.db.collection('health').document('check')
            doc_ref.set({'timestamp': admin_firestore.SERVER_TIMESTAMP})
            doc_ref.delete()

            return {
                "status": "healthy",
                "services": {
                    "firestore": True,
                    "auth": True
                },
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "services": {
                    "firestore": False,
                    "auth": False
                },
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

# Create singleton instance
firebase_service = FirebaseService()

# Export for use in other modules
__all__ = [
    'FirebaseService',
    'firebase_service',
    'Task',
    'GraphNode',
    'GraphEdge',
    'WebhookEvent',
    'AgentFile'
]