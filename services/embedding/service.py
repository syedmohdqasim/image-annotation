import logging
import json
from common.bus import EventBus
from common.schemas.events import (
    EventType, 
    VectorsCreatedEvent, 
    VectorsCreatedPayload,
    QueryEmbeddedEvent,
    QueryEmbeddedPayload
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EmbeddingService")

class EmbeddingService:
    def __init__(self, bus: EventBus = None):
        self.bus = bus or EventBus()

    def run(self):
        """Starts the service, listening for image descriptions and query submissions."""
        logger.info("Embedding Service starting...")
        handlers = {
            EventType.IMAGE_DESCRIBED.value: self.handle_image_described,
            EventType.QUERY_SUBMITTED.value: self.handle_query_submitted
        }
        self.bus.listen_all(handlers)

    def _generate_vector(self, text: str) -> list[float]:
        """Generates a deterministic vector for a given text string."""
        import hashlib
        # Create a 128-dim vector from the hash of the text
        hash_digest = hashlib.sha256(text.encode()).digest()
        # Repeat/expand to 128 dimensions (128 bytes)
        full_hash = (hash_digest * 4)[:128]
        return [float(b) / 255.0 for b in full_hash]

    def handle_image_described(self, data: dict):
        """Generates vectors for the image description and triggers storage/indexing."""
        image_id = data["payload"]["image_id"]
        description = data["payload"]["description"]
        
        logger.info(f"Generating embedding for image description: {image_id}")
        vector = self._generate_vector(description)
        
        event = VectorsCreatedEvent(
            payload=VectorsCreatedPayload(
                image_id=image_id,
                object_ids=["description"], 
                embeddings_count=1,
                vectors=[vector],
                description=description
            )
        )
        self.bus.publish(event)
        logger.info(f"Published vectors.created for description of {image_id}")

    def handle_query_submitted(self, data: dict):
        """Generates a vector for the search query."""
        query_id = data["payload"]["query_id"]
        query_text = data["payload"]["payload"]
        
        logger.info(f"Generating embedding for query [{query_id}]: {query_text}")
        vector = self._generate_vector(query_text)
        
        event = QueryEmbeddedEvent(
            payload=QueryEmbeddedPayload(
                query_id=query_id,
                vector=vector
            )
        )
        self.bus.publish(event)
        logger.info(f"Published query.embedded for {query_id}")

if __name__ == "__main__":
    svc = EmbeddingService()
    svc.run()
