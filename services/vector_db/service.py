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
    def __init__(self, dimension: int = 3072, index_path: str = "services/vector_db/faiss.index", bus: EventBus = None):
        self.dimension = dimension
        self.index_path = index_path
        self.bus = bus or EventBus()
        self.index = self._load_index()
        self.id_map = {} # internal_id -> {image_id, label}

    def _load_index(self):
        if os.path.exists(self.index_path):
            try:
                idx = faiss.read_index(self.index_path)
                if idx.d == self.dimension:
                    return idx
                logger.warning(f"Index dimension mismatch ({idx.d} != {self.dimension}). Creating new index.")
            except Exception as e:
                logger.error(f"Error loading index: {e}")
        
        return faiss.IndexFlatL2(self.dimension)

    def _save_index(self):
        faiss.write_index(self.index, self.index_path)

    def run(self):
        """Starts the service, listening for vector creation and query embedding events."""
        logger.info(f"Vector DB Service starting (Dim: {self.dimension})...")
        handlers = {
            EventType.VECTORS_CREATED.value: self.handle_vectors_created,
            EventType.QUERY_EMBEDDED.value: self.handle_query_embedded
        }
        self.bus.listen_all(handlers)

    def handle_vectors_created(self, data: dict):
        """Indexes vectors for images or objects."""
        image_id = data["payload"]["image_id"]
        vectors_list = data["payload"].get("vectors", [])
        object_labels = data["payload"].get("object_ids", [])
        
        if not vectors_list:
            logger.warning(f"No vectors received for image {image_id}")
            return

        logger.info(f"Indexing {len(vectors_list)} vectors for image: {image_id}")
        vectors = np.array(vectors_list).astype('float32')
        
        # Ensure dimensionality matches
        if vectors.shape[1] != self.dimension:
            logger.error(f"Vector dimension mismatch: expected {self.dimension}, got {vectors.shape[1]}")
            return

        start_id = self.index.ntotal
        for i in range(len(vectors_list)):
            label = object_labels[i] if i < len(object_labels) else "unknown"
            self.id_map[str(start_id + i)] = {"image_id": image_id, "label": label}
        
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
        
        logger.info(f"Performing multi-vector similarity search for query: {query_id}")

        # FAISS search - find top 10 matches across all vectors
        k = 10
        D, I = self.index.search(query_vector, k)
        
        matches = []
        seen_images = set()
        
        for i, idx in enumerate(I[0]):
            if idx == -1: continue
            meta = self.id_map.get(str(idx))
            if meta:
                image_id = meta["image_id"]
                label = meta["label"]
                
                # We can return all matches, or group them. 
                # Let's keep all for now so Document DB can see which part matched.
                score = max(0, 1.0 - (float(D[0][i]) / 10.0))
                matches.append({
                    "image_id": image_id,
                    "matched_label": label,
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
