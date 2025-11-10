import os
import vertexai
from vertexai.generative_models import GenerativeModel

GCP_PROJECT = os.environ.get("GCP_PROJECT", "sales-ai-automation-v2")
GCP_LOCATION = os.environ.get("GCP_LOCATION", "asia-east1")
MODEL_NAME = "gemini-pro"

def test_vertex_ai_gemini():
    print(f"Testing Vertex AI Gemini API connectivity...")
    print(f"Project: {GCP_PROJECT}, Location: {GCP_LOCATION}, Model: {MODEL_NAME}")

    try:
        vertexai.init(project=GCP_PROJECT, location=GCP_LOCATION)
        model = GenerativeModel(MODEL_NAME)
        
        response = model.generate_content("Hello, Gemini!")
        
        if response.text:
            print(f"SUCCESS: Successfully called Vertex AI Gemini API.")
            print(f"Response: {response.text[:100]}...")
            return True
        else:
            print(f"FAILURE: Vertex AI Gemini API call returned empty response.")
            return False
    except Exception as e:
        print(f"FAILURE: Error calling Vertex AI Gemini API: {e}")
        return False

if __name__ == "__main__":
    test_vertex_ai_gemini()
