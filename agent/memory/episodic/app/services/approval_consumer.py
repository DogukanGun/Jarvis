"""
Approval Consumer Service

Consumes Kafka messages for user approval responses and
triggers the user_approval_graph to process decisions.
"""

from typing import Dict, Any, Optional, Callable
import logging
import threading
import time

logger = logging.getLogger(__name__)


class ApprovalConsumer:
    """
    Kafka consumer for processing user approval responses.

    Listens to the approval response topic and invokes
    user_approval_graph when responses are received.
    """

    def __init__(self, on_approval: Optional[Callable[[Dict[str, Any]], None]] = None):
        """
        Initialize the approval consumer.

        Args:
            on_approval: Optional callback when approval is processed
        """
        self.on_approval = on_approval
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def start(self) -> None:
        """Start the consumer thread."""
        with self._lock:
            if self.running:
                logger.warning("ApprovalConsumer already running")
                return

            self.running = True
            self._thread = threading.Thread(
                target=self._consume_loop,
                name="ApprovalConsumer",
                daemon=True
            )
            self._thread.start()
            logger.info("ApprovalConsumer started")

    def stop(self, timeout: float = 5.0) -> None:
        """
        Stop the consumer gracefully.

        Args:
            timeout: Max seconds to wait for thread to finish
        """
        with self._lock:
            if not self.running:
                return

            self.running = False

            if self._thread:
                self._thread.join(timeout=timeout)
                self._thread = None

            logger.info("ApprovalConsumer stopped")

    def _consume_loop(self) -> None:
        """Main consumer loop - processes Kafka messages."""
        from app.clients.kafka_client import get_kafka_client
        from app.config import config

        client = get_kafka_client()
        topic = config.KAFKA_TOPIC_APPROVAL_RESPONSE

        logger.info(f"Consuming from topic: {topic}")

        while self.running:
            try:
                # Poll for messages with timeout
                messages = client.consume(
                    topic=topic,
                    timeout_ms=1000,
                    max_records=10
                )

                for message in messages:
                    self._process_message(message)

            except Exception as e:
                logger.error(f"Consume error: {str(e)}")
                # Back off on error
                time.sleep(1.0)

    def _process_message(self, message: Dict[str, Any]) -> None:
        """
        Process a single approval response message.

        Args:
            message: Kafka message with approval response
        """
        try:
            from app.graphs.user_approval_graph import run_approval
            from app.storage import get_episode_repository

            # Extract response data
            proposal_id = message.get("proposal_id")
            decision = message.get("decision")  # approved, rejected, edited, timeout
            edited_value = message.get("edited_value")
            reason = message.get("reason")

            if not proposal_id:
                logger.warning(f"Missing proposal_id in message: {message}")
                return

            logger.info(f"Processing approval response: proposal={proposal_id}, decision={decision}")

            # Get the proposal from storage
            repo = get_episode_repository()
            proposal = repo.get_proposal(proposal_id)

            if not proposal:
                logger.warning(f"Proposal not found: {proposal_id}")
                return

            # Run user_approval_graph to process the decision
            result = run_approval(
                proposal_id=proposal_id,
                decision=decision,
                edited_value=edited_value,
                reason=reason
            )

            if result.get("completed"):
                logger.info(f"Approval processed: proposal={proposal_id}, applied={result.get('applied')}")
            else:
                logger.warning(f"Approval processing failed: {result.get('errors')}")

            # Call optional callback
            if self.on_approval:
                self.on_approval(result)

        except Exception as e:
            logger.error(f"Message processing error: {str(e)}")


# Global consumer instance
_approval_consumer: Optional[ApprovalConsumer] = None
_consumer_lock = threading.Lock()


def get_approval_consumer() -> ApprovalConsumer:
    """Get or create the global approval consumer instance."""
    global _approval_consumer

    with _consumer_lock:
        if _approval_consumer is None:
            _approval_consumer = ApprovalConsumer()

        return _approval_consumer


def start_approval_consumer(
    on_approval: Optional[Callable[[Dict[str, Any]], None]] = None
) -> ApprovalConsumer:
    """
    Start the global approval consumer.

    Args:
        on_approval: Optional callback when approval is processed

    Returns:
        The consumer instance
    """
    global _approval_consumer

    with _consumer_lock:
        if _approval_consumer is None:
            _approval_consumer = ApprovalConsumer(on_approval=on_approval)
        elif on_approval:
            _approval_consumer.on_approval = on_approval

        _approval_consumer.start()
        return _approval_consumer


def stop_approval_consumer() -> None:
    """Stop the global approval consumer."""
    global _approval_consumer

    with _consumer_lock:
        if _approval_consumer is not None:
            _approval_consumer.stop()
            _approval_consumer = None


if __name__ == "__main__":
    # Allow running as standalone service
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    def on_approval_callback(result: Dict[str, Any]) -> None:
        """Log approval results."""
        logger.info(f"Approval callback: {result}")

    logger.info("Starting ApprovalConsumer service...")
    consumer = start_approval_consumer(on_approval=on_approval_callback)

    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        stop_approval_consumer()
        sys.exit(0)
