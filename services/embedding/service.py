import logging
import random
import json
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

    def _generate_vector(self, label: str) -> list[float]:
        """Generates a deterministic vector for a given label."""
        import hashlib
        # Create a 128-dim vector from the hash of the label
        hash_digest = hashlib.sha256(label.encode()).digest()
        # Repeat/expand to 128 dimensions (128 bytes)
        full_hash = (hash_digest * 4)[:128]
        return [float(b) / 255.0 for b in full_hash]

    def handle_metadata_persisted(self, data: dict):
        """Generates vectors for detected objects."""
        image_id = data["payload"]["image_id"]
        metadata = data["payload"]["metadata"]
        detections = metadata.get("detections", [])
        
        logger.info(f"Generating embeddings for image: {image_id} ({len(detections)} objects)")

        # In a real scenario, we'd use CLIP/Transformers to generate embeddings
        # Here we use our deterministic hashing
        vectors = []
        object_labels = []
        for det in detections:
            label = det["label"]
            vectors.append(self._generate_vector(label))
            object_labels.append(label)
        
        # We'll store these vectors in a local temporary store or pass them in the payload
        # For this mock, we will pass them in the payload for simplicity, 
        # though in production we'd use a shared storage or a side-channel.
        
        # Create and publish vectors.created event
        event = VectorsCreatedEvent(
            payload=VectorsCreatedPayload(
                image_id=image_id,
                object_ids=object_labels, # Using labels as IDs for simplicity in this mock
                embeddings_count=len(vectors)
            )
        )
        # Add the actual vectors to the payload (extra field not in schema, but Pydantic allows it if configured, 
        # or we just hack it into the dict for this demo)
        event_dict = event.model_dump()
        event_dict["payload"]["vectors"] = vectors
        
        self.bus.client.publish(EventType.VECTORS_CREATED.value, json.dumps(event_dict, default=str))
        logger.info(f"Published vectors created for {image_id}")

if __name__ == "__main__":
    svc = EmbeddingService()
    svc.run()
