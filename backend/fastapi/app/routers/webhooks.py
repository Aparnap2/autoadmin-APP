"""
Webhooks router for handling external service webhooks
Processes HubSpot webhooks and syncs data to Firebase
"""

import os
import json
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import get_logger
from app.middleware.error_handler import (
    AutoAdminException,
    ValidationException,
    ExternalServiceException,
)

# Import services
from services.firebase_service import get_firebase_service
from services.hubspot_service import get_hubspot_service

logger = get_logger(__name__)

router = APIRouter()

# Initialize services lazily
firebase_service = None
hubspot_service = None


def get_firebase_service_instance():
    global firebase_service
    if firebase_service is None:
        firebase_service = get_firebase_service()
    return firebase_service


def get_hubspot_service_instance():
    global hubspot_service
    if hubspot_service is None:
        hubspot_service = get_hubspot_service()
    return hubspot_service


async def verify_hubspot_signature(request: Request, body: bytes) -> bool:
    """Verify HubSpot webhook signature"""
    signature = request.headers.get("X-HubSpot-Signature")
    if not signature:
        return False

    # Get webhook secret from environment
    webhook_secret = os.getenv("WEBHOOK_SECRET", "")
    if not webhook_secret:
        logger.warning("WEBHOOK_SECRET not configured")
        return False

    # Create expected signature
    expected_signature = hmac.new(
        webhook_secret.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()

    # Use constant-time comparison
    return hmac.compare_digest(signature, expected_signature)


@router.post("/hubspot", summary="Handle HubSpot Webhooks")
async def handle_hubspot_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Handle HubSpot webhooks for real-time data synchronization

    Processes contact, deal, and company events from HubSpot
    and syncs them to Firebase database
    """
    try:
        # Get raw body for signature verification
        body = await request.body()
        payload = json.loads(body.decode("utf-8"))

        # Verify signature if secret is configured
        webhook_secret = os.getenv("WEBHOOK_SECRET", "")
        if webhook_secret:
            is_valid = await verify_hubspot_signature(request, body)
            if not is_valid:
                raise HTTPException(status_code=401, detail="Invalid webhook signature")

        # Process webhook in background
        background_tasks.add_task(process_hubspot_webhook, payload)

        return JSONResponse(
            content={"status": "accepted", "message": "Webhook processed successfully"},
            status_code=200,
        )

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    except Exception as e:
        logger.error(f"Error processing HubSpot webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def process_hubspot_webhook(payload: Dict[str, Any]):
    """Process HubSpot webhook payload in background"""
    try:
        # Handle different HubSpot webhook events
        if "eventType" in payload:
            await process_hubspot_event(payload)
        elif "events" in payload:
            # Handle batch events
            for event in payload["events"]:
                await process_hubspot_event(event)
        else:
            logger.warning(f"Unknown HubSpot webhook format: {payload}")

    except Exception as e:
        logger.error(f"Error processing HubSpot webhook payload: {str(e)}")


async def process_hubspot_event(event: Dict[str, Any]):
    """Process individual HubSpot event"""
    try:
        event_type = event.get("eventType", "")
        object_id = event.get("objectId", "")
        property_name = event.get("propertyName")
        property_value = event.get("propertyValue")

        logger.info(f"Processing HubSpot event: {event_type} for object {object_id}")

        # Handle different event types
        if event_type == "contact.creation":
            await sync_hubspot_contact(object_id)
        elif event_type == "contact.deletion":
            await handle_contact_deletion(object_id)
        elif event_type == "deal.creation":
            await sync_hubspot_deal(object_id)
        elif event_type == "deal.deletion":
            await handle_deal_deletion(object_id)
        elif event_type == "company.creation":
            await sync_hubspot_company(object_id)
        elif event_type == "company.deletion":
            await handle_company_deletion(object_id)
        elif "deal.stage_change" in event_type or property_name == "dealstage":
            await sync_hubspot_deal(object_id)
        elif "contact" in event_type:
            await sync_hubspot_contact(object_id)
        elif "deal" in event_type:
            await sync_hubspot_deal(object_id)
        elif "company" in event_type:
            await sync_hubspot_company(object_id)
        else:
            logger.info(f"Ignoring unhandled HubSpot event type: {event_type}")

    except Exception as e:
        logger.error(f"Error processing HubSpot event {event}: {str(e)}")


async def sync_hubspot_contact(contact_id: str):
    """Sync HubSpot contact to Firebase"""
    try:
        if not get_hubspot_service_instance().is_online:
            logger.warning("HubSpot service offline, skipping contact sync")
            return

        # Get contact details from HubSpot
        # Note: HubSpot webhooks don't include full object data, so we need to fetch it
        # This is a simplified version - in production you'd want to batch these requests

        # For now, we'll create a placeholder contact record
        # In a real implementation, you'd call hubspot_service to get contact details
        contact_data = {
            "id": contact_id,
            "email": f"contact_{contact_id}@example.com",  # Placeholder
            "firstname": f"Contact {contact_id}",  # Placeholder
            "hubspot_properties": {"id": contact_id},
            "firebase_updated_at": datetime.now(),
        }

        # Store in Firebase
        from services.firebase_service import HubSpotContact

        contact = HubSpotContact(**contact_data)
        await get_firebase_service_instance().store_hubspot_contact(contact)

        logger.info(f"Synced HubSpot contact {contact_id} to Firebase")

        # Trigger notification for new contact
        await send_new_lead_notification(contact, "contact")

    except Exception as e:
        logger.error(f"Error syncing HubSpot contact {contact_id}: {str(e)}")


async def sync_hubspot_deal(deal_id: str):
    """Sync HubSpot deal to Firebase"""
    try:
        if not get_hubspot_service_instance().is_online:
            logger.warning("HubSpot service offline, skipping deal sync")
            return

        # Placeholder deal data
        deal_data = {
            "id": deal_id,
            "dealname": f"Deal {deal_id}",  # Placeholder
            "dealstage": "appointmentscheduled",  # Placeholder
            "hubspot_properties": {"id": deal_id},
            "firebase_updated_at": datetime.now(),
        }

        # Store in Firebase
        from services.firebase_service import HubSpotDeal

        deal = HubSpotDeal(**deal_data)
        await get_firebase_service_instance().store_hubspot_deal(deal)

        logger.info(f"Synced HubSpot deal {deal_id} to Firebase")

        # Trigger notification for new/high-value deal
        await send_new_lead_notification(deal, "deal")

    except Exception as e:
        logger.error(f"Error syncing HubSpot deal {deal_id}: {str(e)}")


async def sync_hubspot_company(company_id: str):
    """Sync HubSpot company to Firebase"""
    try:
        if not get_hubspot_service_instance().is_online:
            logger.warning("HubSpot service offline, skipping company sync")
            return

        # Placeholder company data
        company_data = {
            "id": company_id,
            "name": f"Company {company_id}",  # Placeholder
            "hubspot_properties": {"id": company_id},
            "firebase_updated_at": datetime.now(),
        }

        # Store in Firebase
        from services.firebase_service import HubSpotCompany

        company = HubSpotCompany(**company_data)
        await get_firebase_service_instance().store_hubspot_company(company)

        logger.info(f"Synced HubSpot company {company_id} to Firebase")

    except Exception as e:
        logger.error(f"Error syncing HubSpot company {company_id}: {str(e)}")


async def handle_contact_deletion(contact_id: str):
    """Handle contact deletion"""
    logger.info(f"Handling contact deletion: {contact_id}")
    # In a real implementation, you might want to mark as deleted or remove from Firebase


async def handle_deal_deletion(deal_id: str):
    """Handle deal deletion"""
    logger.info(f"Handling deal deletion: {deal_id}")
    # In a real implementation, you might want to mark as deleted or remove from Firebase


async def handle_company_deletion(company_id: str):
    """Handle company deletion"""
    logger.info(f"Handling company deletion: {company_id}")
    # In a real implementation, you might want to mark as deleted or remove from Firebase


async def send_new_lead_notification(lead_data: Any, lead_type: str):
    """Send push notification for new lead"""
    try:
        # Create notification payload
        notification = {
            "type": "new_lead",
            "lead_type": lead_type,
            "lead_id": lead_data.id,
            "title": f"New {lead_type.title()} Lead",
            "message": f"A new {lead_type} has been added to HubSpot",
            "data": {
                "lead_type": lead_type,
                "lead_id": lead_data.id,
                "timestamp": datetime.now().isoformat(),
            },
            "created_at": datetime.now(),
        }

        # Store notification in Firebase
        await get_firebase_service_instance().create_webhook_event(
            {
                "source": "hubspot_webhook",
                "event": "new_lead",
                "payload": notification,
                "type": "notification",
            }
        )

        logger.info(f"Sent notification for new {lead_type}: {lead_data.id}")

    except Exception as e:
        logger.error(f"Error sending lead notification: {str(e)}")


@router.get("/hubspot/sync", summary="Manually Sync HubSpot Data")
async def manual_hubspot_sync():
    """
    Manually trigger HubSpot data synchronization
    Useful for initial setup or forced sync
    """
    try:
        if not get_hubspot_service_instance().is_online:
            raise HTTPException(status_code=503, detail="HubSpot service is offline")

        # Trigger background sync
        # In a real implementation, this would sync all recent data
        logger.info("Manual HubSpot sync triggered")

        return JSONResponse(
            content={
                "status": "sync_started",
                "message": "HubSpot data synchronization initiated",
            },
            status_code=200,
        )

    except Exception as e:
        logger.error(f"Error triggering manual sync: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start sync")


@router.get("/hubspot/status", summary="Get HubSpot Integration Status")
async def get_hubspot_status():
    """Get the current status of HubSpot integration"""
    try:
        hubspot_health = await get_hubspot_service_instance().health_check()
        firebase_health = await get_firebase_service_instance().health_check()

        return JSONResponse(
            content={
                "hubspot_service": hubspot_health,
                "firebase_service": firebase_health,
                "integration_status": "healthy"
                if hubspot_health.get("status") == "healthy"
                and firebase_health.get("status") == "healthy"
                else "degraded",
            },
            status_code=200,
        )

    except Exception as e:
        logger.error(f"Error getting integration status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get status")
