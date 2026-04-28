import logging
import os
import json
import time
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
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ImageProcessingService")

# Load environment variables
load_dotenv()

class ImageProcessingService:
    def __init__(self, bus: EventBus = None):
        self.bus = bus or EventBus()
        # Look for both common names for the Gemini API Key
        self.api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-3.1-pro-preview')
            logger.info("Image Processing Service initialized with gemini-3.1-pro-preview.")
        else:
            logger.warning("!!! GOOGLE_API_KEY NOT FOUND !!!")
            logger.warning("Gemini features will be mocked. Please add GOOGLE_API_KEY to your .env file.")
            self.model = None

    def run(self):
        """Starts the service, listening for image submission events."""
        logger.info("Image Processing Service starting...")
        handlers = {
            EventType.IMAGE_SUBMITTED.value: self.handle_image_submitted
        }
        self.bus.listen_all(handlers)

    def _process_image_with_gemini(self, image_path: str):
        """
        Calls Gemini 3.1 Pro to get both a detailed description and object detections.
        """
        if not self.model:
            # Mock fallback
            return (
                "An image with some objects (Mocked - No API Key).",
                [{"label": "unknown", "confidence": 0.5, "bbox": [0, 0, 10, 10]}]
            )

        try:
            img = Image.open(image_path)
            
            # Combined prompt for efficiency: Description + Object Detection
            prompt = (
                "1. Describe this image in great detail. Focus on subjects, colors, and themes.\n"
                "2. List the main objects found in the image. For each object, provide a label. "
                "Format the objects as a JSON list of dictionaries like: "
                "[{'label': 'object name', 'confidence': 0.95}]"
            )
            
            logger.info(f"Sending image to Gemini 3.1 Pro: {image_path}")
            response = self.model.generate_content([prompt, img])
            full_text = response.text.strip()
            
            # Simple parsing: Description is usually the first part, JSON is usually at the end
            # In a production system, we would use structured output (response_mime_type)
            description = full_text.split("2.")[0].replace("1.", "").strip()
            
            detections = []
            if "[" in full_text and "]" in full_text:
                try:
                    json_str = full_text[full_text.find("["):full_text.rfind("]")+1]
                    json_str = json_str.replace("'", "\"") # Cleanup common Gemini quote style
                    detections = json.loads(json_str)
                except Exception as e:
                    logger.warning(f"Failed to parse object JSON: {e}")
                    detections = [{"label": "detected_object", "confidence": 0.9}]

            return description, detections

        except Exception as e:
            logger.error(f"Error calling Gemini: {e}")
            return "Description unavailable.", []

    def handle_image_submitted(self, data: dict):
        """Processes a new image using Gemini 3 Pro."""
        image_id = data["payload"]["image_id"]
        image_path = data["payload"]["path"]
        
        logger.info(f"Processing image: {image_id} at {image_path}")

        # Process image with Gemini
        description, detections = self._process_image_with_gemini(image_path)

        # 1. Publish image.described event (Enriched with detections for embedding)
        desc_event = ImageDescribedEvent(
            payload=ImageDescribedPayload(
                image_id=image_id,
                description=description,
                detections=detections
            )
        )
        self.bus.publish(desc_event)
        logger.info(f"Published description for {image_id}")

        # 2. Publish objects.detected event
        obj_event = ObjectsDetectedEvent(
            payload=ObjectsDetectedPayload(
                image_id=image_id,
                detections=detections
            )
        )
        self.bus.publish(obj_event)
        logger.info(f"Published {len(detections)} objects for {image_id}")

if __name__ == "__main__":
    svc = ImageProcessingService()
    svc.run()
