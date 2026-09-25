<script lang="ts">
	import ArrowUpRight from '~icons/lucide/arrow-up-right';
	import Bookmark from '~icons/lucide/bookmark';
	import MapPin from '~icons/lucide/map-pin';
	import Search from '~icons/lucide/search';
	import X from '~icons/lucide/x';
	import { entities } from '../directory';
	import { counties } from '../geo';
	import { suite } from '../state.svelte';
	import { fitFor, money, sectors, stages } from '../suite-data';
	import Logo from '../ui/Logo.svelte';
	import Score from '../ui/Score.svelte';

	let query = $state('');
	let dataset = $state<'all' | 'real' | 'synthetic' | 'saved'>('all');
	let sector = $state('');
	let stage = $state('');
	let county = $state('');
	let sort = $state<'fit' | 'momentum' | 'name'>('fit');
	let limit = $state(36);

	const scored = $derived(entities.map((e) => ({ e, fit: e.real ? null : fitFor(e, suite.firm).total })));
	const filtered = $derived.by(() => {
		const q = query.trim().toLowerCase();
		return scored
			.filter(({ e }) => {
				if (dataset === 'real' && !e.real) return false;
				if (dataset === 'synthetic' && e.real) return false;
				if (dataset === 'saved' && !suite.saved.includes(e.id)) return false;
				if (sector && e.sector !== sector) return false;
				if (stage && e.stage !== stage) return false;
				if (county && e.county !== county) return false;
				return !q || `${e.name} ${e.town} ${e.sector} ${e.description}`.toLowerCase().includes(q);
			})
			.sort((a, b) =>
				sort === 'name' ? a.e.name.localeCompare(b.e.name) : sort === 'momentum' ? b.e.momentum - a.e.momentum : Number(b.e.real) - Number(a.e.real) || (b.fit ?? 0) - (a.fit ?? 0),
			);
	});
	const realCount = entities.filter((e) => e.real).length;

	function clear() {
		query = sector = stage = county = '';
		dataset = 'all';
	}
</script>

<header class="page-head">
	<div>
		<h1>Companies</h1>
		<p>{entities.length.toLocaleString()} companies. {realCount} are real, verified profiles; the rest are synthetic.</p>
	</div>
	<div class="actions">
		<select class="select" bind:value={sort} aria-label="Sort">
			<option value="fit">Sort: Thesis fit</option>
			<option value="momentum">Sort: Momentum</option>
			<option value="name">Sort: Name</option>
		</select>
	</div>
</header>

