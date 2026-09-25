<script lang="ts">
	import TrendingUp from '~icons/lucide/trending-up';
	import Target from '~icons/lucide/target';
	import { syntheticEntities, type Entity } from '../directory';
	import { hash } from '../nj-towns';
	import { suite } from '../state.svelte';
	import { fitFor, marketCategories, money, sectors, type Sector } from '../suite-data';
	import Logo from '../ui/Logo.svelte';

	let lens = $state<'fit' | 'momentum'>('fit');
	let onlyThesis = $state(false);

	const categoryOf = (e: Entity) => e.deal?.category ?? marketCategories[e.sector][hash(e.id) % marketCategories[e.sector].length];

	const ordered = $derived([...sectors].sort((a, b) => Number(suite.firm.sectors.includes(b)) - Number(suite.firm.sectors.includes(a))).filter((s) => !onlyThesis || suite.firm.sectors.includes(s)));

	const map = $derived.by(() => {
		const bySector = new Map<Sector, { name: string; items: { e: Entity; score: number }[] }[]>();
		for (const s of sectors) bySector.set(s, marketCategories[s].map((name) => ({ name, items: [] })));
		for (const e of syntheticEntities) {
			const cat = bySector.get(e.sector)!.find((c) => c.name === categoryOf(e));
			cat?.items.push({ e, score: lens === 'fit' ? fitFor(e, suite.firm).total : e.momentum });
		}
		for (const cats of bySector.values()) for (const c of cats) c.items.sort((a, b) => b.score - a.score);
		return bySector;
	});

	function heat(score: number) {
		const t = Math.max(0, Math.min(1, (score - 40) / 55));
		return `color-mix(in srgb, var(--accent) ${Math.round(8 + t * 40)}%, rgba(255,255,255,.6))`;
	}
</script>

<header class="page-head">
	<div>
		<h1>Market map</h1>
		<p>{syntheticEntities.length.toLocaleString()} companies grouped by sector and category. Stronger color means a higher score.</p>
	</div>
	<div class="actions">
		<label class="toggle"><input type="checkbox" bind:checked={onlyThesis} /> In-thesis only</label>
		<div class="seg">
			<button class:on={lens === 'fit'} onclick={() => (lens = 'fit')}><Target /> Thesis fit</button>
			<button class:on={lens === 'momentum'} onclick={() => (lens = 'momentum')}><TrendingUp /> Momentum</button>
		</div>
	</div>
</header>

<div class="landscape">
	{#each ordered as sector (sector)}
		{@const cats = map.get(sector)!}
		{@const all = cats.flatMap((c) => c.items)}
		<section class="card sector" class:thesis={suite.firm.sectors.includes(sector)}>
			<header>
				<div><strong>{sector}</strong>{#if suite.firm.sectors.includes(sector)}<i class="pill accent">In thesis</i>{/if}</div>
				<small>{all.length} companies · {money(all.reduce((s, x) => s + (x.e.raise ?? 0), 0))} raised</small>
			</header>
			{#each cats as cat}
				<div class="category">
					<span class="cat-name">{cat.name}<b>{cat.items.length}</b></span>
					<div class="chips">
						{#each cat.items.slice(0, 6) as { e, score } (e.id)}
							<button class="chip" style:background={heat(score)} onclick={() => suite.open(e.id)} title="{e.name} · {lens === 'fit' ? 'fit' : 'momentum'} {score}">
								<Logo name={e.name} hue={e.hue} src={e.logo} seed={e.id} size={13} radius={3.5} />
								<span>{e.name}</span>
								<b>{score}</b>
							</button>
						{/each}
						{#if cat.items.length > 6}<span class="more">+{cat.items.length - 6}</span>{/if}
						{#if !cat.items.length}<span class="whitespace">No tracked companies yet</span>{/if}
					</div>
				</div>
			{/each}
		</section>
	{/each}
</div>

<style>
	.toggle {
		display: flex;
		align-items: center;
		gap: 5px;
		color: var(--muted);
		font-size: 7.5px;
		cursor: pointer;
	}

	.toggle input {
		accent-color: var(--accent);
	}

	.landscape {
		columns: 3 230px;
		column-gap: 10px;
	}

	.sector {
		break-inside: avoid;
		margin-bottom: 10px;
		padding: 11px;
	}

	.sector.thesis {
		border-color: var(--accent-line);
		box-shadow: var(--glass-shadow), 0 0 0 1px var(--accent-soft);
	}

	.sector header {
		margin-bottom: 8px;
	}

	.sector header div {
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.sector header strong {
		font-size: 11px;
		letter-spacing: -0.02em;
	}

	.sector header small {
		display: block;
		margin-top: 2px;
		color: var(--faint);
		font-size: 6.4px;
	}

	.sector .pill {
		font-style: normal;
	}

	.category {
		padding: 7px 0;
		border-top: 1px solid var(--line);
	}

	.cat-name {
		display: flex;
		justify-content: space-between;
		margin-bottom: 5px;
		color: var(--muted);
		font-size: 7.2px;
		font-weight: 600;
	}

	.cat-name b {
		font-weight: 500;
	}

	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 3px;
	}

	.chip {
		max-width: 100%;
		display: inline-flex;
		align-items: center;
		gap: 4px;
		padding: 2px 5px 2px 2px;
		border: 1px solid rgba(255, 255, 255, 0.6);
		border-radius: 5px;
		font-size: 6.5px;
		transition: transform 0.12s ease, box-shadow 0.12s ease;
	}

	.chip:hover {
		transform: translateY(-1px);
		box-shadow: 0 4px 10px rgba(15, 35, 28, 0.12);
	}

	.chip span {
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
	}

	.chip b {
		color: var(--accent-deep);
		font-size: 5.8px;
	}

	.more {
		align-self: center;
		padding: 0 4px;
		color: var(--faint);
		font-size: 6.3px;
	}

	.whitespace {
		width: 100%;
		padding: 5px;
		border: 1px dashed rgba(200, 139, 51, 0.5);
		border-radius: 5px;
		background: var(--amber-soft);
		color: #8d5f1f;
		font-size: 6.3px;
		text-align: center;
	}
</style>
