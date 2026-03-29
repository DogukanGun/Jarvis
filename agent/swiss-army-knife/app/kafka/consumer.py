"""
Kafka consumer for the Swiss Army Knife agent.
Listens to group communication events and executes security tool tasks.
"""

import json
import logging
import os
import sys
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

from app.config import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class SwissKnifeKafkaConsumer:
    """Kafka consumer that participates in Jarvis group communication."""

    def __init__(
        self,
        group_id: str = None,
        agent_id: str = None,
        broker_url: str = None,
    ):
        self.group_id = group_id or config.GROUP_ID
        self.agent_id = agent_id or config.AGENT_ID
        self.broker_url = broker_url or config.KAFKA_BROKERS

        topics = [
            f"group.{self.group_id}.events",
            f"group.{self.group_id}.agent.{self.agent_id}",
        ]

        self.consumer = KafkaConsumer(
            *topics,
            bootstrap_servers=[self.broker_url],
            group_id=f"{self.agent_id}-group",
            auto_offset_reset="latest",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )

        self.producer = KafkaProducer(
            bootstrap_servers=[self.broker_url],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            acks="all",
        )

        logger.info(f"Initialized Kafka consumer for {self.agent_id} in group {self.group_id}")

    def _create_envelope(
        self,
        event_type: str,
        payload: Dict[str, Any],
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a group layer envelope for publishing."""
        return {
            "group_id": self.group_id,
            "message_id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "thread_id": thread_id or str(uuid4()),
            "sender": {
                "id": self.agent_id,
                "role": "MEMBER",
                "agent": self.agent_id,
            },
            "type": event_type,
            "payload": payload,
            "version": "1.0",
        }

    def publish_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        thread_id: Optional[str] = None,
    ) -> str:
        """Publish an event to the group events topic."""
        envelope = self._create_envelope(event_type, payload, thread_id)
        topic = f"group.{self.group_id}.events"

        try:
            future = self.producer.send(
                topic,
                value=envelope,
                key=envelope["thread_id"].encode("utf-8"),
            )
            future.get(timeout=10)
            logger.info(f"Published {event_type} event: {envelope['message_id']}")
            return envelope["message_id"]
        except KafkaError as e:
            logger.error(f"Failed to publish event: {e}")
            raise

    def handle_command(self, envelope: Dict[str, Any]) -> None:
        """Handle security tool execution command."""
        target_agent = envelope["payload"].get("target_agent")
        command = envelope["payload"].get("command")
        args = envelope["payload"].get("args", {})
        task_id = envelope["payload"].get("task_id", str(uuid4()))
        thread_id = envelope["thread_id"]

        if target_agent and target_agent != self.agent_id:
            return

        logger.info(f"Received command: {command} with args: {args}")

        # Publish task started
        self.publish_event(
            "task.started",
            {
                "task_id": task_id,
                "target_agent": self.agent_id,
                "status": "started",
                "thread_id": thread_id,
            },
            thread_id,
        )

        try:
            # Run the tool graph
            from app.graphs.tool_graph import run_tool_graph

            message = args.get("message", command or "")
            user_id = args.get("user_id", "kafka")
            target_tools = args.get("target_tools")
            parameters = args.get("parameters")

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                run_tool_graph(
                    user_id=user_id,
                    message=message,
                    target_tools=target_tools,
                    parameters=parameters,
                )
            )
            loop.close()

            # Publish task completed
            self.publish_event(
                "task.completed",
                {
                    "task_id": task_id,
                    "status": "completed",
                    "result": result.get("response", ""),
                    "tools_used": result.get("tools_used", []),
                    "findings_count": len(result.get("findings", [])),
                    "thread_id": thread_id,
                },
                thread_id,
            )

            # Publish result
            self.publish_event(
                "result.security_scan",
                {
                    "task_id": task_id,
                    "type": "security_scan",
                    "data": {
                        "response": result.get("response", ""),
                        "report": result.get("report", {}),
                        "tools_used": result.get("tools_used", []),
                        "findings": result.get("findings", []),
                    },
                    "success": True,
                    "thread_id": thread_id,
                },
                thread_id,
            )

        except Exception as e:
            logger.error(f"Error executing command: {e}")
            self.publish_event(
                "task.failed",
                {
                    "task_id": task_id,
                    "error": str(e),
                    "status": "failed",
                    "thread_id": thread_id,
                },
                thread_id,
            )

    def handle_task_assign(self, envelope: Dict[str, Any]) -> None:
        """Handle delegated security task from another agent."""
        # Same as command handling but for task.assign events
        self.handle_command(envelope)

    def process_message(self, envelope: Dict[str, Any]) -> None:
        """Process an incoming Kafka message."""
        if not envelope:
            return

        event_type = envelope.get("type", "")
        logger.info(f"Processing event: {event_type}")

        if event_type == "command.run":
            self.handle_command(envelope)
        elif event_type == "task.assign":
            self.handle_task_assign(envelope)
        else:
            logger.debug(f"Ignoring event type: {event_type}")

    def start(self) -> None:
        """Start consuming messages from Kafka."""
        logger.info(f"Starting Kafka consumer for {self.agent_id} in group {self.group_id}")

        try:
            for message in self.consumer:
                try:
                    self.process_message(message.value)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    continue
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
        finally:
            self.close()

    def close(self) -> None:
        """Close Kafka connections."""
        logger.info("Closing Kafka consumer and producer...")
        try:
            self.consumer.close()
            self.producer.close()
        except Exception as e:
            logger.error(f"Error closing Kafka connections: {e}")


def start_consumer():
    """Main entry point for the Kafka consumer."""
    logger.info("Starting Swiss Army Knife Kafka consumer")
    try:
        consumer = SwissKnifeKafkaConsumer()
        consumer.start()
    except Exception as e:
        logger.error(f"Failed to start consumer: {e}")
        sys.exit(1)
