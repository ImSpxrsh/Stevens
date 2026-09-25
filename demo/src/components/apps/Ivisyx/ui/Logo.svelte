<script lang="ts">
	import { hash } from '../nj-towns';

	type Props = { name: string; hue?: number; src?: string; size?: number; seed?: string; radius?: number };
	const { name, hue, src, size = 28, seed, radius }: Props = $props();

	const uid = $props.id();
	const key = $derived(hash(seed ?? name));
	const h = $derived(hue ?? key % 360);
	const variant = $derived(key % 12);
	let failed = $state(false);
</script>

<span class="logo" style:width="{size}px" style:height="{size}px" style:border-radius="{radius ?? size * 0.26}px">
	{#if src && !failed}
		<img {src} alt="" onerror={() => (failed = true)} />
	{:else}
		<svg viewBox="0 0 32 32" aria-hidden="true">
			<defs>
				<linearGradient id="lg-{uid}" x1="0" y1="0" x2="1" y2="1">
					<stop offset="0" stop-color="hsl({h} 64% 56%)" />
					<stop offset="1" stop-color="hsl({(h + 32) % 360} 70% 30%)" />
				</linearGradient>
			</defs>
			<rect width="32" height="32" fill="url(#lg-{uid})" />
			<rect width="32" height="16" fill="white" opacity=".08" />
			<g fill="white" stroke="white" stroke-linecap="round" stroke-linejoin="round">
				{#if variant === 0}
					<circle cx="16" cy="16" r="7.5" fill="none" stroke-width="3" /><circle cx="16" cy="16" r="2.4" stroke="none" />
				{:else if variant === 1}
					<rect x="8" y="9" width="16" height="3.4" rx="1.7" stroke="none" transform="skewX(-14)" /><rect x="10" y="14.3" width="12" height="3.4" rx="1.7" stroke="none" opacity=".8" transform="skewX(-14)" /><rect x="12" y="19.6" width="14" height="3.4" rx="1.7" stroke="none" opacity=".6" transform="skewX(-14)" />
				{:else if variant === 2}
					<path d="M16 7.5 25 23.5H7Z" stroke="none" /><path d="M16 14.5 20 21.5H12Z" fill="url(#lg-{uid})" stroke="none" />
				{:else if variant === 3}
					<path d="M16 7 23.8 11.5v9L16 25l-7.8-4.5v-9Z" fill="none" stroke-width="2.6" /><circle cx="16" cy="16" r="2.6" stroke="none" />
				{:else if variant === 4}
					<circle cx="13" cy="16" r="6.4" stroke="none" opacity=".7" /><circle cx="19.5" cy="16" r="6.4" stroke="none" opacity=".95" />
				{:else if variant === 5}
					<rect x="10" y="10" width="12" height="12" rx="2" stroke="none" transform="rotate(45 16 16)" /><path d="M11 16h10" stroke="url(#lg-{uid})" stroke-width="2.4" />
				{:else if variant === 6}
					<path d="M6.5 18c3-7 6.5-7 9.5 0s6.5 7 9.5 0" fill="none" stroke-width="3" /><circle cx="16" cy="10" r="2" stroke="none" />
				{:else if variant === 7}
					<ellipse cx="16" cy="16" rx="10.5" ry="4.4" fill="none" stroke-width="2.2" transform="rotate(-32 16 16)" /><circle cx="16" cy="16" r="3.4" stroke="none" />
				{:else if variant === 8}
					<text x="16" y="21.5" text-anchor="middle" stroke="none" font-size="15" font-weight="800" font-family="-apple-system, Inter, sans-serif">{name.charAt(0)}</text>
				{:else if variant === 9}
					<path d="M16 8a8 8 0 0 1 8 8h-8Z" stroke="none" /><path d="M16 24a8 8 0 0 1-8-8h8Z" stroke="none" opacity=".75" /><circle cx="21" cy="21" r="2.5" stroke="none" opacity=".9" />
				{:else if variant === 10}
					<rect x="8.5" y="8.5" width="6" height="6" rx="1.6" stroke="none" /><rect x="17.5" y="8.5" width="6" height="6" rx="3" stroke="none" opacity=".7" /><rect x="8.5" y="17.5" width="6" height="6" rx="3" stroke="none" opacity=".7" /><rect x="17.5" y="17.5" width="6" height="6" rx="1.6" stroke="none" />
				{:else}
					<path d="M13 8h9l-3 16h-9Z" stroke="none" /><path d="M16.5 11.5h2.6l-1.8 9.2h-2.6Z" fill="url(#lg-{uid})" stroke="none" />
				{/if}
			</g>
		</svg>
	{/if}
</span>

<style>
	.logo {
		position: relative;
		display: inline-grid;
		flex: 0 0 auto;
		overflow: hidden;
		background: white;
		box-shadow: 0 0 0 0.5px rgba(20, 40, 33, 0.14), 0 2px 6px rgba(15, 35, 28, 0.12);
	}
	img {
		width: 100%;
		height: 100%;
		padding: 12%;
		object-fit: contain;
	}
	svg {
		width: 100%;
		height: 100%;
		display: block;
	}
</style>
