// Canvas 2D reactive orb. setState(state) picks the palette/behaviour;
// feed(level) (0..1) drives radius for listening/speaking reactivity.

const PALETTE = {
  idle:      ['#3fd0ff', '#0a6e7a'],
  listening: ['#19e3b1', '#0b6b55'],
  thinking:  ['#f5a623', '#8a4bd6'],
  speaking:  ['#b388ff', '#7c4dff'],
  error:     ['#ff5252', '#7a1414'],
};

export class Orb {
  constructor(canvas) {
    this.cv = canvas;
    this.ctx = canvas.getContext('2d');
    this.state = 'idle';
    this.level = 0;
    this.t = 0;
    this.shake = 0;
    this._resize();
    window.addEventListener('resize', () => this._resize());
    requestAnimationFrame((ts) => this._loop(ts));
  }

  _resize() {
    const dpr = window.devicePixelRatio || 1;
    this.cv.width = this.cv.clientWidth * dpr;
    this.cv.height = this.cv.clientHeight * dpr;
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  setState(s) {
    this.state = s;
    if (s === 'error') this.shake = 1;
    if (s !== 'listening' && s !== 'speaking') this.level = 0;
  }

  feed(level) { this.level = level || 0; }

  _loop() {
    const ctx = this.ctx;
    const W = this.cv.clientWidth, H = this.cv.clientHeight;
    this.t += 1 / 60;
    ctx.clearRect(0, 0, W, H);

    let cx = W / 2, cy = H / 2;
    if (this.shake > 0) {
      cx += (Math.random() - 0.5) * 24 * this.shake;
      cy += (Math.random() - 0.5) * 24 * this.shake;
      this.shake = Math.max(0, this.shake - 0.03);
    }

    const base = Math.min(W, H) * 0.24;
    let r = base;
    if (this.state === 'idle') {
      r = base * (1 + 0.05 * Math.sin(this.t * 1.4));
    } else if (this.state === 'listening' || this.state === 'speaking') {
      r = base * (1 + 0.5 * this.level + 0.04 * Math.sin(this.t * 3));
    } else if (this.state === 'thinking') {
      r = base * (1 + 0.06 * Math.sin(this.t * 2));
    }

    const [c1, c2] = PALETTE[this.state] || PALETTE.idle;

    // outer glow
    const g = ctx.createRadialGradient(cx, cy, r * 0.2, cx, cy, r * 1.7);
    g.addColorStop(0, c1);
    g.addColorStop(0.55, c2);
    g.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.arc(cx, cy, r * 1.7, 0, Math.PI * 2); ctx.fill();

    // core
    ctx.globalAlpha = 0.92;
    ctx.fillStyle = c1;
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.fill();
    ctx.globalAlpha = 1;

    // indeterminate ring while thinking
    if (this.state === 'thinking') {
      const a = this.t * 3;
      ctx.lineWidth = base * 0.08;
      ctx.strokeStyle = c2;
      ctx.beginPath();
      ctx.arc(cx, cy, r * 1.28, a, a + Math.PI * 1.2);
      ctx.stroke();
    }

    requestAnimationFrame(() => this._loop());
  }
}
