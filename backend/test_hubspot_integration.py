#!/usr/bin/env python3
"""
HubSpot Integration Test Script
Tests all HubSpot endpoints and functionality
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any
from contextlib import asynccontextmanager

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print("⚠️  python-dotenv not available, using system environment variables only")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Import our HubSpot services
from services.hubspot_service import get_hubspot_service
from services.firebase_service import get_firebase_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app with lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global hubspot_service, firebase_service

    # Startup
    logger.info("🚀 HubSpot Integration Test API starting up...")
    try:
        hubspot_service = get_hubspot_service()
        firebase_service = get_firebase_service()
        logger.info("✅ Services initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {e}")

    yield

    # Shutdown
    logger.info("🛑 HubSpot Integration Test API shutting down...")

app = FastAPI(
    title="HubSpot Integration Test API",
    description="Test API for HubSpot CRM integration",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class HubSpotWebhookPayload(BaseModel):
    eventType: str
    objectId: str
    propertyName: str = None
    propertyValue: str = None

# Initialize services (will be done in lifespan)
hubspot_service = None
firebase_service = None

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "HubSpot Integration Test API",
        "status": "running",
        "version": "1.0.0",
        "services": {
            "hubspot": "initialized",
            "firebase": "initialized"
        }
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    hubspot_health = await hubspot_service.health_check()
    firebase_health = await firebase_service.health_check()

    return {
        "status": "healthy" if hubspot_health.get('status') == 'healthy' and firebase_health.get('status') == 'healthy' else "degraded",
        "services": {
            "hubspot": hubspot_health,
            "firebase": firebase_health
        }
    }

# HubSpot API endpoints
@app.get("/api/v1/hubspot/contacts")
async def get_hubspot_contacts(limit: int = 50):
    """Get HubSpot contacts"""
    try:
        contacts = await firebase_service.get_hubspot_contacts(limit)
        return {
            "success": True,
            "data": contacts,
            "count": len(contacts)
        }
    except Exception as e:
        logger.error(f"Error getting contacts: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/v1/hubspot/deals")
async def get_hubspot_deals(limit: int = 50):
    """Get HubSpot deals"""
    try:
        deals = await firebase_service.get_hubspot_deals(limit)
        return {
            "success": True,
            "data": deals,
            "count": len(deals)
        }
    except Exception as e:
        logger.error(f"Error getting deals: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/v1/hubspot/companies")
async def get_hubspot_companies(limit: int = 50):
    """Get HubSpot companies"""
    try:
        companies = await firebase_service.get_hubspot_companies(limit)
        return {
            "success": True,
            "data": companies,
            "count": len(companies)
        }
    except Exception as e:
        logger.error(f"Error getting companies: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/v1/hubspot/recent")
async def get_recent_changes(since_hours: int = 24):
    """Get recent HubSpot changes"""
    try:
        from datetime import datetime, timedelta
        since = datetime.utcnow() - timedelta(hours=since_hours)
        changes = await firebase_service.get_recent_hubspot_changes(since)
        return {
            "success": True,
            "data": changes,
            "since": since.isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting recent changes: {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/v1/hubspot/sync")
async def manual_sync():
    """Manually sync HubSpot data"""
    try:
        # For testing, we'll create some mock data
        from services.firebase_service import HubSpotContact, HubSpotDeal

        # Create mock contact
        contact = HubSpotContact(
            id="test_contact_123",
            email="test@example.com",
            firstname="Test",
            lastname="User",
            lifecyclestage="lead"
        )

        # Create mock deal
        deal = HubSpotDeal(
            id="test_deal_456",
            dealname="Test Deal",
            dealstage="appointmentscheduled",
            amount=50000.0
        )

        # Store in Firebase
        await firebase_service.store_hubspot_contact(contact)
        await firebase_service.store_hubspot_deal(deal)

        return {
            "success": True,
            "message": "Mock data synced successfully",
            "data": {
                "contacts_synced": 1,
                "deals_synced": 1
            }
        }
    except Exception as e:
        logger.error(f"Error syncing data: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/v1/hubspot/status")
async def get_integration_status():
    """Get HubSpot integration status"""
    try:
        hubspot_health = await hubspot_service.health_check()
        firebase_health = await firebase_service.health_check()

        return {
            "success": True,
            "hubspot_service": hubspot_health,
            "firebase_service": firebase_health,
            "integration_status": "healthy" if (
                hubspot_health.get('status') == 'healthy' and
                firebase_health.get('status') == 'healthy'
            ) else 'degraded'
        }
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return {"success": False, "error": str(e)}

# Webhook endpoints
@app.post("/api/v1/webhooks/hubspot")
async def handle_hubspot_webhook(payload: HubSpotWebhookPayload):
    """Handle HubSpot webhooks"""
    try:
        logger.info(f"Received HubSpot webhook: {payload.eventType} for {payload.objectId}")

        # Process webhook based on event type
        if payload.eventType == "contact.creation":
            # Create mock contact
            from services.firebase_service import HubSpotContact
            contact = HubSpotContact(
                id=payload.objectId,
                email=f"contact_{payload.objectId}@example.com",
                firstname=f"Contact {payload.objectId}",
                lifecyclestage="lead"
            )
            await firebase_service.store_hubspot_contact(contact)

        elif payload.eventType == "deal.creation":
            # Create mock deal
            from services.firebase_service import HubSpotDeal
            deal = HubSpotDeal(
                id=payload.objectId,
                dealname=f"Deal {payload.objectId}",
                dealstage="appointmentscheduled"
            )
            await firebase_service.store_hubspot_deal(deal)

        return {"success": True, "message": "Webhook processed"}

    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return {"success": False, "error": str(e)}

# Test data creation
@app.post("/api/v1/test/create-sample-data")
async def create_sample_data():
    """Create sample HubSpot data for testing"""
    try:
        from services.firebase_service import HubSpotContact, HubSpotDeal, HubSpotCompany

        # Create sample contacts
        contacts = [
            HubSpotContact(
                id=f"contact_{i}",
                email=f"contact{i}@example.com",
                firstname=f"First{i}",
                lastname=f"Last{i}",
                lifecyclestage="lead" if i % 3 == 0 else "customer"
            ) for i in range(1, 6)
        ]

        # Create sample deals
        deals = [
            HubSpotDeal(
                id=f"deal_{i}",
                dealname=f"Sample Deal {i}",
                dealstage="appointmentscheduled" if i % 2 == 0 else "closedwon",
                amount=float(10000 * (i + 1))
            ) for i in range(1, 4)
        ]

        # Create sample companies
        companies = [
            HubSpotCompany(
                id=f"company_{i}",
                name=f"Sample Company {i}",
                domain=f"company{i}.com",
                industry="Technology"
            ) for i in range(1, 3)
        ]

        # Store all data
        for contact in contacts:
            await firebase_service.store_hubspot_contact(contact)

        for deal in deals:
            await firebase_service.store_hubspot_deal(deal)

        for company in companies:
            await firebase_service.store_hubspot_company(company)

        return {
            "success": True,
            "message": "Sample data created",
            "data": {
                "contacts_created": len(contacts),
                "deals_created": len(deals),
                "companies_created": len(companies)
            }
        }

    except Exception as e:
        logger.error(f"Error creating sample data: {e}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    print("🚀 Starting HubSpot Integration Test Server...")
    print("📡 Available endpoints:")
    print("   GET  /")
    print("   GET  /health")
    print("   GET  /api/v1/hubspot/contacts")
    print("   GET  /api/v1/hubspot/deals")
    print("   GET  /api/v1/hubspot/companies")
    print("   GET  /api/v1/hubspot/recent")
    print("   POST /api/v1/hubspot/sync")
    print("   GET  /api/v1/hubspot/status")
    print("   POST /api/v1/webhooks/hubspot")
    print("   POST /api/v1/test/create-sample-data")
    print("🌐 Server will be available at: http://localhost:8000")
    print("🧪 Ready for HubSpot integration testing!")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )