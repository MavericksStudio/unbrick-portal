import { Orb } from './orb.js';
import { Bus, b64ToBytes } from './ws.js';
import { AudioIO } from './audio.js';

const orb = new Orb(document.getElementById('orb'));
const captionEl = document.getElementById('caption');
const hintEl = document.getElementById('hint');
const statusEl = document.getElementById('status');
const audio = new AudioIO();

// local interaction mode: 'idle' | 'recording' | 'busy' (brain-driven).
let mode = 'idle';
let stopCapture = null;

const bus = new Bus(`ws://${location.hostname}:8765`, onMessage, onStatus);

function setHint(t) { hintEl.textContent = t || ''; }

function onStatus(s) {
  statusEl.textContent =
    s === 'open' ? '' : (s === 'connecting' ? 'connecting…' : 'reconnecting…');
}

async function onMessage(msg) {
  switch (msg.type) {
    case 'state':
      orb.setState(msg.value);
      if (msg.value === 'idle') { mode = 'idle'; setHint('tap to talk'); }
      else if (msg.value === 'thinking' || msg.value === 'speaking') setHint('');
      else if (msg.value === 'error') setHint('');
      break;

    case 'caption':
      captionEl.textContent = msg.text || '';
      break;

    case 'tts_audio':
      orb.setState('speaking');
      try {
        await audio.play(b64ToBytes(msg.data), (l) => orb.feed(l), () => {});
      } catch (_) { /* brain also sends idle */ }
      break;

    case 'request_frame': {
      setHint('👁 looking…');
      const jpeg = await audio.captureFrame();
      setHint('');
      bus.sendFrame(jpeg || new Uint8Array());  // empty -> brain says "no picture"
      break;
    }
  }
}

async function onTap() {
  await audio.resume();                    // first-gesture AudioContext unlock
  if (mode === 'idle') {
    mode = 'recording';
    orb.setState('listening');
    setHint('listening — tap to send');
    bus.sendPtt();
    try {
      stopCapture = await audio.startCapture((l) => orb.feed(l));
    } catch (_) {
      mode = 'idle';
      setHint('mic blocked — check permissions');
    }
  } else if (mode === 'recording' && stopCapture) {
    mode = 'busy';
    const wav = stopCapture();
    stopCapture = null;
    setHint('');
    bus.sendAudio(wav);                    // brain drives thinking/speaking/idle
  }
  // taps ignored while 'busy'
}

document.body.addEventListener('click', onTap);
setHint('tap to talk');
