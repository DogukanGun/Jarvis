#!/bin/bash

# Setup Kafka topics for the Jarvis group communication layer
# This script creates the necessary topics with appropriate configurations

set -e

# Configuration
KAFKA_BROKERS="${KAFKA_BROKERS:-localhost:9092}"
GROUP_ID="${GROUP_ID:-jarvis-main}"
KAFKA_CMD="${KAFKA_CMD:-kafka-topics.sh}"

echo "Setting up Kafka topics for group layer..."
echo "Kafka Brokers: $KAFKA_BROKERS"
echo "Group ID: $GROUP_ID"

# Topics to create with their configurations
declare -a TOPICS=(
    "group.${GROUP_ID}.events|3|1|604800000"      # 3 partitions, 1 replica, 7 days retention
    "group.${GROUP_ID}.commands|2|1|86400000"     # 2 partitions, 1 replica, 1 day retention
    "group.${GROUP_ID}.approvals|1|1|2592000000"  # 1 partition, 1 replica, 30 days retention
    "group.${GROUP_ID}.results|3|1|2592000000"    # 3 partitions, 1 replica, 30 days retention
    "group.${GROUP_ID}.audit|1|1|7776000000"      # 1 partition, 1 replica, 90 days retention
)

# Function to create topic
create_topic() {
    local topic=$1
    local partitions=$2
    local replicas=$3
    local retention=$4

    echo "Creating topic: $topic"

    # Try to create topic
    if command -v $KAFKA_CMD &> /dev/null; then
        $KAFKA_CMD --create \
            --bootstrap-server "$KAFKA_BROKERS" \
            --topic "$topic" \
            --partitions "$partitions" \
            --replication-factor "$replicas" \
            --config "retention.ms=$retention" \
            --if-not-exists 2>/dev/null || echo "Topic $topic may already exist"
    else
        echo "Warning: $KAFKA_CMD not found in PATH"
        echo "Please ensure Kafka command-line tools are installed and in PATH"
        echo "Or set KAFKA_CMD environment variable"
        return 1
    fi
}

# Create all topics
success=0
failed=0

for topic_config in "${TOPICS[@]}"; do
    IFS='|' read -r topic partitions replicas retention <<< "$topic_config"
    if create_topic "$topic" "$partitions" "$replicas" "$retention"; then
        ((success++))
    else
        ((failed++))
    fi
done

echo ""
echo "Topic creation complete:"
echo "  Success: $success"
echo "  Failed/Skipped: $failed"

# List created topics
echo ""
echo "Verifying topics..."
if command -v kafka-topics.sh &> /dev/null; then
    kafka-topics.sh --list --bootstrap-server "$KAFKA_BROKERS" | grep "group.${GROUP_ID}" || echo "No group topics found"
else
    echo "Cannot verify - kafka-topics.sh not found"
fi

echo "Setup complete!"
