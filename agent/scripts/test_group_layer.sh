#!/bin/bash

# Comprehensive test suite for Jarvis Group Communication Layer
# Tests all major workflows and components

set -e

# Configuration
KAFKA_BROKERS="${KAFKA_BROKERS:-localhost:9092}"
GROUP_ID="${GROUP_ID:-jarvis-main}"
MINIO_ENDPOINT="${MINIO_ENDPOINT:-localhost:9000}"
ROUTER_URL="${ROUTER_URL:-http://localhost:8080}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
log_test() {
    echo -e "${YELLOW}[TEST]${NC} $1"
}

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((TESTS_PASSED++))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((TESTS_FAILED++))
}

log_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

# Test functions

test_kafka_connectivity() {
    log_test "Kafka connectivity"

    if kafka-broker-api-versions.sh --bootstrap-server "$KAFKA_BROKERS" >/dev/null 2>&1; then
        log_pass "Connected to Kafka"
    else
        log_fail "Cannot connect to Kafka at $KAFKA_BROKERS"
        return 1
    fi
}

test_topics_exist() {
    log_test "Kafka topics exist"

    local topics=("group.${GROUP_ID}.events" "group.${GROUP_ID}.commands" "group.${GROUP_ID}.approvals")

    for topic in "${topics[@]}"; do
        if kafka-topics.sh --list --bootstrap-server "$KAFKA_BROKERS" 2>/dev/null | grep -q "^${topic}$"; then
            log_pass "Topic exists: $topic"
        else
            log_fail "Topic missing: $topic"
            return 1
        fi
    done
}

test_minio_connectivity() {
    log_test "MinIO connectivity"

    if curl -s "http://${MINIO_ENDPOINT}/minio/health/live" >/dev/null; then
        log_pass "Connected to MinIO"
    else
        log_fail "Cannot connect to MinIO at $MINIO_ENDPOINT"
        return 1
    fi
}

test_router_health() {
    log_test "Router health check"

    response=$(curl -s "$ROUTER_URL/health")

    if echo "$response" | jq -e '.status == "healthy"' >/dev/null 2>&1; then
        log_pass "Router is healthy"
    else
        log_fail "Router is not healthy: $response"
        return 1
    fi
}

test_orchestrator_status() {
    log_test "Orchestrator status"

    response=$(curl -s "$ROUTER_URL/orchestrator/status")

    if echo "$response" | jq -e '.enabled == true' >/dev/null 2>&1; then
        log_pass "Orchestrator is enabled"
    else
        log_fail "Orchestrator is not enabled: $response"
        return 1
    fi
}

test_message_publish() {
    log_test "Publish message"

    response=$(curl -s -X POST "$ROUTER_URL/message" \
        -H "Content-Type: application/json" \
        -d '{"message": "Test message"}')

    if echo "$response" | jq -e '.response' >/dev/null 2>&1; then
        log_pass "Message published successfully"
    else
        log_fail "Failed to publish message: $response"
        return 1
    fi
}

test_schema_compilation() {
    log_test "Schema package compilation"

    if go build -o /tmp/test-schema ./schemas/group 2>/dev/null; then
        log_pass "Schema package compiles"
    else
        log_fail "Schema package compilation failed"
        return 1
    fi
}

test_orchestrator_compilation() {
    log_test "Orchestrator package compilation"

    if go build -o /tmp/test-orchestrator ./router/orchestrator 2>/dev/null; then
        log_pass "Orchestrator package compiles"
    else
        log_fail "Orchestrator package compilation failed"
        return 1
    fi
}

test_unit_tests() {
    log_test "Schema unit tests"

    if go test ./schemas/group -v >/dev/null 2>&1; then
        log_pass "Schema unit tests pass"
    else
        log_fail "Schema unit tests failed"
        return 1
    fi

    log_test "Orchestrator unit tests"

    if go test ./router/orchestrator -v >/dev/null 2>&1; then
        log_pass "Orchestrator unit tests pass"
    else
        log_fail "Orchestrator unit tests failed"
        return 1
    fi
}

test_kafka_topic_creation() {
    log_test "Create missing topics"

    ./scripts/setup_group_topics.sh >/dev/null 2>&1

    if kafka-topics.sh --list --bootstrap-server "$KAFKA_BROKERS" 2>/dev/null | grep -q "group.${GROUP_ID}.events"; then
        log_pass "Topics created successfully"
    else
        log_fail "Failed to create topics"
        return 1
    fi
}

test_event_envelope_validation() {
    log_test "Event envelope validation"

    # This would require publishing a valid event and checking it
    # For now, just verify schemas are valid

    if go test ./schemas/group -run TestValidateEnvelope -v >/dev/null 2>&1; then
        log_pass "Envelope validation works"
    else
        log_fail "Envelope validation test failed"
        return 1
    fi
}

test_permissions_enforcement() {
    log_test "Permission enforcement"

    if go test ./schemas/group -run TestValidateEventPermission -v >/dev/null 2>&1; then
        log_pass "Permission enforcement works"
    else
        log_fail "Permission enforcement test failed"
        return 1
    fi
}

test_state_manager() {
    log_test "State manager operations"

    if go test ./router/orchestrator -run TestStateManager -v >/dev/null 2>&1; then
        log_pass "State manager tests pass"
    else
        log_fail "State manager tests failed"
        return 1
    fi
}

# Main execution

main() {
    echo "======================================"
    echo "Jarvis Group Layer Test Suite"
    echo "======================================"
    echo ""

    log_info "Configuration:"
    log_info "  Kafka Brokers: $KAFKA_BROKERS"
    log_info "  Group ID: $GROUP_ID"
    log_info "  MinIO Endpoint: $MINIO_ENDPOINT"
    log_info "  Router URL: $ROUTER_URL"
    echo ""

    # Infrastructure tests
    log_info "=== Infrastructure Tests ==="
    test_kafka_connectivity || true
    test_minio_connectivity || true
    test_kafka_topic_creation || true
    test_topics_exist || true
    echo ""

    # Compilation tests
    log_info "=== Compilation Tests ==="
    test_schema_compilation || true
    test_orchestrator_compilation || true
    echo ""

    # Unit tests
    log_info "=== Unit Tests ==="
    test_unit_tests || true
    test_event_envelope_validation || true
    test_permissions_enforcement || true
    test_state_manager || true
    echo ""

    # Integration tests
    log_info "=== Integration Tests ==="
    test_router_health || true
    test_orchestrator_status || true
    test_message_publish || true
    echo ""

    # Summary
    echo "======================================"
    TOTAL=$((TESTS_PASSED + TESTS_FAILED))

    if [ "$TESTS_FAILED" -eq 0 ]; then
        echo -e "${GREEN}All $TOTAL tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}$TESTS_FAILED of $TOTAL tests failed${NC}"
        echo "Passed: $TESTS_PASSED"
        echo "Failed: $TESTS_FAILED"
        exit 1
    fi
}

# Run main
main "$@"
