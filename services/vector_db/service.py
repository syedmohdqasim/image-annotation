import logging
import faiss
import numpy as np
import os
from common.bus import EventBus
from common.schemas.events import (
    EventType, 
    IndexingCompletedEvent, 
    IndexingCompletedPayload,
    SimilarityMatchedEvent,
    SimilarityMatchedPayload
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VectorDBService")

class VectorDBService:
    def __init__(self, dimension: int = 128, index_path: str = "services/vector_db/faiss.index", bus: EventBus = None):
        self.dimension = dimension
        self.index_path = index_path
        self.bus = bus or EventBus()
        self.index = self._load_index()
        self.id_map = {} # internal_id -> image_id

    def _load_index(self):
        if os.path.exists(self.index_path):
            return faiss.read_index(self.index_path)
        return faiss.IndexFlatL2(self.dimension)

    def _save_index(self):
        faiss.write_index(self.index, self.index_path)

    def run(self):
        """Starts the service, listening for vector creation and query embedding events."""
        logger.info("Vector DB Service starting...")
        handlers = {
            EventType.VECTORS_CREATED.value: self.handle_vectors_created,
            EventType.QUERY_EMBEDDED.value: self.handle_query_embedded
        }
        self.bus.listen_all(handlers)

    def handle_vectors_created(self, data: dict):
        """Indexes vectors for images or objects."""
        image_id = data["payload"]["image_id"]
        vectors_list = data["payload"].get("vectors", [])
        
        if not vectors_list:
            logger.warning(f"No vectors received for image {image_id}")
            return

        logger.info(f"Indexing {len(vectors_list)} vectors for image: {image_id}")
        vectors = np.array(vectors_list).astype('float32')
        
        start_id = self.index.ntotal
        for i in range(len(vectors_list)):
            self.id_map[str(start_id + i)] = image_id
        
        self.index.add(vectors)
        self._save_index()

        event = IndexingCompletedEvent(
            payload=IndexingCompletedPayload(
                image_id=image_id,
                index_version="v1"
            )
        )
        self.bus.publish(event)
        logger.info(f"Published indexing.completed for {image_id}")

    def handle_query_embedded(self, data: dict):
        """Performs a similarity search using a pre-generated vector."""
        query_id = data["payload"]["query_id"]
        query_vector = np.array([data["payload"]["vector"]]).astype('float32')
        
        logger.info(f"Performing similarity search for query: {query_id}")

        # FAISS search
        D, I = self.index.search(query_vector, k=5)
        
        matches = []
        for i, idx in enumerate(I[0]):
            if idx == -1: continue
            image_id = self.id_map.get(str(idx))
            if image_id:
                # Score is L2 distance, smaller is better.
                score = max(0, 1.0 - (float(D[0][i]) / 10.0))
                matches.append({
                    "image_id": image_id,
                    "score": score
                })

        event = SimilarityMatchedEvent(
            payload=SimilarityMatchedPayload(
                query_id=query_id,
                matches=matches
            )
        )
        self.bus.publish(event)
        logger.info(f"Published similarity.matched for {query_id}")

if __name__ == "__main__":
    svc = VectorDBService()
    svc.run()
