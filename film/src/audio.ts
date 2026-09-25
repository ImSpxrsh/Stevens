/** Film sound, synthesised with WebAudio so there are no audio files to ship. */
export type Cue = 'whoosh' | 'click' | 'type' | 'chime' | 'drop';

export class Sound {
	enabled = false;
	#ctx: AudioContext | null = null;
	#master: GainNode | null = null;
	#pad: GainNode | null = null;
	#noise: AudioBuffer | null = null;
	#lastType = 0;

	/** Must be called from a user gesture the first time. */
	async setEnabled(on: boolean) {
		this.enabled = on;
		if (on && !this.#ctx) this.#init();
		if (!this.#ctx) return;
		if (on) await this.#ctx.resume();
		const now = this.#ctx.currentTime;
		this.#master!.gain.cancelScheduledValues(now);
		this.#master!.gain.linearRampToValueAtTime(on ? 0.9 : 0, now + 0.4);
	}

	/** Stream of the film's audio, for recording. */
	stream() {
		if (!this.#ctx) this.#init();
		const dest = this.#ctx!.createMediaStreamDestination();
		this.#master!.connect(dest);
		return dest.stream;
	}

	#init() {
		const ctx = (this.#ctx = new AudioContext());
		this.#master = ctx.createGain();
		this.#master.gain.value = 0;
		this.#master.connect(ctx.destination);

		const len = ctx.sampleRate * 1.5;
		this.#noise = ctx.createBuffer(1, len, ctx.sampleRate);
		const data = this.#noise.getChannelData(0);
		for (let i = 0; i < len; i++) data[i] = Math.random() * 2 - 1;

		// Ambient bed: a soft A-major pad through a slow low-pass sweep.
		this.#pad = ctx.createGain();
		this.#pad.gain.value = 0.05;
		const filter = ctx.createBiquadFilter();
		filter.type = 'lowpass';
		filter.frequency.value = 700;
		const lfo = ctx.createOscillator();
		const lfoGain = ctx.createGain();
		lfo.frequency.value = 0.05;
		lfoGain.gain.value = 350;
		lfo.connect(lfoGain).connect(filter.frequency);
		lfo.start();
		for (const [freq, type, detune] of [[110, 'sine', 0], [164.81, 'triangle', 4], [220, 'sine', -5], [277.18, 'sine', 3]] as const) {
			const o = ctx.createOscillator();
			o.type = type;
			o.frequency.value = freq;
			o.detune.value = detune;
			o.connect(filter);
			o.start();
		}
		filter.connect(this.#pad).connect(this.#master);
	}

	play(cue: Cue) {
		if (!this.enabled || !this.#ctx) return;
		const ctx = this.#ctx;
		const t = ctx.currentTime;
		const out = this.#master!;

		if (cue === 'whoosh') {
			const src = ctx.createBufferSource();
			src.buffer = this.#noise;
			const bp = ctx.createBiquadFilter();
			bp.type = 'bandpass';
			bp.Q.value = 0.8;
			bp.frequency.setValueAtTime(250, t);
			bp.frequency.exponentialRampToValueAtTime(2200, t + 0.45);
			bp.frequency.exponentialRampToValueAtTime(500, t + 0.9);
			const g = ctx.createGain();
			g.gain.setValueAtTime(0.0001, t);
			g.gain.exponentialRampToValueAtTime(0.09, t + 0.35);
			g.gain.exponentialRampToValueAtTime(0.0001, t + 0.95);
			src.connect(bp).connect(g).connect(out);
			src.start(t);
			src.stop(t + 1);
		} else if (cue === 'click' || cue === 'drop') {
			const o = ctx.createOscillator();
			const g = ctx.createGain();
			o.type = 'sine';
			o.frequency.setValueAtTime(cue === 'drop' ? 520 : 1500, t);
			o.frequency.exponentialRampToValueAtTime(cue === 'drop' ? 260 : 900, t + 0.05);
			g.gain.setValueAtTime(0.12, t);
			g.gain.exponentialRampToValueAtTime(0.0001, t + (cue === 'drop' ? 0.18 : 0.06));
			o.connect(g).connect(out);
			o.start(t);
			o.stop(t + 0.2);
		} else if (cue === 'type') {
			if (t - this.#lastType < 0.03) return;
			this.#lastType = t;
			const src = ctx.createBufferSource();
			src.buffer = this.#noise;
			const hp = ctx.createBiquadFilter();
			hp.type = 'highpass';
			hp.frequency.value = 2500 + Math.random() * 1500;
			const g = ctx.createGain();
			g.gain.setValueAtTime(0.05, t);
			g.gain.exponentialRampToValueAtTime(0.0001, t + 0.035);
			src.connect(hp).connect(g).connect(out);
			src.start(t, Math.random());
			src.stop(t + 0.05);
		} else if (cue === 'chime') {
			for (const [freq, delay] of [[659.25, 0], [987.77, 0.08]] as const) {
				const o = ctx.createOscillator();
				const g = ctx.createGain();
				o.type = 'sine';
				o.frequency.value = freq;
				g.gain.setValueAtTime(0.0001, t + delay);
				g.gain.exponentialRampToValueAtTime(0.05, t + delay + 0.02);
				g.gain.exponentialRampToValueAtTime(0.0001, t + delay + 1.4);
				o.connect(g).connect(out);
				o.start(t + delay);
				o.stop(t + delay + 1.5);
			}
		}
	}
}
