import os
import pytest
from unittest.mock import patch, Mock
from datetime import datetime, timezone
from rflogs import main, upload_files, BASE_URL

# Path to the test data directory
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'test_data')

@pytest.fixture
def mock_session():
    with patch('rflogs.get_session') as mock:
        yield mock.return_value

@pytest.fixture
def mock_requests_post(mock_session):
    def mock_post(*args, **kwargs):
        response = Mock()
        response.status_code = 200
        if 'files' in kwargs:
            file_data = list(kwargs['files'].values())[0]
            file_name = file_data[0] if isinstance(file_data, tuple) else 'file'
            response.json.return_value = {
                "id": "test-file-id",
                "file_url": f"/files/{file_name}"
            }
        else:
            response.json.return_value = {
                "run_id": "test-run-id",
                "start_time": datetime.now(timezone.utc).isoformat(),
                "end_time": datetime.now(timezone.utc).isoformat()
            }
        return response
    mock_session.post.side_effect = mock_post
    return mock_session.post

@pytest.fixture
def mock_environment():
    with patch.dict(os.environ, {"RFLOGS_API_KEY": "dummy_key"}):
        yield

def test_cli_default_options(mock_requests_post, mock_environment, capsys):
    with patch('sys.argv', ['rflogs', 'upload', TEST_DATA_DIR]):
        main()
    
    captured = capsys.readouterr()
    assert "Uploading results" in captured.out
    assert "output.xml" in captured.out
    assert "log.html" in captured.out
    assert "report.html" in captured.out
    assert f"{BASE_URL}/files/log.html" in captured.out
    assert f"{BASE_URL}/files/report.html" in captured.out

def test_cli_custom_filenames(mock_requests_post, mock_environment, capsys):
    with patch('sys.argv', ['rflogs', 'upload', TEST_DATA_DIR, 
                            '--output', 'custom_output.xml', 
                            '--log', 'custom_log.html', 
                            '--report', 'custom_report.html']):
        main()
    
    captured = capsys.readouterr()
    assert "Uploading results" in captured.out
    assert "custom_output.xml" in captured.out
    assert "custom_log.html" in captured.out
    assert "custom_report.html" in captured.out
    assert f"{BASE_URL}/files/custom_log.html" in captured.out
    assert f"{BASE_URL}/files/custom_report.html" in captured.out

def test_cli_none_options(mock_requests_post, mock_environment, capsys):
    with patch('sys.argv', ['rflogs', 'upload', TEST_DATA_DIR, '--log', 'NONE', '--report', 'NONE']):
        main()
    
    captured = capsys.readouterr()
    assert "Uploading results" in captured.out
    assert "output.xml" in captured.out
    assert "log.html" not in captured.out
    assert "report.html" not in captured.out

def test_cli_no_files_found(mock_environment, capsys):
    non_existent_dir = os.path.join(TEST_DATA_DIR, 'non_existent')
    with pytest.raises(SystemExit) as exc_info:
        with patch('sys.argv', ['rflogs', 'upload', non_existent_dir]):
            main()
    
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Error: No Robot Framework test results found" in captured.out

def test_upload_files_custom_filenames(mock_session, mock_requests_post, mock_environment):
    result = upload_files(TEST_DATA_DIR, output="custom_output.xml", log="custom_log.html", report="custom_report.html")
    
    assert result == True
    assert mock_requests_post.call_count == 4  # One for creating run, three for uploading files
    
    # Check that the correct data was sent in the POST request
    run_data = mock_requests_post.call_args_list[0][1]['json']
    
    # Check if start_time and end_time are present in the run_data
    assert 'start_time' in run_data, "start_time is missing from run_data"
    assert 'end_time' in run_data, "end_time is missing from run_data"
    
    # If they are present, check if they are strings
    if run_data['start_time'] is not None:
        assert isinstance(run_data['start_time'], str), "start_time should be a string"
    if run_data['end_time'] is not None:
        assert isinstance(run_data['end_time'], str), "end_time should be a string"

    # Check that file uploads were called
    uploaded_files = []
    for call in mock_requests_post.call_args_list[1:]:  # Skip the first call (run creation)
        files = call[1].get('files', {})
        if files:
            file_data = list(files.values())[0]
            file_name = file_data[0] if isinstance(file_data, tuple) else 'file'
            uploaded_files.append(file_name)

    # Check specific file uploads
    assert 'custom_output.xml' in uploaded_files, "custom_output.xml was not uploaded"
    assert 'custom_log.html' in uploaded_files, "custom_log.html was not uploaded"
    assert 'custom_report.html' in uploaded_files, "custom_report.html was not uploaded"

    # Print debug information
    print("Uploaded files:", uploaded_files)
    for i, call in enumerate(mock_requests_post.call_args_list):
        print(f"Call {i}:", call)