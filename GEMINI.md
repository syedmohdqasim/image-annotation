# Gemini Instruction Context: Image Annotation & Retrieval System

This project is a modular, event-driven system for processing images, detecting objects, and enabling semantic search using vector embeddings and document metadata.

## 🏗 Project Overview

- **Core Architecture:** Event-driven (Pub-Sub) microservices using **Redis** as the message bus.
- **Main Technologies:**
    - **Language:** Python 3.10+
    - **Messaging:** Redis (standard and `fakeredis` for mocking)
    - **AI/ML:** Gemini 1.5 Flash (for image descriptions), Deterministic Hashing (for mock embeddings).
    - **Validation:** Pydantic (Event schemas)
    - **Storage:** `image_store/` (Local FS for raw images), JSON files (Document DB), FAISS (Vector DB).

## 📂 Key Directory Structure

- `common/`: Shared logic and schemas.
    - `bus.py`: Implementation of the `EventBus`.
    - `schemas/events.py`: Pydantic models for all system events.
- `services/`: Individual microservices.
    - `cli/`: User entry point; now uses events for uploads.
    - `upload/`: Listens for `upload.requested` and saves to `image_store/`.
    - `image_processing/`: Generates image descriptions (Gemini) and detects objects.
    - `document_db/`: Persists metadata, detections, and AI descriptions.
    - `embedding/`: Generates vectors for labels.
    - `vector_db/`: Maintains FAISS index.

## 📡 Updated Event Lifecycle

1.  **`upload.requested`**: Initiated by CLI.
2.  **`image.submitted`**: Raw image saved; path and metadata available.
3.  **`image.described`**: Gemini-generated description added.
4.  **`objects.detected`**: Object labels and bounding boxes found.
5.  **`metadata.persisted`**: Record updated in Document DB.
6.  **`vectors.created`**: Embedding vectors generated.
7.  **`indexing.completed`**: Vector index updated.

## 📜 Development Conventions

1.  **Asynchronous First:** Do not call service methods directly. Use the `EventBus` to trigger actions (e.g., use `upload.requested` instead of `UploadService().upload()`).
2.  **Gemini Integration:** Use the `GOOGLE_API_KEY` environment variable for real AI features; otherwise, the system will use mocked descriptions.
3.  **Local Storage:** Images are stored in `image_store/` with unique IDs.
4.  **Mocking:** Use `FakeRedis` for testing to ensure hermeticity.
