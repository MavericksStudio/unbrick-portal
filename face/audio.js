// Mic capture (-> 16k WAV), TTS playback (-> level for the orb), and on-demand
// single-frame camera capture. All WebAudio/DOM; verified on-device.
import { downsample, encodeWav16 } from './wav.js';

export class AudioIO {
  constructor() { this.ac = null; this._cap = null; }

  _ctx() {
    if (!this.ac) this.ac = new (window.AudioContext || window.webkitAudioContext)();
    return this.ac;
  }

  async resume() {
    const ac = this._ctx();
    if (ac.state !== 'running') await ac.resume();
  }

  // Begin mic capture. onLevel(0..1) fires per audio block. Returns a stop()
  // that ends capture and yields a 16 kHz mono 16-bit WAV (Uint8Array).
  async startCapture(onLevel) {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const ac = this._ctx();
    await this.resume();
    const src = ac.createMediaStreamSource(stream);
    const analyser = ac.createAnalyser();
    analyser.fftSize = 512;
    src.connect(analyser);

    const node = ac.createScriptProcessor(4096, 1, 1);
    const mute = ac.createGain();
    mute.gain.value = 0;                 // avoid feeding mic to the speakers
    src.connect(node);
    node.connect(mute);
    mute.connect(ac.destination);

    const chunks = [];
    let total = 0;
    const lvlBuf = new Float32Array(analyser.fftSize);
    node.onaudioprocess = (e) => {
      const ch = e.inputBuffer.getChannelData(0);
      chunks.push(new Float32Array(ch));
      total += ch.length;
      analyser.getFloatTimeDomainData(lvlBuf);
      let peak = 0;
      for (const v of lvlBuf) peak = Math.max(peak, Math.abs(v));
      onLevel && onLevel(Math.min(1, peak * 1.4));
    };

    this._cap = { stream, src, node, mute, analyser, chunks,
                  getTotal: () => total, srcRate: ac.sampleRate };
    return () => this._stopCapture();
  }

  _stopCapture() {
    const c = this._cap;
    if (!c) return new Uint8Array();
    c.node.onaudioprocess = null;
    c.node.disconnect(); c.mute.disconnect(); c.analyser.disconnect(); c.src.disconnect();
    c.stream.getTracks().forEach((t) => t.stop());
    const all = new Float32Array(c.getTotal());
    let o = 0;
    for (const ch of c.chunks) { all.set(ch, o); o += ch.length; }
    this._cap = null;
    const ds = downsample(all, c.srcRate, 16000);
    return encodeWav16(ds, 16000);
  }

  // Decode+play MP3 bytes; onLevel(0..1) drives the speaking orb; onEnded on finish.
  async play(mp3Bytes, onLevel, onEnded) {
    const ac = this._ctx();
    await this.resume();
    const arr = mp3Bytes.buffer.slice(
      mp3Bytes.byteOffset, mp3Bytes.byteOffset + mp3Bytes.byteLength);
    const audioBuf = await ac.decodeAudioData(arr);
    const node = ac.createBufferSource();
    node.buffer = audioBuf;
    const analyser = ac.createAnalyser();
    analyser.fftSize = 512;
    node.connect(analyser);
    analyser.connect(ac.destination);
    const buf = new Float32Array(analyser.fftSize);
    let raf;
    const tick = () => {
      analyser.getFloatTimeDomainData(buf);
      let peak = 0;
      for (const v of buf) peak = Math.max(peak, Math.abs(v));
      onLevel && onLevel(Math.min(1, peak * 1.4));
      raf = requestAnimationFrame(tick);
    };
    node.onended = () => {
      cancelAnimationFrame(raf);
      onLevel && onLevel(0);
      onEnded && onEnded();
    };
    tick();
    node.start();
  }

  // On-demand: open camera, grab ONE downscaled JPEG, release the camera.
  async captureFrame() {
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia(
        { video: { width: 320, height: 240 } });
    } catch (_) {
      return null;
    }
    try {
      const video = document.createElement('video');
      video.srcObject = stream;
      video.muted = true;
      video.playsInline = true;
      await video.play();
      await new Promise((r) => setTimeout(r, 250)); // let a frame land
      const canvas = document.createElement('canvas');
      canvas.width = 320; canvas.height = 240;
      canvas.getContext('2d').drawImage(video, 0, 0, 320, 240);
      const blob = await new Promise((res) => canvas.toBlob(res, 'image/jpeg', 0.6));
      return new Uint8Array(await blob.arrayBuffer());
    } finally {
      stream.getTracks().forEach((t) => t.stop());  // camera OFF
    }
  }
}
