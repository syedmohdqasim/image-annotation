import threading
import time
from common.bus import ChaosBus
from common.schemas.events import ImageSubmittedEvent, ImageSubmittedPayload

def test_idempotency():
    """Verify that duplicate events are only processed once."""
    bus = ChaosBus(use_mock=True, dup_rate=1.0) # Force duplicates
    
    process_count = 0
    def handler(data):
        nonlocal process_count
        process_count += 1
        print(f"DEBUG: Handler processing event {data['event_id']}")

    # Start subscriber
    threading.Thread(target=lambda: bus.subscribe("image.submitted", handler), daemon=True).start()
    time.sleep(1)

    # Publish ONE event (which will be duplicated by ChaosBus)
    event = ImageSubmittedEvent(
        payload=ImageSubmittedPayload(image_id="img_dup_test", path="test.jpg")
    )
    print("Publishing event with duplication forced...")
    bus.publish(event)
    
    time.sleep(2)
    
    print(f"Total process count: {process_count}")
    # Even with 100% duplication, it should only be processed once due to idempotency check
    assert process_count == 1
    print("SUCCESS: Idempotency test passed (duplicates filtered)!")

def test_robustness_to_drops():
    """Verify system doesn't crash on dropped events (simulated)."""
    # This is more of a smoke test to ensure ChaosBus doesn't break the client
    bus = ChaosBus(use_mock=True, drop_rate=0.5) 
    
    event = ImageSubmittedEvent(
        payload=ImageSubmittedPayload(image_id="img_drop_test", path="test.jpg")
    )
    
    print("Publishing multiple events with 50% drop rate...")
    for _ in range(10):
        bus.publish(event)
    
    print("SUCCESS: Robustness test passed (system stable under drops)!")

if __name__ == "__main__":
    print("\n--- Starting Defensive Testing (Chaos Bus) ---")
    test_idempotency()
    test_robustness_to_drops()
