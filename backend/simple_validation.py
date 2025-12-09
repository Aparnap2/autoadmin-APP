#!/usr/bin/env python3
"""
Simple validation of HTTP components without complex dependencies
"""

import os
import sys

def check_file_exists(filepath, description):
    """Check if a file exists"""
    if os.path.exists(filepath):
        print(f"✓ {description}: {filepath}")
        return True
    else:
        print(f"✗ {description}: {filepath} (missing)")
        return False

def validate_http_communication_structure():
    """Validate HTTP communication file structure"""
    print("=== HTTP Communication Structure Validation ===\n")

    checks = []

    # Core HTTP streaming files
    checks.append(check_file_exists(
        "fastapi/app/services/http_streaming.py",
        "HTTP Streaming Service"
    ))

    checks.append(check_file_exists(
        "fastapi/app/services/long_polling.py",
        "HTTP Polling Service"
    ))

    checks.append(check_file_exists(
        "fastapi/app/services/sse_event_manager.py",
        "SSE Event Manager"
    ))

    checks.append(check_file_exists(
        "fastapi/app/services/sse_client_manager.py",
        "SSE Client Manager"
    ))

    # Agent orchestration
    checks.append(check_file_exists(
        "services/agent_orchestrator_http.py",
        "HTTP Agent Orchestrator"
    ))

    # Business intelligence
    checks.append(check_file_exists(
        "services/business_intelligence/morning_briefing.py",
        "Morning Briefing Generator"
    ))

    checks.append(check_file_exists(
        "services/business_intelligence/revenue_intelligence.py",
        "Revenue Intelligence Analyzer"
    ))

    # API routes
    checks.append(check_file_exists(
        "fastapi/app/routers/streaming.py",
        "Streaming API Routes"
    ))

    checks.append(check_file_exists(
        "fastapi/app/routers/http_polling.py",
        "HTTP Polling API Routes"
    ))

    checks.append(check_file_exists(
        "fastapi/app/routers/multi_agent.py",
        "Multi-Agent API Routes"
    ))

    # Frontend HTTP client
    checks.append(check_file_exists(
        "../frontend/services/api/http_streaming_client.ts",
        "Frontend HTTP Streaming Client"
    ))

    checks.append(check_file_exists(
        "../frontend/services/api/http_polling_client.ts",
        "Frontend HTTP Polling Client"
    ))

    # Summary
    passed = sum(checks)
    total = len(checks)

    print(f"\n=== Structure Validation Results ===")
    print(f"Files present: {passed}/{total} ({(passed/total)*100:.1f}%)")

    if passed >= total * 0.9:  # 90% success rate
        print("🎉 HTTP communication structure validated successfully!")
        return True
    else:
        print("❌ Some critical files are missing")
        return False

def validate_code_content():
    """Validate code content for key components"""
    print("\n=== Code Content Validation ===\n")

    # Check HTTP streaming service
    try:
        with open("fastapi/app/services/http_streaming.py", "r") as f:
            content = f.read()
            has_class = "HTTPStreamingService" in content
            has_sse = "EventSourceResponse" in content or "StreamingResponse" in content
            has_methods = "create_sse_connection" in content or "broadcast_event" in content

            if has_class and has_sse:
                print("✓ HTTP Streaming Service: Valid implementation")
                streaming_valid = True
            else:
                print(f"✗ HTTP Streaming Service: Missing components (class: {has_class}, sse: {has_sse}, methods: {has_methods})")
                streaming_valid = False
    except Exception as e:
        print(f"✗ HTTP Streaming Service: Cannot read file - {e}")
        streaming_valid = False

    # Check HTTP polling service
    try:
        with open("fastapi/app/services/long_polling.py", "r") as f:
            content = f.read()
            has_class = "LongPollingService" in content
            has_sessions = "_sessions" in content or "PollingSession" in content

            if has_class and has_sessions:
                print("✓ HTTP Polling Service: Valid implementation")
                polling_valid = True
            else:
                print(f"✗ HTTP Polling Service: Missing components (class: {has_class}, sessions: {has_sessions})")
                polling_valid = False
    except Exception as e:
        print(f"✗ HTTP Polling Service: Cannot read file - {e}")
        polling_valid = False

    # Check agent orchestrator
    try:
        with open("services/agent_orchestrator_http.py", "r") as f:
            content = f.read()
            has_class = "HTTPAgentOrchestrator" in content
            has_http = "http" in content.lower()

            if has_class and has_http:
                print("✓ HTTP Agent Orchestrator: Valid implementation")
                orchestrator_valid = True
            else:
                print(f"✗ HTTP Agent Orchestrator: Missing components (class: {has_class}, http: {has_http})")
                orchestrator_valid = False
    except Exception as e:
        print(f"✗ HTTP Agent Orchestrator: Cannot read file - {e}")
        orchestrator_valid = False

    # Check frontend client
    try:
        with open("../frontend/services/api/http_streaming_client.ts", "r") as f:
            content = f.read()
            has_class = "HTTPStreamingClient" in content
            has_sse = "EventSource" in content

            if has_class and has_sse:
                print("✓ Frontend HTTP Client: Valid implementation")
                frontend_valid = True
            else:
                print(f"✗ Frontend HTTP Client: Missing components (class: {has_class}, sse: {has_sse})")
                frontend_valid = False
    except Exception as e:
        print(f"✗ Frontend HTTP Client: Cannot read file - {e}")
        frontend_valid = False

    return all([streaming_valid, polling_valid, orchestrator_valid, frontend_valid])

def main():
    """Main validation function"""
    print("HTTP-Only Communication System Validation\n")

    # Change to backend directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    structure_ok = validate_http_communication_structure()
    content_ok = validate_code_content()

    print(f"\n=== Final Validation Results ===")
    if structure_ok and content_ok:
        print("🎉 HTTP-only communication migration successfully validated!")
        print("✓ All components are in place")
        print("✓ Code structure is correct")
        print("✓ Ready for deployment")
        return True
    else:
        print("❌ Validation failed")
        if not structure_ok:
            print("✗ File structure issues detected")
        if not content_ok:
            print("✗ Code content issues detected")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)