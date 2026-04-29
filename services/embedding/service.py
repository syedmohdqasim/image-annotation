import logging
import json
import os
from common.bus import EventBus
from common.schemas.events import (
    EventType, 
    VectorsCreatedEvent, 
    VectorsCreatedPayload,
    QueryEmbeddedEvent,
    QueryEmbeddedPayload
)
import google.generativeai as genai
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EmbeddingService")

# Load environment variables
load_dotenv()

class EmbeddingService:
    def __init__(self, bus: EventBus = None):
        self.bus = bus or EventBus()
        self.api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.dimension = 3072 # Standard for gemini-embedding-2
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
            logger.info("Embedding Service initialized with Gemini real embeddings.")
        else:
            logger.warning("GOOGLE_API_KEY not found. Falling back to mock hashing.")

    def run(self):
        """Starts the service, listening for image descriptions and query submissions."""
        logger.info("Embedding Service starting...")
        handlers = {
            EventType.IMAGE_DESCRIBED.value: self.handle_image_described,
            EventType.QUERY_SUBMITTED.value: self.handle_query_submitted
        }
        self.bus.listen_all(handlers)

    def _generate_vector(self, text: str) -> list[float]:
        """Generates a real semantic vector using Gemini or fallback hash."""
        if not self.api_key:
            # Fallback mock hashing
            import hashlib
            hash_digest = hashlib.sha256(text.encode()).digest()
            # Expand to 3072 dimensions
            full_hash = (hash_digest * 96)[:3072]
            return [float(b) / 255.0 for b in full_hash]

        try:
            result = genai.embed_content(
                model="models/gemini-embedding-2",
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            logger.error(f"Error calling Gemini Embedding: {e}")
            # Dynamic fallback to hash on error
            import hashlib
            hash_digest = hashlib.sha256(text.encode()).digest()
            full_hash = (hash_digest * 96)[:3072]
            return [float(b) / 255.0 for b in full_hash]

    def handle_image_described(self, data: dict):
        """Generates vectors for the description AND all detected objects."""
        image_id = data["payload"]["image_id"]
        description = data["payload"]["description"]
        detections = data["payload"].get("detections", [])
        
        logger.info(f"Generating multi-vector embeddings for image: {image_id}")
        
        vectors = []
        object_labels = []

        # 1. Vectorize the full description
        vectors.append(self._generate_vector(description))
        object_labels.append("description")

        # 2. Vectorize each object label
        for det in detections:
            label = det.get("label")
            if label:
                logger.info(f"Vectorizing object: {label}")
                vectors.append(self._generate_vector(label))
                object_labels.append(label)
        
        event = VectorsCreatedEvent(
            payload=VectorsCreatedPayload(
                image_id=image_id,
                object_ids=object_labels, 
                embeddings_count=len(vectors),
                vectors=vectors,
                description=description
            )
        )
        self.bus.publish(event)
        logger.info(f"Published {len(vectors)} vectors for image {image_id}")

    def handle_query_submitted(self, data: dict):
        """Generates a semantic vector for the search query."""
        query_id = data["payload"]["query_id"]
        query_text = data["payload"]["payload"]
        
        logger.info(f"Generating semantic embedding for query [{query_id}]: {query_text}")
        
        # Use 'retrieval_query' task type for better search performance
        if self.api_key:
            try:
                result = genai.embed_content(
                    model="models/gemini-embedding-2",
                    content=query_text,
                    task_type="retrieval_query"
                )
                vector = result['embedding']
            except:
                vector = self._generate_vector(query_text)
        else:
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
