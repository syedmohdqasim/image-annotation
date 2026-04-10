# Image Annotation & Retrieval System

A modular, event-driven system for processing images, detecting objects, and enabling semantic search using vector embeddings and document metadata.

## 🏗 Architecture & Technology Stack

The system is built on a **Pub-Sub** architecture using **Redis** as the central nervous system. Services are strictly decoupled, ensuring that no service bypasses the event bus to talk to another's data store.

### System Diagram

```mermaid
graph TD
    CLI((CLI)) -->|1. Upload| Upload[Upload Service]
    
    subgraph "Event Bus (Redis)"
        Bus{Redis Pub/Sub}
    end

    Upload -->|2. image.submitted| Bus
    Bus -->|3. image.submitted| Proc[Image Processing]
    
    Proc -->|4. objects.detected| Bus
    Bus -->|5. objects.detected| DocSvc[Document DB Service]
    
    DocSvc -->|6. metadata.persisted| Bus
    Bus -->|7. metadata.persisted| Embed[Embedding Service]
    
    Embed -->|8. vectors.created| Bus
    Bus -->|9. vectors.created| VecSvc[Vector DB Service]
    
    VecSvc -->|10. indexing.completed| Bus

    subgraph "Query Path"
        CLI -->|A. query.submitted| Bus
        Bus -->|B. query.submitted| VecSvc
        VecSvc -->|C. similarity.results| Bus
        Bus -->|D. similarity.results| DocSvc
        DocSvc -->|E. query.completed| Bus
        Bus -->|F. query.completed| CLI
    end

    subgraph "Data Ownership"
        Upload --- ImgStore[(Local FS)]
        DocSvc --- Mongo[(MongoDB)]
        VecSvc --- FAISS[(FAISS Index)]
    end
```

### Technology Breakdown

| Service | Technology | Role |
| :--- | :--- | :--- |
| **CLI** | **Python Typer** | Entry point for triggering uploads and searching objects. |
| **Upload** | **FastAPI** | Validates image files and persists them to the storage layer. |
| **Image Processing**| **PyTorch (YOLO)** | Detects objects, bounding boxes, and initial labels. |
| **Document DB** | **MongoDB** | Stores rich, nested JSON metadata for images and detections. |
| **Embedding** | **CLIP / Transformers** | Generates high-dimensional vectors for detected objects. |
| **Vector DB** | **FAISS** | Maintains the similarity index and handles vector lookups. |
| **Event Bus** | **Redis** | Orchestrates asynchronous communication between all services. |

## 📡 Event Lifecycle

1.  **`image.submitted`**: Ingestion complete; raw image is ready for analysis.
2.  **`objects.detected`**: Image Processing complete; labels and coordinates found.
3.  **`metadata.persisted`**: Document DB has stored the detections; ready for vectorization.
4.  **`vectors.created`**: Embedding Service has generated numerical representations.
5.  **`indexing.completed`**: Vector DB has updated its index; system is now searchable.
6.  **`query.submitted`**: User has initiated a search (text or image similarity).

## 🛡 System Guarantees

*   **Idempotency**: Services track `event_id` to prevent duplicate processing of the same image/query.
*   **Robustness**: Defensive validation ensures that malformed payloads do not crash subscribers.
*   **Eventual Consistency**: The query path reflects the latest state once the indexing cycle completes.
*   **Auditability**: The event bus allows for deterministic replay and fault injection testing.

## 🛠 Directory Structure

```text
.
├── services/
│   ├── cli/               # Typer-based CLI
│   ├── upload/            # Image ingestion (FastAPI)
│   ├── image-processing/  # AI Inference (YOLO)
│   ├── document-db/       # MongoDB Persistence
│   ├── embedding/         # Vector Generation (CLIP)
│   └── vector-db/         # Indexing (FAISS)
├── common/                # Shared Redis & Pydantic logic
├── generator/             # Testing & Event replay utility
└── tests/                 # Integration & Fault-injection tests
```
