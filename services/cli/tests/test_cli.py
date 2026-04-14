import os
import pytest
from typer.testing import CliRunner
from unittest.mock import MagicMock, patch
from services.cli.main import app

runner = CliRunner()

def test_upload_file_not_found():
    """Test upload command with a non-existent file."""
    result = runner.invoke(app, ["upload", "non_existent_file.jpg"])
    assert result.exit_code == 1
    assert "Error: File non_existent_file.jpg not found." in result.stdout

@patch("services.cli.main.UploadService")
@patch("services.cli.main.EventBus")
def test_upload_success(mock_bus, mock_svc_class):
    """Test successful upload command."""
    # Setup mock service
    mock_svc = mock_svc_class.return_value
    mock_svc.upload_image.return_value = ("img_test_123", "/path/to/img.jpg")
    
    # Create a dummy file
    test_file = "test_cli_upload.jpg"
    with open(test_file, "w") as f:
        f.write("dummy content")
    
    try:
        result = runner.invoke(app, ["upload", test_file])
        
        assert result.exit_code == 0
        assert "Successfully uploaded! Image ID: img_test_123" in result.stdout
        assert "Internal storage path: /path/to/img.jpg" in result.stdout
        
        # Verify service was called
        mock_svc.upload_image.assert_called_once_with(test_file)
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)

@patch("services.cli.main.EventBus")
def test_search_timeout(mock_bus_class):
    """Test search command timing out."""
    # Mock the bus so it doesn't actually block or do anything
    mock_bus = mock_bus_class.return_value
    
    # Run search - it will timeout because we aren't sending a QueryCompletedEvent
    # We reduce the timeout in the test by patching the wait? 
    # For now, let's just mock the behavior.
    
    with patch("threading.Event.wait", return_value=False):
        result = runner.invoke(app, ["search", "dog"])
        assert "Search timed out." in result.stdout

@patch("services.cli.main.EventBus")
def test_search_success(mock_bus_class):
    """Test successful search command."""
    mock_bus = mock_bus_class.return_value
    
    # To simulate success, we need to trigger the callback that search() passes to subscribe()
    # We'll capture the handler when subscribe is called
    handler_to_call = None
    def mock_subscribe(topic, handler):
        nonlocal handler_to_call
        if topic == "query.completed":
            handler_to_call = handler

    mock_bus.subscribe.side_effect = mock_subscribe

    # We also need to mock the wait so it doesn't block
    with patch("threading.Event.wait") as mock_wait:
        # Define what happens when wait is called
        def simulate_response(*args, **kwargs):
            if handler_to_call:
                # Call the handler with mock results
                handler_to_call({
                    "payload": {
                        "query_id": "any", # The CLI checks this, so we'll patch the UUID too
                        "results": [{"image_id": "img_1", "label": "dog", "score": 0.99}]
                    }
                })
            return True
        
        mock_wait.side_effect = simulate_response
        
        # Patch uuid so the IDs match
        with patch("uuid.uuid4") as mock_uuid:
            # CLI uses query_id = f"q_{uuid.uuid4().hex[:6]}"
            mock_uuid.return_value.hex = "12345678"
            expected_query_id = "q_123456"
            
            # Update simulate_call to use correct query_id
            def simulate_response_fixed(*args, **kwargs):
                if handler_to_call:
                    handler_to_call({
                        "payload": {
                            "query_id": expected_query_id,
                            "results": [{"image_id": "img_1", "label": "dog", "score": 0.99}]
                        }
                    })
                return True
            mock_wait.side_effect = simulate_response_fixed

            result = runner.invoke(app, ["search", "dog"])
            
            assert "Search Results for 'dog'" in result.stdout
            assert "Image ID: img_1 | Label: dog | Confidence: 0.99" in result.stdout

if __name__ == "__main__":
    pytest.main([__file__])
