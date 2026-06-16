import base64, requests
from brain.chat import API_URL, _headers, _extract_text

def describe_with_claude(api_key, model, jpeg_bytes, query, timeout=60):
    b64 = base64.b64encode(jpeg_bytes).decode()
    r = requests.post(
        API_URL,
        headers=_headers(api_key),
        json={
            "model": model,
            "max_tokens": 200,
            "messages": [{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64",
                 "media_type": "image/jpeg", "data": b64}},
                {"type": "text", "text": query or "Briefly describe what you see."},
            ]}],
        },
        timeout=timeout,
    )
    r.raise_for_status()
    return _extract_text(r.json())
