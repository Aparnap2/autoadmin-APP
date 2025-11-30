"""
HubSpot API router for CRM data access
Provides endpoints for contacts, deals, and companies
"""

import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import get_logger
from app.middleware.error_handler import (
    AutoAdminException,
    ExternalServiceException
)

# Import services
from services.firebase_service import get_firebase_service
from services.hubspot_service import get_hubspot_service

logger = get_logger(__name__)

router = APIRouter()

# Initialize services
firebase_service = get_firebase_service()
hubspot_service = get_hubspot_service()

@router.get("/contacts", summary="Get HubSpot Contacts")
async def get_hubspot_contacts(
    limit: int = Query(default=100, ge=1, le=1000, description="Number of contacts to retrieve"),
    after: Optional[str] = Query(default=None, description="Pagination cursor")
):
    """
    Get HubSpot contacts from Firebase cache
    Data is synced via webhooks and manual sync operations
    """
    try:
        contacts = await firebase_service.get_hubspot_contacts(limit)
        return JSONResponse(
            content={
                "success": True,
                "data": contacts,
                "count": len(contacts),
                "timestamp": datetime.utcnow().isoformat()
            },
            status_code=200
        )

    except Exception as e:
        logger.error(f"Error getting HubSpot contacts: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve contacts")

@router.get("/deals", summary="Get HubSpot Deals")
async def get_hubspot_deals(
    limit: int = Query(default=100, ge=1, le=1000, description="Number of deals to retrieve"),
    after: Optional[str] = Query(default=None, description="Pagination cursor")
):
    """
    Get HubSpot deals from Firebase cache
    Data is synced via webhooks and manual sync operations
    """
    try:
        deals = await firebase_service.get_hubspot_deals(limit)
        return JSONResponse(
            content={
                "success": True,
                "data": deals,
                "count": len(deals),
                "timestamp": datetime.utcnow().isoformat()
            },
            status_code=200
        )

    except Exception as e:
        logger.error(f"Error getting HubSpot deals: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve deals")

@router.get("/companies", summary="Get HubSpot Companies")
async def get_hubspot_companies(
    limit: int = Query(default=100, ge=1, le=1000, description="Number of companies to retrieve"),
    after: Optional[str] = Query(default=None, description="Pagination cursor")
):
    """
    Get HubSpot companies from Firebase cache
    Data is synced via webhooks and manual sync operations
    """
    try:
        companies = await firebase_service.get_hubspot_companies(limit)
        return JSONResponse(
            content={
                "success": True,
                "data": companies,
                "count": len(companies),
                "timestamp": datetime.utcnow().isoformat()
            },
            status_code=200
        )

    except Exception as e:
        logger.error(f"Error getting HubSpot companies: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve companies")

@router.get("/recent", summary="Get Recent HubSpot Changes")
async def get_recent_hubspot_changes(
    since_hours: int = Query(default=24, ge=1, le=168, description="Hours to look back for changes")
):
    """
    Get recent HubSpot data changes from Firebase
    Useful for displaying recent activity
    """
    try:
        since = datetime.utcnow() - timedelta(hours=since_hours)
        changes = await firebase_service.get_recent_hubspot_changes(since)

        return JSONResponse(
            content={
                "success": True,
                "data": changes,
                "since": since.isoformat(),
                "total_changes": changes["total_changes"],
                "timestamp": datetime.utcnow().isoformat()
            },
            status_code=200
        )

    except Exception as e:
        logger.error(f"Error getting recent HubSpot changes: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve recent changes")

@router.post("/sync", summary="Manually Sync HubSpot Data")
async def manual_sync_hubspot_data(
    background_tasks: BackgroundTasks
):
    """
    Manually trigger HubSpot data synchronization
    Fetches latest data from HubSpot and updates Firebase cache
    """
    try:
        if not hubspot_service.is_online:
            raise HTTPException(status_code=503, detail="HubSpot service is offline")

        # Trigger background sync
        background_tasks.add_task(sync_hubspot_data_background)

        return JSONResponse(
            content={
                "success": True,
                "message": "HubSpot data synchronization started",
                "timestamp": datetime.utcnow().isoformat()
            },
            status_code=202
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering manual sync: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start sync")

@router.get("/status", summary="Get HubSpot Integration Status")
async def get_hubspot_integration_status():
    """
    Get the current status of HubSpot integration
    Includes service health and recent sync information
    """
    try:
        hubspot_health = await hubspot_service.health_check()
        firebase_health = await firebase_service.health_check()

        # Get recent sync stats
        recent_changes = await firebase_service.get_recent_hubspot_changes(
            datetime.utcnow() - timedelta(hours=24)
        )

        return JSONResponse(
            content={
                "success": True,
                "hubspot_service": hubspot_health,
                "firebase_service": firebase_health,
                "recent_activity": {
                    "contacts_last_24h": len(recent_changes.get("contacts", [])),
                    "deals_last_24h": len(recent_changes.get("deals", [])),
                    "total_changes_last_24h": recent_changes.get("total_changes", 0)
                },
                "integration_status": "healthy" if (
                    hubspot_health.get('status') == 'healthy' and
                    firebase_health.get('status') == 'healthy'
                ) else 'degraded',
                "timestamp": datetime.utcnow().isoformat()
            },
            status_code=200
        )

    except Exception as e:
        logger.error(f"Error getting integration status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get status")

async def sync_hubspot_data_background():
    """Background task to sync HubSpot data"""
    try:
        logger.info("Starting background HubSpot data sync")

        # Sync contacts
        if hubspot_service.is_online:
            try:
                contacts = await hubspot_service.get_contacts(limit=100)
                for contact in contacts:
                    await firebase_service.store_hubspot_contact(contact)
                logger.info(f"Synced {len(contacts)} contacts")
            except Exception as e:
                logger.error(f"Error syncing contacts: {str(e)}")

            # Sync deals
            try:
                deals = await hubspot_service.get_deals(limit=100)
                for deal in deals:
                    await firebase_service.store_hubspot_deal(deal)
                logger.info(f"Synced {len(deals)} deals")
            except Exception as e:
                logger.error(f"Error syncing deals: {str(e)}")

            # Sync companies
            try:
                companies = await hubspot_service.get_companies(limit=100)
                for company in companies:
                    await firebase_service.store_hubspot_company(company)
                logger.info(f"Synced {len(companies)} companies")
            except Exception as e:
                logger.error(f"Error syncing companies: {str(e)}")

        # Sync offline storage if any
        await hubspot_service.sync_offline_storage()

        logger.info("HubSpot data sync completed")

    except Exception as e:
        logger.error(f"Error in background HubSpot sync: {str(e)}")

# Add router to main app
def register_hubspot_router(app):
    """Register HubSpot router with the FastAPI app"""
    app.include_router(
        router,
        prefix="/api/v1/hubspot",
        tags=["HubSpot"],
        responses={404: {"description": "Not found"}},
    )