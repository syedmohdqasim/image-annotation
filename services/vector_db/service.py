import logging
import faiss
import numpy as np
import os
from common.bus import EventBus
from common.schemas.events import EventType, IndexingCompletedEvent, IndexingCompletedPayload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VectorDBService")

class VectorDBService:
    def __init__(self, dimension: int = 128, index_path: str = "services/vector_db/faiss.index", bus: EventBus = None):
        self.dimension = dimension
        self.index_path = index_path
        self.bus = bus or EventBus()
        self.index = self._load_index()
        self.id_map = {} # obj_id -> internal_id

    def _load_index(self):
        if os.path.exists(self.index_path):
            return faiss.read_index(self.index_path)
        return faiss.IndexFlatL2(self.dimension)

    def _save_index(self):
        faiss.write_index(self.index, self.index_path)

    def run(self):
        """Starts the service, listening for vector creation events."""
        logger.info("Vector DB Service starting...")
        handlers = {
            EventType.VECTORS_CREATED.value: self.handle_vectors_created
        }
        self.bus.listen_all(handlers)

    def handle_vectors_created(self, data: dict):
        """Indexes vectors for detected objects."""
        image_id = data["payload"]["image_id"]
        object_ids = data["payload"]["object_ids"]
        embeddings_count = data["payload"]["embeddings_count"]
        
        logger.info(f"Indexing vectors for image: {image_id} ({embeddings_count} objects)")

        # Generate fake vectors to index (128D)
        # In a real system, we'd fetch these from the embedding service's store
        vectors = np.random.random((embeddings_count, self.dimension)).astype('float32')
        
        self.index.add(vectors)
        self._save_index()

        # Create and publish indexing.completed event
        event = IndexingCompletedEvent(
            payload=IndexingCompletedPayload(
                image_id=image_id,
                index_version="v1"
            )
        )
        self.bus.publish(event)
        logger.info(f"Published indexing completed for {image_id}")

if __name__ == "__main__":
    svc = VectorDBService()
    svc.run()
