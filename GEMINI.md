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
    - `cli/`: User entry point for uploads and semantic search.
    - `upload/`: Handles `upload.requested` and persists raw images.
    - `image_processing/`: Generates `image.described` and `objects.detected` events.
    - `document_db/`: Finalizes records on `vectors.created` and resolves search results on `similarity.matched`.
    - `embedding/`: Generates embeddings for both image descriptions and search queries.
    - `vector_db/`: Manages FAISS index and performs similarity search.

## 📡 Updated Event Lifecycle

### Indexing Pipeline
1.  **`upload.requested`**: Triggered by CLI.
2.  **`image.submitted`**: Image saved to `image_store/`.
3.  **`image.described`**: Semantic description generated via Gemini.
4.  **`objects.detected`**: Object labels and bounding boxes found.
5.  **`vectors.created`**: Embedding generated from description (published by Embedding Service).
6.  **`indexing.completed`**: Vector indexed in FAISS.
7.  **`metadata.persisted`**: Record finalized in Document DB with full metadata.

### Search Pipeline
1.  **`query.submitted`**: User search request.
2.  **`query.embedded`**: Embedding Service generates search vector.
3.  **`similarity.matched`**: Vector DB finds closest image IDs.
4.  **`query.completed`**: Document DB attaches metadata and returns results.

## 📜 Development Conventions

1.  **Asynchronous First:** Communication is exclusively via the `EventBus`.
2.  **Decoupled Search:** The search flow is split between Embedding (math), Vector DB (similarity), and Document DB (context).
3.  **Gemini Integration:** Use `GOOGLE_API_KEY` for AI features; otherwise, mocked descriptions are used.
4.  **Mocking:** Use `FakeRedis` for unit and integration tests.
