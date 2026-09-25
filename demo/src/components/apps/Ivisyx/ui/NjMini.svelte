<script lang="ts">
	import { geoMercator, geoPath } from 'd3-geo';
	import { countyMesh, newJersey, towns } from '../geo';

	type Props = { width?: number; height?: number; pulse?: [number, number] | null };
	const { width = 180, height = 220, pulse = null }: Props = $props();

	const projection = $derived(geoMercator().fitExtent([[8, 8], [width - 8, height - 8]], newJersey));
	const path = $derived(geoPath(projection));
	const dots = $derived(towns.filter((t) => t.weight >= 3).map((t) => ({ t, p: projection(t.coordinates) as [number, number] })));
	const ping = $derived(pulse ? (projection(pulse) as [number, number]) : null);
</script>

<svg viewBox="0 0 {width} {height}" {width} {height} class="mini" aria-hidden="true">
	<defs>
		<radialGradient id="nm-heat"><stop offset="0" style:stop-color="var(--accent-glow)" stop-opacity=".7" /><stop offset="1" style:stop-color="var(--accent-glow)" stop-opacity="0" /></radialGradient>
	</defs>
	<path d={path(newJersey)} class="land" />
	<path d={path(countyMesh)} class="mesh" />
	<g style:mix-blend-mode="screen" opacity=".6">
		{#each dots as { t, p } (t.id)}<circle cx={p[0]} cy={p[1]} r={2 + t.signals30d * 0.22} fill="url(#nm-heat)" />{/each}
	</g>
	{#each dots as { t, p } (t.id)}
		{#if t.weight >= 6}<circle cx={p[0]} cy={p[1]} r="1.3" class="node" />{/if}
	{/each}
	{#if ping}
		<circle cx={ping[0]} cy={ping[1]} r="2.2" fill="#ffd27a" />
	{/if}
</svg>

<style>
	.mini {
		display: block;
		overflow: visible;
	}
	.land {
		fill: rgba(140, 240, 200, 0.08);
		stroke: color-mix(in oklab, var(--accent-glow) 70%, white);
		stroke-width: 1;
	}
	.mesh {
		fill: none;
		stroke: rgba(160, 240, 210, 0.22);
		stroke-width: 0.5;
		stroke-dasharray: 2 2;
	}
	.node {
		fill: #e6fff4;
	}
</style>