<div class="filters">
	<label class="field"><Search /><input bind:value={query} placeholder="Search companies, towns, sectors…" aria-label="Search companies" />{#if query}<button onclick={() => (query = '')} aria-label="Clear"><X /></button>{/if}</label>
	<div class="seg">
		<button class:on={dataset === 'all'} onclick={() => (dataset = 'all')}>All</button>
		<button class:on={dataset === 'real'} onclick={() => (dataset = 'real')}>Real <b>{realCount}</b></button>
		<button class:on={dataset === 'synthetic'} onclick={() => (dataset = 'synthetic')}>Synthetic</button>
		<button class:on={dataset === 'saved'} onclick={() => (dataset = 'saved')}>Watchlist <b>{suite.saved.length}</b></button>
	</div>
	<select class="select" bind:value={sector} aria-label="Sector"><option value="">All sectors</option>{#each sectors as s}<option>{s}</option>{/each}</select>
	<select class="select" bind:value={stage} aria-label="Stage"><option value="">All stages</option>{#each stages as s}<option>{s}</option>{/each}</select>
	<select class="select" bind:value={county} aria-label="County"><option value="">All counties</option>{#each counties as c}<option>{c.name}</option>{/each}</select>
</div>

<div class="count">{filtered.length.toLocaleString()} results {#if query || sector || stage || county || dataset !== 'all'}<button onclick={clear}>Clear filters</button>{/if}</div>

<div class="grid">
	{#each filtered.slice(0, limit) as { e, fit }, i (e.id)}
		<article class="card profile">
			<div class="top">
				<Logo name={e.name} hue={e.hue} src={e.logo} seed={e.id} size={34} />
				<div class="top-right">
					{#if fit !== null}<Score value={fit} />{/if}
					<button class="save" class:saved={suite.saved.includes(e.id)} onclick={() => suite.toggleSaved(e.id)} aria-label="{suite.saved.includes(e.id) ? 'Remove' : 'Add'} {e.name} watchlist"><Bookmark /></button>
				</div>
			</div>
			<span class="pill {e.real ? 'accent' : 'amber'}">{e.real ? 'Real company' : 'Synthetic'}</span>
			<h2>{e.name}</h2>
			<p>{e.description}</p>
			<div class="meta">
				<span><MapPin />{e.town}{e.state !== 'NJ' ? `, ${e.state}` : ''}</span>
				<span>{e.sector}</span>
				{#if e.stage}<span>{e.stage}</span>{/if}
				{#if e.raise}<span>{money(e.raise)}</span>{/if}
			</div>
			<button class="open" onclick={() => suite.open(e.id)}>View profile <ArrowUpRight /></button>
		</article>
	{:else}
		<div class="empty card"><Bookmark /><h2>{dataset === 'saved' ? 'Your watchlist is empty.' : 'No companies match.'}</h2><p>{dataset === 'saved' ? 'Bookmark companies to follow them here.' : 'Try a different search or clear filters.'}</p><button class="btn primary" onclick={clear}>Show all companies</button></div>
	{/each}
</div>

{#if filtered.length > limit}
	<div class="more"><button class="btn" onclick={() => (limit += 36)}>Show more · {(filtered.length - limit).toLocaleString()} remaining</button></div>
{/if}

<style>
	.filters {
		display: grid;
		grid-template-columns: minmax(160px, 1fr) auto auto auto auto;
		gap: 6px;
		align-items: center;
	}

	.filters .field button {
		color: var(--faint);
		font-size: 10px;
	}

	.count {
		display: flex;
		gap: 8px;
		margin: 10px 2px 8px;
		color: var(--faint);
		font-size: 7px;
	}

	.count button {
		color: var(--accent);
		font-weight: 600;
	}

	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(176px, 1fr));
		gap: 9px;
	}

	.profile {
		display: flex;
		flex-direction: column;
		padding: 12px;
		transition: transform 0.18s ease, box-shadow 0.18s ease;
	}

	.profile:hover {
		transform: translateY(-2px);
		box-shadow: var(--glass-shadow), 0 16px 32px rgba(13, 35, 28, 0.1);
	}

	.top {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		margin-bottom: 9px;
	}

	.top-right {
		display: flex;
		align-items: center;
		gap: 4px;
	}

	.save {
		width: 22px;
		height: 22px;
		display: grid;
		place-items: center;
		border-radius: 6px;
		color: var(--faint);
		font-size: 11px;
	}

	.save:hover {
		background: rgba(31, 53, 45, 0.07);
	}

	.save.saved {
		color: var(--accent);
	}

	.save.saved :global(path) {
		fill: currentColor;
	}

	.pill {
		align-self: flex-start;
	}

	h2 {
		margin: 6px 0 4px;
		font-size: 11px;
		letter-spacing: -0.02em;
	}

	p {
		flex: 1;
		color: var(--muted);
		font-size: 7px;
		line-height: 1.45;
	}

	.meta {
		display: flex;
		flex-wrap: wrap;
		gap: 3px 8px;
		margin: 9px 0;
		color: var(--faint);
		font-size: 6.4px;
	}

	.meta span {
		display: flex;
		align-items: center;
		gap: 2px;
	}

	.open {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding-top: 8px;
		border-top: 1px solid var(--line);
		color: var(--accent-deep);
		font-size: 7.2px;
		font-weight: 650;
	}

	.empty {
		grid-column: 1 / -1;
		display: grid;
		justify-items: center;
		gap: 6px;
		padding: 40px;
		text-align: center;
		font-size: 20px;
		color: var(--faint);
	}

	.empty h2 {
		color: var(--ink);
		font-size: 13px;
	}

	.more {
		display: grid;
		place-items: center;
		margin-top: 12px;
	}
</style>
