// WebSocket client for the brain. JSON text frames; binary as base64.

export function bytesToB64(bytes) {
  let s = '';
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    s += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
  }
  return btoa(s);
}

export function b64ToBytes(b64) {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

export class Bus {
  constructor(url, onMessage, onStatus) {
    this.url = url;
    this.onMessage = onMessage;
    this.onStatus = onStatus;
    this.ws = null;
    this.backoff = 500;
    this._connect();
  }

  _connect() {
    this.onStatus && this.onStatus('connecting');
    const ws = new WebSocket(this.url);
    this.ws = ws;
    ws.onopen = () => { this.backoff = 500; this.onStatus && this.onStatus('open'); };
    ws.onmessage = (e) => {
      try { this.onMessage(JSON.parse(e.data)); } catch (_) { /* ignore */ }
    };
    ws.onclose = () => { this.onStatus && this.onStatus('closed'); this._retry(); };
    ws.onerror = () => { try { ws.close(); } catch (_) {} };
  }

  _retry() {
    setTimeout(() => this._connect(), this.backoff);
    this.backoff = Math.min(this.backoff * 2, 8000);
  }

  _send(obj) {
    if (this.ws && this.ws.readyState === 1) this.ws.send(JSON.stringify(obj));
  }

  sendPtt() { this._send({ type: 'ptt', state: 'start' }); }
  sendAudio(wavBytes) { this._send({ type: 'audio', data: bytesToB64(wavBytes) }); }
  sendFrame(jpegBytes) { this._send({ type: 'frame', data: bytesToB64(jpegBytes) }); }
}
