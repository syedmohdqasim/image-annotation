import json
import logging
import random
import time
from typing import Callable, Optional, Type, TypeVar
import redis
from fakeredis import FakeRedis
from pydantic import BaseModel

from common.schemas.events import BaseEvent

T = TypeVar("T", bound=BaseEvent)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EventBus")

class EventBus:
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0, use_mock: bool = False, client: Optional[redis.Redis] = None):
        self.host = host
        self.port = port
        self.db = db
        self.processed_events = set() # For idempotency checking
        
        if client:
            self.client = client
            return

        if use_mock:
            logger.info("Using Mock Redis (fakeredis)")
            self.client = FakeRedis()
        else:
            try:
                self.client = redis.Redis(host=host, port=port, db=db, socket_timeout=5)
                self.client.ping()
                logger.info(f"Connected to Redis at {host}:{port}")
            except redis.ConnectionError:
                logger.warning(f"Could not connect to Redis at {host}:{port}. Falling back to FakeRedis.")
                self.client = FakeRedis()

    def publish(self, event: BaseEvent):
        """Publishes an event to its corresponding topic."""
        topic = event.type.value
        payload = event.model_dump_json()
        self.client.publish(topic, payload)
        logger.info(f"Published {event.type.value} [ID: {event.event_id}]")

    def subscribe(self, topic: str, handler: Callable[[dict], None]):
        """Subscribes to a topic and calls the handler on each message."""
        pubsub = self.client.pubsub()
        pubsub.subscribe(topic)
        logger.info(f"Subscribed to topic: {topic}")
        
        for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    # Basic Idempotency check
                    event_id = data.get("event_id")
                    if event_id in self.processed_events:
                        logger.warning(f"DUPLICATE DETECTED: Skipping event {event_id}")
                        continue
                    
                    self.processed_events.add(event_id)
                    handler(data)
                except Exception as e:
                    logger.error(f"Error handling message on {topic}: {e}")

    def listen_all(self, handlers: dict[str, Callable[[dict], None]]):
        """Listens to multiple topics simultaneously."""
        pubsub = self.client.pubsub()
        for topic in handlers.keys():
            pubsub.subscribe(topic)
            logger.info(f"Subscribed to topic: {topic}")

        for message in pubsub.listen():
            if message["type"] == "message":
                topic = message["channel"].decode("utf-8") if isinstance(message["channel"], bytes) else message["channel"]
                if topic in handlers:
                    try:
                        data = json.loads(message["data"])
                        # Basic Idempotency check
                        event_id = data.get("event_id")
                        if event_id in self.processed_events:
                            logger.warning(f"DUPLICATE DETECTED: Skipping event {event_id}")
                            continue
                        
                        self.processed_events.add(event_id)
                        handlers[topic](data)
                    except Exception as e:
                        logger.error(f"Error handling message on {topic}: {e}")

class ChaosBus(EventBus):
    """
    An EventBus wrapper that injects faults:
    - Duplicates messages
    - Drops messages
    - Delays messages
    """
    def __init__(self, *args, drop_rate: float = 0.0, dup_rate: float = 0.0, delay_range: tuple[float, float] = (0, 0), **kwargs):
        super().__init__(*args, **kwargs)
        self.drop_rate = drop_rate
        self.dup_rate = dup_rate
        self.delay_range = delay_range

    def publish(self, event: BaseEvent):
        # Fault: Drop message
        if random.random() < self.drop_rate:
            logger.error(f"CHAOS: Dropped event {event.event_id}")
            return

        # Fault: Delay message
        delay = random.uniform(*self.delay_range)
        if delay > 0:
            logger.warning(f"CHAOS: Delaying event {event.event_id} by {delay:.2f}s")
            time.sleep(delay)

        # Normal publish
        super().publish(event)

        # Fault: Duplicate message
        if random.random() < self.dup_rate:
            logger.warning(f"CHAOS: Duplicating event {event.event_id}")
            super().publish(event)
