import threading
import time
import os
import shutil
import redis
import pytest
from common.bus import EventBus
from services.upload.service import UploadService
from services.image_processing.service import ImageProcessingService
from services.document_db.service import DocumentDBService
from services.embedding.service import EmbeddingService
from services.vector_db.service import VectorDBService

@pytest.mark.skipif(os.getenv("RUN_REAL_REDIS") != "true", reason="Requires local Redis. Set RUN_REAL_REDIS=true to run.")
def test_full_pipeline_real_redis():
    """
    End-to-end integration test using the real local Redis instance.
    Ensures all services can communicate asynchronously via the event bus.
    """
    # 1. Pre-test cleanup: Flush Redis to ensure a clean state
    # We use a direct redis client to flush DB 0 (default)
    r = redis.Redis(host="localhost", port=6379, db=0)
    try:
        r.flushdb()
        print("Connected to Redis and flushed DB 0 for testing.")
    except redis.ConnectionError:
        print("ERROR: Could not connect to local Redis. Is it running?")
        return

    # 2. Initialize all services (they will use the real Redis by default now)
    upload_svc = UploadService(bus=EventBus())
    proc_svc = ImageProcessingService(bus=EventBus())
    doc_svc = DocumentDBService(bus=EventBus(), db_path="tests/test_real_doc_db.json")
    embed_svc = EmbeddingService(bus=EventBus())
    vec_svc = VectorDBService(bus=EventBus(), index_path="tests/test_real_faiss.index")

    # Monitor bus instance
    monitor_bus = EventBus()
    
    # Cleanup old test files
    for f in ["tests/test_real_doc_db.json", "tests/test_real_faiss.index"]:
        if os.path.exists(f): os.remove(f)

    # 3. Track received events to verify the pipeline flow
    received_types = []
    def monitor_handler(data):
        received_types.append(data["type"])
        print(f"PIPELINE MONITOR: Captured {data['type']}")

    def run_monitor():
        # Listen for all events in the chain
        topics = [
            "image.submitted", 
            "objects.detected", 
            "metadata.persisted", 
            "vectors.created", 
            "indexing.completed"
        ]
        print("PIPELINE MONITOR: Subscribing to topics...")
        monitor_bus.listen_all({t: monitor_handler for t in topics})

    # Start monitor and background services in separate threads
    monitor_thread = threading.Thread(target=run_monitor, daemon=True)
    monitor_thread.start()

    for svc in [proc_svc, doc_svc, embed_svc, vec_svc]:
        threading.Thread(target=svc.run, daemon=True).start()

    # Wait for all background services to subscribe to Redis
    print("Waiting for services to be ready...")
    time.sleep(3) 

    # 4. Trigger the pipeline via the Upload Service
    sample_file = "sample_data/test_image.jpg"
    if not os.path.exists(sample_file):
        os.makedirs("sample_data", exist_ok=True)
        with open(sample_file, "w") as f: f.write("test binary data")

    print("\n--- Starting End-to-End Pipeline Test (REAL REDIS) ---")
    image_id, path = upload_svc.upload_image(sample_file)
    print(f"Initial upload successful: {image_id}")

    # 5. Wait for the final 'indexing.completed' event
    timeout = 15
    start_time = time.time()
    while "indexing.completed" not in received_types and time.time() - start_time < timeout:
        time.sleep(0.5)

    print(f"\nCaptured Event Chain: {received_types}")
    
    # Assertions to verify the entire flow was executed correctly
    assert "image.submitted" in received_types
    assert "objects.detected" in received_types
    assert "metadata.persisted" in received_types
    assert "vectors.created" in received_types
    assert "indexing.completed" in received_types
    
    print("\nSUCCESS: End-to-end pipeline verified on real Redis!")

if __name__ == "__main__":
    if os.getenv("RUN_REAL_REDIS") == "true":
        test_full_pipeline_real_redis()
    else:
        print("Skipping REAL REDIS test. Set RUN_REAL_REDIS=true to run.")
