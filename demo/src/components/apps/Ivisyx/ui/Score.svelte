<script lang="ts">
	const { value }: { value: number } = $props();
	const tier = $derived(value >= 80 ? 'high' : value >= 60 ? 'mid' : 'low');
</script>

<span class="score {tier}" title="Thesis fit {value}/100">{value}</span>

<style>
	.score {
		min-width: 22px;
		height: 15px;
		display: inline-grid;
		place-items: center;
		flex: 0 0 auto;
		padding: 0 4px;
		border-radius: 4px;
		font-size: 7px;
		font-weight: 650;
		font-variant-numeric: tabular-nums;
	}

	.high {
		background: var(--accent-soft);
		color: var(--accent-deep);
	}

	.mid {
		background: rgba(200, 139, 51, 0.14);
		color: #8d5f1f;
	}

	.low {
		background: rgba(103, 116, 109, 0.12);
		color: #5f6c66;
	}
</style>
