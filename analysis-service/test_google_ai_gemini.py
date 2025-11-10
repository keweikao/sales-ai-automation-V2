import os
import google.generativeai as genai

MODEL_NAME = "gemini-pro-latest" # Using the generic name
API_KEY = os.getenv("GEMINI_API_KEY")

def test_google_ai_gemini():
    print(f"Testing Google AI Gemini API connectivity...")
    print(f"Model: {MODEL_NAME}")

    if not API_KEY:
        print("FAILURE: GEMINI_API_KEY environment variable is not set.")
        return False

    try:
        genai.configure(api_key=API_KEY)

        # First, list available models
        print("\nListing available models for this API Key:")
        found_gemini_pro = False
        for m in genai.list_models():
            if "generateContent" in m.supported_generation_methods:
                print(f"- {m.name} (supported for generateContent)")
                if m.name == f"models/{MODEL_NAME}":
                    found_gemini_pro = True
            else:
                print(f"- {m.name} (NOT supported for generateContent)")

        if not found_gemini_pro:
            print(f"\nWARNING: '{MODEL_NAME}' was not found or does not support 'generateContent' for this API Key.")
            print("Please ensure the API Key has access to Gemini Pro and the Generative Language API is enabled.")
            return False

        # If found, proceed with content generation
        model = genai.GenerativeModel(MODEL_NAME)
        
        response = model.generate_content("Hello, Google AI Gemini!")
        
        if response.text:
            print(f"\nSUCCESS: Successfully called Google AI Gemini API with '{MODEL_NAME}'.")
            print(f"Response: {response.text[:100]}...")
            return True
        else:
            print(f"\nFAILURE: Google AI Gemini API call returned empty response for '{MODEL_NAME}'.")
            return False
    except Exception as e:
        print(f"\nFAILURE: Error calling Google AI Gemini API: {e}")
        return False

if __name__ == "__main__":
    test_google_ai_gemini()
