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
        """Starts the service, listening for upload, detection, and description events."""
        logger.info("Document DB Service starting...")
        handlers = {
            EventType.IMAGE_SUBMITTED.value: self.handle_image_submitted,
            EventType.OBJECTS_DETECTED.value: self.handle_objects_detected,
            EventType.IMAGE_DESCRIBED.value: self.handle_image_described
        }
        self.bus.listen_all(handlers)

    def handle_image_described(self, data: dict):
        """Updates record with image description."""
        image_id = data["payload"]["image_id"]
        description = data["payload"]["description"]
        
        if image_id not in self.db:
            logger.warning(f"Received description for unknown image {image_id}. Creating new record.")
            self.db[image_id] = {"image_id": image_id}

        logger.info(f"Updating description for image: {image_id}")
        self.db[image_id]["description"] = description
        self._save_db()

    def handle_image_submitted(self, data: dict):
        """Creates initial record with image path."""
        image_id = data["payload"]["image_id"]
        path = data["payload"]["path"]
        
        logger.info(f"Recording initial upload for image: {image_id}")
        self.db[image_id] = {
            "image_id": image_id,
            "path": path,
            "detections": [],
            "timestamp": data["timestamp"]
        }
        self._save_db()

    def handle_objects_detected(self, data: dict):
        """Updates record with detected objects."""
        image_id = data["payload"]["image_id"]
        detections = data["payload"]["detections"]
        
        if image_id not in self.db:
            logger.warning(f"Received detections for unknown image {image_id}. Creating new record.")
            self.db[image_id] = {"image_id": image_id}

        logger.info(f"Updating metadata for image: {image_id}")
        self.db[image_id]["detections"] = detections
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
