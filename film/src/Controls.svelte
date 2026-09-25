<script lang="ts">
	import { fade, fly } from 'svelte/transition';
	import Captions from '~icons/lucide/captions';
	import Circle from '~icons/lucide/circle';
	import Keyboard from '~icons/lucide/keyboard';
	import Link from '~icons/lucide/link';
	import List from '~icons/lucide/list-video';
	import Maximize from '~icons/lucide/maximize';
	import Minimize from '~icons/lucide/minimize';
	import Pause from '~icons/lucide/pause';
	import Play from '~icons/lucide/play';
	import Pointer from '~icons/lucide/mouse-pointer-click';
	import Repeat from '~icons/lucide/repeat';
	import Restart from '~icons/lucide/rotate-ccw';
	import Square from '~icons/lucide/square';
	import Volume from '~icons/lucide/volume-2';
	import Mute from '~icons/lucide/volume-x';
	import X from '~icons/lucide/x';
	import type { Aspect, Director } from './engine.svelte';

	type Props = {
		director: Director;
		ui: { captions: boolean; transcript: boolean; help: boolean; clean: boolean; explore: boolean; sound: boolean; chrome: boolean; recording: boolean; recStart: number; fullscreen: boolean };
		api: {
			start: (i?: number) => void;
			setExplore: (on: boolean) => void;
			setSound: (on: boolean) => void;
			setAspect: (a: Aspect) => void;
			share: () => void;
			toggleFullscreen: () => void;
			record: () => void;
			wake: () => void;
		};
	};
	const { director, ui, api }: Props = $props();

	let hover = $state<{ x: number; i: number } | null>(null);
	let now = $state(Date.now());
	$effect(() => {
		if (!ui.recording) return;
		const t = setInterval(() => (now = Date.now()), 500);
		return () => clearInterval(t);
	});

	const fmt = (ms: number) => `${Math.floor(ms / 60000)}:${String(Math.floor((ms % 60000) / 1000)).padStart(2, '0')}`;
	const speeds = [0.5, 1, 1.5, 2];
	const aspectList: Aspect[] = ['16:9', '1:1', '9:16'];
	const shortcuts = [
		['Space', 'Play or pause'],
		['← →', 'Previous or next chapter'],
		['1–9, 0', 'Jump to a chapter'],
		['R', 'Restart'],
		['E', 'Explore the live app'],
		['C', 'Captions'],
		['T', 'Transcript and presenter notes'],
		['S', 'Playback speed'],
		['A', 'Aspect: 16:9, 1:1, 9:16'],
		['M', 'Sound'],
		['L', 'Loop'],
		['H', 'Hide controls'],
		['F', 'Full screen'],
	];

	function seekAt(event: MouseEvent) {
		const rect = (event.currentTarget as HTMLElement).getBoundingClientRect();
		const ms = ((event.clientX - rect.left) / rect.width) * director.total;
		director.seekTime(ms);
		api.wake();
	}

	function hoverAt(event: MouseEvent) {
		const rect = (event.currentTarget as HTMLElement).getBoundingClientRect();
		const ms = ((event.clientX - rect.left) / rect.width) * director.total;
		hover = { x: event.clientX - rect.left, i: Math.max(0, director.offsets.findLastIndex((o) => o <= ms)) };
	}
</script>

