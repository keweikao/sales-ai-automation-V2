import os
import logging
from google.cloud import speech_v2
from google.cloud.speech_v2.types import cloud_speech
from google.api_core import exceptions as gapi_exceptions
from google.api_core.client_options import ClientOptions

logging.basicConfig(level=logging.INFO)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/stephen/Desktop/sales-ai-automation-V2/sales-ai-automation-v2-85d6460d778e.json"

project_id = "sales-ai-automation-v2"
location = "us"
recognizer_id = "test-recognizer-v2-chirp3-no-diar"

client = speech_v2.SpeechClient(
    client_options=ClientOptions(
        api_endpoint=f"{location}-speech.googleapis.com"
    )
)
parent = f"projects/{project_id}/locations/{location}"

# 1. Create recognizer WITHOUT diarization
request = cloud_speech.CreateRecognizerRequest(
    parent=parent,
    recognizer_id=recognizer_id,
    recognizer=cloud_speech.Recognizer(
        default_recognition_config=cloud_speech.RecognitionConfig(
            auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
            language_codes=["cmn-Hant-TW", "en-US"],
            model="chirp_3",
            features=cloud_speech.RecognitionFeatures(
                enable_word_time_offsets=True,
                enable_automatic_punctuation=True,
            ),
        )
    ),
)

try:
    print("Creating recognizer...")
    operation = client.create_recognizer(request=request)
    operation.result(timeout=60)
    recognizer_path = f"{parent}/recognizers/{recognizer_id}"
    print(f"Recognizer created: {recognizer_path}")

    # 2. Try BatchRecognize with diarization override
    print("Testing BatchRecognize with diarization override...")
    
    # Check if config field exists in constructor
    try:
        batch_request = cloud_speech.BatchRecognizeRequest(
            recognizer=recognizer_path,
            files=[cloud_speech.BatchRecognizeFileMetadata(uri="gs://sales-ai-audio-bucket/dummy.m4a")],
            recognition_output_config=cloud_speech.RecognitionOutputConfig(
                inline_response_config=cloud_speech.InlineOutputConfig()
            ),
            config=cloud_speech.RecognitionConfig(
                features=cloud_speech.RecognitionFeatures(
                    diarization_config=cloud_speech.SpeakerDiarizationConfig(
                        min_speaker_count=2,
                        max_speaker_count=4,
                    )
                )
            )
        )
        print("BatchRecognizeRequest with config created successfully!")
    except TypeError as e:
        print(f"BatchRecognizeRequest failed: {e}")

finally:
    try:
        client.delete_recognizer(name=f"{parent}/recognizers/{recognizer_id}")
        print("Recognizer deleted.")
    except:
        pass
