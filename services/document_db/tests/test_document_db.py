import os
import json
import pytest
from unittest.mock import MagicMock
from services.document_db.service import DocumentDBService
from common.bus import EventBus
from common.schemas.events import EventType

@pytest.fixture
def mock_bus():
    return MagicMock(spec=EventBus)

@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_db.json"
    return str(db_file)

def test_handle_objects_detected_persists_metadata(temp_db, mock_bus):
    # Setup
    svc = DocumentDBService(db_path=temp_db, bus=mock_bus)
    test_payload = {
        "event_id": "evt_test_123",
        "timestamp": "2026-04-09T18:00:00Z",
        "type": "objects.detected",
        "payload": {
            "image_id": "img_test_123",
            "detections": [{"label": "cat", "confidence": 0.99}]
        }
    }
    
    # Act
    svc.handle_objects_detected(test_payload)
    
    # Assert - Check DB file
    assert os.path.exists(temp_db)
    with open(temp_db, "r") as f:
        db_data = json.load(f)
        assert "img_test_123" in db_data
        assert db_data["img_test_123"]["detections"][0]["label"] == "cat"

def test_handle_objects_detected_publishes_event(temp_db, mock_bus):
    # Setup
    svc = DocumentDBService(db_path=temp_db, bus=mock_bus)
    test_payload = {
        "event_id": "evt_test_123",
        "timestamp": "2026-04-09T18:00:00Z",
        "type": "objects.detected",
        "payload": {
            "image_id": "img_test_123",
            "detections": [{"label": "cat"}]
        }
    }
    
    # Act
    svc.handle_objects_detected(test_payload)
    
    # Assert - Check Bus
    mock_bus.publish.assert_called_once()
    published_event = mock_bus.publish.call_args[0][0]
    
    assert published_event.type == EventType.METADATA_PERSISTED
    assert published_event.payload.image_id == "img_test_123"
    assert "cat" in published_event.payload.metadata["detections"][0]["label"]

def test_db_loading(temp_db, mock_bus):
    # Setup - Pre-fill DB
    initial_data = {"img_old": {"image_id": "img_old", "detections": []}}
    with open(temp_db, "w") as f:
        json.dump(initial_data, f)
    
    svc = DocumentDBService(db_path=temp_db, bus=mock_bus)
    
    # Assert
    assert "img_old" in svc.db
    assert svc.db["img_old"]["image_id"] == "img_old"

if __name__ == "__main__":
    pytest.main([__file__])
