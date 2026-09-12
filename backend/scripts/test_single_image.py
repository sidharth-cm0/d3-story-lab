#!/usr/bin/env python3
"""Single-image smoke test for D3 Story Lab.

Tests cloud image generation for exactly ONE test image.
Prints strictly:
  CLOUD SUCCESS
  MIME type: ...
  saved asset path: ...
  model: ...
or:
  CLOUD FAILURE
  category: QUOTA_EXCEEDED / AUTH_ERROR / MODEL_UNAVAILABLE / etc.
  message: ...
  http_status: ...
  google_status: ...
  quota_metric: ...
  model: ...

No secrets or API keys are ever printed.
"""

import os
import sys
import json
import base64
import argparse
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.storyboard.image_provider import _load_env_file, StoryboardAssetStore

_load_env_file()


def run_single_image_test(model: str = None) -> int:
    api_key = (
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or os.environ.get("IMAGEN_API_KEY")
    )
    selected_model = (
        model
        or os.environ.get("STORYBOARD_IMAGE_MODEL")
        or "gemini-3.1-flash-image"
    )

    if not api_key:
        print("CLOUD FAILURE")
        print("category: NO_API_KEY")
        print("message: No GEMINI_API_KEY, GOOGLE_API_KEY, or IMAGEN_API_KEY configured in environment.")
        print(f"model: {selected_model}")
        return 1

    prompt = "A high-contrast noir ink sketch of a rainy alleyway, comic book style, sharp black lines."

    try:
        import httpx

        is_imagen_predict = selected_model.startswith("imagen-")
        if is_imagen_predict:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{selected_model}:predict?key={api_key}"
            payload = {
                "instances": [{"prompt": prompt}],
                "parameters": {
                    "sampleCount": 1,
                    "aspectRatio": "1:1",
                    "outputMimeType": "image/jpeg",
                    "personGeneration": "ALLOW_ADULT",
                },
            }
        else:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{selected_model}:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseModalities": ["image", "text"]},
            }

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, json=payload)
            status_code = resp.status_code

            if status_code == 200:
                data = resp.json()
                raw_bytes = b""
                if is_imagen_predict:
                    predictions = data.get("predictions", [])
                    if predictions and "bytesBase64Encoded" in predictions[0]:
                        raw_bytes = base64.b64decode(predictions[0]["bytesBase64Encoded"])
                else:
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        for part in parts:
                            if "inlineData" in part and "data" in part["inlineData"]:
                                raw_bytes = base64.b64decode(part["inlineData"]["data"])
                                break

                if raw_bytes:
                    mime = "image/png"
                    ext = "png"
                    if raw_bytes.startswith(b"\xff\xd8\xff"):
                        mime = "image/jpeg"
                        ext = "jpg"
                    elif raw_bytes.startswith(b"RIFF") and b"WEBP" in raw_bytes[:12]:
                        mime = "image/webp"
                        ext = "webp"

                    store = StoryboardAssetStore("data/projects")
                    asset_url = store.save_asset(
                        project_id="_smoke_test",
                        category="single_image",
                        filename=f"smoke_single.{ext}",
                        content=raw_bytes,
                    )
                    saved_path = store.get_asset_path("_smoke_test", "single_image", f"smoke_single.{ext}")

                    print("CLOUD SUCCESS")
                    print(f"MIME type: {mime}")
                    print(f"saved asset path: {saved_path}")
                    print(f"model: {selected_model}")
                    return 0
                else:
                    print("CLOUD FAILURE")
                    print("category: INVALID_RESPONSE")
                    print("message: Google API responded with status 200 but returned no image bytes.")
                    print(f"model: {selected_model}")
                    return 1

            elif status_code == 429:
                err_data = {}
                try:
                    err_data = resp.json().get("error", {})
                except Exception:
                    pass
                msg = err_data.get("message", "")
                google_status = err_data.get("status", "RESOURCE_EXHAUSTED")
                metric_lines = [l.strip() for l in msg.split("\n") if "metric:" in l]
                quota_metric = metric_lines[0] if metric_lines else "generativelanguage.googleapis.com/generate_content_free_tier_requests"

                print("CLOUD FAILURE")
                print("category: QUOTA_EXCEEDED")
                print("message: Cloud image generation unavailable because this Google project currently has no usable quota for the selected image model.")
                print(f"http_status: {status_code}")
                print(f"google_status: {google_status}")
                print(f"quota_metric: {quota_metric}")
                print(f"model: {selected_model}")
                return 1

            elif status_code in (401, 403):
                print("CLOUD FAILURE")
                print("category: AUTH_ERROR")
                print("message: Google API authentication failed. Verify API key credentials.")
                print(f"http_status: {status_code}")
                print(f"model: {selected_model}")
                return 1

            elif status_code == 404:
                print("CLOUD FAILURE")
                print("category: MODEL_UNAVAILABLE")
                print(f"message: Model '{selected_model}' is not supported or not found on this API path.")
                print(f"http_status: {status_code}")
                print(f"model: {selected_model}")
                return 1

            else:
                print("CLOUD FAILURE")
                print("category: REQUEST_FAILED")
                print(f"message: Request failed with HTTP {status_code}.")
                print(f"http_status: {status_code}")
                print(f"model: {selected_model}")
                return 1

    except Exception as e:
        print("CLOUD FAILURE")
        print("category: REQUEST_FAILED")
        print(f"message: {str(e)}")
        print(f"model: {selected_model}")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smoke test cloud image generation for single image.")
    parser.add_argument("--model", type=str, default=None, help="Image model override")
    args = parser.parse_args()
    sys.exit(run_single_image_test(model=args.model))
