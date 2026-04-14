import pytest
from unittest.mock import MagicMock
from services.image_processing.service import ImageProcessingService
from common.bus import EventBus
from common.schemas.events import EventType

@pytest.fixture
def mock_bus():
    return MagicMock(spec=EventBus)

def test_handle_image_submitted_publishes_detections(mock_bus):
    # Setup
    svc = ImageProcessingService(bus=mock_bus)
    test_payload = {
        "event_id": "evt_test_123",
        "timestamp": "2026-04-09T18:00:00Z",
        "type": "image.submitted",
        "payload": {
            "image_id": "img_test_123",
            "path": "test/path/img.jpg",
            "source": "cli"
        }
    }
    
    # Act
    svc.handle_image_submitted(test_payload)
    
    # Assert
    mock_bus.publish.assert_called_once()
    published_event = mock_bus.publish.call_args[0][0]
    
    assert published_event.type == EventType.OBJECTS_DETECTED
    assert published_event.payload.image_id == "img_test_123"
    assert len(published_event.payload.detections) > 0
    assert published_event.payload.detections[0]["label"] == "dog"

def test_service_start_subscribes_to_correct_topic(mock_bus):
    # Setup
    svc = ImageProcessingService(bus=mock_bus)
    
    # Mock listen_all as it's a blocking call in real life
    mock_bus.listen_all = MagicMock()
    svc.run()
    
    # Assert
    mock_bus.listen_all.assert_called_once()
    handlers = mock_bus.listen_all.call_args[0][0]
    assert EventType.IMAGE_SUBMITTED.value in handlers
    assert handlers[EventType.IMAGE_SUBMITTED.value] == svc.handle_image_submitted

if __name__ == "__main__":
    pytest.main([__file__])
