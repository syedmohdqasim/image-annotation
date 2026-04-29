import os
import pytest
from typer.testing import CliRunner
from unittest.mock import MagicMock, patch
from services.cli.main import app
from common.schemas.events import EventType

runner = CliRunner()

def test_upload_file_not_found():
    """Test upload command with a non-existent file."""
    result = runner.invoke(app, ["upload", "non_existent_file.jpg"])
    assert result.exit_code == 1
    assert "Error: File non_existent_file.jpg not found." in result.stdout

@patch("services.cli.main.EventBus")
def test_upload_success(mock_bus_class):
    """Test successful upload command."""
    mock_bus = mock_bus_class.return_value
    
    # Create a dummy file
    test_file = "test_cli_upload.jpg"
    with open(test_file, "w") as f:
        f.write("dummy content")
    
    try:
        result = runner.invoke(app, ["upload", test_file])
        
        assert result.exit_code == 0
        assert "Requesting upload for test_cli_upload.jpg..." in result.stdout
        assert "Upload request sent to the bus." in result.stdout
        
        # Verify event was published
        mock_bus.publish.assert_called_once()
        event = mock_bus.publish.call_args[0][0]
        assert event.type == EventType.UPLOAD_REQUESTED
        assert event.payload.source_path.endswith(test_file)
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)

@patch("services.cli.main.EventBus")
def test_search_timeout(mock_bus_class):
    """Test search command timing out."""
    # Mock the bus so it doesn't actually block or do anything
    mock_bus = mock_bus_class.return_value
    
    with patch("threading.Event.wait", return_value=False):
        result = runner.invoke(app, ["search", "dog"])
        assert "Search timed out." in result.stdout

@patch("services.cli.main.EventBus")
def test_search_success(mock_bus_class):
    """Test successful search command."""
    mock_bus = mock_bus_class.return_value
    
    # To simulate success, we need to trigger the callback that search() passes to subscribe()
    handler_to_call = None
    def mock_subscribe(topic, handler):
        nonlocal handler_to_call
        if topic == "query.completed":
            handler_to_call = handler

    mock_bus.subscribe.side_effect = mock_subscribe

    # We also need to mock the wait so it doesn't block
    with patch("threading.Event.wait") as mock_wait:
        # Patch uuid so the IDs match
        with patch("uuid.uuid4") as mock_uuid:
            # CLI uses query_id = f"q_{uuid.uuid4().hex[:6]}"
            mock_uuid.return_value.hex = "12345678"
            expected_query_id = "q_123456"
            
            # Define what happens when wait is called
            def simulate_response(*args, **kwargs):
                if handler_to_call:
                    handler_to_call({
                        "payload": {
                            "query_id": expected_query_id,
                            "results": [{"image_id": "img_1", "matched_as": "dog", "score": 0.99, "description": "A dog", "path": "dog.jpg"}]
                        }
                    })
                return True
            
            mock_wait.side_effect = simulate_response

            result = runner.invoke(app, ["search", "dog"])
            
            assert "Search Results for 'dog'" in result.stdout
            assert "Image ID: img_1 | Score: 0.99 | Matched: dog" in result.stdout
            assert "Description: A dog" in result.stdout

if __name__ == "__main__":
    pytest.main([__file__])
