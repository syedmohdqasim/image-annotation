import os
import faiss
import numpy as np
import pytest
from unittest.mock import MagicMock, patch
from services.vector_db.service import VectorDBService
from common.bus import EventBus
from common.schemas.events import EventType

@pytest.fixture
def mock_bus():
    return MagicMock(spec=EventBus)

@pytest.fixture
def temp_index_path(tmp_path):
    index_file = tmp_path / "test_faiss.index"
    return str(index_file)

def test_vector_db_initialization_creates_index(temp_index_path, mock_bus):
    # Setup
    svc = VectorDBService(dimension=64, index_path=temp_index_path, bus=mock_bus)
    
    # Assert
    assert isinstance(svc.index, faiss.IndexFlatL2)
    assert svc.index.d == 64
    assert svc.index.ntotal == 0

def test_handle_vectors_created_adds_to_index(temp_index_path, mock_bus):
    # Setup
    svc = VectorDBService(dimension=128, index_path=temp_index_path, bus=mock_bus)
    test_payload = {
        "event_id": "evt_test_123",
        "type": "vectors.created",
        "payload": {
            "image_id": "img_test_123",
            "object_ids": ["obj_1", "obj_2"],
            "embeddings_count": 2
        }
    }
    
    # Act
    svc.handle_vectors_created(test_payload)
    
    # Assert - Index should now have 2 vectors
    assert svc.index.ntotal == 2
    assert os.path.exists(temp_index_path)

def test_handle_vectors_created_publishes_event(temp_index_path, mock_bus):
    # Setup
    svc = VectorDBService(dimension=128, index_path=temp_index_path, bus=mock_bus)
    test_payload = {
        "event_id": "evt_test_123",
        "type": "vectors.created",
        "payload": {
            "image_id": "img_test_123",
            "object_ids": ["obj_1"],
            "embeddings_count": 1
        }
    }
    
    # Act
    svc.handle_vectors_created(test_payload)
    
    # Assert - Check Bus
    mock_bus.publish.assert_called_once()
    published_event = mock_bus.publish.call_args[0][0]
    
    assert published_event.type == EventType.INDEXING_COMPLETED
    assert published_event.payload.image_id == "img_test_123"

def test_index_persistence(temp_index_path, mock_bus):
    # Setup - Create index and add vector
    svc1 = VectorDBService(dimension=128, index_path=temp_index_path, bus=mock_bus)
    svc1.index.add(np.random.random((1, 128)).astype('float32'))
    svc1._save_index()
    
    # Load in a new service instance
    svc2 = VectorDBService(dimension=128, index_path=temp_index_path, bus=mock_bus)
    
    # Assert
    assert svc2.index.ntotal == 1

if __name__ == "__main__":
    pytest.main([__file__])
