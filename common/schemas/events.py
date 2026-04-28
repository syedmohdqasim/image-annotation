from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4
from pydantic import BaseModel, Field

class EventType(str, Enum):
    UPLOAD_REQUESTED = "upload.requested"
    IMAGE_SUBMITTED = "image.submitted"
    OBJECTS_DETECTED = "objects.detected"
    METADATA_PERSISTED = "metadata.persisted"
    VECTORS_CREATED = "vectors.created"
    INDEXING_COMPLETED = "indexing.completed"
    IMAGE_DESCRIBED = "image.described"
    QUERY_SUBMITTED = "query.submitted"
    QUERY_EMBEDDED = "query.embedded"
    SIMILARITY_MATCHED = "similarity.matched"
    QUERY_COMPLETED = "query.completed"

class BaseEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{uuid4().hex[:8]}")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    type: EventType

# --- Payloads ---

class UploadRequestedPayload(BaseModel):
    source_path: str

class ImageSubmittedPayload(BaseModel):
    image_id: str
    path: str
    original_name: Optional[str] = None
    source: str = "cli"

class ObjectsDetectedPayload(BaseModel):
    image_id: str
    detections: List[Dict[str, Any]]

class ImageDescribedPayload(BaseModel):
    image_id: str
    description: str
    detections: List[Dict[str, Any]] = []

class MetadataPersistedPayload(BaseModel):
    image_id: str
    document_id: str
    metadata: Dict[str, Any]

class VectorsCreatedPayload(BaseModel):
    image_id: str
    object_ids: List[str]
    embeddings_count: int
    vectors: List[List[float]] = []
    description: Optional[str] = None

class IndexingCompletedPayload(BaseModel):
    image_id: str
    index_version: str

class QuerySubmittedPayload(BaseModel):
    query_id: str
    query_type: str  # "text" or "image"
    payload: Any      # Text string or image_id

class QueryEmbeddedPayload(BaseModel):
    query_id: str
    vector: List[float]

class SimilarityMatchedPayload(BaseModel):
    query_id: str
    matches: List[Dict[str, Any]] # List of {image_id, score}

class QueryCompletedPayload(BaseModel):
    query_id: str
    results: List[Dict[str, Any]]

# --- Specific Events ---

class ImageSubmittedEvent(BaseEvent):
    type: EventType = EventType.IMAGE_SUBMITTED
    payload: ImageSubmittedPayload

class ObjectsDetectedEvent(BaseEvent):
    type: EventType = EventType.OBJECTS_DETECTED
    payload: ObjectsDetectedPayload

class ImageDescribedEvent(BaseEvent):
    type: EventType = EventType.IMAGE_DESCRIBED
    payload: ImageDescribedPayload

class MetadataPersistedEvent(BaseEvent):
    type: EventType = EventType.METADATA_PERSISTED
    payload: MetadataPersistedPayload

class VectorsCreatedEvent(BaseEvent):
    type: EventType = EventType.VECTORS_CREATED
    payload: VectorsCreatedPayload

class IndexingCompletedEvent(BaseEvent):
    type: EventType = EventType.INDEXING_COMPLETED
    payload: IndexingCompletedPayload

class QuerySubmittedEvent(BaseEvent):
    type: EventType = EventType.QUERY_SUBMITTED
    payload: QuerySubmittedPayload

class QueryEmbeddedEvent(BaseEvent):
    type: EventType = EventType.QUERY_EMBEDDED
    payload: QueryEmbeddedPayload

class SimilarityMatchedEvent(BaseEvent):
    type: EventType = EventType.SIMILARITY_MATCHED
    payload: SimilarityMatchedPayload

class QueryCompletedEvent(BaseEvent):
    type: EventType = EventType.QUERY_COMPLETED
    payload: QueryCompletedPayload

class UploadRequestedEvent(BaseEvent):
    type: EventType = EventType.UPLOAD_REQUESTED
    payload: UploadRequestedPayload
