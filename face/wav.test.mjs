import { test } from 'node:test';
import assert from 'node:assert/strict';
import { downsample, encodeWav16 } from './wav.js';

test('downsample reduces length by the rate ratio', () => {
  const src = new Float32Array(48000).fill(0.5); // 1s @ 48k
  const out = downsample(src, 48000, 16000);
  assert.ok(Math.abs(out.length - 16000) <= 1);
});

test('downsample is a passthrough when rates match', () => {
  const src = new Float32Array([0.1, 0.2, 0.3]);
  const out = downsample(src, 16000, 16000);
  assert.deepEqual(Array.from(out), Array.from(src));
});

test('encodeWav16 writes a valid 16k mono PCM header', () => {
  const pcm = new Float32Array(16000); // 1s of silence
  const bytes = encodeWav16(pcm, 16000);
  const dv = new DataView(bytes.buffer);
  const tag = (o) => String.fromCharCode(bytes[o], bytes[o + 1], bytes[o + 2], bytes[o + 3]);
  assert.equal(tag(0), 'RIFF');
  assert.equal(tag(8), 'WAVE');
  assert.equal(tag(12), 'fmt ');
  assert.equal(dv.getUint16(20, true), 1);       // PCM
  assert.equal(dv.getUint16(22, true), 1);       // mono
  assert.equal(dv.getUint32(24, true), 16000);   // sample rate
  assert.equal(dv.getUint16(34, true), 16);      // bits/sample
  assert.equal(tag(36), 'data');
  assert.equal(dv.getUint32(40, true), 16000 * 2); // data length
  assert.equal(bytes.length, 44 + 16000 * 2);
});

test('encodeWav16 clamps and converts amplitude', () => {
  const pcm = new Float32Array([1.0, -1.0, 2.0, -2.0, 0]);
  const dv = new DataView(encodeWav16(pcm, 16000).buffer);
  assert.equal(dv.getInt16(44, true), 32767);    // +1.0 -> max
  assert.equal(dv.getInt16(46, true), -32768);   // -1.0 -> min
  assert.equal(dv.getInt16(48, true), 32767);    // clamp > 1
  assert.equal(dv.getInt16(50, true), -32768);   // clamp < -1
  assert.equal(dv.getInt16(52, true), 0);
});
