import json
import logging
import os
from common.bus import EventBus
from common.schemas.events import EventType, MetadataPersistedEvent, MetadataPersistedPayload

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
        """Starts the service, listening for detection events."""
        logger.info("Document DB Service starting...")
        handlers = {
            EventType.OBJECTS_DETECTED.value: self.handle_objects_detected
        }
        self.bus.listen_all(handlers)

    def handle_objects_detected(self, data: dict):
        """Stores detected objects in the document database."""
        image_id = data["payload"]["image_id"]
        detections = data["payload"]["detections"]
        
        logger.info(f"Storing metadata for image: {image_id}")

        # Store in DB
        self.db[image_id] = {
            "image_id": image_id,
            "detections": detections,
            "timestamp": data["timestamp"]
        }
        self._save_db()

        # Create and publish metadata.persisted event
        event = MetadataPersistedEvent(
            payload=MetadataPersistedPayload(
                image_id=image_id,
                document_id=image_id, # Simplified
                metadata=self.db[image_id]
            )
        )
        self.bus.publish(event)
        logger.info(f"Published metadata persisted for {image_id}")

if __name__ == "__main__":
    svc = DocumentDBService()
    svc.run()
