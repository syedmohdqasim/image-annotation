import os
import shutil
import pytest
from unittest.mock import MagicMock
from services.upload.service import UploadService
from common.bus import EventBus
from common.schemas.events import EventType

@pytest.fixture
def mock_bus():
    return MagicMock(spec=EventBus)

@pytest.fixture
def temp_storage(tmp_path):
    storage = tmp_path / "storage"
    storage.mkdir()
    return str(storage)

def test_upload_image_persists_file(temp_storage, mock_bus, tmp_path):
    # Setup
    svc = UploadService(storage_dir=temp_storage, bus=mock_bus)
    source_file = tmp_path / "test.jpg"
    source_file.write_text("fake image data")
    
    # Act
    image_id, target_path = svc.upload_image(str(source_file))
    
    # Assert
    assert os.path.exists(target_path)
    assert image_id in target_path
    with open(target_path, "r") as f:
        assert f.read() == "fake image data"

def test_upload_image_publishes_event(temp_storage, mock_bus, tmp_path):
    # Setup
    svc = UploadService(storage_dir=temp_storage, bus=mock_bus)
    source_file = tmp_path / "test.jpg"
    source_file.write_text("data")
    
    # Act
    image_id, _ = svc.upload_image(str(source_file))
    
    # Assert
    mock_bus.publish.assert_called_once()
    published_event = mock_bus.publish.call_args[0][0]
    assert published_event.type == EventType.IMAGE_SUBMITTED
    assert published_event.payload.image_id == image_id
    assert published_event.payload.path.endswith(f"{image_id}.jpg")

def test_upload_image_file_not_found(temp_storage, mock_bus):
    svc = UploadService(storage_dir=temp_storage, bus=mock_bus)
    
    with pytest.raises(FileNotFoundError):
        svc.upload_image("non_existent_path.jpg")

if __name__ == "__main__":
    pytest.main([__file__])
