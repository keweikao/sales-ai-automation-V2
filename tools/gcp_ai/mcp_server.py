#!/usr/bin/env python3
"""
Custom MCP Server for Google Gemini API

Provides tools to interact with the Gemini API using an API key.
"""
import sys
import json
import os
from typing import Any, Dict, List

try:
    import google.generativeai as genai
except ImportError:
    genai = None

def configure_genai():
    """Configures the Gemini API with the API key."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set.")
    genai.configure(api_key=api_key)

def list_models() -> Dict[str, Any]:
    """Lists available Gemini models."""
    if genai is None:
        return {"error": "google-generativeai library not installed."}
    try:
        configure_genai()
        models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                models.append({"name": m.name, "description": m.description})
        return {"models": models}
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}

def generate_content(prompt: str, model: str = "gemini-pro") -> Dict[str, Any]:
    """
    Generates content using the specified Gemini model.

    Args:
        prompt: The text prompt to send to the model.
        model: The model to use for generation (e.g., "gemini-pro").

    Returns:
        A dictionary containing the generated text or an error.
    """
    if genai is None:
        return {"error": "google-generativeai library not installed."}

    try:
        configure_genai()
        model_instance = genai.GenerativeModel(model)
        response = model_instance.generate_content(prompt)
        return {"text": response.text}
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}

# MCP Protocol Handler
def handle_request(request: dict) -> dict:
    method = request.get("method")

    if method == "tools/list":
        return {
            "tools": [
                {
                    "name": "generate_content",
                    "description": "Generates content using the Google Gemini API.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "prompt": {"type": "string", "description": "The text prompt to send to the model."},
                            "model": {"type": "string", "description": "The model to use for generation.", "default": "gemini-pro"}
                        },
                        "required": ["prompt"]
                    }
                },
                {
                    "name": "list_models",
                    "description": "Lists available models for content generation.",
                    "inputSchema": {"type": "object", "properties": {}}
                }
            ]
        }

    elif method == "tools/call":
        tool_name = request["params"]["name"]
        arguments = request["params"]["arguments"]

        if tool_name == "generate_content":
            return generate_content(**arguments)
        elif tool_name == "list_models":
            return list_models()
        else:
            return {"error": f"Unknown tool: {tool_name}"}

    else:
        return {"error": f"Unknown method: {method}"}

if __name__ == "__main__":
    for line in sys.stdin:
        try:
            request = json.loads(line)
            response = handle_request(request)
            print(json.dumps(response, ensure_ascii=False))
            sys.stdout.flush()
        except Exception as e:
            error_response = {"error": str(e)}
            print(json.dumps(error_response, ensure_ascii=False))
            sys.stdout.flush()