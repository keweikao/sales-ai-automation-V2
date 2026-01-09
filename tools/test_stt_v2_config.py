import os
import logging
from google.cloud import speech_v2
from google.cloud.speech_v2.types import cloud_speech
from google.api_core.client_options import ClientOptions

logging.basicConfig(level=logging.INFO)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/stephen/Desktop/sales-ai-automation-V2/sales-ai-automation-v2-85d6460d778e.json"

project_id = "sales-ai-automation-v2"
location = "us"
recognizer_id = "test-recognizer-v2-chirp3-us"

client = speech_v2.SpeechClient(
    client_options=ClientOptions(
        api_endpoint=f"{location}-speech.googleapis.com"
    )
)
parent = f"projects/{project_id}/locations/{location}"

features = cloud_speech.RecognitionFeatures(
    enable_word_time_offsets=True,
    enable_automatic_punctuation=True,
    diarization_config=cloud_speech.SpeakerDiarizationConfig(
        min_speaker_count=2,
        max_speaker_count=4,
    )
)

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

print(f"Submitting CreateRecognizerRequest to {parent}...")
try:
    operation = client.create_recognizer(request=request)
    print("Operation started...")
    operation.result(timeout=60)
    print("Recognizer created successfully!")
except Exception as e:
    print(f"\nCaught exception: {type(e).__name__}: {e}")
    if hasattr(e, 'errors'):
        print(f"Errors metadata: {e.errors}")
    # Try to extract more details if it's a gRPC error
    try:
        # This might be tricky without full proto access, but let's see.
        pass
    except Exception:
        pass
finally:
    # Cleanup if needed
    try:
        client.delete_recognizer(name=f"{parent}/recognizers/{recognizer_id}")
        print("Test recognizer deleted.")
    except Exception:
        pass
