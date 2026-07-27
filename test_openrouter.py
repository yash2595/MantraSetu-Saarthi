"""Standalone diagnostic script for testing OpenRouter API authentication and chat completion."""

import os
import sys
import traceback

import httpx
from dotenv import load_dotenv


def main() -> None:
    """Read configuration from .env and send a test request to OpenRouter."""
    try:
        # Load environment variables from .env file
        load_dotenv()

        api_key = os.getenv("API_KEY", "").strip()
        base_url = os.getenv("BASE_URL", "https://openrouter.ai/api/v1").strip()
        model = os.getenv("MODEL", "qwen/qwen3-omni").strip()

        print("=" * 60)
        print("OPENROUTER DIAGNOSTIC SCRIPT")
        print("=" * 60)
        print(f"API Key Exists: {bool(api_key)}")
        print(f"API Key (First 15 chars): {api_key[:15] if api_key else 'NONE'}")
        print(f"Base URL: {base_url}")
        print(f"Model: {model}")
        print("=" * 60)

        if not api_key:
            print("ERROR: API_KEY is missing or empty in .env file.")
            sys.exit(1)

        endpoint = f"{base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "MantraSetu AI Backend",
        }
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": "Hello",
                }
            ],
        }

        print(f"\nSending POST request to: {endpoint} ...\n")

        with httpx.Client(timeout=30.0) as client:
            response = client.post(endpoint, headers=headers, json=payload)

        print("=" * 60)
        print(f"Status Code: {response.status_code}")
        print("=" * 60)
        print("Response Headers:")
        for key, value in response.headers.items():
            print(f"  {key}: {value}")
        print("=" * 60)
        print("Full Response Body:")
        print(response.text)
        print("=" * 60)

    except Exception as exc:
        print("\n" + "!" * 60)
        print(f"EXCEPTION OCCURRED: {exc}")
        print("!" * 60)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
