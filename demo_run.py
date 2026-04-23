import threading
import time
import os
from common.bus import EventBus
from services.upload.service import UploadService
from services.image_processing.service import ImageProcessingService
from services.document_db.service import DocumentDBService
from services.embedding.service import EmbeddingService
from services.vector_db.service import VectorDBService
from common.schemas.events import (
    QuerySubmittedEvent, 
    QuerySubmittedPayload, 
    EventType,
    UploadRequestedEvent,
    UploadRequestedPayload
)
import uuid
import json

from fakeredis import FakeRedis

def run_demo():
    # Setup shared mock redis client
    redis_client = FakeRedis()
    
    # Initialize all services sharing the same mock client
    bus_kwargs = {"client": redis_client}
    
    upload_svc = UploadService(bus=EventBus(**bus_kwargs))
    proc_svc = ImageProcessingService(bus=EventBus(**bus_kwargs))
    doc_svc = DocumentDBService(bus=EventBus(**bus_kwargs), db_path="demo_doc_db.json")
    embed_svc = EmbeddingService(bus=EventBus(**bus_kwargs))
    vec_svc = VectorDBService(bus=EventBus(**bus_kwargs), index_path="demo_faiss.index")

    # Cleanup old test files
    for f in ["demo_doc_db.json", "demo_faiss.index"]:
        if os.path.exists(f): os.remove(f)

    # Start all background services in threads
    print("--- Starting Services ---")
    services = [
        ("Upload", upload_svc),
        ("Image Processing", proc_svc),
        ("Document DB", doc_svc),
        ("Embedding", embed_svc),
        ("Vector DB", vec_svc)
    ]
    
    for name, svc in services:
        t = threading.Thread(target=svc.run, daemon=True)
        t.start()
        print(f"Started {name} Service")
    
    time.sleep(1) # wait for all subs

    # 1. Request Upload Dog
    print("\n--- Step 1: Requesting Dog Image Upload ---")
    bus = EventBus(**bus_kwargs)
    bus.publish(UploadRequestedEvent(payload=UploadRequestedPayload(source_path="sample_data/dog.jpg")))

    # 2. Request Upload Cat
    print("\n--- Step 2: Requesting Cat Image Upload ---")
    bus.publish(UploadRequestedEvent(payload=UploadRequestedPayload(source_path="sample_data/cat.jpg")))

    print("\nWaiting for pipeline to finish indexing...")
    time.sleep(6)

    # Check Document DB content
    if os.path.exists("demo_doc_db.json"):
        with open("demo_doc_db.json", "r") as f:
            db_content = json.load(f)
            print("\n--- Document DB Contents ---")
            for img_id, data in db_content.items():
                desc = data.get("description", "N/A")
                print(f"Image {img_id}: {desc}")

    # 3. Search for Dog
    print("\n--- Step 3: Searching for 'dog' ---")
    # In this mock, the description for dog is "A cute dog sitting in a park."
    # Our deterministic hash means searching for exactly that will match perfectly.
    search_query(redis_client, "A cute dog sitting in a park.")

    # 4. Search for Cat
    print("\n--- Step 4: Searching for 'cat' ---")
    search_query(redis_client, "A fluffy cat playing with a yarn ball.")

def search_query(redis_client, query_text):
    bus = EventBus(client=redis_client)
    query_id = f"q_{uuid.uuid4().hex[:6]}"
    results_box = []
    found = threading.Event()

    def handle_query_completed(data):
        if data["payload"]["query_id"] == query_id:
            results_box.extend(data["payload"]["results"])
            found.set()

    # Listen for results in background
    sub_thread = threading.Thread(target=lambda: bus.subscribe(EventType.QUERY_COMPLETED.value, handle_query_completed), daemon=True)
    sub_thread.start()
    
    time.sleep(1) # wait for subscription

    # Publish query
    event = QuerySubmittedEvent(
        payload=QuerySubmittedPayload(
            query_id=query_id,
            query_type="text",
            payload=query_text
        )
    )
    bus.publish(event)
    
    if found.wait(timeout=5):
        print(f"Results for '{query_text}':")
        for res in results_box:
            print(f"  - Image: {res['image_id']} | Score: {res['score']:.4f} | Path: {res.get('path')}")
            print(f"    Description: {res.get('description')}")
    else:
        print(f"Search for '{query_text}' timed out.")

if __name__ == "__main__":
    run_demo()
