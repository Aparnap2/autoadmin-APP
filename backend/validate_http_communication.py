#!/usr/bin/env python3
"""
Quick validation test for HTTP-only communication system
"""

import asyncio
import json
import time
from datetime import datetime

async def test_http_streaming_service():
    """Test HTTP streaming service basic functionality"""
    print("Testing HTTP Streaming Service...")

    try:
        # Test import
        from fastapi.app.services.http_streaming import HTTPStreamingService
        print("✓ HTTP Streaming Service import successful")

        # Test instantiation
        streaming_service = HTTPStreamingService()
        print("✓ HTTP Streaming Service instantiation successful")

        # Test basic methods
        connections = streaming_service.get_active_connections()
        print(f"✓ Active connections: {len(connections)}")

        return True
    except Exception as e:
        print(f"✗ HTTP Streaming Service test failed: {e}")
        return False

async def test_long_polling_service():
    """Test long polling service basic functionality"""
    print("\nTesting HTTP Polling Service...")

    try:
        # Test import
        from fastapi.app.services.long_polling import HTTPPollingService
        print("✓ HTTP Polling Service import successful")

        # Test instantiation
        polling_service = HTTPPollingService()
        print("✓ HTTP Polling Service instantiation successful")

        # Test basic methods
        sessions = polling_service.get_active_sessions()
        print(f"✓ Active sessions: {len(sessions)}")

        return True
    except Exception as e:
        print(f"✗ HTTP Polling Service test failed: {e}")
        return False

async def test_agent_orchestrator():
    """Test HTTP agent orchestrator basic functionality"""
    print("\nTesting HTTP Agent Orchestrator...")

    try:
        # Test import
        from services.agent_orchestrator_http import HTTPAgentOrchestrator
        print("✓ HTTP Agent Orchestrator import successful")

        # Test instantiation
        orchestrator = HTTPAgentOrchestrator()
        print("✓ HTTP Agent Orchestrator instantiation successful")

        # Test basic methods
        agents = orchestrator.get_agent_status()
        print(f"✓ Agent status retrieved: {len(agents)} agents")

        return True
    except Exception as e:
        print(f"✗ HTTP Agent Orchestrator test failed: {e}")
        return False

async def test_morning_briefing():
    """Test morning briefing generator"""
    print("\nTesting Morning Briefing Generator...")

    try:
        # Test import
        from services.business_intelligence.morning_briefing import MorningBriefingGenerator
        print("✓ Morning Briefing Generator import successful")

        # Test instantiation
        briefing_gen = MorningBriefingGenerator()
        print("✓ Morning Briefing Generator instantiation successful")

        return True
    except Exception as e:
        print(f"✗ Morning Briefing Generator test failed: {e}")
        return False

async def main():
    """Run all validation tests"""
    print("=== HTTP-Only Communication System Validation ===\n")

    start_time = time.time()
    results = []

    # Run all tests
    results.append(await test_http_streaming_service())
    results.append(await test_long_polling_service())
    results.append(await test_agent_orchestrator())
    results.append(await test_morning_briefing())

    # Summary
    end_time = time.time()
    passed = sum(results)
    total = len(results)

    print(f"\n=== Validation Summary ===")
    print(f"Tests passed: {passed}/{total}")
    print(f"Success rate: {(passed/total)*100:.1f}%")
    print(f"Total time: {end_time - start_time:.2f}s")

    if passed == total:
        print("🎉 All HTTP-only communication components validated successfully!")
        return True
    else:
        print("❌ Some components failed validation")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)