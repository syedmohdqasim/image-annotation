import os
import threading
import time
import uuid
import typer
from services.upload.service import UploadService
from common.bus import EventBus
from common.schemas.events import QuerySubmittedEvent, QuerySubmittedPayload, EventType

app = typer.Typer()

@app.command()
def upload(file_path: str):
    """
    Upload an image to the system.
    """
    if not os.path.exists(file_path):
        typer.echo(f"Error: File {file_path} not found.")
        raise typer.Exit(code=1)

    typer.echo(f"Uploading {file_path}...")
    
    bus = EventBus()
    svc = UploadService(bus=bus)
    
    image_id, target_path = svc.upload_image(file_path)
    
    typer.echo(f"Successfully uploaded! Image ID: {image_id}")
    typer.echo(f"Internal storage path: {target_path}")

@app.command()
def search(query: str, query_type: str = "text"):
    """
    Search for images by topic or similarity.
    """
    typer.echo(f"Initiating search: {query} ({query_type})...")
    
    bus = EventBus()
    query_id = f"q_{uuid.uuid4().hex[:6]}"
    results = []
    found = threading.Event()

    def handle_query_completed(data):
        if data["payload"]["query_id"] == query_id:
            results.extend(data["payload"]["results"])
            found.set()

    # Listen for results in background
    sub_thread = threading.Thread(target=lambda: bus.subscribe(EventType.QUERY_COMPLETED.value, handle_query_completed), daemon=True)
    sub_thread.start()
    
    time.sleep(1) # wait for sub

    # Publish query
    event = QuerySubmittedEvent(
        payload=QuerySubmittedPayload(
            query_id=query_id,
            query_type=query_type,
            payload=query
        )
    )
    bus.publish(event)
    
    # Wait for results
    typer.echo("Waiting for results...")
    if found.wait(timeout=10):
        typer.echo(f"\n--- Search Results for '{query}' ---")
        for res in results:
            typer.echo(f"Image ID: {res['image_id']} | Label: {res['label']} | Confidence: {res['score']:.2f}")
    else:
        typer.echo("Search timed out.")

if __name__ == "__main__":
    app()
