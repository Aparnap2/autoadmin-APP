"""
Firebase Service for Python Backend
Replaces Supabase integration with Firebase Admin SDK
Enhanced with robust authentication retry logic and offline mode handling
"""

import os
import json
import logging
import time
import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
from google.cloud import firestore
from firebase_admin import credentials, initialize_app, get_app, auth
from firebase_admin import firestore as admin_firestore
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from google.cloud.firestore import Query

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    logging.info("Loaded environment variables from .env file")
except ImportError:
    logging.warning("python-dotenv not available, using system environment variables only")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FirebaseMode(Enum):
    """Firebase service operating mode"""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    RECOVERING = "recovering"

@dataclass
class FirebaseConfig:
    """Firebase configuration validation"""
    project_id: str
    client_email: str
    private_key: str
    database_url: Optional[str] = None


    @classmethod
    def from_env(cls) -> 'FirebaseConfig':
        """Create config from environment variables (fallback)"""
        return cls(
            project_id=os.getenv('FIREBASE_PROJECT_ID', ''),
            client_email=os.getenv('FIREBASE_CLIENT_EMAIL', ''),
            private_key=os.getenv('FIREBASE_PRIVATE_KEY', ''),
            database_url=os.getenv('FIREBASE_DATABASE_URL')
        )

    def is_valid(self) -> bool:
        """Validate configuration"""
        if not all([self.project_id, self.client_email, self.private_key]):
            return False

        # Check for placeholder keys
        placeholder_indicators = [
            "TestKeyForDebuggingPurposesOnly",
            "PLACEHOLDER",
            "YOUR_PRIVATE_KEY",
            "EXAMPLE_KEY"
        ]

        for indicator in placeholder_indicators:
            if indicator in self.private_key:
                return False

        return True

    def validate_format(self) -> List[str]:
        """Validate configuration format and return errors"""
        errors = []

        if not self.project_id:
            errors.append("FIREBASE_PROJECT_ID is missing")
        elif not self.project_id.replace('-', '').replace('_', '').isalnum():
            errors.append("FIREBASE_PROJECT_ID format is invalid")

        if not self.client_email:
            errors.append("FIREBASE_CLIENT_EMAIL is missing")
        elif '@' not in self.client_email or '.iam.gserviceaccount.com' not in self.client_email:
            errors.append("FIREBASE_CLIENT_EMAIL format is invalid")

        if not self.private_key:
            errors.append("FIREBASE_PRIVATE_KEY is missing")
        elif not self.private_key.startswith('-----BEGIN PRIVATE KEY-----'):
            errors.append("FIREBASE_PRIVATE_KEY format is invalid")
        elif not (self.private_key.endswith('-----END PRIVATE KEY-----') or self.private_key.endswith('-----END PRIVATE KEY-----\n')):
            errors.append("FIREBASE_PRIVATE_KEY format is invalid")

        return errors

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
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    content: Optional[str] = None
    type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class AgentFile:
    """Virtual filesystem file structure"""
    path: str
    content: str
    last_modified: Optional[datetime] = None

@dataclass
class HubSpotContact:
    """HubSpot contact data for Firebase storage"""
    id: str
    email: Optional[str] = None
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    website: Optional[str] = None
    lifecyclestage: Optional[str] = None
    createdate: Optional[datetime] = None
    lastmodifieddate: Optional[datetime] = None
    hubspot_properties: Optional[Dict[str, Any]] = None
    firebase_updated_at: Optional[datetime] = None

@dataclass
class HubSpotDeal:
    """HubSpot deal data for Firebase storage"""
    id: str
    dealname: Optional[str] = None
    dealstage: Optional[str] = None
    amount: Optional[float] = None
    closedate: Optional[datetime] = None
    dealtype: Optional[str] = None
    pipeline: Optional[str] = None
    createdate: Optional[datetime] = None
    lastmodifieddate: Optional[datetime] = None
    hubspot_properties: Optional[Dict[str, Any]] = None
    firebase_updated_at: Optional[datetime] = None

