import logging
from common.bus import EventBus
from common.schemas.events import EventType, QueryCompletedEvent, QueryCompletedPayload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("QueryService")

class QueryService:
    def __init__(self, bus: EventBus = None):
        self.bus = bus or EventBus()

    def run(self):
        """Starts the service, listening for query submissions."""
        logger.info("Query Service starting...")
        handlers = {
            EventType.QUERY_SUBMITTED.value: self.handle_query_submitted
        }
        self.bus.listen_all(handlers)

    def handle_query_submitted(self, data: dict):
        """Orchestrates search results."""
        query_id = data["payload"]["query_id"]
        query_type = data["payload"]["query_type"]
        query_payload = data["payload"]["payload"]
        
        logger.info(f"Received query [{query_id}]: {query_type} -> {query_payload}")

        # In a real system, the Query Service would:
        # 1. Ask Vector DB for top K similar object IDs
        # 2. Ask Document DB for metadata of those objects
        # 3. Aggregate and return
        
        # Simulating orchestration
        results = [
            {"image_id": "img_mock_1", "label": "dog", "score": 0.98},
            {"image_id": "img_mock_2", "label": "tree", "score": 0.85}
        ]

        # Create and publish query.completed event
        event = QueryCompletedEvent(
            payload=QueryCompletedPayload(
                query_id=query_id,
                results=results
            )
        )
        self.bus.publish(event)
        logger.info(f"Published query results for {query_id}")

if __name__ == "__main__":
    svc = QueryService()
    svc.run()
