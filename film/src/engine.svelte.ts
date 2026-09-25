/**
 * The film engine: a pausable clock, an animated camera, a simulated cursor
 * and a director that plays chapters in order. Everything that takes time
 * awaits the film clock, so pause, speed and seek apply to the whole film.
 */

export class Cancelled extends Error {}

export const ease = {
	linear: (t: number) => t,
	out: (t: number) => 1 - (1 - t) ** 4,
	in: (t: number) => t ** 3,
	inOut: (t: number) => (t < 0.5 ? 8 * t ** 4 : 1 - (-2 * t + 2) ** 4 / 2),
	/** Slow start, confident middle, long settle. Used for camera moves. */
	camera: (t: number) => (t < 0.5 ? 16 * t ** 5 : 1 - (-2 * t + 2) ** 5 / 2),
};

type Waiter = { at: number; resolve: () => void; reject: (e: Error) => void };
type Ticker = (t: number) => void;

export class Clock {
	t = $state(0);
	playing = $state(false);
	speed = $state(1);
	#last = performance.now();
	#waiters: Waiter[] = [];
	#tickers = new Set<Ticker>();

	constructor() {
		const frame = (now: number) => {
			const dt = Math.min(80, now - this.#last);
			this.#last = now;
			if (this.playing) this.t += dt * this.speed;
			for (const tick of [...this.#tickers]) tick(this.t);
			const due = this.#waiters.filter((w) => w.at <= this.t);
			if (due.length) {
				this.#waiters = this.#waiters.filter((w) => w.at > this.t);
				for (const w of due) w.resolve();
			}
			requestAnimationFrame(frame);
		};
		requestAnimationFrame(frame);
	}

	wait(ms: number) {
		return new Promise<void>((resolve, reject) => this.#waiters.push({ at: this.t + Math.max(0, ms), resolve, reject }));
	}

	/** Calls `step` with eased progress 0→1 over `ms` of film time. */
	tween(ms: number, step: (p: number) => void, curve = ease.inOut) {
		const start = this.t;
		return new Promise<void>((resolve, reject) => {
			const tick: Ticker = (t) => {
				const p = ms <= 0 ? 1 : Math.min(1, (t - start) / ms);
				step(curve(p));
				if (p >= 1) {
					this.#tickers.delete(tick);
					resolve();
				}
			};
			(tick as Ticker & { reject?: (e: Error) => void }).reject = reject;
			this.#tickers.add(tick);
			tick(this.t);
		});
	}

	/** Rejects every pending wait and tween. Used when seeking. */
	cancelAll() {
		const err = new Cancelled();
		for (const w of this.#waiters) w.reject(err);
		this.#waiters = [];
		for (const tick of this.#tickers) (tick as Ticker & { reject?: (e: Error) => void }).reject?.(err);
		this.#tickers.clear();
	}
}

export type Rect = { x: number; y: number; w: number; h: number };
export type Aspect = '16:9' | '1:1' | '9:16';
export const aspects: Record<Aspect, [number, number]> = { '16:9': [1920, 1080], '1:1': [1080, 1080], '9:16': [1080, 1920] };
export const WINDOW = { w: 1180, h: 720 };

export class Stage {
	aspect = $state<Aspect>('16:9');
	vw = $derived(aspects[this.aspect][0]);
	vh = $derived(aspects[this.aspect][1]);
	/** Screen pixels per logical pixel. */
	fit = $state(1);
	cam = $state({ s: 1, x: 0, y: 0, rx: 0, ry: 0, lift: 0 });
	spot = $state<Rect | null>(null);
	backdropBlur = $state(0);
	cursor = $state({ x: 0, y: 0, visible: false, down: false, ripple: 0 });
	viewportEl: HTMLElement | null = null;
	windowEl: HTMLElement | null = null;
	ghostEl: HTMLElement | null = null;

	get window() {
		return { x: (this.vw - WINDOW.w) / 2, y: (this.vh - WINDOW.h) / 2, ...WINDOW };
	}

	/** Camera that frames the whole app window. */
	rest() {
		const s = Math.min((this.vw * 0.8) / WINDOW.w, (this.vh * 0.8) / WINDOW.h);
		return { s, x: (this.vw / 2) * (1 - s), y: (this.vh / 2) * (1 - s) };
	}

	/** Converts an element's on-screen box into world coordinates. */
	toWorld(el: Element): Rect | null {
		if (!this.viewportEl) return null;
		const r = el.getBoundingClientRect();
		const v = this.viewportEl.getBoundingClientRect();
		const fit = v.width / this.vw;
		const { s, x, y } = this.cam;
		return {
			x: ((r.left - v.left) / fit - x) / s,
			y: ((r.top - v.top) / fit - y) / s,
			w: r.width / fit / s,
			h: r.height / fit / s,
		};
	}

	framing(rect: Rect, { pad = 0.72, max = 3.2, min = 0.5, dy = -0.03 } = {}) {
		const s = Math.max(min, Math.min(max, (this.vw * pad) / rect.w, (this.vh * pad) / rect.h));
		return { s, x: this.vw / 2 - (rect.x + rect.w / 2) * s, y: this.vh * (0.5 + dy) - (rect.y + rect.h / 2) * s };
	}
}

export type TitleCard = {
	id: number;
	kicker?: string;
	lines: string[];
	sub?: string;
	logo?: boolean;
	backdrop?: 'none' | 'dim' | 'black';
	size?: 'hero' | 'statement';
	fine?: string;
};

export type Chapter = {
	id: string;
	title: string;
	duration: number;
	captions: string[];
	notes: string;
	setup: (ctx: Ctx, fresh: boolean) => Promise<void> | void;
	run: (ctx: Ctx) => Promise<void>;
};

export type Ctx = ReturnType<Director['makeCtx']>;

export class Director {
	clock = new Clock();
	stage = new Stage();
	chapters: Chapter[] = [];
	index = $state(0);
	chapterStart = $state(0);
	ended = $state(false);
	started = $state(false);
	caption = $state<string | null>(null);
	title = $state<TitleCard | null>(null);
	keys = $state<string[] | null>(null);
	loop = $state(false);
	sfx: (name: 'whoosh' | 'click' | 'type' | 'chime' | 'drop') => void = () => {};
	onEnd: () => void = () => {};
	#token = 0;
	#titleId = 0;

	offsets = $derived.by(() => {
		let at = 0;
		return this.chapters.map((c) => {
			const start = at;
			at += c.duration;
			return start;
		});
	});
	total = $derived(this.chapters.reduce((s, c) => s + c.duration, 0));
	/** Position on the timeline in ms, clamped to the current chapter's budget. */
	position = $derived(
		this.chapters.length
			? this.offsets[this.index] + Math.min(this.chapters[this.index].duration, Math.max(0, this.clock.t - this.chapterStart))
			: 0,
	);

	constructor(chapters: Chapter[]) {
		this.chapters = chapters;
	}

	play() {
		if (this.ended) return this.seek(0);
		if (!this.started) {
			this.started = true;
			this.#runFrom(this.index);
		}
		this.clock.playing = true;
	}

	pause() {
		this.clock.playing = false;
	}

	toggle() {
		if (this.clock.playing) this.pause();
		else this.play();
	}

	seek(index: number, autoplay = true) {
		index = Math.max(0, Math.min(this.chapters.length - 1, index));
		this.ended = false;
		this.started = true;
		this.#runFrom(index, true);
		if (autoplay) this.clock.playing = true;
	}

	seekTime(ms: number) {
		const i = this.offsets.findLastIndex((o) => o <= ms);
		this.seek(Math.max(0, i), this.clock.playing || !this.started);
	}

	/** Stops the film and hands the app back to the viewer. */
	halt() {
		this.#token++;
		this.clock.cancelAll();
		this.clock.playing = false;
		this.started = false;
		this.title = null;
		this.caption = null;
		this.keys = null;
		this.stage.spot = null;
		this.stage.cursor.visible = false;
	}

	async #runFrom(start: number, fresh = false) {
		const token = ++this.#token;
		this.clock.cancelAll();
		this.title = null;
		this.caption = null;
		this.keys = null;
		this.stage.spot = null;
		const ctx = this.makeCtx(token);
		for (let i = start; i < this.chapters.length; i++) {
			const chapter = this.chapters[i];
			this.index = i;
			this.chapterStart = this.clock.t;
			try {
				await chapter.setup(ctx, fresh || i === start);
				await chapter.run(ctx);
				await ctx.until(chapter.duration);
			} catch (err) {
				if (err instanceof Cancelled || token !== this.#token) return;
				console.error(`[film] chapter "${chapter.id}" failed`, err);
			}
			if (token !== this.#token) return;
			fresh = false;
		}
		if (this.loop) return this.#runFrom(0, true);
		this.ended = true;
		this.clock.playing = false;
		this.onEnd();
	}

	makeCtx(token: number) {
		const director = this;
		const { clock, stage } = this;
		const live = () => {
			if (token !== director.#token) throw new Cancelled();
		};
		const wait = async (ms: number) => {
			await clock.wait(ms);
			live();
		};
		const frame = () => new Promise((r) => requestAnimationFrame(r));

		const q = (selector: string) => stage.windowEl?.querySelector<HTMLElement>(selector) ?? null;
		const find = (selector: string, text: string) =>
			[...(stage.windowEl?.querySelectorAll<HTMLElement>(selector) ?? [])].find((el) => el.textContent?.includes(text)) ?? null;
		async function waitFor<T>(get: () => T | null | undefined, timeout = 3000): Promise<T | null> {
			const end = performance.now() + timeout;
			while (performance.now() < end) {
				const v = get();
				if (v) return v;
				await frame();
				live();
			}
			return null;
		}

		const resolve = (target: Element | string | null) => (typeof target === 'string' ? q(target) : target);

		/**
		 * Scrolls the app's own scroll areas so `el` is visible inside the window.
		 * (Element.scrollIntoView would also scroll the film's stage.)
		 */
		async function reveal(el: Element) {
			let moved = false;
			for (let node = el.parentElement; node && node !== stage.windowEl; node = node.parentElement) {
				const style = getComputedStyle(node);
				const scrollsY = /(auto|scroll)/.test(style.overflowY) && node.scrollHeight > node.clientHeight + 1;
				if (!scrollsY) continue;
				const box = node.getBoundingClientRect();
				const r = el.getBoundingClientRect();
				if (r.top >= box.top && r.bottom <= box.bottom) continue;
				const ratio = node.clientHeight / box.height;
				const delta = (r.top - box.top) * ratio - Math.max(0, (node.clientHeight - r.height * ratio) / 2);
				node.scrollTo({ top: node.scrollTop + delta, behavior: 'smooth' });
				moved = true;
			}
			if (moved) await wait(650);
		}

		const camera = {
			async to(next: Partial<Stage['cam']>, ms = 1200, curve = ease.camera) {
				const from = { ...stage.cam };
				if (ms > 300) director.sfx('whoosh');
				await clock.tween(ms, (p) => {
					for (const key of Object.keys(next) as (keyof Stage['cam'])[]) stage.cam[key] = from[key] + ((next[key] as number) - from[key]) * p;
				}, curve);
				live();
			},
			rest(ms = 1200) {
				stage.spot = null;
				return camera.to({ ...stage.rest(), rx: 0, ry: 0, lift: 0 }, ms);
			},
			set(next: Partial<Stage['cam']>) {
				Object.assign(stage.cam, next);
			},
			/** Frames an element. `spot` dims everything around it. */
			async focus(target: Element | string | null, opts: { pad?: number; max?: number; dy?: number; ms?: number; spot?: boolean } = {}) {
				const el = resolve(target);
				if (!el) return;
				await reveal(el);
				const rect = stage.toWorld(el);
				if (!rect) return;
				stage.spot = opts.spot ? rect : null;
				await camera.to(stage.framing(rect, opts), opts.ms ?? 1300);
			},
		};

		const cursor = {
			show(at?: { x: number; y: number }) {
				if (at) Object.assign(stage.cursor, at);
				stage.cursor.visible = true;
			},
			hide() {
				stage.cursor.visible = false;
			},
			async move(target: Element | string | null, ms = 750, anchor = { x: 0.5, y: 0.5 }) {
				const el = resolve(target);
				if (!el) return;
				await reveal(el);
				const r = stage.toWorld(el);
				if (!r) return;
				stage.cursor.visible = true;
				const from = { x: stage.cursor.x, y: stage.cursor.y };
				const to = { x: r.x + r.w * anchor.x, y: r.y + r.h * anchor.y };
				// A slight arc reads as a human hand rather than a robot.
				const bend = Math.min(60, Math.hypot(to.x - from.x, to.y - from.y) * 0.12);
				await clock.tween(ms, (p) => {
					stage.cursor.x = from.x + (to.x - from.x) * p;
					stage.cursor.y = from.y + (to.y - from.y) * p - Math.sin(Math.PI * p) * bend;
				}, ease.inOut);
				live();
			},
			async press() {
				stage.cursor.down = true;
				stage.cursor.ripple++;
				director.sfx('click');
				await wait(110);
				stage.cursor.down = false;
			},
			async click(target: Element | string | null, ms = 750) {
				const el = resolve(target);
				if (!el) return;
				await cursor.move(el, ms);
				await cursor.press();
				el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
				await wait(60);
			},
			hover(target: Element | string | null) {
				const el = resolve(target);
				el?.dispatchEvent(new PointerEvent('pointerenter', { bubbles: false }));
				el?.dispatchEvent(new MouseEvent('mouseenter', { bubbles: false }));
			},
			unhover(target: Element | string | null) {
				const el = resolve(target);
				el?.dispatchEvent(new PointerEvent('pointerleave', { bubbles: false }));
			},
			/** Types into an input one character at a time. */
			async type(target: Element | string | null, text: string, cps = 16) {
				const el = resolve(target) as HTMLInputElement | null;
				if (!el) return;
				el.focus({ preventScroll: true });
				for (let i = 1; i <= text.length; i++) {
					el.value = text.slice(0, i);
					el.dispatchEvent(new Event('input', { bubbles: true }));
					director.sfx('type');
					await wait(1000 / cps + (Math.sin(i * 2.3) + 1) * 18);
				}
			},
			/** Sweeps a pointer across an element, e.g. to scrub a chart tooltip. */
			async scrub(target: Element | string | null, ms = 1600) {
				const el = resolve(target);
				if (!el) return;
				const r = el.getBoundingClientRect();
				const w = stage.toWorld(el)!;
				stage.cursor.visible = true;
				await clock.tween(ms, (p) => {
					const cx = r.left + r.width * (0.08 + p * 0.86);
					const cy = r.top + r.height * 0.45;
					el.dispatchEvent(new PointerEvent('pointermove', { clientX: cx, clientY: cy, bubbles: true }));
					stage.cursor.x = w.x + w.w * (0.08 + p * 0.86);
					stage.cursor.y = w.y + w.h * 0.45;
				}, ease.inOut);
				live();
				el.dispatchEvent(new PointerEvent('pointerleave', { bubbles: true }));
			},
			/** Drags a copy of `from` onto `to`, then calls `drop`. */
			async drag(from: Element | null, to: Element | null, drop: () => void, ms = 1300) {
				if (!from || !to || !stage.ghostEl) return drop();
				const a = stage.toWorld(from)!;
				const b = stage.toWorld(to)!;
				await cursor.move(from, 700, { x: 0.4, y: 0.3 });
				const app = stage.windowEl?.querySelector<HTMLElement>('.ivx.app');
				const zoom = app ? parseFloat(getComputedStyle(app).zoom) || 1 : 1;
				const wrap = document.createElement('div');
				wrap.className = 'ivx ghost';
				wrap.style.cssText = `position:absolute;left:${a.x}px;top:${a.y}px;width:${a.w / zoom}px;zoom:${zoom};--accent:${app?.style.getPropertyValue('--accent') || '#1d6751'};`;
				wrap.appendChild(from.cloneNode(true));
				stage.ghostEl.appendChild(wrap);
				(from as HTMLElement).style.opacity = '0.28';
				stage.cursor.down = true;
				director.sfx('click');
				const tx = b.x + 6 - a.x;
				const ty = b.y + 40 - a.y;
				const cx = stage.cursor.x;
				const cy = stage.cursor.y;
				await clock.tween(ms, (p) => {
					const lift = Math.sin(Math.PI * p);
					wrap.style.transform = `translate(${tx * p}px, ${ty * p - lift * 30}px) rotate(${lift * 2.5}deg) scale(${1 + lift * 0.04})`;
					stage.cursor.x = cx + tx * p;
					stage.cursor.y = cy + ty * p - lift * 30;
				}, ease.inOut);
				live();
				stage.cursor.down = false;
				director.sfx('drop');
				wrap.remove();
				(from as HTMLElement).style.opacity = '';
				drop();
			},
		};

		return {
			director,
			stage,
			wait,
			frame,
			q,
			reveal,
			find,
			waitFor,
			camera,
			cursor,
			/** Waits until this chapter has used `ms` of its time budget. */
			until: (ms: number) => wait(ms - (clock.t - director.chapterStart)),
			say(text: string | null) {
				director.caption = text;
			},
			async titleCard(card: Omit<TitleCard, 'id'>, hold = 2600) {
				director.title = { ...card, id: ++director.#titleId };
				director.sfx('chime');
				await wait(hold);
			},
			clearTitle() {
				director.title = null;
			},
			async keycaps(keys: string[], hold = 900) {
				director.keys = keys;
				director.sfx('click');
				await wait(hold);
				director.keys = null;
			},
		};
	}
}