{#if !ui.clean}
	<div class="chrome" class:hidden={!ui.chrome && director.clock.playing} role="toolbar" aria-label="Film controls" tabindex="-1" onpointerenter={api.wake}>
		<div class="scrub-wrap">
			<button class="scrub" aria-label="Seek" onclick={seekAt} onpointermove={hoverAt} onpointerleave={() => (hover = null)}>
				{#each director.chapters as c, i}
					{@const start = director.offsets[i]}
					{@const fill = Math.max(0, Math.min(1, (director.position - start) / c.duration))}
					<span class="seg" style:flex={c.duration}><i style:width="{fill * 100}%"></i></span>
				{/each}
			</button>
			{#if hover}
				<span class="scrub-tip" style:left="{hover.x}px">{String(hover.i + 1).padStart(2, '0')} · {director.chapters[hover.i].title}</span>
			{/if}
		</div>
		<div class="bar">
			<button class="icon big" onclick={() => director.toggle()} aria-label={director.clock.playing ? 'Pause' : 'Play'}>
				{#if director.clock.playing}<Pause />{:else}<Play />{/if}
			</button>
			<button class="icon" onclick={() => api.start(0)} aria-label="Restart"><Restart /></button>
			<span class="time">{fmt(director.position)} / {fmt(director.total)}</span>
			<span class="chapter"><b>{String(director.index + 1).padStart(2, '0')}</b>{director.chapters[director.index].title}</span>
			<span class="spacer"></span>
			{#if ui.recording}<span class="rec"><i></i>Recording {fmt(now - ui.recStart)}</span>{/if}
			<button class="pill" onclick={() => (director.clock.speed = speeds[(speeds.indexOf(director.clock.speed) + 1) % speeds.length])} aria-label="Playback speed">{director.clock.speed}×</button>
			<button class="pill" onclick={() => api.setAspect(aspectList[(aspectList.indexOf(director.stage.aspect) + 1) % aspectList.length])} aria-label="Aspect ratio">{director.stage.aspect}</button>
			<button class="icon" class:on={ui.captions} onclick={() => (ui.captions = !ui.captions)} aria-label="Captions"><Captions /></button>
			<button class="icon" class:on={ui.sound} onclick={() => api.setSound(!ui.sound)} aria-label="Sound">{#if ui.sound}<Volume />{:else}<Mute />{/if}</button>
			<button class="icon" class:on={director.loop} onclick={() => (director.loop = !director.loop)} aria-label="Loop"><Repeat /></button>
			<button class="icon" class:on={ui.transcript} onclick={() => (ui.transcript = !ui.transcript)} aria-label="Transcript"><List /></button>
			<button class="icon" class:on={ui.explore} onclick={() => api.setExplore(!ui.explore)} aria-label="Explore the app"><Pointer /></button>
			<button class="icon" onclick={api.share} aria-label="Copy link to this chapter"><Link /></button>
			<button class="icon" class:rec-on={ui.recording} onclick={api.record} aria-label={ui.recording ? 'Stop recording' : 'Record video'}>{#if ui.recording}<Square />{:else}<Circle />{/if}</button>
			<button class="icon" onclick={() => (ui.help = !ui.help)} aria-label="Keyboard shortcuts"><Keyboard /></button>
			<button class="icon" onclick={api.toggleFullscreen} aria-label="Full screen">{#if ui.fullscreen}<Minimize />{:else}<Maximize />{/if}</button>
		</div>
	</div>
{/if}

{#if ui.transcript}
	<aside class="panel" transition:fly={{ x: 24, duration: 220 }}>
		<header><strong>Transcript</strong><button class="icon" onclick={() => (ui.transcript = false)} aria-label="Close"><X /></button></header>
		<ol>
			{#each director.chapters as c, i}
				<li class:current={i === director.index}>
					<button onclick={() => api.start(i)}>
						<span class="stamp">{fmt(director.offsets[i])}</span>
						<span class="body">
							<strong>{c.title}</strong>
							{#each c.captions as line}<span class="line">{line}</span>{/each}
							<em>{c.notes}</em>
						</span>
					</button>
				</li>
			{/each}
		</ol>
	</aside>
{/if}

{#if ui.help}
	<div class="help-wrap" role="presentation" transition:fade={{ duration: 150 }} onclick={(e) => e.target === e.currentTarget && (ui.help = false)}>
		<div class="help" role="dialog" aria-label="Keyboard shortcuts">
			<header><strong>Keyboard shortcuts</strong><button class="icon" onclick={() => (ui.help = false)} aria-label="Close"><X /></button></header>
			<dl>{#each shortcuts as [k, v]}<dt><kbd>{k}</kbd></dt><dd>{v}</dd>{/each}</dl>
			<p>Links: add <code>#map</code> (any chapter id) to start at a chapter, <code>?autoplay</code>, <code>?clean</code>, <code>?loop</code>, <code>?cut=9:16</code> or <code>?explore</code>.</p>
		</div>
	</div>
{/if}

<style>
	.chrome {
		position: absolute;
		left: 0;
		right: 0;
		bottom: 0;
		z-index: 50;
		padding: 40px 18px 12px;
		background: linear-gradient(transparent, rgba(0, 0, 0, 0.72));
		transition: opacity 0.35s ease, transform 0.35s ease;
	}

	.chrome.hidden {
		opacity: 0;
		transform: translateY(10px);
		pointer-events: none;
	}

	.scrub-wrap {
		position: relative;
	}

	.scrub {
		width: 100%;
		height: 16px;
		display: flex;
		align-items: center;
		gap: 3px;
		padding: 0;
	}

	.seg {
		position: relative;
		height: 4px;
		overflow: hidden;
		border-radius: 2px;
		background: rgba(255, 255, 255, 0.22);
		transition: height 0.15s ease;
	}

	.scrub:hover .seg {
		height: 7px;
	}

	.seg i {
		position: absolute;
		inset: 0 auto 0 0;
		background: #f4f6f5;
	}

	.scrub-tip {
		position: absolute;
		bottom: 22px;
		padding: 5px 9px;
		border-radius: 8px;
		background: rgba(20, 24, 22, 0.95);
		font-size: 12px;
		white-space: nowrap;
		translate: -50% 0;
		pointer-events: none;
	}

	.bar {
		display: flex;
		align-items: center;
		gap: 4px;
		margin-top: 6px;
		font-size: 13px;
	}

	.icon {
		width: 34px;
		height: 34px;
		display: grid;
		place-items: center;
		border-radius: 10px;
		color: rgba(244, 246, 245, 0.78);
		font-size: 17px;
		transition: background 0.15s ease, color 0.15s ease;
	}

	.icon:hover {
		background: rgba(255, 255, 255, 0.1);
		color: #fff;
	}

	.icon.on {
		color: #fff;
		background: rgba(255, 255, 255, 0.14);
	}

	.icon.big {
		width: 40px;
		height: 40px;
		font-size: 20px;
	}

	.rec-on {
		color: #ff5f56;
	}

	.time {
		margin: 0 8px;
		color: rgba(244, 246, 245, 0.75);
		font-variant-numeric: tabular-nums;
	}

	.chapter {
		overflow: hidden;
		color: rgba(244, 246, 245, 0.9);
		white-space: nowrap;
		text-overflow: ellipsis;
	}

	.chapter b {
		margin-right: 8px;
		color: rgba(244, 246, 245, 0.45);
		font-weight: 500;
		font-variant-numeric: tabular-nums;
	}

	.spacer {
		flex: 1;
	}

	.pill {
		height: 28px;
		padding: 0 10px;
		border-radius: 14px;
		background: rgba(255, 255, 255, 0.1);
		color: rgba(244, 246, 245, 0.85);
		font-size: 12px;
		font-weight: 600;
		font-variant-numeric: tabular-nums;
	}

	.pill:hover {
		background: rgba(255, 255, 255, 0.18);
	}

	.rec {
		display: flex;
		align-items: center;
		gap: 6px;
		margin-right: 8px;
		color: #ffb3ae;
		font-variant-numeric: tabular-nums;
	}

	.rec i {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: #ff5f56;
		animation: blink 1s steps(2) infinite;
	}

	@keyframes blink {
		50% {
			opacity: 0.2;
		}
	}

	.panel {
		position: absolute;
		top: 14px;
		right: 14px;
		bottom: 110px;
		z-index: 55;
		width: min(360px, 88vw);
		display: flex;
		flex-direction: column;
		overflow: hidden;
		border-radius: 16px;
		background: rgba(16, 20, 18, 0.92);
		box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
		backdrop-filter: blur(20px);
	}

	.panel header,
	.help header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 12px 10px 8px 16px;
		font-size: 15px;
	}

	ol {
		flex: 1;
		overflow: auto;
		margin: 0;
		padding: 0 8px 10px;
		list-style: none;
	}

	li button {
		width: 100%;
		display: grid;
		grid-template-columns: 42px 1fr;
		gap: 8px;
		padding: 9px 8px;
		border-radius: 10px;
		text-align: left;
	}

	li button:hover {
		background: rgba(255, 255, 255, 0.06);
	}

	li.current button {
		background: rgba(255, 255, 255, 0.1);
	}

	.stamp {
		color: rgba(244, 246, 245, 0.45);
		font-size: 12px;
		font-variant-numeric: tabular-nums;
	}

	.body {
		display: grid;
		gap: 3px;
		font-size: 13px;
	}

	.line {
		color: rgba(244, 246, 245, 0.72);
	}

	.body em {
		color: rgba(244, 246, 245, 0.42);
		font-size: 12px;
		font-style: normal;
	}

	.help-wrap {
		position: absolute;
		inset: 0;
		z-index: 58;
		display: grid;
		place-items: center;
		background: rgba(0, 0, 0, 0.45);
	}

	.help {
		width: min(460px, 90vw);
		padding-bottom: 14px;
		border-radius: 16px;
		background: rgba(18, 22, 20, 0.96);
		box-shadow: 0 30px 80px rgba(0, 0, 0, 0.55);
	}

	dl {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 8px 14px;
		margin: 4px 16px 12px;
		font-size: 13px;
	}

	dt {
		text-align: right;
	}

	dd {
		margin: 0;
		align-self: center;
		color: rgba(244, 246, 245, 0.75);
	}

	kbd {
		padding: 2px 7px;
		border-radius: 6px;
		background: rgba(255, 255, 255, 0.12);
		font-family: inherit;
		font-size: 12px;
	}

	.help p {
		margin: 0 16px;
		color: rgba(244, 246, 245, 0.5);
		font-size: 12px;
		line-height: 1.5;
	}

	code {
		color: rgba(244, 246, 245, 0.8);
	}

	@media (max-width: 720px) {
		.chapter,
		.pill {
			display: none;
		}
	}
</style>
