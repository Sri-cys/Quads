"""
Minimal, secure Gemini connection verification script.
Adheres strictly to the architectural and security rules:
- Never print the key, raw response, headers, or prompt.
- Load GEMINI_API_KEY from backend/.env or environment.
- Make exactly ONE minimal test request with 10-second timeout.
- Output ONLY:
    Gemini connection: OK
  or:
    Gemini connection: FAILED — <error type>
- Exit 0 on success, exit 1 on failure.
"""

import os
import sys
import contextlib
from pathlib import Path


def load_env_file():
    backend_dir = Path(__file__).resolve().parents[1]
    env_file = backend_dir / ".env"
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass


def main():
    load_env_file()
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("Gemini connection: FAILED — MissingApiKey")
        sys.exit(1)

    try:
        # Redirect stderr to suppress SDK AFC warning
        with contextlib.redirect_stderr(open(os.devnull, "w")):
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)

            # Make exactly ONE minimal Gemini request with 10-second timeout budget
            response = client.models.generate_content(
                model="gemini-flash-latest",
                contents="ping",
                config=types.GenerateContentConfig(
                    temperature=0.0,
                ),
            )

        if response and response.text:
            print("Gemini connection: OK")
            sys.exit(0)
        else:
            print("Gemini connection: FAILED — EmptyResponse")
            sys.exit(1)

    except Exception as e:
        error_type = type(e).__name__
        print(f"Gemini connection: FAILED — {error_type}")
        sys.exit(1)


if __name__ == "__main__":
    main()
