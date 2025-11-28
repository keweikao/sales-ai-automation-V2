import unittest
from unittest.mock import MagicMock, patch
import json
import os
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

# Set env vars before importing main
os.environ["TRANSCRIPTION_ENGINE"] = "gemini"
os.environ["GCP_PROJECT_ID"] = "test-project"

# Mock imports that might fail or have side effects
with patch.dict('sys.modules', {
    'google.cloud': MagicMock(),
    'google.cloud.storage': MagicMock(),
    'google.cloud.firestore': MagicMock(),
    'google.cloud.tasks_v2': MagicMock(),
    'src.transcription.gemini_pipeline': MagicMock(),
}):
    from transcription import main

class TestTranscriptionPersistence(unittest.TestCase):

    def setUp(self):
        self.app = main.flask_app.test_client()
        self.app.testing = True
        
        # Reset mocks
        main.storage_client = MagicMock()
        main.pipeline = MagicMock()
        main.status_tracker = MagicMock()

    @patch('src.transcription.main.storage_client')
    @patch('src.transcription.main.get_pipeline')
    def test_persistence_resume(self, mock_get_pipeline, mock_storage_client):
        """Test that existing JSON in GCS is used (Resume)."""
        
        # Setup mocks
        mock_pipeline = MagicMock()
        mock_get_pipeline.return_value = mock_pipeline
        
        mock_bucket = MagicMock()
        mock_storage_client.bucket.return_value = mock_bucket
        
        mock_blob_audio = MagicMock()
        mock_blob_json = MagicMock()
        
        # Simulate audio blob exists
        def blob_side_effect(name):
            if name.endswith('.m4a'):
                return mock_blob_audio
            if name.endswith('.json'):
                return mock_blob_json
            return MagicMock()
            
        mock_bucket.blob.side_effect = blob_side_effect
        
        # Simulate JSON exists
        mock_blob_json.exists.return_value = True
        mock_blob_json.download_as_text.return_value = json.dumps({
            "text": "Cached transcript",
            "segments": [],
            "success": True
        })
        
        # Make request
        payload = {
            "gcs_uri": "gs://test-bucket/audio.m4a",
            "caseId": "test-case"
        }
        response = self.app.post('/transcribe', json=payload)
        
        # Verify
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['text'], "Cached transcript")
        
        # Verify pipeline was NOT called
        mock_pipeline.transcribe.assert_not_called()
        mock_pipeline.process_audio.assert_not_called()
        
        # Verify JSON was loaded
        mock_blob_json.download_as_text.assert_called_once()

    @patch('src.transcription.main.logger')
    @patch('src.transcription.main.storage_client')
    @patch('src.transcription.main.get_pipeline')
    def test_persistence_save(self, mock_get_pipeline, mock_storage_client, mock_logger):
        """Test that new result is saved to GCS."""
        
        # Setup mocks
        mock_pipeline = MagicMock()
        mock_get_pipeline.return_value = mock_pipeline
        
        mock_bucket = MagicMock()
        mock_storage_client.bucket.return_value = mock_bucket
        
        mock_blob_audio = MagicMock()
        mock_blob_json = MagicMock()
        
        mock_bucket.blob.side_effect = lambda name: mock_blob_json if name.endswith('.json') else mock_blob_audio
        
        # Simulate JSON does NOT exist
        mock_blob_json.exists.return_value = False
        
        # Simulate Pipeline success
        mock_pipeline.transcribe.return_value = {
            "text": "New transcript",
            "segments": [],
            "success": True
        }
        
        # Make request
        payload = {
            "gcs_uri": "gs://test-bucket/audio.m4a",
            "caseId": "test-case"
        }
        response = self.app.post('/transcribe', json=payload)
        
        # Verify
        if response.status_code != 200:
            print(f"Test failed with status {response.status_code}. Response: {response.get_data(as_text=True)}")
            print("Logger error calls:")
            for call in mock_logger.error.call_args_list:
                print(call)
                
        self.assertEqual(response.status_code, 200)
        
        # Verify pipeline WAS called
        mock_pipeline.transcribe.assert_called_once()
        
        # Verify JSON was SAVED
        mock_blob_json.upload_from_string.assert_called_once()
        args, _ = mock_blob_json.upload_from_string.call_args
        saved_json = json.loads(args[0])
        self.assertEqual(saved_json['text'], "New transcript")

if __name__ == '__main__':
    unittest.main()
