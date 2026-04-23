import json
import logging
import os
from common.bus import EventBus
from common.schemas.events import (
    EventType, 
    MetadataPersistedEvent, 
    MetadataPersistedPayload,
    QueryCompletedEvent,
    QueryCompletedPayload
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DocumentDBService")

class DocumentDBService:
    def __init__(self, db_path: str = "services/document_db/data.json", bus: EventBus = None):
        self.db_path = db_path
        self.bus = bus or EventBus()
        self.db = self._load_db()

    def _load_db(self):
        if os.path.exists(self.db_path):
            with open(self.db_path, "r") as f:
                return json.load(f)
        return {}

    def _save_db(self):
        with open(self.db_path, "w") as f:
            json.dump(self.db, f, indent=2)

    def run(self):
        """Starts the service, listening for events to persist metadata and resolve queries."""
        logger.info("Document DB Service starting...")
        handlers = {
            EventType.IMAGE_SUBMITTED.value: self.handle_image_submitted,
            EventType.OBJECTS_DETECTED.value: self.handle_objects_detected,
            EventType.VECTORS_CREATED.value: self.handle_vectors_created,
            EventType.SIMILARITY_MATCHED.value: self.handle_similarity_matched
        }
        self.bus.listen_all(handlers)

    def handle_image_submitted(self, data: dict):
        """Creates initial record with image path."""
        image_id = data["payload"]["image_id"]
        path = data["payload"]["path"]
        
        logger.info(f"Recording initial upload for image: {image_id}")
        self.db[image_id] = {
            "image_id": image_id,
            "path": path,
            "detections": [],
            "description": None,
            "timestamp": data["timestamp"]
        }
        self._save_db()

    def handle_objects_detected(self, data: dict):
        """Updates record with detected objects."""
        image_id = data["payload"]["image_id"]
        detections = data["payload"]["detections"]
        
        if image_id not in self.db:
            logger.warning(f"Received detections for unknown image {image_id}.")
            return

        logger.info(f"Updating object detections for image: {image_id}")
        self.db[image_id]["detections"] = detections
        self._save_db()

    def handle_vectors_created(self, data: dict):
        """Updates record with semantic description when vectors are ready."""
        image_id = data["payload"]["image_id"]
        description = data["payload"].get("description")
        
        if not description:
            return

        if image_id not in self.db:
            logger.warning(f"Received vectors for unknown image {image_id}.")
            return

        logger.info(f"Updating description from vector event for image: {image_id}")
        self.db[image_id]["description"] = description
        self._save_db()

        # Publish metadata persisted event as the record is now fully enriched
        event = MetadataPersistedEvent(
            payload=MetadataPersistedPayload(
                image_id=image_id,
                document_id=image_id,
                metadata=self.db[image_id]
            )
        )
        self.bus.publish(event)

    def handle_similarity_matched(self, data: dict):
        """Resolves rich metadata for similarity search results."""
        query_id = data["payload"]["query_id"]
        matches = data["payload"]["matches"]
        
        logger.info(f"Resolving metadata for {len(matches)} matches (Query: {query_id})")
        
        results = []
        for match in matches:
            image_id = match["image_id"]
            if image_id in self.db:
                record = self.db[image_id]
                results.append({
                    "image_id": image_id,
                    "score": match["score"],
                    "description": record.get("description"),
                    "path": record.get("path")
                })

        event = QueryCompletedEvent(
            payload=QueryCompletedPayload(
                query_id=query_id,
                results=results
            )
        )
        self.bus.publish(event)
        logger.info(f"Published query.completed for {query_id}")

if __name__ == "__main__":
    svc = DocumentDBService()
    svc.run()
