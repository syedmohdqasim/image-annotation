import threading
import time
import os
import shutil
from common.bus import EventBus
from services.upload.service import UploadService
from services.image_processing.service import ImageProcessingService
from services.document_db.service import DocumentDBService
from services.embedding.service import EmbeddingService
from services.vector_db.service import VectorDBService

from fakeredis import FakeRedis

def test_full_pipeline():
    # Setup shared mock redis client
    redis_client = FakeRedis()
    
    # Initialize all services with their OWN EventBus sharing the client
    upload_svc = UploadService(bus=EventBus(client=redis_client))
    proc_svc = ImageProcessingService(bus=EventBus(client=redis_client))
    doc_svc = DocumentDBService(bus=EventBus(client=redis_client), db_path="tests/test_doc_db.json")
    embed_svc = EmbeddingService(bus=EventBus(client=redis_client))
    vec_svc = VectorDBService(bus=EventBus(client=redis_client), index_path="tests/test_faiss.index")

    # Monitor bus with its OWN instance
    monitor_bus = EventBus(client=redis_client)
    
    # Cleanup old test files
    for f in ["tests/test_doc_db.json", "tests/test_faiss.index"]:
        if os.path.exists(f): os.remove(f)

    # Track received events
    received_types = []
    def monitor_handler(data):
        received_types.append(data["type"])

    # Subscribe to all topics for monitoring
    for topic in ["image.submitted", "objects.detected", "metadata.persisted", "vectors.created", "indexing.completed"]:
        # Each monitor subscription can use the SAME monitor_bus instance
        # BUT wait - if monitor_bus handles all topics, it will see image.submitted only once?
        # That's fine, we want to see it at least once.
        pass

    # Actually, we can use one monitor_bus to listen to multiple topics
    def run_monitor():
        monitor_bus.listen_all({
            t: monitor_handler for t in ["image.submitted", "objects.detected", "metadata.persisted", "vectors.created", "indexing.completed"]
        })

    threading.Thread(target=run_monitor, daemon=True).start()
    
    # Start all background services in threads
    for svc in [proc_svc, doc_svc, embed_svc, vec_svc]:
        threading.Thread(target=svc.run, daemon=True).start()
    
    time.sleep(1) # wait for all subs

    # Trigger full pipeline via upload
    sample_file = "sample_data/test_image.jpg"
    if not os.path.exists(sample_file):
        os.makedirs("sample_data", exist_ok=True)
        with open(sample_file, "w") as f: f.write("test data")

    print("\n--- Starting Full Pipeline Integration Test ---")
    upload_svc.upload_image(sample_file)

    # Wait for the last event in the chain
    timeout = 10
    start_time = time.time()
    while "indexing.completed" not in received_types and time.time() - start_time < timeout:
        time.sleep(0.5)

    print(f"Events captured: {received_types}")
    
    assert "image.submitted" in received_types
    assert "objects.detected" in received_types
    assert "metadata.persisted" in received_types
    assert "vectors.created" in received_types
    assert "indexing.completed" in received_types
    
    print("\nSUCCESS: Full End-to-End Pipeline test passed!")

if __name__ == "__main__":
    test_full_pipeline()
