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
        """Starts the service, listening for vector creation and query events."""
        logger.info("Vector DB Service starting...")
        handlers = {
            EventType.VECTORS_CREATED.value: self.handle_vectors_created,
            EventType.QUERY_SUBMITTED.value: self.handle_query_submitted
        }
        self.bus.listen_all(handlers)

    def handle_vectors_created(self, data: dict):
        """Indexes vectors for detected objects."""
        image_id = data["payload"]["image_id"]
        object_labels = data["payload"]["object_ids"]
        vectors_list = data["payload"].get("vectors", [])
        
        if not vectors_list:
            logger.warning(f"No vectors received for image {image_id}")
            return

        logger.info(f"Indexing {len(vectors_list)} vectors for image: {image_id}")

        vectors = np.array(vectors_list).astype('float32')
        
        # Store metadata for each vector added
        start_id = self.index.ntotal
        for i, label in enumerate(object_labels):
            self.id_map[str(start_id + i)] = {"image_id": image_id, "label": label}
        
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

    def handle_query_submitted(self, data: dict):
        """Performs a similarity search."""
        query_id = data["payload"]["query_id"]
        query_text = data["payload"]["payload"]
        
        logger.info(f"Searching for: {query_text}")

        # In this mock, we convert the query text to a vector using the SAME logic
        import hashlib
        hash_digest = hashlib.sha256(query_text.encode()).digest()
        full_hash = (hash_digest * 4)[:128]
        query_vector = np.array([[float(b) / 255.0 for b in full_hash]]).astype('float32')

        # FAISS search
        D, I = self.index.search(query_vector, k=5)
        
        results = []
        for i, idx in enumerate(I[0]):
            if idx == -1: continue
            meta = self.id_map.get(str(idx))
            if meta:
                # Score is L2 distance, so smaller is better. Convert to "confidence"
                score = max(0, 1.0 - (float(D[0][i]) / 10.0))
                results.append({
                    "image_id": meta["image_id"],
                    "label": meta["label"],
                    "score": score
                })

        # We don't publish QUERY_COMPLETED directly here if we want the Query Service to orchestrate,
        # but for simplicity in this "make it work" phase, we can either publish it or 
        # let Query Service handle the final response. 
        # Let's publish a temporary "similarity.results" or just use QUERY_COMPLETED for now.
        from common.schemas.events import QueryCompletedEvent, QueryCompletedPayload
        event = QueryCompletedEvent(
            payload=QueryCompletedPayload(
                query_id=query_id,
                results=results
            )
        )
        self.bus.publish(event)

if __name__ == "__main__":
    svc = VectorDBService()
    svc.run()
