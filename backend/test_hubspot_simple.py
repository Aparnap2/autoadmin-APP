#!/usr/bin/env python3
"""
Simple HubSpot Service Test
Tests HubSpot service initialization and basic functionality
"""

import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print("⚠️  python-dotenv not available, using system environment variables only")

async def test_hubspot_service():
    """Test HubSpot service initialization and basic functions"""
    print("\n🧪 Testing HubSpot Service...")

    try:
        from services.hubspot_service import get_hubspot_service, HubSpotContact, HubSpotDeal

        print("1. Getting HubSpot service instance...")
        hubspot_service = get_hubspot_service()
    
        # Wait a bit for async initialization
        import asyncio
        await asyncio.sleep(2)
    
        print("2. Checking service mode...")
        print(f"   Mode: {hubspot_service.mode}")
        print(f"   Is Online: {hubspot_service.is_online}")
        print(f"   Is Offline: {hubspot_service.is_offline}")
    
        # Debug: Check environment variable directly
        import os
        token = os.getenv('HUBSPOT_ACCESS_TOKEN', '')
        print(f"   Direct env check - Token: {token[:10]}... (length: {len(token)})")
    
        # Debug: Check service config
        if hasattr(hubspot_service, '_config') and hubspot_service._config:
            print(f"   Service config token: {hubspot_service._config.access_token[:10] if hubspot_service._config.access_token else 'None'}...")
            print(f"   Service config valid: {hubspot_service._config.is_valid()}")
    
        print("3. Testing health check...")
        health = await hubspot_service.health_check()
        print(f"   Status: {health.get('status')}")
        print(f"   Mode: {health.get('mode')}")
        print(f"   Has Token: {health.get('configuration', {}).get('has_access_token')}")
        print(f"   Token Prefix: {health.get('configuration', {}).get('token_prefix')}")

        if hubspot_service.is_online:
            print("4. Testing contact retrieval...")
            contacts = await hubspot_service.get_contacts(limit=5)
            print(f"   Retrieved {len(contacts)} contacts")

            print("5. Testing deal retrieval...")
            deals = await hubspot_service.get_deals(limit=5)
            print(f"   Retrieved {len(deals)} deals")

            print("6. Testing offline contact creation...")
            test_contact = HubSpotContact(
                email="test@example.com",
                firstname="Test",
                lastname="User",
                lifecyclestage="lead"
            )
            created = await hubspot_service.create_contact(test_contact.__dict__)
            print(f"   Created contact: {created is not None}")

        print("\n✅ HubSpot Service Test Completed Successfully!")
        return True

    except Exception as e:
        print(f"\n❌ HubSpot Service Test Failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_firebase_service():
    """Test Firebase service (minimal)"""
    print("\n🧪 Testing Firebase Service...")

    try:
        from services.firebase_service import get_firebase_service

        print("1. Getting Firebase service instance...")
        firebase_service = get_firebase_service()

        print("2. Checking service mode...")
        print(f"   Is Online: {firebase_service.is_online}")
        print(f"   Is Offline: {firebase_service.is_offline}")

        print("3. Testing health check...")
        health = await firebase_service.health_check()
        print(f"   Status: {health.get('status')}")

        print("\n✅ Firebase Service Test Completed!")
        return True

    except Exception as e:
        print(f"\n❌ Firebase Service Test Failed: {str(e)}")
        return False

async def main():
    """Main test function"""
    print("🚀 Starting HubSpot Integration Tests")
    print("=" * 50)

    # Test individual services
    hubspot_ok = await test_hubspot_service()
    firebase_ok = await test_firebase_service()

    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"   HubSpot Service: {'✅ PASS' if hubspot_ok else '❌ FAIL'}")
    print(f"   Firebase Service: {'✅ PASS' if firebase_ok else '❌ FAIL'}")

    if hubspot_ok and firebase_ok:
        print("\n🎉 All tests passed! HubSpot integration is ready.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)