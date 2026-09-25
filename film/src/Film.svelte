<script lang="ts">
	import { onMount } from 'svelte';
	import { fade, fly } from 'svelte/transition';
	import Play from '~icons/lucide/play';
	import Pointer from '~icons/lucide/mouse-pointer-click';
	import Ivisyx from '@ivisyx/Ivisyx.svelte';
	import { suite } from '@ivisyx/state.svelte';
	import logo from '@ivisyx/logo.svg?raw';
	import { Sound } from './audio';
	import { chapters } from './chapters';
	import Controls from './Controls.svelte';
	import Cursor from './Cursor.svelte';
	import { Director, type Aspect } from './engine.svelte';
	import { canRecord, download, startRecording, type Recording } from './recorder';
	import Title from './Title.svelte';

	const director = new Director(chapters);
	const stage = director.stage;
	const sound = new Sound();
	director.sfx = (cue) => sound.play(cue);

	let playerEl = $state<HTMLElement>();
	let W = $state(1280);
	let H = $state(720);
	const fit = $derived(Math.min(W / stage.vw, H / stage.vh));
	$effect(() => {
		stage.fit = fit;
	});

	const ui = $state({
		poster: true,
		captions: true,
		transcript: false,
		help: false,
		clean: false,
		explore: false,
		sound: false,
		chrome: true,
		recording: false,
		recStart: 0,
		fullscreen: false,
		toast: '',
	});

	let recording: Recording | null = null;
	let hideTimer: ReturnType<typeof setTimeout>;
	let toastTimer: ReturnType<typeof setTimeout>;

	const accent = $derived(suite.firm.accent);
	const cam = $derived(stage.cam);
	const zoomed = $derived(cam.s / stage.rest().s);

	function toast(text: string) {
		ui.toast = text;
		clearTimeout(toastTimer);
		toastTimer = setTimeout(() => (ui.toast = ''), 2400);
	}

	function wake() {
		ui.chrome = true;
		clearTimeout(hideTimer);
		hideTimer = setTimeout(() => {
			if (director.clock.playing && !ui.transcript && !ui.help) ui.chrome = false;
		}, 2600);
	}

	function posterPose() {
		const r = stage.rest();
		Object.assign(stage.cam, { ...r, s: r.s * 0.86, rx: 14, ry: 0, lift: 40 });
	}

	function start(index = director.index) {
		ui.poster = false;
		if (ui.explore) setExplore(false);
		director.seek(index);
		wake();
	}

	function setExplore(on: boolean) {
		ui.explore = on;
		if (on) {
			ui.poster = false;
			director.halt();
			suite.autoSignals = true;
			suite.paletteOpen = false;
			Object.assign(stage.cam, { ...stage.rest(), rx: 0, ry: 0, lift: 0 });
			toast('You have the live app. Press E to return to the film.');
		} else {
			suite.autoSignals = false;
			director.seek(director.index);
		}
	}

	async function setSound(on: boolean) {
		ui.sound = on;
		await sound.setEnabled(on);
	}

	function setAspect(next: Aspect) {
		stage.aspect = next;
		if (director.started) director.seek(director.index, director.clock.playing);
		else posterPose();
	}

	function share() {
		const url = `${location.origin}${location.pathname}${location.search}#${director.chapters[director.index].id}`;
		navigator.clipboard?.writeText(url).then(
			() => toast('Link to this chapter copied'),
			() => toast(url),
		);
	}

	async function toggleFullscreen() {
		if (document.fullscreenElement) await document.exitFullscreen();
		else await playerEl?.requestFullscreen();
	}

	async function record() {
		if (recording) return finishRecording();
		if (!canRecord()) return toast('Recording needs a desktop Chromium browser');
		try {
			recording = await startRecording(stage.viewportEl!, ui.sound ? sound.stream() : null);
		} catch {
			return toast('Recording cancelled');
		}
		ui.recording = true;
		ui.recStart = Date.now();
		ui.clean = true;
		ui.transcript = ui.help = false;
		director.onEnd = () => finishRecording();
		recording.ended.then(() => ui.recording && finishRecording());
		start(0);
	}

	async function finishRecording() {
		const r = recording;
		if (!r) return;
		recording = null;
		director.onEnd = () => {};
		r.stop();
		const blob = await r.done;
		ui.recording = false;
		ui.clean = false;
		download(blob, `ivisyx-film.${r.ext}`);
		toast(`Saved ivisyx-film.${r.ext}`);
	}

	const api = { start, setExplore, setSound, setAspect, share, toggleFullscreen, record, wake, toast };

	function onkeydown(event: KeyboardEvent) {
		const typing = event.target instanceof HTMLElement && (event.target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(event.target.tagName));
		if (ui.explore && typing && event.key !== 'Escape') return;
		if (event.metaKey || event.ctrlKey || event.altKey) return;
		const key = event.key.toLowerCase();
		const handled = (() => {
			if (key === ' ' || key === 'k') return ui.poster ? start(0) : director.toggle(), true;
			if (key === 'arrowright') return start(Math.min(director.chapters.length - 1, director.index + 1)), true;
			if (key === 'arrowleft') return start(Math.max(0, director.index - (director.position - director.offsets[director.index] > 1500 ? 0 : 1))), true;
			if (/^[1-9]$/.test(key)) return start(Number(key) - 1), true;
			if (key === '0') return start(9), true;
			if (key === 'r') return start(0), true;
			if (key === 'e') return setExplore(!ui.explore), true;
			if (key === 'f') return toggleFullscreen(), true;
			if (key === 'm') return setSound(!ui.sound), true;
			if (key === 'c') return (ui.captions = !ui.captions), true;
			if (key === 't') return (ui.transcript = !ui.transcript), true;
			if (key === 'h') return (ui.clean = !ui.clean), true;
			if (key === 'l') return (director.loop = !director.loop), toast(director.loop ? 'Loop on' : 'Loop off'), true;
			if (key === 's') {
				const speeds = [0.5, 1, 1.5, 2];
				director.clock.speed = speeds[(speeds.indexOf(director.clock.speed) + 1) % speeds.length];
				return toast(`Speed ${director.clock.speed}×`), true;
			}
			if (key === 'a') {
				const list: Aspect[] = ['16:9', '1:1', '9:16'];
				return setAspect(list[(list.indexOf(stage.aspect) + 1) % list.length]), true;
			}
			if (key === '?' || key === '/') return (ui.help = !ui.help), true;
			if (key === 'escape') {
				if (ui.recording) finishRecording();
				ui.help = ui.transcript = false;
				return true;
			}
			return false;
		})();
		if (handled) {
			event.preventDefault();
			event.stopPropagation();
			wake();
		}
	}

	onMount(() => {
		suite.autoSignals = false;
		posterPose();
		try {
			localStorage.removeItem('ivisyx-v1');
		} catch {}
		const params = new URLSearchParams(location.search);
		const cut = params.get('cut') as Aspect | null;
		if (cut && ['16:9', '1:1', '9:16'].includes(cut)) stage.aspect = cut;
		ui.clean = params.has('clean');
		director.loop = params.has('loop');
		const hash = location.hash.slice(1);
		const fromHash = director.chapters.findIndex((c) => c.id === hash);
		if (fromHash >= 0) director.index = fromHash;
		if (params.has('t')) director.index = Math.max(0, director.offsets.findLastIndex((o) => o <= Number(params.get('t')) * 1000));
		if (params.has('explore')) setExplore(true);
		else if (params.has('autoplay')) start(director.index);

		const onFs = () => (ui.fullscreen = !!document.fullscreenElement);
		document.addEventListener('fullscreenchange', onFs);
		const onVisibility = () => {
			if (document.hidden && director.clock.playing && !ui.recording) director.pause();
		};
		document.addEventListener('visibilitychange', onVisibility);
		(window as unknown as { IvisyxFilm: unknown }).IvisyxFilm = { director, seek: (i: number) => start(i), chapters: director.chapters.map((c) => c.id) };
		return () => {
			document.removeEventListener('fullscreenchange', onFs);
			document.removeEventListener('visibilitychange', onVisibility);
		};
	});
