import logging
import os
import json
from common.bus import EventBus
from common.schemas.events import (
    EventType, 
    ObjectsDetectedEvent, 
    ObjectsDetectedPayload,
    ImageDescribedEvent,
    ImageDescribedPayload
)
import google.generativeai as genai
from PIL import Image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ImageProcessingService")

class ImageProcessingService:
    def __init__(self, bus: EventBus = None):
        self.bus = bus or EventBus()
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            logger.warning("GOOGLE_API_KEY not found. Gemini features will be mocked.")
            self.model = None

    def run(self):
        """Starts the service, listening for image submission events."""
        logger.info("Image Processing Service starting...")
        handlers = {
            EventType.IMAGE_SUBMITTED.value: self.handle_image_submitted
        }
        self.bus.listen_all(handlers)

    def _get_gemini_description(self, image_path: str, original_name: str = "") -> str:
        """Calls Gemini to get a description of the image."""
        if not self.model:
            # Fallback mock logic if no API key
            search_text = (image_path + original_name).lower()
            if "dog" in search_text:
                return "A cute dog sitting in a park."
            elif "cat" in search_text:
                return "A fluffy cat playing with a yarn ball."
            return "An image with some objects."

        try:
            img = Image.open(image_path)
            response = self.model.generate_content(["Describe this image in one sentence.", img])
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error calling Gemini: {e}")
            return "Description unavailable."

    def handle_image_submitted(self, data: dict):
        """Processes a new image, detects objects, and generates a description via Gemini."""
        image_id = data["payload"]["image_id"]
        image_path = data["payload"]["path"]
        original_name = data["payload"].get("original_name", "")
        
        logger.info(f"Received image for processing: {image_id} (orig: {original_name})")

        # 1. Generate Description via Gemini
        description = self._get_gemini_description(image_path, original_name)
        logger.info(f"Generated description for {image_id}: {description}")

        # 2. Publish image.described event
        desc_event = ImageDescribedEvent(
            payload=ImageDescribedPayload(
                image_id=image_id,
                description=description
            )
        )
        self.bus.publish(desc_event)

        # 3. Simulate Object Detection (for compatibility with Vector DB flow)
        detections = []
        search_text = (original_name + image_path).lower()
        if "dog" in search_text:
            detections.append({"label": "dog", "confidence": 0.98, "bbox": [50, 50, 200, 300]})
        elif "cat" in search_text:
            detections.append({"label": "cat", "confidence": 0.95, "bbox": [30, 40, 150, 250]})
        else:
            detections.append({"label": "unknown", "confidence": 0.5, "bbox": [0, 0, 10, 10]})

        # Create and publish objects.detected event
        obj_event = ObjectsDetectedEvent(
            payload=ObjectsDetectedPayload(
                image_id=image_id,
                detections=detections
            )
        )
        self.bus.publish(obj_event)
        logger.info(f"Published objects detected for {image_id}: {detections}")

if __name__ == "__main__":
    svc = ImageProcessingService()
    svc.run()
