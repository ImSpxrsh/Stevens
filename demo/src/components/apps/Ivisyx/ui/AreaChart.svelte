<script lang="ts">
	import { smoothPath } from './Sparkline.svelte';

	type Series = { name: string; values: number[]; color: string };
	type Props = { series: Series[]; labels: string[]; height?: number; format?: (v: number) => string; zero?: boolean; dark?: boolean };
	const { series, labels, height = 150, format = (v) => String(v), zero = false, dark = false }: Props = $props();

	const uid = $props.id();
	let width = $state(400);
	let hover = $state<number | null>(null);

	const pad = { l: 26, r: 8, t: 10, b: 18 };
	const all = $derived(series.flatMap((s) => s.values));
	const min = $derived(zero ? Math.min(0, ...all) : Math.min(...all) * 0.9);
	const max = $derived(Math.max(...all) * 1.08);
	const x = (i: number) => pad.l + (i / (labels.length - 1)) * (width - pad.l - pad.r);
	const y = (v: number) => pad.t + (1 - (v - min) / (max - min || 1)) * (height - pad.t - pad.b);
	const ticks = $derived([0, 1, 2, 3].map((i) => min + ((max - min) * i) / 3));

	function move(event: PointerEvent) {
		const rect = (event.currentTarget as SVGElement).getBoundingClientRect();
		const px = ((event.clientX - rect.left) / rect.width) * width;
		hover = Math.max(0, Math.min(labels.length - 1, Math.round(((px - pad.l) / (width - pad.l - pad.r)) * (labels.length - 1))));
	}
</script>

<div class="chart" class:dark bind:clientWidth={width}>
	<svg viewBox="0 0 {width} {height}" {height} role="img" aria-label={series.map((s) => s.name).join(' and ')} onpointermove={move} onpointerleave={() => (hover = null)}>
		<defs>
			{#each series as s, i}
				<linearGradient id="ac-{uid}-{i}" x1="0" y1="0" x2="0" y2="1">
					<stop offset="0" style:stop-color={s.color} stop-opacity=".32" />
					<stop offset="1" style:stop-color={s.color} stop-opacity="0" />
				</linearGradient>
			{/each}
		</defs>
		{#each ticks as t}
			<line x1={pad.l} x2={width - pad.r} y1={y(t)} y2={y(t)} class="grid" />
			<text x={pad.l - 5} y={y(t) + 2.5} class="tick" text-anchor="end">{format(Math.round(t * 10) / 10)}</text>
		{/each}
		{#if zero && min < 0}<line x1={pad.l} x2={width - pad.r} y1={y(0)} y2={y(0)} class="zero" />{/if}
		{#each labels as label, i}
			{#if i % 2 === 0 || labels.length < 8}<text x={x(i)} y={height - 4} class="tick" text-anchor="middle">{label}</text>{/if}
		{/each}
		{#each series as s, i}
			{@const pts = s.values.map((v, j) => [x(j), y(v)] as [number, number])}
			{@const d = smoothPath(pts)}
			<path d="{d} L{pts[pts.length - 1][0]},{y(zero ? Math.max(min, 0) : min)} L{pts[0][0]},{y(zero ? Math.max(min, 0) : min)} Z" fill="url(#ac-{uid}-{i})" class="area" />
			<path {d} fill="none" style:stroke={s.color} stroke-width="1.8" class="line" />
		{/each}
		{#if hover !== null}
			<line x1={x(hover)} x2={x(hover)} y1={pad.t} y2={height - pad.b} class="cursor" />
			{#each series as s}<circle cx={x(hover)} cy={y(s.values[hover])} r="3.2" style:fill={s.color} stroke="white" stroke-width="1.4" />{/each}
		{/if}
	</svg>
	{#if hover !== null}
		<div class="tip" style:left="{Math.min(width - 110, Math.max(0, x(hover) - 50))}px">
			<strong>{labels[hover]}</strong>
			{#each series as s}<span><i style:background={s.color}></i>{s.name}<b>{format(s.values[hover])}</b></span>{/each}
		</div>
	{/if}
</div>

<style>
	.chart {
		position: relative;
		width: 100%;
	}
	svg {
		display: block;
		width: 100%;
		overflow: visible;
	}
	.grid {
		stroke: rgba(31, 53, 45, 0.08);
	}
	.zero {
		stroke: rgba(31, 53, 45, 0.3);
		stroke-dasharray: 3 3;
	}
	.tick {
		fill: #7b8781;
		font-size: 6.5px;
	}
	.dark .grid {
		stroke: rgba(255, 255, 255, 0.07);
	}
	.dark .zero {
		stroke: rgba(255, 255, 255, 0.3);
	}
	.dark .tick {
		fill: rgba(220, 235, 228, 0.5);
	}
	.line {
		stroke-dasharray: 1400;
		stroke-dashoffset: 1400;
		animation: draw 1.4s cubic-bezier(0.3, 0.7, 0.2, 1) forwards;
	}
	.area {
		opacity: 0;
		animation: appear 0.9s 0.4s ease forwards;
	}
	@keyframes draw {
		to {
			stroke-dashoffset: 0;
		}
	}
	@keyframes appear {
		to {
			opacity: 1;
		}
	}
	.cursor {
		stroke: rgba(31, 53, 45, 0.25);
		stroke-dasharray: 2 2;
	}
	.dark .cursor {
		stroke: rgba(255, 255, 255, 0.3);
	}
	.tip {
		position: absolute;
		top: -4px;
		width: 110px;
		padding: 6px 7px;
		border-radius: 7px;
		background: rgba(18, 30, 26, 0.92);
		color: white;
		font-size: 7px;
		pointer-events: none;
		box-shadow: 0 8px 20px rgba(0, 0, 0, 0.2);
		backdrop-filter: blur(8px);
	}
	.tip strong {
		display: block;
		margin-bottom: 3px;
		font-size: 7.5px;
	}
	.tip span {
		display: flex;
		align-items: center;
		gap: 4px;
		color: rgba(255, 255, 255, 0.7);
	}
	.tip i {
		width: 5px;
		height: 5px;
		border-radius: 50%;
	}
	.tip b {
		margin-left: auto;
		color: white;
	}
</style>
