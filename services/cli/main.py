import os
import threading
import time
import uuid
import typer
from services.upload.service import UploadService
from common.bus import EventBus
from common.schemas.events import QuerySubmittedEvent, QuerySubmittedPayload, EventType, UploadRequestedEvent, UploadRequestedPayload

app = typer.Typer()

@app.command()
def upload(file_path: str):
    """
    Request an image upload via the event bus.
    """
    if not os.path.exists(file_path):
        typer.echo(f"Error: File {file_path} not found.")
        raise typer.Exit(code=1)

    typer.echo(f"Requesting upload for {file_path}...")
    
    bus = EventBus()
    event = UploadRequestedEvent(
        payload=UploadRequestedPayload(
            source_path=os.path.abspath(file_path)
        )
    )
    bus.publish(event)
    typer.echo("Upload request sent to the bus.")

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
    typer.echo("Waiting for results (timeout: 30s)...")
    if found.wait(timeout=30):
        typer.echo(f"\n--- Search Results for '{query}' ---")
        for res in results:
            desc = res.get('description', 'No description')
            path = res.get('path', 'Unknown path')
            matched_as = res.get('matched_as', 'description')
            typer.echo(f"Image ID: {res['image_id']} | Score: {res['score']:.2f} | Matched: {matched_as}")
            typer.echo(f"  Description: {desc}")
            typer.echo(f"  Path: {path}")
            typer.echo("-" * 40)
    else:
        typer.echo("Search timed out.")

if __name__ == "__main__":
    app()
