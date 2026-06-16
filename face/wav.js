// Pure audio helpers — no DOM/WebAudio refs, so they run under `node --test`.

// Downsample mono Float32 PCM from srcRate to dstRate by averaging each output
// window (cheap anti-aliasing). Whisper wants 16 kHz; the mic is usually 48 kHz.
export function downsample(input, srcRate, dstRate) {
  if (dstRate <= 0 || dstRate === srcRate) return input;
  const ratio = srcRate / dstRate;
  const outLen = Math.floor(input.length / ratio);
  const out = new Float32Array(outLen);
  for (let i = 0; i < outLen; i++) {
    const start = Math.floor(i * ratio);
    const end = Math.min(Math.floor((i + 1) * ratio), input.length);
    let sum = 0, n = 0;
    for (let j = start; j < end; j++) { sum += input[j]; n++; }
    out[i] = n ? sum / n : 0;
  }
  return out;
}

// Encode mono Float32 PCM [-1,1] as a 16-bit PCM WAV (RIFF). Returns Uint8Array.
export function encodeWav16(samples, sampleRate) {
  const dataLen = samples.length * 2;
  const buffer = new ArrayBuffer(44 + dataLen);
  const dv = new DataView(buffer);
  const writeStr = (o, s) => { for (let i = 0; i < s.length; i++) dv.setUint8(o + i, s.charCodeAt(i)); };
  writeStr(0, 'RIFF');
  dv.setUint32(4, 36 + dataLen, true);
  writeStr(8, 'WAVE');
  writeStr(12, 'fmt ');
  dv.setUint32(16, 16, true);              // fmt chunk size
  dv.setUint16(20, 1, true);               // audio format = PCM
  dv.setUint16(22, 1, true);               // channels = mono
  dv.setUint32(24, sampleRate, true);
  dv.setUint32(28, sampleRate * 2, true);  // byte rate (mono * 16-bit)
  dv.setUint16(32, 2, true);               // block align
  dv.setUint16(34, 16, true);              // bits per sample
  writeStr(36, 'data');
  dv.setUint32(40, dataLen, true);
  let o = 44;
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    dv.setInt16(o, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    o += 2;
  }
  return new Uint8Array(buffer);
}
