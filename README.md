# Image Annotation & Retrieval System

A modular, event-driven system for processing images, detecting objects, and enabling semantic search using vector embeddings and document metadata.

## 🏗 Architecture & Technology Stack

The system is built on a **Pub-Sub** architecture using **Redis** as the central nervous system. Services are strictly decoupled and communicate exclusively through the event bus.

### System Diagram

```mermaid
graph TD
    CLI((CLI)) -->|1. upload.requested| Bus
    
    subgraph "Event Bus (Redis)"
        Bus{Redis Pub/Sub}
    end

    Bus -->|2. upload.requested| Upload[Upload Service]
    Upload -->|3. image.submitted| Bus
    
    Bus -->|4. image.submitted| Proc[Image Processing]
    Bus -->|4. image.submitted| DocSvc[Document DB Service]
    
    Proc -->|5. image.described| Bus
    Proc -->|6. objects.detected| Bus
    
    Bus -->|7. image.described| Embed[Embedding Service]
    Bus -->|7. image.described| DocSvc
    Bus -->|8. objects.detected| DocSvc
    
    Embed -->|9. vectors.created| Bus
    Bus -->|10. vectors.created| VecSvc[Vector DB Service]
    Bus -->|10. vectors.created| DocSvc
    
    VecSvc -->|11. indexing.completed| Bus
    DocSvc -->|12. metadata.persisted| Bus

    subgraph "Query Path"
        CLI -->|A. query.submitted| Bus
        Bus -->|B. query.submitted| Embed
        Embed -->|C. query.embedded| Bus
        Bus -->|D. query.embedded| VecSvc
        VecSvc -->|E. similarity.matched| Bus
        Bus -->|F. similarity.matched| DocSvc
        DocSvc -->|G. query.completed| Bus
        Bus -->|H. query.completed| CLI
    end

    subgraph "Data Ownership"
        Upload --- ImgStore[(image_store)]
        DocSvc --- JSONDB[(JSON File DB)]
        VecSvc --- FAISS[(FAISS Index)]
    end
```

### Technology Breakdown

| Service | Technology | Role |
| :--- | :--- | :--- |
| **CLI** | **Python Typer** | Entry point for requesting uploads and searching. |
| **Upload** | **Python** | Listens for requests, saves images to `image_store`. |
| **Image Processing**| **Gemini 1.5 Flash** | Generates image descriptions and detects objects. |
| **Document DB** | **JSON/File** | Stores metadata, detections, and resolves search results. |
| **Embedding** | **Deterministic Hashing**| Generates vectors for descriptions and search queries. |
| **Vector DB** | **FAISS** | Maintains similarity index and performs vector lookups. |
| **Event Bus** | **Redis** | Orchestrates asynchronous communication. |

## 🚀 Getting Started

### 1. Prerequisites
- **Python 3.10+**
- **Redis Server**
- **Google API Key** (Optional, for Gemini features)

### 2. Setup Environment
```bash
pip install -r requirements.txt
export GOOGLE_API_KEY="your_key_here"
```

### 3. Running the System
Start the services in separate terminal windows:
```bash
# Terminal 1
python services/upload/service.py

# Terminal 2
python services/image_processing/service.py

# Terminal 3
python services/document_db/service.py

# Terminal 4
python services/embedding/service.py

# Terminal 5
python services/vector_db/service.py
```

Then use the CLI:
```bash
python services/cli/main.py upload sample_data/dog.jpg
python services/cli/main.py search "dog"
```

## 📡 Event Lifecycle

### Indexing Pipeline
1.  **`upload.requested`**: CLI requests an image to be ingested.
2.  **`image.submitted`**: Raw image is saved; Document DB creates initial record.
3.  **`image.described`**: Gemini generates a semantic description.
4.  **`objects.detected`**: Object labels and bounding boxes identified.
5.  **`vectors.created`**: Embedding Service generates vectors from the description.
6.  **`indexing.completed`**: Vector DB has indexed the new vector.
7.  **`metadata.persisted`**: Document DB has finalized the record with description and metadata.

### Search Pipeline
1.  **`query.submitted`**: User initiates a text search via CLI.
2.  **`query.embedded`**: Embedding Service generates a vector for the search query.
3.  **`similarity.matched`**: Vector DB finds the most similar image IDs.
4.  **`query.completed`**: Document DB resolves image IDs to full metadata and returns to CLI.

## 🛠 Directory Structure

```text
.
├── services/
│   ├── cli/               # Typer-based CLI
│   ├── upload/            # Image ingestion (Async)
│   ├── image_processing/  # Gemini & AI Inference
│   ├── document_db/       # Metadata Persistence & Query Resolution
│   ├── embedding/         # Vector Generation (Description & Query)
│   └── vector_db/         # Vector Similarity Search (FAISS)
├── common/                # Shared Redis & Pydantic logic
├── image_store/           # Persistent storage for raw images
└── tests/                 # Integration & Unit tests
```
