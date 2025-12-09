"""
HubSpot Service for Python Backend
Integrates with HubSpot CRM API for contacts, deals, and companies
Includes offline support and robust error handling
"""

import os
import json
import logging
import time
import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

try:
    from hubspot import HubSpot
    from hubspot.crm.contacts import SimplePublicObjectInputForCreate as ContactInput, ApiException as ContactApiException
    from hubspot.crm.deals import SimplePublicObjectInputForCreate as DealInput, ApiException as DealApiException
    from hubspot.crm.companies import SimplePublicObjectInputForCreate as CompanyInput, ApiException as CompanyApiException
    HUBSPOT_AVAILABLE = True
except ImportError:
    HUBSPOT_AVAILABLE = False
    HubSpot = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("Loaded environment variables from .env file")
except ImportError:
    logger.warning("python-dotenv not available, using system environment variables only")

class HubSpotMode(Enum):
    """HubSpot service operating mode"""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    RECOVERING = "recovering"

@dataclass
class HubSpotConfig:
    """HubSpot configuration validation"""
    access_token: str
    api_base_url: str = "https://api.hubapi.com"

    @classmethod
    def from_env(cls) -> 'HubSpotConfig':
        """Create config from environment variables"""
        return cls(
            access_token=os.getenv('HUBSPOT_ACCESS_TOKEN', ''),
            api_base_url=os.getenv('HUBSPOT_API_BASE_URL', 'https://api.hubapi.com')
        )

    def is_valid(self) -> bool:
        """Validate configuration"""
        if not self.access_token:
            return False

        # Check for placeholder tokens
        placeholder_indicators = [
            "PLACEHOLDER",
            "YOUR_TOKEN",
            "EXAMPLE_TOKEN",
            "pat-test"
        ]

        for indicator in placeholder_indicators:
            if indicator in self.access_token.lower():
                return False

        # Check if it looks like a private app token (starts with pat-)
        if not self.access_token.startswith('pat-'):
            return False

        return True

    def validate_format(self) -> List[str]:
        """Validate configuration format and return errors"""
        errors = []

        if not self.access_token:
            errors.append("HUBSPOT_ACCESS_TOKEN is missing")
        elif not self.access_token.startswith('pat-'):
            errors.append("HUBSPOT_ACCESS_TOKEN should start with 'pat-' for private app tokens")
        elif len(self.access_token) < 20:
            errors.append("HUBSPOT_ACCESS_TOKEN appears to be too short")

        return errors

@dataclass
class HubSpotContact:
    """HubSpot contact data structure"""
    id: Optional[str] = None
    email: Optional[str] = None
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    website: Optional[str] = None
    lifecyclestage: Optional[str] = None
    createdate: Optional[datetime] = None
    lastmodifieddate: Optional[datetime] = None
    properties: Optional[Dict[str, Any]] = None

@dataclass
class HubSpotDeal:
    """HubSpot deal data structure"""
    id: Optional[str] = None
    dealname: Optional[str] = None
    dealstage: Optional[str] = None
    amount: Optional[float] = None
    closedate: Optional[datetime] = None
    dealtype: Optional[str] = None
    pipeline: Optional[str] = None
    createdate: Optional[datetime] = None
    lastmodifieddate: Optional[datetime] = None
    properties: Optional[Dict[str, Any]] = None

@dataclass
class HubSpotCompany:
    """HubSpot company data structure"""
    id: Optional[str] = None
    name: Optional[str] = None
    domain: Optional[str] = None
    industry: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    createdate: Optional[datetime] = None
    lastmodifieddate: Optional[datetime] = None
    properties: Optional[Dict[str, Any]] = None

