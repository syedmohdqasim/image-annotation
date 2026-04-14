import pytest
from unittest.mock import MagicMock
from services.embedding.service import EmbeddingService
from common.bus import EventBus
from common.schemas.events import EventType

@pytest.fixture
def mock_bus():
    return MagicMock(spec=EventBus)

def test_handle_metadata_persisted_publishes_vectors_created(mock_bus):
    # Setup
    svc = EmbeddingService(bus=mock_bus)
    test_payload = {
        "event_id": "evt_test_123",
        "timestamp": "2026-04-09T18:00:00Z",
        "type": "metadata.persisted",
        "payload": {
            "image_id": "img_test_123",
            "metadata": {
                "detections": [
                    {"label": "dog"},
                    {"label": "car"}
                ]
            }
        }
    }
    
    # Act
    svc.handle_metadata_persisted(test_payload)
    
    # Assert
    mock_bus.publish.assert_called_once()
    published_event = mock_bus.publish.call_args[0][0]
    
    assert published_event.type == EventType.VECTORS_CREATED
    assert published_event.payload.image_id == "img_test_123"
    assert published_event.payload.embeddings_count == 2
    assert len(published_event.payload.object_ids) == 2
    assert "obj_img_test_123_0" in published_event.payload.object_ids

def test_handle_metadata_with_no_detections(mock_bus):
    # Setup
    svc = EmbeddingService(bus=mock_bus)
    test_payload = {
        "event_id": "evt_test_123",
        "type": "metadata.persisted",
        "payload": {
            "image_id": "img_empty",
            "metadata": {"detections": []}
        }
    }
    
    # Act
    svc.handle_metadata_persisted(test_payload)
    
    # Assert
    mock_bus.publish.assert_called_once()
    published_event = mock_bus.publish.call_args[0][0]
    assert published_event.payload.embeddings_count == 0

if __name__ == "__main__":
    pytest.main([__file__])
