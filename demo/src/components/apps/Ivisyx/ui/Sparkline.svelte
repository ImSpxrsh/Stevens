<script lang="ts" module>
	/** Smooth path through points using a Catmull-Rom → cubic Bézier conversion. */
	export function smoothPath(points: [number, number][]) {
		if (points.length < 2) return '';
		let d = `M${points[0][0]},${points[0][1]}`;
		for (let i = 0; i < points.length - 1; i++) {
			const [x0, y0] = points[i - 1] ?? points[i];
			const [x1, y1] = points[i];
			const [x2, y2] = points[i + 1];
			const [x3, y3] = points[i + 2] ?? points[i + 1];
			d += ` C${x1 + (x2 - x0) / 6},${y1 + (y2 - y0) / 6} ${x2 - (x3 - x1) / 6},${y2 - (y3 - y1) / 6} ${x2},${y2}`;
		}
		return d;
	}
</script>

<script lang="ts">
	type Props = { values: number[]; width?: number; height?: number; color?: string; fill?: boolean; stroke?: number; dot?: boolean };
	const { values, width = 80, height = 24, color = 'var(--accent)', fill = true, stroke = 1.4, dot = true }: Props = $props();

	const uid = $props.id();
	const points = $derived.by(() => {
		const min = Math.min(...values);
		const range = Math.max(...values) - min || 1;
		return values.map((v, i) => [(i / (values.length - 1)) * (width - 4) + 2, height - 3 - ((v - min) / range) * (height - 6)] as [number, number]);
	});
	const line = $derived(smoothPath(points));
	const last = $derived(points[points.length - 1]);
</script>

<svg class="spark" viewBox="0 0 {width} {height}" {width} {height} aria-hidden="true">
	<defs>
		<linearGradient id="sp-{uid}" x1="0" y1="0" x2="0" y2="1">
			<stop offset="0" style:stop-color={color} stop-opacity=".28" />
			<stop offset="1" style:stop-color={color} stop-opacity="0" />
		</linearGradient>
	</defs>
	{#if fill}<path d="{line} L{last[0]},{height} L{points[0][0]},{height} Z" fill="url(#sp-{uid})" />{/if}
	<path d={line} fill="none" style:stroke={color} stroke-width={stroke} stroke-linecap="round" />
	{#if dot}<circle cx={last[0]} cy={last[1]} r="2" style:fill={color} /><circle cx={last[0]} cy={last[1]} r="4.5" style:fill={color} opacity=".18" />{/if}
</svg>

<style>
	.spark {
		display: block;
		overflow: visible;
	}
</style>
