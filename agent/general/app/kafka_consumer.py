"""
Kafka consumer for the General Agent that listens to group communication events.
Integrates the general agent with the Jarvis group communication layer.
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GroupConsumerException(Exception):
    """Custom exception for group consumer errors"""
    pass


class GeneralAgentKafkaConsumer:
    """
    Kafka consumer for the General Agent that participates in group communication.
    """

    def __init__(
        self,
        group_id: str = "jarvis-main",
        agent_id: str = "general-agent",
        broker_url: str = "localhost:9092",
    ):
        """
        Initialize the Kafka consumer for group communication.

        Args:
            group_id: The group ID for the orchestrator
            agent_id: This agent's unique ID
            broker_url: Kafka broker URL
        """
        self.group_id = group_id
        self.agent_id = agent_id
        self.broker_url = broker_url

        # Initialize Kafka consumer
        topics = [
            f"group.{group_id}.events",
            f"group.{group_id}.agent.{agent_id}",
        ]

        self.consumer = KafkaConsumer(
            *topics,
            bootstrap_servers=[broker_url],
            group_id=f"{agent_id}-group",
            auto_offset_reset="latest",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            consumer_timeout_ms=1000,
        )

        # Initialize Kafka producer for publishing events
        self.producer = KafkaProducer(
            bootstrap_servers=[broker_url],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            acks="all",
        )

        logger.info(
            f"Initialized Kafka consumer for {agent_id} in group {group_id}"
        )

    def _create_envelope(
        self,
        event_type: str,
        payload: Dict[str, Any],
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a group layer envelope for publishing.

        Args:
            event_type: The event type
            payload: Event payload
            thread_id: Optional thread ID

        Returns:
            Envelope dict
        """
        if thread_id is None:
            thread_id = str(uuid4())

        return {
            "group_id": self.group_id,
            "message_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "thread_id": thread_id,
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
        """
        Publish an event to the group events topic.

        Args:
            event_type: The event type
            payload: Event payload
            thread_id: Optional thread ID

        Returns:
            Message ID
        """
        envelope = self._create_envelope(event_type, payload, thread_id)
        topic = f"group.{self.group_id}.events"

        try:
            future = self.producer.send(
                topic,
                value=envelope,
                key=envelope["thread_id"].encode("utf-8"),
            )
            future.get(timeout=10)
            logger.info(
                f"Published {event_type} event: {envelope['message_id']}"
            )
            return envelope["message_id"]
        except KafkaError as e:
            logger.error(f"Failed to publish event: {e}")
            raise GroupConsumerException(f"Failed to publish event: {e}")

    def handle_chat_message(self, envelope: Dict[str, Any]) -> None:
        """
        Handle chat message from owner.
        Generate a proposal based on the message.

        Args:
            envelope: The message envelope
        """
        text = envelope["payload"].get("text", "")
        thread_id = envelope["thread_id"]

        if not text:
            logger.warning("Received empty chat message")
            return

        logger.info(f"Received chat message from owner: {text}")

        # Import agent module for processing
        try:
            from app.agent import run_agent
        except ImportError:
            logger.error("Failed to import agent module")
            return

        # Run the agent to process the message
        try:
            logger.info("Running agent on message...")
            result = run_agent(text)

            if result:
                # Publish proposal event
                proposal_id = str(uuid4())
                payload = {
                    "text": result,
                    "proposal_id": proposal_id,
                    "title": "Agent Response",
                    "description": result,
                    "action": "execute_proposal",
                    "context": text,
                    "confidence": 0.8,
                    "requires_approval": True,
                    "thread_id": thread_id,
                }

                self.publish_event("proposal.created", payload, thread_id)
            else:
                logger.warning("Agent returned empty result")

        except Exception as e:
            logger.error(f"Error running agent: {e}")
            # Publish error event
            payload = {
                "code": "agent_error",
                "text": f"Error processing message: {str(e)}",
                "source": self.agent_id,
                "thread_id": thread_id,
            }
            self.publish_event("error", payload, thread_id)

    def handle_command(self, envelope: Dict[str, Any]) -> None:
        """
        Handle command execution request.

        Args:
            envelope: The command envelope
        """
        target_agent = envelope["payload"].get("target_agent")
        command = envelope["payload"].get("command")
        args = envelope["payload"].get("args", {})
        task_id = envelope["payload"].get("task_id", str(uuid4()))
        thread_id = envelope["thread_id"]

        if target_agent != self.agent_id:
            logger.info(
                f"Command not for this agent ({target_agent} != {self.agent_id})"
            )
            return

        logger.info(f"Received command: {command} with args: {args}")

        # Publish task started event
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

        # Import agent module for processing
        try:
            from app.agent import run_agent
        except ImportError:
            logger.error("Failed to import agent module")
            self.publish_event(
                "task.failed",
                {
                    "task_id": task_id,
                    "error": "Failed to import agent module",
                    "thread_id": thread_id,
                },
                thread_id,
            )
            return

        # Run the agent
        try:
            prompt = args.get("prompt", command)
            logger.info(f"Running agent with prompt: {prompt}")
            result = run_agent(prompt)

            # Publish task completed event
            self.publish_event(
                "task.completed",
                {
                    "task_id": task_id,
                    "status": "completed",
                    "result": result,
                    "duration": 0,
                    "thread_id": thread_id,
                },
                thread_id,
            )

            # Publish result event
            self.publish_event(
                "result.generated",
                {
                    "task_id": task_id,
                    "type": "text",
                    "data": {"output": result},
                    "success": True,
                    "duration": 0,
                    "thread_id": thread_id,
                },
                thread_id,
            )

        except Exception as e:
            logger.error(f"Error executing command: {e}")
            # Publish task failed event
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

    def process_message(self, envelope: Dict[str, Any]) -> None:
        """
        Process an incoming Kafka message.

        Args:
            envelope: The message envelope
        """
        if not envelope:
            return

        event_type = envelope.get("type", "")
        sender_role = envelope.get("sender", {}).get("role", "")

        logger.info(
            f"Processing event: {event_type} from {sender_role}"
        )

        # Route by event type
        if event_type == "chat.message":
            # Only process owner messages
            if sender_role == "OWNER":
                self.handle_chat_message(envelope)
            else:
                logger.info(
                    f"Ignoring chat message from non-owner: {sender_role}"
                )

        elif event_type == "command.run":
            self.handle_command(envelope)

        else:
            logger.debug(f"Ignoring event type: {event_type}")

    def start(self) -> None:
        """
        Start consuming messages from Kafka.
        """
        logger.info(
            f"Starting Kafka consumer for {self.agent_id} "
            f"in group {self.group_id}"
        )

        try:
            for message in self.consumer:
                try:
                    envelope = message.value
                    self.process_message(envelope)
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    continue

        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
        finally:
            self.close()

    def close(self) -> None:
        """
        Close the Kafka consumer and producer.
        """
        logger.info("Closing Kafka consumer and producer...")
        try:
            self.consumer.close()
            self.producer.close()
        except Exception as e:
            logger.error(f"Error closing Kafka connections: {e}")


def main():
    """Main entry point for the Kafka consumer."""
    # Get configuration from environment
    group_id = os.getenv("GROUP_ID", "jarvis-main")
    agent_id = os.getenv("AGENT_ID", "general-agent")
    kafka_brokers = os.getenv("KAFKA_BROKERS", "localhost:9092")

    logger.info(
        f"Starting General Agent Kafka consumer"
    )
    logger.info(f"Group ID: {group_id}")
    logger.info(f"Agent ID: {agent_id}")
    logger.info(f"Kafka Brokers: {kafka_brokers}")

    try:
        consumer = GeneralAgentKafkaConsumer(
            group_id=group_id,
            agent_id=agent_id,
            broker_url=kafka_brokers,
        )
        consumer.start()
    except Exception as e:
        logger.error(f"Failed to start consumer: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