class HubSpotService:
    """
    HubSpot service with robust error handling and offline support
    """

    _instance = None
    _client = None
    _mode = HubSpotMode.OFFLINE
    _config = None
    _last_api_call = None
    _retry_count = 0
    _max_retries = 3
    _retry_delays = [1, 2, 5]  # seconds
    _offline_storage = {}  # In-memory offline storage
    _health_status = {"last_check": None, "consecutive_failures": 0}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(HubSpotService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the service with enhanced error handling"""
        if not hasattr(self, '_initialized'):
            self._initialized = True
            asyncio.create_task(self._initialize_with_retry())

    async def _initialize_with_retry(self):
        """Initialize HubSpot client with retry logic"""
        try:
            await self._validate_configuration()
            await self._attempt_initialization()
        except Exception as e:
            logger.error(f"HubSpot initialization failed: {e}")
            await self._fallback_to_offline_mode(str(e))

    async def _validate_configuration(self):
        """Validate HubSpot configuration"""
        if not HUBSPOT_AVAILABLE:
            raise ImportError("HubSpot API client not available. Install with: pip install hubspot-api-client")

        self._config = HubSpotConfig.from_env()
        errors = self._config.validate_format()
        if errors:
            logger.warning(f"HubSpot configuration validation errors: {errors}")

        if not self._config.is_valid():
            logger.warning("HubSpot configuration invalid, proceeding in offline mode")
            await self._fallback_to_offline_mode("Invalid HubSpot configuration")

    async def _attempt_initialization(self, is_retry: bool = False):
        """Attempt HubSpot client initialization"""
        if is_retry:
            self._mode = HubSpotMode.RECOVERING

        try:
            if not self._config.is_valid():
                raise ValueError("Invalid HubSpot configuration")

            # Initialize HubSpot client
            self._client = HubSpot(access_token=self._config.access_token)

            # Test the connection
            await self._test_connection()

            self._mode = HubSpotMode.ONLINE
            self._retry_count = 0
            self._health_status["consecutive_failures"] = 0

            logger.info("HubSpot client initialized successfully")

        except Exception as e:
            logger.error(f"HubSpot initialization attempt {self._retry_count + 1} failed: {str(e)}")

            if self._retry_count < self._max_retries:
                self._retry_count += 1
                delay = self._retry_delays[min(self._retry_count - 1, len(self._retry_delays) - 1)]

                logger.info(f"Retrying HubSpot initialization in {delay} seconds (attempt {self._retry_count + 1}/{self._max_retries})")

                await asyncio.sleep(delay)
                await self._attempt_initialization(is_retry=True)
            else:
                logger.error("Max retry attempts reached, falling back to offline mode")
                await self._fallback_to_offline_mode(str(e))

    async def _test_connection(self):
        """Test HubSpot API connection"""
        if not self._client:
            raise ValueError("HubSpot client not initialized")

        try:
            # Test with a simple API call - get contacts (limit 1)
            response = self._client.crm.contacts.get_all(limit=1)
            logger.info("HubSpot API connection test successful")
        except Exception as e:
            logger.warning(f"HubSpot API test failed: {e}")
            # Don't fail initialization for test errors, just log

    async def _fallback_to_offline_mode(self, reason: str):
        """Fallback to offline mode"""
        logger.warning(f"Falling back to offline mode: {reason}")
        self._mode = HubSpotMode.OFFLINE
        self._client = None
        self._health_status["consecutive_failures"] += 1

    async def attempt_recovery(self):
        """Attempt to recover from offline mode"""
        if self._mode == HubSpotMode.ONLINE:
            return True

        if self._last_api_call and (time.time() - self._last_api_call) < 60:
            return False  # Wait before next attempt

        self._last_api_call = time.time()
        logger.info("Attempting HubSpot recovery...")

        try:
            if self._config.is_valid():
                await self._attempt_initialization()
                return self._mode == HubSpotMode.ONLINE
            else:
                logger.warning("HubSpot configuration still invalid during recovery")
                return False

        except Exception as e:
            logger.error(f"HubSpot recovery failed: {e}")
            return False

    @property
    def mode(self) -> HubSpotMode:
        """Get current service mode"""
        return self._mode

    @property
    def is_online(self) -> bool:
        """Check if service is online"""
        return self._mode == HubSpotMode.ONLINE

    @property
    def is_offline(self) -> bool:
        """Check if service is offline"""
        return self._mode in [HubSpotMode.OFFLINE, HubSpotMode.DEGRADED]

    @property
    def client(self) -> HubSpot:
        """Get HubSpot client"""
        if self._client is None:
            if not self.is_online:
                asyncio.create_task(self.attempt_recovery())
            raise Exception("HubSpot is not initialized. Running in offline mode.")
        return self._client

    async def safe_hubspot_operation(self, operation_name: str, operation_func):
        """Execute a HubSpot operation with error handling and recovery"""
        if not self.is_online:
            logger.info(f"Skipping {operation_name} - HubSpot is offline")
            return None

        try:
            self._last_api_call = time.time()
            return await operation_func()
        except Exception as e:
            logger.error(f"HubSpot operation '{operation_name}' failed: {str(e)}")
            self._health_status["consecutive_failures"] += 1

            # If too many failures, attempt recovery
            if self._health_status["consecutive_failures"] >= 3:
                logger.warning("Multiple HubSpot failures detected, attempting recovery")
                await self.attempt_recovery()

            raise

    # Contact Operations
    async def get_contacts(self, limit: int = 100, after: Optional[str] = None) -> List[HubSpotContact]:
        """Get contacts from HubSpot"""
        try:
            if self.is_offline:
                logger.info("Returning empty contacts list - HubSpot offline")
                return []

            async def get_operation():
                if after:
                    response = self.client.crm.contacts.basic_api.get_page(limit=limit, after=after)
                else:
                    response = self.client.crm.contacts.basic_api.get_page(limit=limit)
                contacts = []

                for contact in response.results:
                    contact_data = {
                        'id': contact.id,
                        'properties': contact.properties
                    }

                    # Extract common properties
                    props = contact.properties
                    contacts.append(HubSpotContact(
                        id=contact.id,
                        email=props.get('email'),
                        firstname=props.get('firstname'),
                        lastname=props.get('lastname'),
                        phone=props.get('phone'),
                        company=props.get('company'),
                        website=props.get('website'),
                        lifecyclestage=props.get('lifecyclestage'),
                        createdate=self._parse_hubspot_date(props.get('createdate')),
                        lastmodifieddate=self._parse_hubspot_date(props.get('lastmodifieddate')),
                        properties=props
                    ))

                return contacts

            return await self.safe_hubspot_operation("get_contacts", get_operation) or []

        except Exception as e:
            logger.error(f"Error getting contacts: {str(e)}")
            return []

    async def create_contact(self, contact_data: Dict[str, Any]) -> Optional[HubSpotContact]:
        """Create a contact in HubSpot"""
        try:
            if self.is_offline:
                # Store in offline storage
                offline_contact_data = contact_data.copy()
                offline_contact_data['id'] = f"offline_{int(time.time())}"
                offline_contact_data['created_at'] = datetime.now()

                self._offline_storage[f"contact_{offline_contact_data['id']}"] = {
                    'data': offline_contact_data,
                    'created_at': datetime.now(),
                    'operation': 'create_contact'
                }

                logger.info(f"Created contact in offline mode: {offline_contact_data['id']}")
                return HubSpotContact(**offline_contact_data)

            async def create_operation():
                input_obj = ContactInput(properties=contact_data)
                response = self.client.crm.contacts.basic_api.create(input_obj)

                return HubSpotContact(
                    id=response.id,
                    email=contact_data.get('email'),
                    firstname=contact_data.get('firstname'),
                    lastname=contact_data.get('lastname'),
                    properties=response.properties
                )

            return await self.safe_hubspot_operation("create_contact", create_operation)

        except Exception as e:
            logger.error(f"Error creating contact: {str(e)}")
            return None

    # Deal Operations
    async def get_deals(self, limit: int = 100, after: Optional[str] = None) -> List[HubSpotDeal]:
        """Get deals from HubSpot"""
        try:
            if self.is_offline:
                logger.info("Returning empty deals list - HubSpot offline")
                return []

            async def get_operation():
                if after:
                    response = self.client.crm.deals.basic_api.get_page(limit=limit, after=after)
                else:
                    response = self.client.crm.deals.basic_api.get_page(limit=limit)
                deals = []

                for deal in response.results:
                    props = deal.properties
                    deals.append(HubSpotDeal(
                        id=deal.id,
                        dealname=props.get('dealname'),
                        dealstage=props.get('dealstage'),
                        amount=float(props.get('amount', 0)) if props.get('amount') else None,
                        closedate=self._parse_hubspot_date(props.get('closedate')),
                        dealtype=props.get('dealtype'),
                        pipeline=props.get('pipeline'),
                        createdate=self._parse_hubspot_date(props.get('createdate')),
                        lastmodifieddate=self._parse_hubspot_date(props.get('lastmodifieddate')),
                        properties=props
                    ))

                return deals

            return await self.safe_hubspot_operation("get_deals", get_operation) or []

        except Exception as e:
            logger.error(f"Error getting deals: {str(e)}")
            return []

    async def create_deal(self, deal_data: Dict[str, Any]) -> Optional[HubSpotDeal]:
        """Create a deal in HubSpot"""
        try:
            if self.is_offline:
                # Store in offline storage
                offline_deal_data = deal_data.copy()
                offline_deal_data['id'] = f"offline_{int(time.time())}"
                offline_deal_data['created_at'] = datetime.now()

                self._offline_storage[f"deal_{offline_deal_data['id']}"] = {
                    'data': offline_deal_data,
                    'created_at': datetime.now(),
                    'operation': 'create_deal'
                }

                logger.info(f"Created deal in offline mode: {offline_deal_data['id']}")
                return HubSpotDeal(**offline_deal_data)

            async def create_operation():
                input_obj = DealInput(properties=deal_data)
                response = self.client.crm.deals.basic_api.create(input_obj)

                return HubSpotDeal(
                    id=response.id,
                    dealname=deal_data.get('dealname'),
                    dealstage=deal_data.get('dealstage'),
                    amount=float(deal_data.get('amount', 0)) if deal_data.get('amount') else None,
                    properties=response.properties
                )

            return await self.safe_hubspot_operation("create_deal", create_operation)

        except Exception as e:
            logger.error(f"Error creating deal: {str(e)}")
            return None

    # Company Operations
    async def get_companies(self, limit: int = 100, after: Optional[str] = None) -> List[HubSpotCompany]:
        """Get companies from HubSpot"""
        try:
            if self.is_offline:
                logger.info("Returning empty companies list - HubSpot offline")
                return []

            async def get_operation():
                if after:
                    response = self.client.crm.companies.basic_api.get_page(limit=limit, after=after)
                else:
                    response = self.client.crm.companies.basic_api.get_page(limit=limit)
                companies = []

                for company in response.results:
                    props = company.properties
                    companies.append(HubSpotCompany(
                        id=company.id,
                        name=props.get('name'),
                        domain=props.get('domain'),
                        industry=props.get('industry'),
                        city=props.get('city'),
                        state=props.get('state'),
                        country=props.get('country'),
                        createdate=self._parse_hubspot_date(props.get('createdate')),
                        lastmodifieddate=self._parse_hubspot_date(props.get('lastmodifieddate')),
                        properties=props
                    ))

                return companies

            return await self.safe_hubspot_operation("get_companies", get_operation) or []

        except Exception as e:
            logger.error(f"Error getting companies: {str(e)}")
            return []

    # Recent Changes
    async def get_recent_contacts(self, since: datetime) -> List[HubSpotContact]:
        """Get contacts modified since a specific date"""
        try:
            if self.is_offline:
                return []

            # Convert datetime to HubSpot timestamp (milliseconds)
            since_timestamp = int(since.timestamp() * 1000)

            async def search_operation():
                from hubspot.crm.contacts import PublicObjectSearchRequest, Filter, FilterGroup

                filter_group = FilterGroup(
                    filters=[
                        Filter(
                            property_name="lastmodifieddate",
                            operator="GT",
                            value=str(since_timestamp)
                        )
                    ]
                )

                search_request = PublicObjectSearchRequest(
                    filter_groups=[filter_group],
                    limit=100
                )

                response = self.client.crm.contacts.search_api.do_search(search_request)
                contacts = []

                for contact in response.results:
                    props = contact.properties
                    contacts.append(HubSpotContact(
                        id=contact.id,
                        email=props.get('email'),
                        firstname=props.get('firstname'),
                        lastname=props.get('lastname'),
                        properties=props
                    ))

                return contacts

            return await self.safe_hubspot_operation("get_recent_contacts", search_operation) or []

        except Exception as e:
            logger.error(f"Error getting recent contacts: {str(e)}")
            return []

    async def get_recent_deals(self, since: datetime) -> List[HubSpotDeal]:
        """Get deals modified since a specific date"""
        try:
            if self.is_offline:
                return []

            since_timestamp = int(since.timestamp() * 1000)

            async def search_operation():
                from hubspot.crm.deals import PublicObjectSearchRequest, Filter, FilterGroup

                filter_group = FilterGroup(
                    filters=[
                        Filter(
                            property_name="lastmodifieddate",
                            operator="GT",
                            value=str(since_timestamp)
                        )
                    ]
                )

                search_request = PublicObjectSearchRequest(
                    filter_groups=[filter_group],
                    limit=100
                )

                response = self.client.crm.deals.search_api.do_search(search_request)
                deals = []

                for deal in response.results:
                    props = deal.properties
                    deals.append(HubSpotDeal(
                        id=deal.id,
                        dealname=props.get('dealname'),
                        dealstage=props.get('dealstage'),
                        properties=props
                    ))

                return deals

            return await self.safe_hubspot_operation("get_recent_deals", search_operation) or []

        except Exception as e:
            logger.error(f"Error getting recent deals: {str(e)}")
            return []

    def _parse_hubspot_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse HubSpot date string to datetime"""
        if not date_str:
            return None

        try:
            # HubSpot dates are in milliseconds since epoch
            timestamp = int(date_str) / 1000
            return datetime.fromtimestamp(timestamp)
        except (ValueError, TypeError):
            return None

    async def sync_offline_storage(self) -> Dict[str, Any]:
        """Sync offline storage with HubSpot when connection is restored"""
        try:
            if not self.is_online:
                return {"success": False, "error": "HubSpot is offline"}

            if not self._offline_storage:
                return {"success": True, "synced": 0, "error": None}

            synced_count = 0
            errors = []

            for key, item in list(self._offline_storage.items()):
                try:
                    operation = item['operation']
                    data = item['data']

                    if operation == 'create_contact':
                        # Sync contact to HubSpot
                        contact_data = {k: v for k, v in data.items() if k not in ['id', 'created_at']}
                        await self.create_contact(contact_data)
                        synced_count += 1

                    elif operation == 'create_deal':
                        # Sync deal to HubSpot
                        deal_data = {k: v for k, v in data.items() if k not in ['id', 'created_at']}
                        await self.create_deal(deal_data)
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

    async def health_check(self) -> Dict[str, Any]:
        """HubSpot service health check"""
        health_status = {
            "status": "healthy",
            "mode": self._mode.value,
            "services": {
                "hubspot_api": False
            },
            "metrics": {
                "consecutive_failures": self._health_status["consecutive_failures"],
                "retry_count": self._retry_count,
                "offline_storage_items": len(self._offline_storage)
            },
            "configuration": {
                "has_access_token": bool(self._config.access_token if self._config else None),
                "is_valid_config": self._config.is_valid() if self._config else False,
                "token_prefix": self._config.access_token[:4] if self._config and self._config.access_token else None
            },
            "timestamp": datetime.utcnow().isoformat(),
            "last_check": self._health_status["last_check"]
        }

        try:
            if self.is_online and self._client:
                # Test HubSpot API connection
                await self._test_connection()
                health_status["services"]["hubspot_api"] = True

                # Reset failure count on successful health check
                self._health_status["consecutive_failures"] = 0

            else:
                health_status["status"] = "degraded" if self._mode == HubSpotMode.DEGRADED else "offline"
                health_status["services"]["hubspot_api"] = False

        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
            health_status["services"]["hubspot_api"] = False

        self._health_status["last_check"] = datetime.utcnow().isoformat()
        return health_status

# Create singleton instance
hubspot_service = None

def get_hubspot_service():
    """Get or create HubSpot service instance"""
    global hubspot_service
    if hubspot_service is None:
        hubspot_service = HubSpotService()
    return hubspot_service

# Export for use in other modules
__all__ = [
    'HubSpotService',
    'hubspot_service',
    'get_hubspot_service',
    'HubSpotContact',
    'HubSpotDeal',
    'HubSpotCompany'
]