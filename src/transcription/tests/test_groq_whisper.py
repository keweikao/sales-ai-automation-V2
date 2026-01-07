"""
Tests for Groq Whisper Pipeline Integration

Usage:
    export GROQ_API_KEY="your-api-key"
    pytest tests/test_groq_whisper.py -v
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock


class TestGroqWhisperPipeline:
    """Test suite for Groq Whisper transcription pipeline"""

    def test_import_groq_pipeline(self):
        """Test that GroqWhisperPipeline can be imported"""
        from transcription.groq_whisper_pipeline import GroqWhisperPipeline
        assert GroqWhisperPipeline is not None

    def test_pipeline_initialization_requires_api_key(self):
        """Test that pipeline requires API key"""
        from transcription.groq_whisper_pipeline import GroqWhisperPipeline

        with pytest.raises(ValueError, match="GROQ_API_KEY is required"):
            GroqWhisperPipeline(api_key=None)

    def test_pipeline_initialization_with_api_key(self):
        """Test that pipeline initializes correctly with API key"""
        from transcription.groq_whisper_pipeline import GroqWhisperPipeline

        pipeline = GroqWhisperPipeline(api_key="test-key-123")
        assert pipeline.model_name == "whisper-large-v3-turbo"
        assert pipeline.max_file_size_mb == 24
        assert pipeline.chunk_duration == 600

    @patch('transcription.groq_whisper_pipeline.storage.Client')
    @patch('transcription.groq_whisper_pipeline.Groq')
    def test_transcribe_local_file(self, mock_groq_class, mock_storage_class):
        """Test transcription of local audio file"""
        from transcription.groq_whisper_pipeline import GroqWhisperPipeline

        # Mock Groq client
        mock_groq = MagicMock()
        mock_groq_class.return_value = mock_groq

        # Mock transcription response
        mock_response = MagicMock()
        mock_response.text = "這是測試轉錄文字"
        mock_groq.audio.transcriptions.create.return_value = mock_response

        # Mock subprocess for duration check
        with patch('subprocess.check_output', return_value=b'120.5\n12345678'):
            pipeline = GroqWhisperPipeline(api_key="test-key")

            # Test with mock local file
            with patch('builtins.open', create=True) as mock_open:
                with patch('os.path.getsize', return_value=10 * 1024 * 1024):  # 10MB
                    result = pipeline.transcribe("/tmp/test.mp3")

            assert result["success"] is True
            assert "這是測試轉錄文字" in result["full_text"]
            assert result["audio_info"]["duration"] == 120.5
            assert result["segments"] == []
            assert result["speakers"] == []

    @patch('transcription.groq_whisper_pipeline.storage.Client')
    @patch('transcription.groq_whisper_pipeline.Groq')
    def test_transcribe_gcs_file(self, mock_groq_class, mock_storage_class):
        """Test transcription of GCS audio file"""
        from transcription.groq_whisper_pipeline import GroqWhisperPipeline

        # Mock Storage client
        mock_storage = MagicMock()
        mock_storage_class.return_value = mock_storage
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_storage.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        # Mock Groq client
        mock_groq = MagicMock()
        mock_groq_class.return_value = mock_groq
        mock_response = MagicMock()
        mock_response.text = "GCS 音檔轉錄成功"
        mock_groq.audio.transcriptions.create.return_value = mock_response

        with patch('subprocess.check_output', return_value=b'180.0\n12345678'):
            with patch('builtins.open', create=True):
                with patch('os.path.getsize', return_value=8 * 1024 * 1024):
                    pipeline = GroqWhisperPipeline(api_key="test-key")
                    result = pipeline.transcribe("gs://test-bucket/audio.mp3")

        assert result["success"] is True
        assert "GCS 音檔轉錄成功" in result["full_text"]
        mock_blob.download_to_filename.assert_called_once()

    @patch('transcription.groq_whisper_pipeline.storage.Client')
    @patch('transcription.groq_whisper_pipeline.Groq')
    def test_chunking_for_large_files(self, mock_groq_class, mock_storage_class):
        """Test that large files are automatically chunked"""
        from transcription.groq_whisper_pipeline import GroqWhisperPipeline

        mock_groq = MagicMock()
        mock_groq_class.return_value = mock_groq
        mock_response = MagicMock()
        mock_response.text = "Chunk transcription"
        mock_groq.audio.transcriptions.create.return_value = mock_response

        # Mock a 30-minute file (> 10 min chunk duration)
        with patch('subprocess.check_output', return_value=b'1800.0\n50000000'):  # 30 min, 50MB
            with patch('subprocess.run'):  # Mock ffmpeg
                with patch('builtins.open', create=True):
                    with patch('os.path.getsize', return_value=50 * 1024 * 1024):  # 50MB
                        pipeline = GroqWhisperPipeline(api_key="test-key")
                        result = pipeline.transcribe("/tmp/large.mp3")

        # Should create multiple chunks
        assert result["audio_info"]["num_chunks"] >= 2

    def test_get_pipeline_factory_groq(self):
        """Test that get_pipeline factory creates GroqWhisperPipeline"""
        from transcription.pipeline import get_pipeline

        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
            pipeline = get_pipeline(engine="groq_whisper")

            from transcription.groq_whisper_pipeline import GroqWhisperPipeline
            assert isinstance(pipeline, GroqWhisperPipeline)

    def test_error_handling_missing_api_key(self):
        """Test error handling when API key is missing"""
        from transcription.pipeline import get_pipeline

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="GROQ_API_KEY is required"):
                get_pipeline(engine="groq_whisper")


@pytest.mark.integration
class TestGroqWhisperIntegration:
    """Integration tests requiring real Groq API key"""

    @pytest.fixture
    def api_key(self):
        """Get API key from environment"""
        key = os.getenv("GROQ_API_KEY")
        if not key:
            pytest.skip("GROQ_API_KEY not set, skipping integration test")
        return key

    @pytest.fixture
    def pipeline(self, api_key):
        """Create pipeline instance"""
        from transcription.groq_whisper_pipeline import GroqWhisperPipeline
        return GroqWhisperPipeline(api_key=api_key)

    def test_real_transcription_short_file(self, pipeline, tmp_path):
        """Test real transcription with a short audio file"""
        # This test requires a real audio file
        # Skip if test audio not available
        test_audio = os.getenv("TEST_AUDIO_PATH")
        if not test_audio:
            pytest.skip("TEST_AUDIO_PATH not set")

        result = pipeline.transcribe(test_audio)

        assert result["success"] is True
        assert len(result["full_text"]) > 0
        assert result["audio_info"]["duration"] > 0
        assert result["audio_info"]["processing_time"] > 0

        # Speed should be > 100x realtime for short files
        speed_ratio = result["audio_info"]["duration"] / result["audio_info"]["processing_time"]
        assert speed_ratio > 100, f"Speed ratio {speed_ratio:.1f}x is too slow"

        print(f"\n✓ Transcription successful:")
        print(f"  Duration: {result['audio_info']['duration']:.1f}s")
        print(f"  Processing: {result['audio_info']['processing_time']:.1f}s")
        print(f"  Speed: {speed_ratio:.1f}x realtime")
        print(f"  Text length: {len(result['full_text'])} chars")
        print(f"  Preview: {result['full_text'][:200]}...")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
