import threading
import time
import os
from common.bus import EventBus
from services.upload.service import UploadService
from services.image_processing.service import ImageProcessingService

from fakeredis import FakeRedis

def test_upload_to_processing():
    # Setup shared mock redis client
    redis_client = FakeRedis()
    
    # Initialize services with their OWN EventBus sharing the client
    bus_proc = EventBus(client=redis_client)
    bus_upload = EventBus(client=redis_client)
    bus_monitor = EventBus(client=redis_client)
    
    processing_svc = ImageProcessingService(bus=bus_proc)
    upload_svc = UploadService(bus=bus_upload)

    received_events = []
    def monitor_handler(data):
        received_events.append(data)

    # Listen for objects.detected to verify the end of this stage
    sub_thread = threading.Thread(target=lambda: bus_monitor.subscribe("objects.detected", monitor_handler), daemon=True)
    sub_thread.start()
    
    # Start the processing service in a thread
    proc_thread = threading.Thread(target=processing_svc.run, daemon=True)
    proc_thread.start()
    
    time.sleep(1) # wait for subs

    # Trigger upload
    sample_file = "sample_data/test_image.jpg"
    if not os.path.exists(sample_file):
        os.makedirs("sample_data", exist_ok=True)
        with open(sample_file, "w") as f: f.write("test")

    print("Triggering upload...")
    upload_svc.upload_image(sample_file)

    # Wait for processing to complete
    time.sleep(2)
    
    assert any(e["type"] == "objects.detected" for e in received_events)
    print("SUCCESS: Pipeline Stage 1 (Upload -> Image Processing) passed!")

if __name__ == "__main__":
    test_upload_to_processing()
