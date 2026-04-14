import threading
import time
from common.bus import EventBus
from common.schemas.events import ImageSubmittedEvent, ImageSubmittedPayload

def test_publish_subscribe():
    bus = EventBus(use_mock=True)
    received_events = []

    def handler(data):
        print(f"DEBUG: Handler received: {data}")
        received_events.append(data)

    # Start subscriber in a separate thread
    def run_subscriber():
        bus.subscribe("image.submitted", handler)

    sub_thread = threading.Thread(target=run_subscriber, daemon=True)
    sub_thread.start()
    
    # Wait for subscription to be active
    time.sleep(0.5)

    # Publish an event
    event = ImageSubmittedEvent(
        payload=ImageSubmittedPayload(image_id="img_123", path="test/path.jpg")
    )
    bus.publish(event)

    # Wait for message to propagate
    time.sleep(1)
    
    assert len(received_events) > 0
    assert received_events[0]["payload"]["image_id"] == "img_123"
    print("SUCCESS: Event Bus Publish/Subscribe test passed!")

if __name__ == "__main__":
    test_publish_subscribe()
