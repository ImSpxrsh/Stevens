<script lang="ts">
	const { x, y, visible, down, ripple, scale }: { x: number; y: number; visible: boolean; down: boolean; ripple: number; scale: number } = $props();
	// The pointer lives in the recorded screen, so it zooms with the camera,
	// but not all the way: at 3× zoom a true-scale cursor would fill the frame.
	const size = $derived(1 / scale ** 0.55);
</script>

<div class="cursor" class:visible style:transform="translate({x}px, {y}px) scale({size})">
	{#if ripple}{#key ripple}<i class="ripple"></i>{/key}{/if}
	<svg class:down viewBox="0 0 28 34" width="28" height="34" aria-hidden="true">
		<path d="M4 2.5v24.2l6.1-5.9 3.7 8.8 4-1.7-3.7-8.6h8.7Z" fill="#111" stroke="#fff" stroke-width="1.6" stroke-linejoin="round" />
	</svg>
</div>

<style>
	.cursor {
		position: absolute;
		left: 0;
		top: 0;
		z-index: 30;
		width: 0;
		height: 0;
		opacity: 0;
		transform-origin: 0 0;
		transition: opacity 0.25s ease;
		pointer-events: none;
	}

	.visible {
		opacity: 1;
	}

	svg {
		position: absolute;
		left: -4px;
		top: -2px;
		overflow: visible;
		filter: drop-shadow(0 3px 5px rgba(0, 0, 0, 0.35));
		transition: transform 0.1s ease;
		transform-origin: 4px 2px;
	}

	svg.down {
		transform: scale(0.86);
	}

	.ripple {
		position: absolute;
		left: -22px;
		top: -22px;
		width: 44px;
		height: 44px;
		border: 2px solid rgba(255, 255, 255, 0.9);
		border-radius: 50%;
		box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.15);
		opacity: 0;
		animation: ripple 0.55s ease-out;
	}

	@keyframes ripple {
		from {
			transform: scale(0.3);
			opacity: 0.9;
		}
		to {
			transform: scale(1.3);
			opacity: 0;
		}
	}
</style>
