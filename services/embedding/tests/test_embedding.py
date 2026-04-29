import pytest
import json
from unittest.mock import MagicMock
from services.embedding.service import EmbeddingService
from common.bus import EventBus
from common.schemas.events import EventType

@pytest.fixture
def mock_bus():
    bus = MagicMock(spec=EventBus)
    bus.client = MagicMock()
    return bus

def test_handle_image_described_publishes_vectors_created(mock_bus):
    # Setup
    svc = EmbeddingService(bus=mock_bus)
    test_payload = {
        "event_id": "evt_test_123",
        "type": "image.described",
        "payload": {
            "image_id": "img_test_123",
            "description": "A cute dog in a park"
        }
    }
    
    # Act
    svc.handle_image_described(test_payload)
    
    # Assert
    mock_bus.publish.assert_called_once()
    published_event = mock_bus.publish.call_args[0][0]
    
    assert published_event.type == EventType.VECTORS_CREATED
    assert published_event.payload.image_id == "img_test_123"
    assert published_event.payload.description == "A cute dog in a park"
    assert len(published_event.payload.vectors) == 1

def test_handle_query_submitted_publishes_query_embedded(mock_bus):
    # Setup
    svc = EmbeddingService(bus=mock_bus)
    test_payload = {
        "event_id": "evt_query_123",
        "type": "query.submitted",
        "payload": {
            "query_id": "q_123",
            "query_type": "text",
            "payload": "find a dog"
        }
    }
    
    # Act
    svc.handle_query_submitted(test_payload)
    
    # Assert
    mock_bus.publish.assert_called_once()
    published_event = mock_bus.publish.call_args[0][0]
    
    assert published_event.type == EventType.QUERY_EMBEDDED
    assert published_event.payload.query_id == "q_123"
    assert len(published_event.payload.vector) == 3072

if __name__ == "__main__":
    pytest.main([__file__])
