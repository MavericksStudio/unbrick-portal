import base64

def describe_with_claude(escalator_client, model, jpeg_bytes, query):
    b64 = base64.b64encode(jpeg_bytes).decode()
    resp = escalator_client.messages.create(
        model=model, max_tokens=200,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64",
             "media_type": "image/jpeg", "data": b64}},
            {"type": "text", "text": query or "Briefly describe what you see."},
        ]}],
    )
    return "".join(getattr(b, "text", "") for b in resp.content).strip()
