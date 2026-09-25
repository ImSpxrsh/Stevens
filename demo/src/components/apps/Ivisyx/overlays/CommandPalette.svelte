<script lang="ts">
	import { onMount } from 'svelte';
	import { fade, scale } from 'svelte/transition';
	import ArrowRight from '~icons/lucide/arrow-right';
	import CornerDownLeft from '~icons/lucide/corner-down-left';
	import MapPin from '~icons/lucide/map-pin';
	import Search from '~icons/lucide/search';
	import Sparkles from '~icons/lucide/sparkles';
	import Zap from '~icons/lucide/zap';
	import { entities } from '../directory';
	import { towns } from '../geo';
	import { suite, viewLabels, type View } from '../state.svelte';
	import { firmPresets } from '../suite-data';
	import Logo from '../ui/Logo.svelte';

	type Item = { group: string; label: string; sub?: string; run: () => void; entity?: (typeof entities)[number]; icon?: 'go' | 'town' | 'action' | 'ai' };

	let query = $state('');
	let index = $state(0);
	let inputEl = $state<HTMLInputElement>();

	const items = $derived.by(() => {
		const q = query.trim().toLowerCase();
		const has = (s: string) => !q || s.toLowerCase().includes(q);
		const out: Item[] = [];
		for (const [id, label] of Object.entries(viewLabels)) if (has(label)) out.push({ group: 'Go to', label, run: () => suite.go(id as View), icon: 'go' });
		if (q) {
			for (const e of entities.filter((e) => has(`${e.name} ${e.town} ${e.sector}`)).slice(0, 6)) out.push({ group: 'Companies', label: e.name, sub: `${e.real ? 'Real' : e.sector} · ${e.town}`, run: () => suite.open(e.id), entity: e });
			for (const t of towns.filter((t) => has(t.name)).slice(0, 4)) out.push({ group: 'Towns', label: t.name, sub: `${t.county} · ${t.startups} startups`, run: () => { suite.radarTarget = t.id; suite.go('radar'); }, icon: 'town' });
		}
		const actions: Item[] = [
			{ group: 'Actions', label: 'Simulate a new signal', run: () => { suite.addSignal(); suite.toast('New signal simulated', 'success'); }, icon: 'action' },
			{ group: 'Actions', label: suite.playing ? 'Pause live stream' : 'Resume live stream', run: () => (suite.playing = !suite.playing), icon: 'action' },
			{ group: 'Actions', label: 'Set up your firm & thesis', run: () => (suite.setupOpen = true), icon: 'action' },
			...firmPresets.filter((f) => f.id !== suite.firmId).map((f) => ({ group: 'Actions', label: `Switch workspace to ${f.name}`, run: () => { suite.firmId = f.id; suite.toast(`Switched to ${f.name}`, 'success'); }, icon: 'action' as const })),
		];
		out.push(...actions.filter((a) => has(a.label)));
		if (q) out.push({ group: 'Ivisyx AI', label: `Ask: “${query.trim()}”`, run: () => suite.ask(query.trim()), icon: 'ai' });
		return out;
	});

	$effect(() => {
		query;
		index = 0;
	});

	function run(item: Item | undefined) {
		if (!item) return;
		suite.paletteOpen = false;
		item.run();
	}

	function onkeydown(event: KeyboardEvent) {
		if (event.key === 'ArrowDown') {
			event.preventDefault();
			index = Math.min(items.length - 1, index + 1);
		} else if (event.key === 'ArrowUp') {
			event.preventDefault();
			index = Math.max(0, index - 1);
		} else if (event.key === 'Enter') {
			event.preventDefault();
			run(items[index]);
		}
	}

	onMount(() => inputEl?.focus());
</script>

<div class="backdrop" role="presentation" transition:fade={{ duration: 120 }} onclick={(e) => e.target === e.currentTarget && (suite.paletteOpen = false)}>
	<div class="palette" role="dialog" aria-modal="true" aria-label="Command palette" transition:scale={{ start: 0.97, duration: 140 }}>
		<label class="input"><Search /><input bind:this={inputEl} bind:value={query} {onkeydown} placeholder="Search companies, towns, screens, or ask a question…" aria-label="Command" /><kbd>esc</kbd></label>
		<div class="results scroll">
			{#each items as item, i}
				{#if i === 0 || items[i - 1].group !== item.group}<div class="group">{item.group}</div>{/if}
				<button class:active={i === index} onmouseenter={() => (index = i)} onclick={() => run(item)}>
					<span class="icon">
						{#if item.entity}<Logo name={item.entity.name} hue={item.entity.hue} src={item.entity.logo} seed={item.entity.id} size={18} />
						{:else if item.icon === 'town'}<MapPin />
						{:else if item.icon === 'ai'}<Sparkles />
						{:else if item.icon === 'action'}<Zap />
						{:else}<ArrowRight />{/if}
					</span>
					<span class="label">{item.label}{#if item.sub}<small>{item.sub}</small>{/if}</span>
					{#if i === index}<CornerDownLeft />{/if}
				</button>
			{:else}
				<div class="empty">No results.</div>
			{/each}
		</div>
		<footer><span><kbd>↑</kbd><kbd>↓</kbd> navigate</span><span><kbd>↵</kbd> open</span><span><kbd>⌘K</kbd> toggle</span></footer>
	</div>
</div>

<style>
	.backdrop {
		position: absolute;
		inset: 0;
		z-index: 50;
		display: flex;
		justify-content: center;
		padding-top: 70px;
		background: rgba(8, 18, 15, 0.3);
		color: var(--ink);
		backdrop-filter: blur(3px);
	}

	.palette {
		width: min(460px, 86%);
		height: max-content;
		max-height: 70%;
		display: flex;
		flex-direction: column;
		overflow: hidden;
		border: 1px solid rgba(255, 255, 255, 0.7);
		border-radius: 14px;
		background: rgba(248, 250, 248, 0.96);
		box-shadow: 0 30px 80px rgba(5, 20, 14, 0.35);
		backdrop-filter: blur(30px);
	}

	.input {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 12px 14px;
		border-bottom: 1px solid var(--line);
		color: var(--muted);
		font-size: 13px;
	}

	.input input {
		flex: 1;
		border: 0;
		outline: 0;
		background: transparent;
		color: var(--ink);
		font-size: 10px;
	}

	.results {
		min-height: 0;
		padding: 6px;
	}

	.group {
		padding: 7px 8px 4px;
		color: var(--faint);
		font-size: 6.3px;
		font-weight: 700;
		letter-spacing: 0.1em;
		text-transform: uppercase;
	}

	.results button {
		width: 100%;
		display: grid;
		grid-template-columns: 20px 1fr auto;
		align-items: center;
		gap: 8px;
		padding: 6px 8px;
		border-radius: 8px;
		color: var(--ink-2);
		font-size: 8.3px;
		text-align: left;
	}

	.results button.active {
		background: var(--accent-deep);
		color: white;
	}

	.results button.active small {
		color: rgba(255, 255, 255, 0.65);
	}

	.icon {
		display: grid;
		place-items: center;
		color: var(--accent);
		font-size: 11px;
	}

	.active .icon {
		color: #b8f5dc;
	}

	.label small {
		margin-left: 7px;
		color: var(--faint);
		font-size: 6.8px;
	}

	.empty {
		padding: 20px;
		color: var(--faint);
		text-align: center;
	}

	footer {
		display: flex;
		gap: 12px;
		padding: 8px 14px;
		border-top: 1px solid var(--line);
		color: var(--faint);
		font-size: 6.6px;
	}

	footer kbd {
		margin-right: 2px;
	}
</style>
