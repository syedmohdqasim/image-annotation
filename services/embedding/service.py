import logging
import random
from common.bus import EventBus
from common.schemas.events import EventType, VectorsCreatedEvent, VectorsCreatedPayload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EmbeddingService")

class EmbeddingService:
    def __init__(self, bus: EventBus = None):
        self.bus = bus or EventBus()

    def run(self):
        """Starts the service, listening for metadata persisted events."""
        logger.info("Embedding Service starting...")
        handlers = {
            EventType.METADATA_PERSISTED.value: self.handle_metadata_persisted
        }
        self.bus.listen_all(handlers)

    def handle_metadata_persisted(self, data: dict):
        """Generates vectors for detected objects."""
        image_id = data["payload"]["image_id"]
        metadata = data["payload"]["metadata"]
        detections = metadata.get("detections", [])
        
        logger.info(f"Generating embeddings for image: {image_id} ({len(detections)} objects)")

        # In a real scenario, we'd use CLIP/Transformers to generate embeddings
        # Here we simulate vector generation
        object_ids = [f"obj_{image_id}_{i}" for i in range(len(detections))]
        
        # We don't publish the vectors directly in the event to keep it light (per design)
        # Instead, we just signal that they are ready and let the Vector DB service handle indexing
        # In a real system, we might store these in a staging area.

        # Create and publish vectors.created event
        event = VectorsCreatedEvent(
            payload=VectorsCreatedPayload(
                image_id=image_id,
                object_ids=object_ids,
                embeddings_count=len(object_ids)
            )
        )
        self.bus.publish(event)
        logger.info(f"Published vectors created for {image_id}")

if __name__ == "__main__":
    svc = EmbeddingService()
    svc.run()
