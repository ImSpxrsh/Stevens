<script lang="ts">
	import { fade } from 'svelte/transition';
	import logo from '@ivisyx/logo.svg?raw';
	import type { TitleCard } from './engine.svelte';

	const { card, vw, vh }: { card: TitleCard | null; vw: number; vh: number } = $props();
	// Type is designed at 1920 wide and scales with the frame, so social cuts stay balanced.
	const unit = $derived(Math.min(vw, vh * 1.6) / 1920);
</script>

{#key card?.id}
	{#if card}
		<div class="title {card.backdrop ?? 'dim'} {card.size ?? 'statement'}" style:--u={unit} in:fade|global={{ duration: 450 }} out:fade|global={{ duration: 500 }}>
			<div class="inner">
				{#if card.logo}<div class="logo">{@html logo}</div>{/if}
				{#if card.kicker}<p class="kicker" style:--d="0ms">{card.kicker}</p>{/if}
				{#each card.lines as line, li}
					<h1>
						{#each line.split(' ') as word, wi}<span style:--d="{(card.logo ? 650 : 120) + (li * 3 + wi) * 110}ms">{word}</span>{' '}{/each}
					</h1>
				{/each}
				{#if card.sub}<p class="sub" style:--d="{card.logo ? 1500 : 700}ms">{card.sub}</p>{/if}
				{#if card.fine}<p class="fine" style:--d="2300ms">{card.fine}</p>{/if}
			</div>
		</div>
	{/if}
{/key}

<style>
	.title {
		position: absolute;
		inset: 0;
		z-index: 20;
		display: grid;
		place-items: center;
		color: #f5f7f6;
		text-align: center;
		pointer-events: none;
	}

	.black {
		background: #000;
	}

	.dim {
		background: rgba(4, 8, 7, 0.6);
		backdrop-filter: blur(22px) saturate(1.15);
	}

	.inner {
		display: grid;
		justify-items: center;
		padding: 0 calc(120px * var(--u));
	}

	h1 {
		margin: 0;
		font-weight: 700;
		line-height: 1.02;
		letter-spacing: -0.045em;
	}

	.hero h1 {
		font-size: calc(200px * var(--u));
		letter-spacing: -0.055em;
	}

	.statement h1 {
		font-size: calc(112px * var(--u));
	}

	.statement h1 + h1 {
		color: rgba(245, 247, 246, 0.55);
	}

	span,
	.kicker,
	.sub,
	.fine {
		display: inline-block;
		opacity: 0;
		filter: blur(calc(18px * var(--u)));
		transform: translateY(0.3em);
		animation: resolve 1.1s cubic-bezier(0.2, 0.7, 0.2, 1) var(--d) forwards;
	}

	@keyframes resolve {
		to {
			opacity: 1;
			filter: blur(0);
			transform: none;
		}
	}

	.kicker {
		margin: 0 0 calc(22px * var(--u));
		color: rgba(245, 247, 246, 0.6);
		font-size: calc(34px * var(--u));
		font-weight: 600;
	}

	.sub {
		margin: calc(26px * var(--u)) 0 0;
		color: rgba(235, 242, 238, 0.62);
		font-size: calc(44px * var(--u));
		font-weight: 500;
		letter-spacing: -0.02em;
	}

	.fine {
		max-width: calc(1100px * var(--u));
		margin: calc(90px * var(--u)) 0 0;
		color: rgba(235, 242, 238, 0.4);
		font-size: calc(19px * var(--u));
		line-height: 1.5;
	}

	.logo {
		width: calc(200px * var(--u));
		margin-bottom: calc(40px * var(--u));
		clip-path: inset(0 100% 0 0);
		transform: scale(0.9);
		filter: blur(calc(10px * var(--u)));
		animation: wipe 1.3s cubic-bezier(0.65, 0, 0.35, 1) 0.1s forwards;
	}

	.logo :global(svg) {
		display: block;
		width: 100%;
		height: auto;
		filter: drop-shadow(0 calc(20px * var(--u)) calc(40px * var(--u)) rgba(0, 0, 0, 0.5));
	}

	/* The logo reads light-on-dark: invert the dark plate into a bright one. */
	.black .logo :global(svg) {
		filter: invert(1) hue-rotate(180deg) brightness(1.05);
	}

	@keyframes wipe {
		to {
			clip-path: inset(0 0 0 0);
			transform: none;
			filter: blur(0);
		}
	}
</style>