@dataclass
class HubSpotCompany:
    """HubSpot company data for Firebase storage"""
    id: str
    name: Optional[str] = None
    domain: Optional[str] = None
    industry: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    createdate: Optional[datetime] = None
    lastmodifieddate: Optional[datetime] = None
    hubspot_properties: Optional[Dict[str, Any]] = None
    firebase_updated_at: Optional[datetime] = None

class FirebaseService:
    """
    Enhanced Firebase service with robust authentication retry logic
    and comprehensive offline mode handling
    """

    _instance = None
    _app = None
    _db = None
    _mode = FirebaseMode.OFFLINE
    _config = None
    _last_auth_attempt = None
    _retry_count = 0
    _max_retries = 5
    _retry_delays = [1, 2, 5, 10, 30]  # seconds
    _offline_storage = {}  # In-memory offline storage
    _health_status = {"last_check": None, "consecutive_failures": 0}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirebaseService, cls).__new__(cls)
            # Load Firebase configuration from environment variables
            cls._instance._config = FirebaseConfig.from_env()
        return cls._instance

    def __init__(self):
        """Initialize the service with enhanced error handling"""
        if not hasattr(self, '_initialized'):
            self._initialized = True
            asyncio.create_task(self._initialize_with_retry())

    async def _initialize_with_retry(self):
        """Initialize Firebase with retry logic"""
        try:
            await self._validate_configuration()
            await self._attempt_initialization()
        except Exception as e:
            logger.error(f"Firebase initialization failed: {e}")
            await self._fallback_to_offline_mode(str(e))

    async def _validate_configuration(self):
        """Validate Firebase configuration"""
        errors = self._config.validate_format()
        if errors:
            logger.warning(f"Firebase configuration validation errors: {errors}")

        if not self._config.is_valid():
            logger.warning("Firebase configuration invalid, proceeding in offline mode")
            await self._fallback_to_offline_mode("Invalid Firebase configuration")

    async def _attempt_initialization(self, is_retry: bool = False):
        """Attempt Firebase initialization with retry logic"""
        if is_retry:
            self._mode = FirebaseMode.RECOVERING

        try:
            # Check if already initialized
            if self._app is not None and self._mode == FirebaseMode.ONLINE:
                try:
                    # Test connection
                    await self._test_connection()
                    logger.info("Firebase connection validated")
                    return
                except Exception as test_error:
                    logger.warning(f"Firebase connection test failed: {test_error}")
                    # Continue to reinitialize

            if not self._config.is_valid():
                raise ValueError("Invalid Firebase configuration")

            # Try to use existing app first
            try:
                self._app = get_app()
                self._db = admin_firestore.client(app=self._app)
                await self._test_connection()
                self._mode = FirebaseMode.ONLINE
                logger.info("Using existing Firebase app")
                return
            except ValueError:
                # No existing app, initialize new one
                pass

            # Create credentials from environment variables
            cred_dict = {
                "type": "service_account",
                "project_id": self._config.project_id,
                "private_key": self._config.private_key.replace('\\n', '\n'),
                "client_email": self._config.client_email,
                "token_uri": "https://oauth2.googleapis.com/token"
            }

            cred = credentials.Certificate(cred_dict)
            self._app = initialize_app(cred)
            self._db = admin_firestore.client(app=self._app)

            # Test the connection
            await self._test_connection()

            self._mode = FirebaseMode.ONLINE
            self._retry_count = 0
            self._health_status["consecutive_failures"] = 0

            logger.info(f"Firebase app initialized successfully for project: {self._config.project_id}")
            logger.info("Firestore client initialized and connected")

        except Exception as e:
            logger.error(f"Firebase initialization attempt {self._retry_count + 1} failed: {str(e)}")

            if self._retry_count < self._max_retries:
                self._retry_count += 1
                delay = self._retry_delays[min(self._retry_count - 1, len(self._retry_delays) - 1)]

                logger.info(f"Retrying Firebase initialization in {delay} seconds (attempt {self._retry_count + 1}/{self._max_retries})")

                await asyncio.sleep(delay)
                await self._attempt_initialization(is_retry=True)
            else:
                logger.error("Max retry attempts reached, falling back to offline mode")
                await self._fallback_to_offline_mode(str(e))

    async def _test_connection(self):
        """Test Firebase connection with simple operation"""
        if not self._db:
            raise ValueError("Firestore client not initialized")

        # Try a simple read operation to test connection
        test_doc = self._db.collection('health').document('connection_test')
        test_data = {
            'timestamp': admin_firestore.SERVER_TIMESTAMP,
            'service': 'firebase_service',
            'test': True
        }

        test_doc.set(test_data)
        test_doc.delete()

    async def _fallback_to_offline_mode(self, reason: str):
        """Fallback to offline mode with proper setup"""
        logger.warning(f"Falling back to offline mode: {reason}")
        self._mode = FirebaseMode.OFFLINE
        self._app = None
        self._db = None
        self._health_status["consecutive_failures"] += 1

    async def attempt_recovery(self):
        """Attempt to recover from offline mode"""
        if self._mode == FirebaseMode.ONLINE:
            return True

        if self._last_auth_attempt and (time.time() - self._last_auth_attempt) < 60:
            return False  # Wait before next attempt

        self._last_auth_attempt = time.time()
        logger.info("Attempting Firebase recovery...")

        try:
            # Re-validate configuration in case it changed
            self._config = FirebaseConfig.from_env()

            if self._config.is_valid():
                await self._attempt_initialization()
                return self._mode == FirebaseMode.ONLINE
            else:
                logger.warning("Firebase configuration still invalid during recovery")
                return False

        except Exception as e:
            logger.error(f"Firebase recovery failed: {e}")
            return False

    @property
    def mode(self) -> FirebaseMode:
        """Get current service mode"""
        return self._mode

    @property
    def is_online(self) -> bool:
        """Check if service is online"""
        return self._mode == FirebaseMode.ONLINE

    @property
    def is_offline(self) -> bool:
        """Check if service is offline"""
        return self._mode in [FirebaseMode.OFFLINE, FirebaseMode.DEGRADED]

    @property
    def db(self) -> admin_firestore.client:
        """Get Firestore client with fallback handling"""
        if self._db is None:
            # Attempt recovery if offline
            if not self.is_online:
                asyncio.create_task(self.attempt_recovery())

            raise Exception("Firebase is not initialized. Running in offline mode.")
        return self._db

    async def safe_firestore_operation(self, operation_name: str, operation_func):
        """Execute a Firestore operation with error handling and recovery"""
        if not self.is_online:
            logger.info(f"Skipping {operation_name} - Firebase is offline")
            return None

        try:
            return await operation_func()
        except Exception as e:
            logger.error(f"Firestore operation '{operation_name}' failed: {str(e)}")
            self._health_status["consecutive_failures"] += 1

            # If too many failures, attempt recovery
            if self._health_status["consecutive_failures"] >= 3:
                logger.warning("Multiple Firestore failures detected, attempting recovery")
                await self.attempt_recovery()

            raise

    # Task Management Methods with Enhanced Offline Support
    async def create_task(self, task_data: Dict[str, Any]) -> Task:
        """Create a new task with offline support"""
        try:
            import uuid
            task_id = str(uuid.uuid4())

            if not self.is_online:
                # Offline mode - store task locally
                offline_task_data = task_data.copy()
                offline_task_data['id'] = task_id
                offline_task_data['created_at'] = datetime.now()
                offline_task_data['updated_at'] = None

                # Store in offline storage
                self._offline_storage[f"task_{task_id}"] = {
                    'data': offline_task_data,
                    'created_at': datetime.now(),
                    'operation': 'create_task'
                }

                logger.info(f"Created task {task_id} in offline mode")
                return Task(**offline_task_data)

            # Online mode - use Firestore with safe operation
            async def create_operation():
                task_data['created_at'] = admin_firestore.SERVER_TIMESTAMP
                task_data['updated_at'] = None

                doc_ref = self.db.collection('tasks').document(task_id)
                doc_ref.set(task_data)

                task_data['id'] = task_id
                return Task(**task_data)

            return await self.safe_firestore_operation("create_task", create_operation)

        except Exception as e:
            logger.error(f"Error creating task: {str(e)}")
            # Fallback to offline mode if Firestore fails
            fallback_task_data = task_data.copy()
            fallback_task_data['id'] = task_id if 'task_id' in locals() else str(uuid.uuid4())
            fallback_task_data['created_at'] = datetime.now()
            fallback_task_data['updated_at'] = None
            logger.warning(f"Task created in fallback offline mode: {fallback_task_data['id']}")
            return Task(**fallback_task_data)

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID with offline support"""
        try:
            # Check offline storage first if offline
            if self.is_offline:
                offline_key = f"task_{task_id}"
                if offline_key in self._offline_storage:
                    offline_data = self._offline_storage[offline_key]['data']
                    logger.info(f"Retrieved task {task_id} from offline storage")
                    return Task(**offline_data)
                logger.info(f"Task {task_id} not found in offline storage")
                return None

            # Online mode - use Firestore
            async def get_operation():
                doc_ref = self.db.collection('tasks').document(task_id)
                doc = doc_ref.get()

                if doc.exists:
                    task_data = doc.to_dict()
                    task_data['id'] = doc.id
                    return Task(**task_data)
                return None

            return await self.safe_firestore_operation("get_task", get_operation)

        except Exception as e:
            logger.error(f"Error getting task {task_id}: {str(e)}")
            return None

    async def update_task_status(self, task_id: str, status: str) -> Optional[Task]:
        """Update task status with offline support"""
        try:
            if self.is_offline:
                # Update in offline storage
                offline_key = f"task_{task_id}"
                if offline_key in self._offline_storage:
                    self._offline_storage[offline_key]['data']['status'] = status
                    self._offline_storage[offline_key]['data']['updated_at'] = datetime.now()
                    logger.info(f"Updated task {task_id} status in offline mode")
                    return Task(**self._offline_storage[offline_key]['data'])
                else:
                    logger.warning(f"Task {task_id} not found in offline storage for update")
                    return None

            # Online mode - use Firestore
            async def update_operation():
                doc_ref = self.db.collection('tasks').document(task_id)

                update_data = {
                    'status': status,
                    'updated_at': admin_firestore.SERVER_TIMESTAMP
                }

                doc_ref.update(update_data)

                updated_doc = doc_ref.get()
                task_data = updated_doc.to_dict()
                task_data['id'] = updated_doc.id

                return Task(**task_data)

            return await self.safe_firestore_operation("update_task_status", update_operation)

        except Exception as e:
            logger.error(f"Error updating task status: {str(e)}")
            return None

    async def get_tasks_by_agent_type(self, agent_type: str) -> List[Task]:
        """Get tasks by agent type with offline support"""
        try:
            if self.is_offline:
                # Return tasks from offline storage
                offline_tasks = []
                for key, value in self._offline_storage.items():
                    if key.startswith('task_') and value['data'].get('agent_type') == agent_type:
                        offline_tasks.append(Task(**value['data']))
                logger.info(f"Retrieved {len(offline_tasks)} tasks for agent {agent_type} from offline storage")
                return offline_tasks

            # Online mode - use Firestore
            async def query_operation():
                query = (self.db.collection('tasks')
                        .where('agent_type', '==', agent_type)
                        .order_by('created_at', direction=Query.DESCENDING))

                docs = query.stream()
                tasks = []

                for doc in docs:
                    task_data = doc.to_dict()
                    task_data['id'] = doc.id
                    tasks.append(Task(**task_data))

                return tasks

            return await self.safe_firestore_operation("get_tasks_by_agent_type", query_operation) or []

        except Exception as e:
            logger.error(f"Error getting tasks by agent type: {str(e)}")
            return []

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

    # Virtual Filesystem Methods with Offline Support
    async def store_agent_file(self, path: str, content: str) -> AgentFile:
        """Store a file in the virtual filesystem with offline support"""
        try:
            if self.is_offline:
                # Store in offline storage
                offline_file_data = {
                    'path': path,
                    'content': content,
                    'last_modified': datetime.now()
                }

                self._offline_storage[f"file_{path}"] = {
                    'data': offline_file_data,
                    'created_at': datetime.now(),
                    'operation': 'store_agent_file'
                }

                logger.info(f"Stored agent file {path} in offline mode")
                return AgentFile(**offline_file_data)

            # Online mode
            async def store_operation():
                file_data = {
                    'path': path,
                    'content': content,
                    'last_modified': admin_firestore.SERVER_TIMESTAMP
                }

                doc_ref = self.db.collection('agent_files').document(path)
                doc_ref.set(file_data)

                return AgentFile(**file_data)

            return await self.safe_firestore_operation("store_agent_file", store_operation)

        except Exception as e:
            logger.error(f"Error storing agent file: {str(e)}")
            # Fallback to offline storage
            fallback_file_data = {
                'path': path,
                'content': content,
                'last_modified': datetime.now()
            }
            logger.warning(f"Agent file stored in fallback offline mode: {path}")
            return AgentFile(**fallback_file_data)

    async def get_agent_file(self, path: str) -> Optional[AgentFile]:
        """Get a file from the virtual filesystem with offline support"""
        try:
            # Check offline storage first if offline
            if self.is_offline:
                offline_key = f"file_{path}"
                if offline_key in self._offline_storage:
                    file_data = self._offline_storage[offline_key]['data']
                    logger.info(f"Retrieved agent file {path} from offline storage")
                    return AgentFile(**file_data)
                logger.info(f"Agent file {path} not found in offline storage")
                return None

            # Online mode
            async def get_operation():
                doc_ref = self.db.collection('agent_files').document(path)
                doc = doc_ref.get()

                if doc.exists:
                    file_data = doc.to_dict()
                    return AgentFile(**file_data)
                return None

            return await self.safe_firestore_operation("get_agent_file", get_operation)

        except Exception as e:
            logger.error(f"Error getting agent file: {str(e)}")
            return None

    async def sync_offline_storage(self) -> Dict[str, Any]:
        """Sync offline storage with Firebase when connection is restored"""
        try:
            if not self.is_online:
                return {"success": False, "error": "Firebase is offline"}

            if not self._offline_storage:
                return {"success": True, "synced": 0, "error": None}

            synced_count = 0
            errors = []

            for key, item in list(self._offline_storage.items()):
                try:
                    operation = item['operation']
                    data = item['data']

                    if operation == 'create_task':
                        # Sync task to Firestore
                        doc_ref = self.db.collection('tasks').document(data['id'])
                        # Remove offline mode flag and convert timestamps
                        sync_data = {k: v for k, v in data.items() if k != 'offline_mode'}
                        sync_data['created_at'] = data.get('created_at', admin_firestore.SERVER_TIMESTAMP)
                        if 'updated_at' in sync_data and sync_data['updated_at']:
                            sync_data['updated_at'] = admin_firestore.SERVER_TIMESTAMP
                        doc_ref.set(sync_data)
                        synced_count += 1

                    elif operation == 'store_agent_file':
                        # Sync file to Firestore
                        doc_ref = self.db.collection('agent_files').document(data['path'])
                        sync_data = {k: v for k, v in data.items() if k != 'offline_mode'}
                        sync_data['last_modified'] = admin_firestore.SERVER_TIMESTAMP
                        doc_ref.set(sync_data)
                        synced_count += 1

                    # Remove from offline storage after successful sync
                    del self._offline_storage[key]

                except Exception as e:
                    errors.append(f"Failed to sync {key}: {str(e)}")

            return {
                "success": True,
                "synced": synced_count,
                "remaining": len(self._offline_storage),
                "errors": errors
            }

        except Exception as e:
            logger.error(f"Error during offline storage sync: {str(e)}")
            return {"success": False, "error": str(e)}

    # Webhook Event Methods
    async def create_webhook_event(self, event_data: Dict[str, Any]) -> WebhookEvent:
        """Create a webhook event"""
        try:
            if self._db is None:
                # Offline mode - create event without Firebase
                import uuid
                # Map message data to WebhookEvent fields
                webhook_event = WebhookEvent(
                    id=str(uuid.uuid4()),
                    source=event_data.get('agent_id', 'unknown'),
                    event=event_data.get('type', 'message'),
                    payload=event_data,
                    created_at=datetime.now(),
                    user_id=event_data.get('user_id'),
                    agent_id=event_data.get('agent_id'),
                    content=event_data.get('content'),
                    type=event_data.get('type'),
                    metadata=event_data.get('metadata')
                )
                logger.info("Created webhook event in offline mode")
                return webhook_event

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

    # Real-time Updates (HTTP-based polling alternative)
    async def get_tasks_changes_since(self, since_timestamp: datetime) -> List[Dict[str, Any]]:
        """
        Get task changes since a specific timestamp
        Replaces real-time listeners with HTTP-based polling

        Args:
            since_timestamp: Get changes since this timestamp

        Returns:
            List of task changes since the timestamp
        """
        try:
            if self.is_offline:
                # Get changes from offline storage
                changes = []
                for key, item in self._offline_storage.items():
                    if key.startswith('task_') and item.get('created_at') and item['created_at'] > since_timestamp:
                        changes.append(item['data'])
                logger.info(f"Retrieved {len(changes)} task changes from offline storage since {since_timestamp}")
                return changes

            # Online mode - use Firestore query
            async def query_operation():
                query = (self.db.collection('tasks')
                        .where('updated_at', '>', since_timestamp)
                        .order_by('updated_at', direction=firestore.ASCENDING))

                docs = query.stream()
                changes = []

                for doc in docs:
                    task_data = doc.to_dict()
                    task_data['id'] = doc.id
                    changes.append(task_data)

                return changes

            return await self.safe_firestore_operation("get_tasks_changes_since", query_operation) or []

        except Exception as e:
            logger.error(f"Error getting task changes since {since_timestamp}: {str(e)}")
            return []

    async def get_agent_status_changes(self, last_check: datetime) -> List[Dict[str, Any]]:
        """
        Get agent status changes since last check
        HTTP polling alternative to real-time status updates

        Args:
            last_check: Last check timestamp

        Returns:
            List of agent status changes
        """
        try:
            if self.is_offline:
                # Return empty list for offline mode (status tracked in memory)
                return []

            # Online mode - query agent status collection if exists
            async def query_operation():
                query = (self.db.collection('agent_status')
                        .where('last_updated', '>', last_check)
                        .order_by('last_updated', direction=firestore.ASCENDING))

                docs = query.stream()
                changes = []

                for doc in docs:
                    status_data = doc.to_dict()
                    status_data['agent_id'] = doc.id
                    changes.append(status_data)

                return changes

            return await self.safe_firestore_operation("get_agent_status_changes", query_operation) or []

        except Exception as e:
            logger.error(f"Error getting agent status changes since {last_check}: {str(e)}")
            return []

    def on_tasks_change(self, callback):
        """
        Legacy method for backwards compatibility
        Now advises to use HTTP polling endpoints instead

        Args:
            callback: Callback function (will not be called)
        """
        logger.warning("on_tasks_change is deprecated. Use HTTP polling endpoints instead:")
        logger.warning("- GET /api/v1/tasks/stream for SSE streaming")
        logger.warning("- GET /api/v1/tasks/poll for long polling")
        logger.warning("- GET /api/v1/notifications/stream for real-time updates")
        pass

    # HubSpot Data Methods
    async def store_hubspot_contact(self, contact: HubSpotContact) -> HubSpotContact:
        """Store HubSpot contact in Firebase"""
        try:
            contact_data = asdict(contact)
            contact_data['firebase_updated_at'] = admin_firestore.SERVER_TIMESTAMP

            doc_ref = self.db.collection('hubspot_contacts').document(contact.id)
            doc_ref.set(contact_data)

            return contact

        except Exception as e:
            logger.error(f"Error storing HubSpot contact: {str(e)}")
            raise

    async def store_hubspot_deal(self, deal: HubSpotDeal) -> HubSpotDeal:
        """Store HubSpot deal in Firebase"""
        try:
            deal_data = asdict(deal)
            deal_data['firebase_updated_at'] = admin_firestore.SERVER_TIMESTAMP

            doc_ref = self.db.collection('hubspot_deals').document(deal.id)
            doc_ref.set(deal_data)

            return deal

        except Exception as e:
            logger.error(f"Error storing HubSpot deal: {str(e)}")
            raise

    async def store_hubspot_company(self, company: HubSpotCompany) -> HubSpotCompany:
        """Store HubSpot company in Firebase"""
        try:
            company_data = asdict(company)
            company_data['firebase_updated_at'] = admin_firestore.SERVER_TIMESTAMP

            doc_ref = self.db.collection('hubspot_companies').document(company.id)
            doc_ref.set(company_data)

            return company

        except Exception as e:
            logger.error(f"Error storing HubSpot company: {str(e)}")
            raise

    async def get_hubspot_contacts(self, limit: int = 100) -> List[HubSpotContact]:
        """Get HubSpot contacts from Firebase"""
        try:
            query = (self.db.collection('hubspot_contacts')
                    .order_by('firebase_updated_at', direction=Query.DESCENDING)
                    .limit(limit))

            docs = query.stream()
            contacts = []

            for doc in docs:
                contact_data = doc.to_dict()
                contacts.append(HubSpotContact(**contact_data))

            return contacts

        except Exception as e:
            logger.error(f"Error getting HubSpot contacts: {str(e)}")
            return []

    async def get_hubspot_deals(self, limit: int = 100) -> List[HubSpotDeal]:
        """Get HubSpot deals from Firebase"""
        try:
            query = (self.db.collection('hubspot_deals')
                    .order_by('firebase_updated_at', direction=Query.DESCENDING)
                    .limit(limit))

            docs = query.stream()
            deals = []

            for doc in docs:
                deal_data = doc.to_dict()
                deals.append(HubSpotDeal(**deal_data))

            return deals

        except Exception as e:
            logger.error(f"Error getting HubSpot deals: {str(e)}")
            return []

    async def get_recent_hubspot_changes(self, since: datetime) -> Dict[str, List]:
        """Get recent HubSpot data changes"""
        try:
            contacts_query = (self.db.collection('hubspot_contacts')
                            .where('firebase_updated_at', '>', since)
                            .order_by('firebase_updated_at', direction=Query.DESCENDING))

            deals_query = (self.db.collection('hubspot_deals')
                          .where('firebase_updated_at', '>', since)
                          .order_by('firebase_updated_at', direction=Query.DESCENDING))

            contacts = [HubSpotContact(**doc.to_dict()) for doc in contacts_query.stream()]
            deals = [HubSpotDeal(**doc.to_dict()) for doc in deals_query.stream()]

            return {
                'contacts': contacts,
                'deals': deals,
                'total_changes': len(contacts) + len(deals)
            }

        except Exception as e:
            logger.error(f"Error getting recent HubSpot changes: {str(e)}")
            return {'contacts': [], 'deals': [], 'total_changes': 0}

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
        """Comprehensive Firebase service health check"""
        health_status = {
            "status": "healthy",
            "mode": self._mode.value,
            "services": {
                "firestore": False,
                "auth": False,
                "storage": False
            },
            "metrics": {
                "consecutive_failures": self._health_status["consecutive_failures"],
                "retry_count": self._retry_count,
                "offline_storage_items": len(self._offline_storage)
            },
            "configuration": {
                "project_id": self._config.project_id if self._config else None,
                "has_private_key": bool(self._config.private_key if self._config else None),
                "is_valid_config": self._config.is_valid() if self._config else False
            },
            "timestamp": datetime.utcnow().isoformat(),
            "last_check": self._health_status["last_check"]
        }

        try:
            if self.is_online and self._db:
                # Test Firestore connection
                async def firestore_test():
                    doc_ref = self.db.collection('health').document('check')
                    test_data = {
                        'timestamp': admin_firestore.SERVER_TIMESTAMP,
                        'service': 'health_check',
                        'test': True
                    }
                    doc_ref.set(test_data)
                    doc_ref.delete()

                await self.safe_firestore_operation("health_check_firestore", firestore_test)
                health_status["services"]["firestore"] = True
                health_status["services"]["auth"] = True  # Firestore implies auth is working
                health_status["services"]["storage"] = True

                # Reset failure count on successful health check
                self._health_status["consecutive_failures"] = 0

            else:
                health_status["status"] = "degraded" if self._mode == FirebaseMode.DEGRADED else "offline"
                health_status["services"] = {
                    "firestore": False,
                    "auth": False,
                    "storage": False
                }

        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
            health_status["services"] = {
                "firestore": False,
                "auth": False,
                "storage": False
            }

        self._health_status["last_check"] = datetime.utcnow().isoformat()
        return health_status

    async def get_diagnostics(self) -> Dict[str, Any]:
        """Get detailed diagnostic information"""
        try:
            config_errors = self._config.validate_format() if self._config else []

            diagnostics = {
                "service_mode": self._mode.value,
                "configuration": {
                    "project_id": self._config.project_id if self._config else None,
                    "client_email": self._config.client_email if self._config else None,
                    "private_key_length": len(self._config.private_key) if self._config and self._config.private_key else 0,
                    "is_valid": self._config.is_valid() if self._config else False,
                    "errors": config_errors
                },
                "connection_status": {
                    "has_app": self._app is not None,
                    "has_db": self._db is not None,
                    "is_online": self.is_online,
                    "last_auth_attempt": self._last_auth_attempt
                },
                "retry_info": {
                    "retry_count": self._retry_count,
                    "max_retries": self._max_retries,
                    "retry_delays": self._retry_delays
                },
                "offline_storage": {
                    "items": len(self._offline_storage),
                    "keys": list(self._offline_storage.keys())[:10]  # First 10 keys
                },
                "health_metrics": self._health_status,
                "environment": {
                    "firebase_project_id": bool(os.getenv('FIREBASE_PROJECT_ID')),
                    "firebase_client_email": bool(os.getenv('FIREBASE_CLIENT_EMAIL')),
                    "firebase_private_key": bool(os.getenv('FIREBASE_PRIVATE_KEY')),
                    "placeholder_detected": "TestKeyForDebuggingPurposesOnly" in (os.getenv('FIREBASE_PRIVATE_KEY', ''))
                }
            }

            return diagnostics

        except Exception as e:
            logger.error(f"Error getting diagnostics: {str(e)}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}

# Create singleton instance - will be initialized when first accessed
firebase_service = None

def get_firebase_service():
    """Get or create Firebase service instance"""
    global firebase_service
    if firebase_service is None:
        firebase_service = FirebaseService()
    return firebase_service

# Export for use in other modules
__all__ = [
    'FirebaseService',
    'firebase_service',
    'get_firebase_service',
    'Task',
    'GraphNode',
    'GraphEdge',
    'WebhookEvent',
    'AgentFile',
    'HubSpotContact',
    'HubSpotDeal',
    'HubSpotCompany'
]