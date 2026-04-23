import pytest
from unittest.mock import MagicMock
from services.vector_db.service import VectorDBService
from common.bus import EventBus
from common.schemas.events import EventType
import os

@pytest.fixture
def mock_bus():
    return MagicMock(spec=EventBus)

@pytest.fixture
def test_index_path():
    path = "tests/test_vec.index"
    if os.path.exists(path): os.remove(path)
    yield path
    if os.path.exists(path): os.remove(path)

def test_handle_vectors_created_indexes_and_publishes(mock_bus, test_index_path):
    svc = VectorDBService(index_path=test_index_path, bus=mock_bus)
    test_payload = {
        "payload": {
            "image_id": "img_1",
            "vectors": [[0.1] * 128]
        }
    }
    
    svc.handle_vectors_created(test_payload)
    
    assert svc.index.ntotal == 1
    mock_bus.publish.assert_called_once()
    assert mock_bus.publish.call_args[0][0].type == EventType.INDEXING_COMPLETED

def test_handle_query_embedded_returns_matches(mock_bus, test_index_path):
    svc = VectorDBService(index_path=test_index_path, bus=mock_bus)
    # Index one vector first
    svc.handle_vectors_created({
        "payload": {"image_id": "img_1", "vectors": [[0.1] * 128]}
    })
    mock_bus.publish.reset_mock()
    
    query_payload = {
        "payload": {
            "query_id": "q_1",
            "vector": [0.1] * 128
        }
    }
    
    svc.handle_query_embedded(query_payload)
    
    mock_bus.publish.assert_called_once()
    event = mock_bus.publish.call_args[0][0]
    assert event.type == EventType.SIMILARITY_MATCHED
    assert event.payload.query_id == "q_1"
    assert len(event.payload.matches) > 0
    assert event.payload.matches[0]["image_id"] == "img_1"

if __name__ == "__main__":
    pytest.main([__file__])