</script>

<svelte:window onkeydowncapture={onkeydown} />

<div
	class="player"
	class:clean={ui.clean}
	class:explore={ui.explore}
	class:hide-cursor={!ui.chrome && director.clock.playing}
	bind:this={playerEl}
	bind:clientWidth={W}
	bind:clientHeight={H}
	onpointermove={wake}
	role="presentation"
>
	<div
		class="viewport"
		bind:this={stage.viewportEl}
		style:width="{stage.vw}px"
		style:height="{stage.vh}px"
		style:transform="translate({(W - stage.vw * fit) / 2}px, {(H - stage.vh * fit) / 2}px) scale({fit})"
		style:--accent={accent}
	>
		<div class="backdrop" style:filter="blur({Math.max(0, zoomed - 1) * 6}px)" style:transform="scale({1 + (zoomed - 1) * 0.04})">
			<div class="light" style:transform="translate({(cam.x - stage.rest().x) * -0.04}px, {(cam.y - stage.rest().y) * -0.04}px)"></div>
		</div>

		<div class="world" style:transform="translate({cam.x}px, {cam.y}px) scale({cam.s})">
			<div
				class="tilt"
				style:left="{stage.window.x}px"
				style:top="{stage.window.y}px"
				style:width="{stage.window.w}px"
				style:height="{stage.window.h}px"
				style:transform="perspective(2600px) translateY({cam.lift}px) rotateX({cam.rx}deg) rotateY({cam.ry}deg)"
			>
				<div class="shadow"></div>
				<div class="mac" bind:this={stage.windowEl}>
					<div class="wallpaper"></div>
					<div class="traffic" aria-hidden="true"><i></i><i></i><i></i></div>
					<Ivisyx />
				</div>
			</div>
			{#if stage.spot}
				<div class="spot" transition:fade={{ duration: 400 }} style:left="{stage.spot.x - 8}px" style:top="{stage.spot.y - 8}px" style:width="{stage.spot.w + 16}px" style:height="{stage.spot.h + 16}px"></div>
			{/if}
			<div class="ghosts" bind:this={stage.ghostEl}></div>
			<Cursor x={stage.cursor.x} y={stage.cursor.y} visible={stage.cursor.visible && !ui.explore} down={stage.cursor.down} ripple={stage.cursor.ripple} scale={cam.s} />
		</div>

		<Title card={director.title} unit={stage.unit} />

		{#if director.keys}
			<div class="keycaps" transition:fly={{ y: 20, duration: 250 }}>
				{#each director.keys as key, i}<kbd style:--d="{i * 120}ms">{key}</kbd>{/each}
			</div>
		{/if}

		{#if ui.captions && director.caption && !director.title}
			{#key director.caption}
				<p class="caption" style:--u={stage.unit} in:fly|global={{ y: 14, duration: 450 }} out:fade|global={{ duration: 200 }}>{director.caption}</p>
			{/key}
		{/if}

		<span class="watermark">Demo · fictional companies and firms</span>
	</div>

	{#if ui.poster}
		<div class="poster" transition:fade={{ duration: 400 }}>
			<div class="poster-inner">
				<span class="poster-logo">{@html logo}</span>
				<h1>Ivisyx</h1>
				<p>The film. {Math.floor(director.total / 60000)} min {Math.round((director.total % 60000) / 1000)} s · {director.chapters.length} chapters · driven live by the real app</p>
				<div class="poster-actions">
					<button class="primary" onclick={() => start(director.index)}><Play /> Play the film</button>
					<button onclick={() => setExplore(true)}><Pointer /> Explore the app</button>
				</div>
				<ol class="poster-chapters" aria-label="Chapters">
					{#each director.chapters as c, i}
						<li><button onclick={() => start(i)}><b>{String(i + 1).padStart(2, '0')}</b>{c.title}</button></li>
					{/each}
				</ol>
				<small>Sound is optional (press M). Press ? for shortcuts.</small>
			</div>
		</div>
	{/if}

	{#if ui.explore}
		<div class="explore-bar" transition:fly={{ y: -12, duration: 200 }}>
			<span>Exploring the live app</span>
			<button onclick={() => setExplore(false)}>Resume the film</button>
		</div>
	{/if}

	{#if !ui.poster}
		<Controls {director} {ui} {api} />
	{/if}

	{#if ui.toast}<div class="toast" transition:fly={{ y: 10, duration: 200 }}>{ui.toast}</div>{/if}
</div>

<style>
	:global(html),
	:global(body) {
		height: 100%;
		margin: 0;
		overflow: hidden;
		background: #000;
		font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Inter', 'Helvetica Neue', sans-serif;
		-webkit-font-smoothing: antialiased;
	}

	:global(#film) {
		height: 100%;
	}

	:global(button) {
		font: inherit;
		color: inherit;
		border: 0;
		background: none;
		cursor: pointer;
	}

	.player {
		position: relative;
		width: 100%;
		height: 100%;
		overflow: hidden;
		background: #000;
		color: #f4f6f5;
	}

	.player.hide-cursor {
		cursor: none;
	}

	.viewport {
		position: absolute;
		left: 0;
		top: 0;
		overflow: hidden;
		transform-origin: 0 0;
		background: #040706;
	}

	.backdrop {
		position: absolute;
		inset: -40px;
		background: radial-gradient(ellipse at 50% 120%, color-mix(in srgb, var(--accent) 22%, transparent), transparent 60%), #040706;
		transition: background 1.2s ease;
	}

	.light {
		position: absolute;
		left: 20%;
		top: 8%;
		width: 60%;
		height: 70%;
		border-radius: 50%;
		background: radial-gradient(closest-side, color-mix(in srgb, var(--accent) 30%, transparent), transparent);
		opacity: 0.55;
		transition: background 1.2s ease;
	}

	.world {
		position: absolute;
		inset: 0;
		transform-origin: 0 0;
		pointer-events: none;
	}

	.explore .world {
		pointer-events: auto;
	}

	.tilt {
		position: absolute;
		transform-origin: 50% 60%;
	}

	.shadow {
		position: absolute;
		left: 6%;
		right: 6%;
		bottom: -40px;
		height: 80px;
		border-radius: 50%;
		background: rgba(0, 0, 0, 0.55);
		filter: blur(40px);
	}

	.mac {
		position: absolute;
		inset: 0;
		overflow: hidden;
		border-radius: 12px;
		box-shadow:
			0 0 0 1px rgba(255, 255, 255, 0.12),
			0 40px 90px rgba(0, 0, 0, 0.55),
			0 10px 30px rgba(0, 0, 0, 0.35);
		isolation: isolate;
	}

	/* The desktop the translucent window blurs, as in the demo. */
	.wallpaper {
		position: absolute;
		inset: 0;
		z-index: -1;
		background:
			radial-gradient(circle at 17% 15%, rgba(61, 147, 139, 0.68), transparent 30%),
			radial-gradient(circle at 82% 35%, rgba(45, 91, 120, 0.78), transparent 34%),
			radial-gradient(ellipse at 10% 110%, rgba(255, 118, 54, 0.55), transparent 45%),
			radial-gradient(ellipse at 95% 105%, rgba(223, 155, 63, 0.4), transparent 40%),
			linear-gradient(142deg, #071a21 0%, #0c3b38 45%, #07131a 100%);
	}

	.traffic {
		position: absolute;
		left: 16px;
		top: 16px;
		z-index: 10;
		display: flex;
		gap: 9.6px;
	}

	.traffic i {
		width: 12.8px;
		height: 12.8px;
		border-radius: 50%;
		background: #ff5f56;
		box-shadow: 0 0 0 0.5px #e0443e;
	}

	.traffic i:nth-child(2) {
		background: #ffbd2e;
		box-shadow: 0 0 0 0.5px #dea123;
	}

	.traffic i:nth-child(3) {
		background: #27c93f;
		box-shadow: 0 0 0 0.5px #1aab29;
	}

	.spot {
		position: absolute;
		border-radius: 14px;
		box-shadow:
			0 0 0 2px rgba(255, 255, 255, 0.55),
			0 0 0 9999px rgba(2, 6, 4, 0.5);
		transition:
			left 0.6s ease,
			top 0.6s ease,
			width 0.6s ease,
			height 0.6s ease;
		pointer-events: none;
	}

	.ghosts :global(.ghost) {
		z-index: 25;
		filter: drop-shadow(0 18px 30px rgba(0, 0, 0, 0.35));
		pointer-events: none;
	}

	.keycaps {
		position: absolute;
		left: 50%;
		bottom: 14%;
		z-index: 21;
		display: flex;
		gap: 18px;
		translate: -50% 0;
	}

	.keycaps kbd {
		min-width: 110px;
		height: 110px;
		display: grid;
		place-items: center;
		padding: 0 26px;
		border-radius: 22px;
		background: linear-gradient(180deg, #2a2f2d, #151917);
		box-shadow:
			inset 0 1px 0 rgba(255, 255, 255, 0.14),
			0 10px 0 #0a0c0b,
			0 24px 40px rgba(0, 0, 0, 0.55);
		color: #f4f6f5;
		font-family: inherit;
		font-size: 52px;
		font-weight: 600;
		animation: press 0.5s cubic-bezier(0.3, 0.7, 0.3, 1) calc(var(--d) + 320ms) both;
	}

	@keyframes press {
		40% {
			transform: translateY(8px);
			box-shadow:
				inset 0 1px 0 rgba(255, 255, 255, 0.14),
				0 2px 0 #0a0c0b,
				0 10px 20px rgba(0, 0, 0, 0.5);
		}
	}

	.caption {
		position: absolute;
		left: 50%;
		bottom: calc(64px * var(--u) + 2%);
		z-index: 19;
		max-width: 78%;
		margin: 0;
		padding: calc(16px * var(--u)) calc(30px * var(--u));
		border-radius: calc(18px * var(--u));
		background: rgba(10, 14, 12, 0.84);
		backdrop-filter: blur(16px);
		color: #f4f6f5;
		font-size: calc(34px * var(--u));
		font-weight: 550;
		letter-spacing: -0.015em;
		line-height: 1.3;
		text-align: center;
		translate: -50% 0;
		box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
	}

	.watermark {
		position: absolute;
		right: 28px;
		bottom: 22px;
		z-index: 22;
		color: rgba(255, 255, 255, 0.35);
		font-size: 17px;
		letter-spacing: 0.01em;
	}


	.poster {
		position: absolute;
		inset: 0;
		z-index: 40;
		display: grid;
		place-items: center;
		background: radial-gradient(ellipse at 50% 60%, rgba(4, 8, 7, 0.55), rgba(0, 0, 0, 0.92));
		backdrop-filter: blur(10px);
	}

	.poster-inner {
		display: grid;
		justify-items: center;
		gap: 10px;
		padding: 24px;
		text-align: center;
	}

	.poster-logo {
		width: 64px;
		padding: 12px;
		border-radius: 18px;
		background: linear-gradient(180deg, #fff, #dfe5e7);
		box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
	}

	.poster-logo :global(svg) {
		display: block;
		width: 100%;
		height: auto;
	}

	.poster h1 {
		margin: 12px 0 0;
		font-size: clamp(44px, 7vw, 84px);
		font-weight: 700;
		letter-spacing: -0.05em;
	}

	.poster p {
		margin: 0;
		color: rgba(244, 246, 245, 0.6);
		font-size: clamp(13px, 1.4vw, 17px);
	}

	.poster-actions {
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		gap: 10px;
		margin: 22px 0 8px;
	}

	.poster-actions button {
		height: 44px;
		display: inline-flex;
		align-items: center;
		gap: 8px;
		padding: 0 20px;
		border-radius: 22px;
		background: rgba(255, 255, 255, 0.1);
		font-size: 15px;
		font-weight: 600;
		transition: background 0.15s ease;
	}

	.poster-actions button:hover {
		background: rgba(255, 255, 255, 0.18);
	}

	.poster-actions .primary {
		background: #f4f6f5;
		color: #0b0f0d;
	}

	.poster-actions .primary:hover {
		background: #fff;
	}

	.poster-chapters {
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		gap: 6px;
		max-width: 640px;
		margin: 6px 0 14px;
		padding: 0;
		list-style: none;
	}

	.poster-chapters button {
		padding: 5px 10px;
		border-radius: 13px;
		background: rgba(255, 255, 255, 0.06);
		color: rgba(244, 246, 245, 0.7);
		font-size: 12px;
		transition: background 0.15s ease, color 0.15s ease;
	}

	.poster-chapters button:hover {
		background: rgba(255, 255, 255, 0.14);
		color: #fff;
	}

	.poster-chapters b {
		margin-right: 6px;
		color: rgba(244, 246, 245, 0.38);
		font-weight: 500;
		font-variant-numeric: tabular-nums;
	}

	.poster small {
		color: rgba(244, 246, 245, 0.4);
		font-size: 12px;
	}

	.explore-bar {
		position: absolute;
		left: 50%;
		top: 14px;
		z-index: 45;
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 6px 6px 6px 14px;
		border-radius: 20px;
		background: rgba(14, 18, 16, 0.85);
		backdrop-filter: blur(14px);
		box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
		font-size: 13px;
		translate: -50% 0;
	}

	.explore-bar button {
		padding: 6px 12px;
		border-radius: 14px;
		background: #f4f6f5;
		color: #0b0f0d;
		font-weight: 600;
	}

	.toast {
		position: absolute;
		left: 50%;
		bottom: 96px;
		z-index: 60;
		padding: 9px 16px;
		border-radius: 18px;
		background: rgba(20, 24, 22, 0.92);
		box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
		font-size: 13px;
		translate: -50% 0;
	}
</style>
