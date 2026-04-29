import pytest
import os
from unittest.mock import MagicMock, patch
from services.document_db.service import DocumentDBService
from common.bus import EventBus
from common.schemas.events import EventType

@pytest.fixture
def mock_bus():
    return MagicMock(spec=EventBus)

@pytest.fixture
def no_mongodb():
    with patch("os.getenv", return_value=None):
        yield

@pytest.fixture
def test_db_path():
    path = "tests/test_doc_db.json"
    if os.path.exists(path): os.remove(path)
    yield path
    if os.path.exists(path): os.remove(path)

def test_handle_vectors_created_updates_description(mock_bus, test_db_path, no_mongodb):
    svc = DocumentDBService(db_path=test_db_path, bus=mock_bus)
    # Pre-seed with image
    svc.handle_image_submitted({
        "timestamp": "now",
        "payload": {"image_id": "img_1", "path": "test.jpg"}
    })
    
    test_payload = {
        "payload": {
            "image_id": "img_1",
            "description": "A test description"
        }
    }
    
    svc.handle_vectors_created(test_payload)
    
    assert svc.db["img_1"]["description"] == "A test description"
    mock_bus.publish.assert_called_once()
    assert mock_bus.publish.call_args[0][0].type == EventType.METADATA_PERSISTED

def test_handle_similarity_matched_publishes_query_completed(mock_bus, test_db_path, no_mongodb):
    svc = DocumentDBService(db_path=test_db_path, bus=mock_bus)
    # Seed with image data
    svc.db["img_1"] = {"image_id": "img_1", "description": "desc", "path": "path.jpg"}
    
    test_payload = {
        "payload": {
            "query_id": "q_1",
            "matches": [{"image_id": "img_1", "score": 0.9}]
        }
    }
    
    svc.handle_similarity_matched(test_payload)
    
    mock_bus.publish.assert_called_once()
    event = mock_bus.publish.call_args[0][0]
    assert event.type == EventType.QUERY_COMPLETED
    assert len(event.payload.results) == 1
    assert event.payload.results[0]["image_id"] == "img_1"

if __name__ == "__main__":
    pytest.main([__file__])
