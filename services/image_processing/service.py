import logging
from common.bus import EventBus
from common.schemas.events import EventType, ObjectsDetectedEvent, ObjectsDetectedPayload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ImageProcessingService")

class ImageProcessingService:
    def __init__(self, bus: EventBus = None):
        self.bus = bus or EventBus()

    def run(self):
        """Starts the service, listening for image submission events."""
        logger.info("Image Processing Service starting...")
        handlers = {
            EventType.IMAGE_SUBMITTED.value: self.handle_image_submitted
        }
        self.bus.listen_all(handlers)

    def handle_image_submitted(self, data: dict):
        """Processes a new image and detects objects."""
        image_id = data["payload"]["image_id"]
        image_path = data["payload"]["path"]
        
        logger.info(f"Received image for processing: {image_id} at {image_path}")

        # Simulate Inference (AI Model)
        # In a real scenario, we would use YOLO/FasterRCNN here
        detections = [
            {"label": "dog", "confidence": 0.95, "bbox": [10, 20, 100, 200]},
            {"label": "tree", "confidence": 0.88, "bbox": [150, 50, 300, 400]}
        ]

        # Create and publish objects.detected event
        event = ObjectsDetectedEvent(
            payload=ObjectsDetectedPayload(
                image_id=image_id,
                detections=detections
            )
        )
        self.bus.publish(event)
        logger.info(f"Published objects detected for {image_id}")

if __name__ == "__main__":
    svc = ImageProcessingService()
    svc.run()
