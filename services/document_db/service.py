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
try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure
except ImportError:
    MongoClient = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DocumentDBService")

class DocumentDBService:
    def __init__(self, db_path: str = "services/document_db/data.json", bus: EventBus = None):
        self.bus = bus or EventBus()
        self.mongodb_uri = os.getenv("MONGODB_URI")
        self.use_mongodb = False
        
        if self.mongodb_uri and MongoClient:
            try:
                self.client = MongoClient(self.mongodb_uri)
                # Test connection
                self.client.admin.command('ping')
                self.db_conn = self.client.get_database("image_system")
                self.collection = self.db_conn.get_collection("images")
                self.use_mongodb = True
                logger.info("Connected to MongoDB Atlas successfully.")
            except Exception as e:
                logger.error(f"Failed to connect to MongoDB: {e}. Falling back to JSON.")
        
        if not self.use_mongodb:
            self.db_path = db_path
            self.db = self._load_json_db()
            logger.info(f"Using local JSON database at: {self.db_path}")

    def _load_json_db(self):
        if os.path.exists(self.db_path):
            with open(self.db_path, "r") as f:
                return json.load(f)
        return {}

    def _save_json_db(self):
        if not self.use_mongodb:
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
        record = {
            "image_id": image_id,
            "path": path,
            "detections": [],
            "description": None,
            "timestamp": data["timestamp"]
        }
        
        logger.info(f"Recording initial upload for image: {image_id}")
        if self.use_mongodb:
            self.collection.update_one({"_id": image_id}, {"$set": record}, upsert=True)
        else:
            self.db[image_id] = record
            self._save_json_db()

    def handle_objects_detected(self, data: dict):
        """Updates record with detected objects."""
        image_id = data["payload"]["image_id"]
        detections = data["payload"]["detections"]
        
        logger.info(f"Updating object detections for image: {image_id}")
        if self.use_mongodb:
            self.collection.update_one({"_id": image_id}, {"$set": {"detections": detections}}, upsert=True)
        else:
            if image_id not in self.db: self.db[image_id] = {"image_id": image_id}
            self.db[image_id]["detections"] = detections
            self._save_json_db()

    def handle_vectors_created(self, data: dict):
        """Updates record with semantic description when vectors are ready."""
        image_id = data["payload"]["image_id"]
        description = data["payload"].get("description")
        
        if not description: return

        logger.info(f"Updating description from vector event for image: {image_id}")
        if self.use_mongodb:
            self.collection.update_one({"_id": image_id}, {"$set": {"description": description}}, upsert=True)
            record = self.collection.find_one({"_id": image_id})
        else:
            if image_id not in self.db: self.db[image_id] = {"image_id": image_id}
            self.db[image_id]["description"] = description
            self._save_json_db()
            record = self.db[image_id]

        # Publish metadata persisted event as the record is now fully enriched
        event = MetadataPersistedEvent(
            payload=MetadataPersistedPayload(
                image_id=image_id,
                document_id=image_id,
                metadata=record
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
            matched_label = match.get("matched_label", "unknown")
            record = None
            if self.use_mongodb:
                record = self.collection.find_one({"_id": image_id})
            else:
                record = self.db.get(image_id)
                
            if record:
                results.append({
                    "image_id": image_id,
                    "score": match["score"],
                    "matched_as": matched_label,
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
