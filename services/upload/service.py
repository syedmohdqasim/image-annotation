import os
import shutil
import uuid
import logging
import json
from common.bus import EventBus
from common.schemas.events import (
    ImageSubmittedEvent, 
    ImageSubmittedPayload, 
    EventType, 
    UploadRequestedEvent
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("UploadService")

class UploadService:
    def __init__(self, storage_dir: str = "image_store", bus: EventBus = None):
        self.storage_dir = storage_dir
        self.bus = bus or EventBus()
        os.makedirs(self.storage_dir, exist_ok=True)

    def run(self):
        """Starts the service, listening for upload requests."""
        logger.info(f"Upload Service starting (storage: {self.storage_dir})...")
        handlers = {
            EventType.UPLOAD_REQUESTED.value: self.handle_upload_requested
        }
        self.bus.listen_all(handlers)

    def handle_upload_requested(self, data: dict):
        """Handles an event requesting an image upload."""
        source_path = data["payload"]["source_path"]
        logger.info(f"Received upload request for: {source_path}")
        try:
            image_id, target_path = self.upload_image(source_path)
            logger.info(f"Successfully processed upload: {image_id}")
        except Exception as e:
            logger.error(f"Failed to process upload for {source_path}: {e}")

    def upload_image(self, source_path: str):
        """Saves image to storage and emits image.submitted event."""
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"Source image not found: {source_path}")

        image_id = f"img_{uuid.uuid4().hex[:8]}"
        ext = os.path.splitext(source_path)[1]
        target_path = os.path.join(self.storage_dir, f"{image_id}{ext}")
        
        # Copy file to simulate persistence
        shutil.copy(source_path, target_path)
        
        # Create and publish event
        event = ImageSubmittedEvent(
            payload=ImageSubmittedPayload(
                image_id=image_id,
                path=target_path,
                original_name=os.path.basename(source_path),
                source="cli"
            )
        )
        self.bus.publish(event)
        return image_id, target_path

if __name__ == "__main__":
    svc = UploadService()
    svc.run()
