import asyncio, base64, json, sys, websockets

async def main(wav_path):
    blob = open(wav_path, "rb").read()
    async with websockets.connect("ws://127.0.0.1:8765") as ws:
        await ws.send(json.dumps({"type": "ptt", "state": "start"}))
        await ws.send(json.dumps({"type": "audio",
                                  "data": base64.b64encode(blob).decode()}))
        got_caption = got_audio = False
        for _ in range(20):
            m = json.loads(await asyncio.wait_for(ws.recv(), timeout=120))
            print("<<", m.get("type"), m.get("value", m.get("text", "")[:60]))
            if m["type"] == "caption": got_caption = True
            if m["type"] == "tts_audio": got_audio = True
            if m["type"] == "state" and m["value"] == "idle" and got_caption:
                break
        assert got_caption and got_audio, "missing caption or audio"
        print("SMOKE OK")

asyncio.run(main(sys.argv[1]))
