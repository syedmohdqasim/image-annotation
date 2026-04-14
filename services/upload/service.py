import os
import shutil
import uuid
from common.bus import EventBus
from common.schemas.events import ImageSubmittedEvent, ImageSubmittedPayload

class UploadService:
    def __init__(self, storage_dir: str = "services/upload/data", bus: EventBus = None):
        self.storage_dir = storage_dir
        self.bus = bus or EventBus()
        os.makedirs(self.storage_dir, exist_ok=True)

    def upload_image(self, source_path: str):
        """Simulates an image upload: copies file to storage and emits event."""
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
                source="cli"
            )
        )
        self.bus.publish(event)
        return image_id, target_path

if __name__ == "__main__":
    # For standalone testing
    import sys
    if len(sys.argv) > 1:
        svc = UploadService()
        svc.upload_image(sys.argv[1])
