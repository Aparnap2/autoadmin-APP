#!/bin/bash

# AutoAdmin E2E Test Runner Script
# Executes comprehensive Maestro tests for PRD validation

set -e

echo "🚀 Starting AutoAdmin PRD Test Suite"
echo "===================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test categories
TEST_CATEGORIES=(
    "agent-chat"
    "business-intelligence"
    "task-delegation"
    "integration"
)

# Function to run a single test
run_test() {
    local test_file=$1
    echo -e "\n📝 Running: ${YELLOW}$test_file${NC}"

    if maestro test "$test_file"; then
        echo -e "✅ ${GREEN}PASSED${NC}: $test_file"
        return 0
    else
        echo -e "❌ ${RED}FAILED${NC}: $test_file"
        return 1
    fi
}

# Function to run all tests in a category
run_category() {
    local category=$1
    echo -e "\n📂 Running ${YELLOW}$category${NC} tests..."

    local failed_count=0
    local total_count=0

    for test_file in .maestro/flows/$category/*.yaml; do
        if [ -f "$test_file" ]; then
            ((total_count++))
            if ! run_test "$test_file"; then
                ((failed_count++))
            fi
        fi
    done

    echo -e "\n📊 $category Results: $((total_count - failed_count))/$total_count passed"
    return $failed_count
}

# Function to run complete workflow test
run_complete_workflow() {
    echo -e "\n🔄 Running ${YELLOW}Complete Workflow Integration Test${NC}"

    if maestro test .maestro/flows/integration/complete-workflow.yaml; then
        echo -e "✅ ${GREEN}Integration Test PASSED${NC}"
        return 0
    else
        echo -e "❌ ${RED}Integration Test FAILED${NC}"
        return 1
    fi
}

# Function to run all tests
run_all_tests() {
    local total_failed=0

    echo -e "\n🧪 Running All AutoAdmin PRD Tests"
    echo "=================================="

    # Check if Maestro is installed
    if ! command -v maestro &> /dev/null; then
        echo -e "❌ ${RED}Maestro CLI not found. Please install it first:${NC}"
        echo "curl -Ls 'https://get.maestro.mobile.dev' | bash"
        exit 1
    fi

    # Check if app is running
    echo -e "\n📱 Checking if app is running..."
    if ! adb devices | grep -q "emulator"; then
        echo -e "⚠️  ${YELLOW}No emulator detected. Starting Android emulator...${NC}"
        # Add emulator startup command here if needed
    fi

    # Run test categories
    for category in "${TEST_CATEGORIES[@]}"; do
        run_category "$category"
        failed_count=$?
        total_failed=$((total_failed + failed_count))
    done

    # Run complete workflow test
    run_complete_workflow
    total_failed=$((total_failed + $?))

    # Summary
    echo -e "\n=================================="
    echo -e "📈 Test Summary"
    echo -e "=================================="

    if [ $total_failed -eq 0 ]; then
        echo -e "🎉 ${GREEN}All tests passed successfully!${NC}"
        echo -e "\n✅ PRD Features Validated:"
        echo -e "  • Real-time Agent Chat System"
        echo -e "  • Business Intelligence Analytics"
        echo -e "  • Task Delegation & Management"
        echo -e "  • Multi-Agent Coordination"
        echo -e "  • HTTP Streaming Communication"
        echo -e "  • Complete Workflow Integration"
        exit 0
    else
        echo -e "❌ ${RED}$total_failed test(s) failed${NC}"
        echo -e "\n⚠️  Please check the failed tests and fix issues before proceeding"
        exit 1
    fi
}

# Function to run specific test
run_specific_test() {
    local test_path=$1
    if [ -f "$test_path" ]; then
        run_test "$test_path"
    else
        echo -e "❌ ${RED}Test file not found: $test_path${NC}"
        exit 1
    fi
}

# Main script logic
case "${1:-all}" in
    "all")
        run_all_tests
        ;;
    "agent-chat")
        run_category "agent-chat"
        ;;
    "business-intelligence")
        run_category "business-intelligence"
        ;;
    "task-delegation")
        run_category "task-delegation"
        ;;
    "integration")
        run_complete_workflow
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [option]"
        echo "Options:"
        echo "  all                  Run all tests (default)"
        echo "  agent-chat           Run agent chat tests"
        echo "  business-intelligence Run business intelligence tests"
        echo "  task-delegation      Run task delegation tests"
        echo "  integration          Run integration tests"
        echo "  [test-file]          Run specific test file"
        echo "  help                 Show this help message"
        exit 0
        ;;
    *)
        run_specific_test "$1"
        ;;
esac