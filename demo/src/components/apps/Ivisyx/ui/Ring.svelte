<script lang="ts">
	type Props = { value: number; size?: number; stroke?: number; color?: string; label?: boolean; track?: string };
	const { value, size = 30, stroke = 3, color, label = true, track = 'rgba(31, 53, 45, 0.1)' }: Props = $props();

	const r = $derived((size - stroke) / 2);
	const c = $derived(2 * Math.PI * r);
	const tone = $derived(color ?? (value >= 80 ? 'var(--accent)' : value >= 60 ? '#c88b33' : '#8a958f'));
</script>

<span class="ring" style:width="{size}px" style:height="{size}px">
	<svg viewBox="0 0 {size} {size}" aria-hidden="true">
		<circle cx={size / 2} cy={size / 2} {r} fill="none" stroke={track} stroke-width={stroke} />
		<circle
			cx={size / 2}
			cy={size / 2}
			{r}
			fill="none"
			style:stroke={tone}
			stroke-width={stroke}
			stroke-linecap="round"
			stroke-dasharray="{(c * value) / 100} {c}"
			transform="rotate(-90 {size / 2} {size / 2})"
		/>
	</svg>
	{#if label}<b style:font-size="{size * 0.3}px">{value}</b>{/if}
</span>

<style>
	.ring {
		position: relative;
		display: inline-grid;
		place-items: center;
		flex: 0 0 auto;
	}
	svg {
		position: absolute;
		inset: 0;
		overflow: visible;
	}
	circle {
		transition: stroke-dasharray 0.6s cubic-bezier(0.3, 0.7, 0.2, 1);
	}
	b {
		font-weight: 700;
		letter-spacing: -0.03em;
		font-variant-numeric: tabular-nums;
	}
</style>
