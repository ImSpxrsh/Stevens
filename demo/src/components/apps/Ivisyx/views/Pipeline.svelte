<script lang="ts">
	import { flip } from 'svelte/animate';
	import ArrowRight from '~icons/lucide/arrow-right';
	import Clock from '~icons/lucide/clock';
	import Grip from '~icons/lucide/grip-vertical';
	import Kanban from '~icons/lucide/kanban';
	import List from '~icons/lucide/list-filter';
	import Plus from '~icons/lucide/plus';
	import { entityById, type Entity } from '../directory';
	import { suite } from '../state.svelte';
	import { deals, money, pipelineStages, team, type PipelineStage } from '../suite-data';
	import Logo from '../ui/Logo.svelte';
	import Ring from '../ui/Ring.svelte';

	let mode = $state<'board' | 'table'>('board');
	let owner = $state<string | null>(null);
	let dragId = $state<string | null>(null);
	let overStage = $state<PipelineStage | null>(null);
	let sortKey = $state<'fit' | 'raise' | 'days'>('fit');

	const stageTone: Record<PipelineStage, string> = {
		Sourced: '#8a958f', 'First meeting': '#2b5f9e', Diligence: '#c88b33', 'IC review': '#6a4fa3', 'Term sheet': 'var(--accent)', Closed: '#1a4d3d',
	};

	type Card = { e: Entity; stage: PipelineStage; fit: number; days: number; owner: string; next: string };
	const cards = $derived(
		Object.entries(suite.pipeline)
			.map(([id, stage]) => {
				const e = entityById.get(id)!;
				const d = deals.find((x) => x.id === id);
				return { e, stage, fit: suite.fit(id) ?? 0, days: d && d.pipeline === stage ? d.daysInStage : 0, owner: suite.owner(id), next: d?.nextStep ?? 'Schedule intro call' } as Card;
			})
			.filter((c) => c.e && (!owner || c.owner === owner)),
	);
	const columns = $derived(pipelineStages.map((stage) => {
		const list = cards.filter((c) => c.stage === stage).sort((a, b) => b.fit - a.fit);
		return { stage, list, total: list.reduce((s, c) => s + (c.e.raise ?? 0), 0) };
	}));
	const open = $derived(cards.filter((c) => c.stage !== 'Closed'));
	const sorted = $derived([...cards].sort((a, b) => (sortKey === 'fit' ? b.fit - a.fit : sortKey === 'raise' ? (b.e.raise ?? 0) - (a.e.raise ?? 0) : b.days - a.days)));

	function next(stage: PipelineStage) {
		return pipelineStages[Math.min(pipelineStages.length - 1, pipelineStages.indexOf(stage) + 1)];
	}
</script>

<header class="page-head">
	<div>
		<span class="eyebrow">Deal flow · {suite.firm.fund}</span>
		<h1>Pipeline</h1>
		<p>Drag companies between stages. Fit scores update with {suite.firm.name}'s thesis.</p>
	</div>
	<div class="actions">
		<div class="owners">
			<button class:on={!owner} onclick={() => (owner = null)}>All</button>
			{#each team as t}<button class:on={owner === t.id} onclick={() => (owner = owner === t.id ? null : t.id)} title={t.name}><span class="avatar" style:background={t.color}>{t.initials}</span></button>{/each}
		</div>
		<div class="seg">
			<button class:on={mode === 'board'} onclick={() => (mode = 'board')}><Kanban /> Board</button>
			<button class:on={mode === 'table'} onclick={() => (mode = 'table')}><List /> Table</button>
		</div>
		<button class="btn primary" onclick={() => (suite.paletteOpen = true)}><Plus /> Add deal</button>
	</div>
</header>

<div class="stats">
	<div class="card kpi"><small>Open deals</small><strong>{open.length}</strong><span>across {pipelineStages.length - 1} stages</span></div>
	<div class="card kpi"><small>Capital in play</small><strong>{money(open.reduce((s, c) => s + (c.e.raise ?? 0), 0))}</strong><span>total round size</span></div>
	<div class="card kpi"><small>Avg thesis fit</small><strong>{Math.round(open.reduce((s, c) => s + c.fit, 0) / Math.max(1, open.length))}</strong><span>out of 100</span></div>
	<div class="card kpi"><small>Closed this fund</small><strong>{cards.filter((c) => c.stage === 'Closed').length}</strong><span>{money(cards.filter((c) => c.stage === 'Closed').reduce((s, c) => s + (c.e.raise ?? 0) * 0.18, 0))} deployed</span></div>
</div>

{#if mode === 'board'}
	<div class="board scroll">
		{#each columns as col (col.stage)}
			<section
				class="column"
				class:over={overStage === col.stage}
				role="list"
				aria-label={col.stage}
				ondragover={(e) => { e.preventDefault(); overStage = col.stage; }}
				ondragleave={() => (overStage = overStage === col.stage ? null : overStage)}
				ondrop={(e) => { e.preventDefault(); if (dragId) suite.moveDeal(dragId, col.stage); dragId = null; overStage = null; }}
			>
				<header>
					<i style:background={stageTone[col.stage]}></i>
					<strong>{col.stage}</strong>
					<b>{col.list.length}</b>
					<span>{money(col.total)}</span>
				</header>
				<div class="cards scroll">
					{#each col.list as c (c.e.id)}
						<article
							class="deal"
							class:dragging={dragId === c.e.id}
							draggable="true"
							role="listitem"
							animate:flip={{ duration: 220 }}
							ondragstart={(e) => { dragId = c.e.id; e.dataTransfer?.setData('text/plain', c.e.id); }}
							ondragend={() => { dragId = null; overStage = null; }}
						>
							<button class="deal-main" onclick={() => suite.open(c.e.id)}>
								<div class="deal-top">
									<Logo name={c.e.name} hue={c.e.hue} src={c.e.logo} seed={c.e.id} size={22} />
									<span><strong>{c.e.name}</strong><small>{c.e.sector} · {c.e.town}</small></span>
									<Ring value={c.fit} size={22} stroke={2.2} />
								</div>
								<p>{c.next}</p>
								<div class="deal-meta">
									<i class="pill">{c.e.stage}</i>
									{#if c.e.raise}<i class="pill accent">{money(c.e.raise)}</i>{/if}
									<span class="days"><Clock />{c.days}d</span>
									<span class="avatar" style:background={team.find((t) => t.id === c.owner)?.color}>{team.find((t) => t.id === c.owner)?.initials}</span>
								</div>
							</button>
							<div class="deal-hover">
								<Grip />
								{#if c.stage !== 'Closed'}<button onclick={() => suite.moveDeal(c.e.id, next(c.stage))}>Move to {next(c.stage)} <ArrowRight /></button>{/if}
							</div>
						</article>
					{/each}
					{#if !col.list.length}<div class="empty">Drop a company here</div>{/if}
				</div>
			</section>
		{/each}
	</div>
{:else}
	<div class="card table-wrap scroll">
		<table>
			<thead>
				<tr>
					<th>Company</th><th>Stage</th><th>Pipeline</th>
					<th><button onclick={() => (sortKey = 'raise')} class:on={sortKey === 'raise'}>Round</button></th>
					<th><button onclick={() => (sortKey = 'fit')} class:on={sortKey === 'fit'}>Fit</button></th>
					<th><button onclick={() => (sortKey = 'days')} class:on={sortKey === 'days'}>Days</button></th>
					<th>Owner</th><th>Next step</th>
				</tr>
			</thead>
			<tbody>
				{#each sorted as c (c.e.id)}
					<tr onclick={() => suite.open(c.e.id)}>
						<td><div class="cell-co"><Logo name={c.e.name} hue={c.e.hue} src={c.e.logo} seed={c.e.id} size={20} /><span><strong>{c.e.name}</strong><small>{c.e.sector} · {c.e.town}</small></span></div></td>
						<td>{c.e.stage}</td>
						<td><span class="stage-chip" style:--tone={stageTone[c.stage]}>{c.stage}</span></td>
						<td class="num">{c.e.raise ? money(c.e.raise) : '—'}</td>
						<td><Ring value={c.fit} size={20} stroke={2} /></td>
						<td class="num">{c.days}d</td>
						<td><span class="avatar" style:background={team.find((t) => t.id === c.owner)?.color}>{team.find((t) => t.id === c.owner)?.initials}</span></td>
						<td class="muted">{c.next}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
{/if}

<style>
	.owners {
		display: flex;
		align-items: center;
		gap: 2px;
		padding: 2px;
		border-radius: 8px;
		background: rgba(52, 72, 64, 0.1);
	}

	.owners button {
		height: 22px;
		min-width: 22px;
		display: grid;
		place-items: center;
		padding: 0 5px;
		border-radius: 6px;
		color: var(--muted);
		font-size: 7px;
	}

	.owners button.on {
		background: rgba(255, 255, 255, 0.86);
		color: var(--accent-deep);
		font-weight: 650;
		box-shadow: 0 1px 4px rgba(28, 50, 42, 0.12);
	}

	.owners .avatar {
		width: 16px;
		height: 16px;
		font-size: 5.8px;
		box-shadow: none;
	}

	.stats {
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		gap: 8px;
		margin-bottom: 10px;
	}

	.stats .kpi {
		padding: 9px 11px;
	}

	.stats .kpi strong {
		font-size: 16px;
	}

	.board {
		flex: 1;
		min-height: 0;
		display: grid;
		grid-template-columns: repeat(6, minmax(118px, 1fr));
		gap: 8px;
		padding-bottom: 2px;
	}

	.column {
		min-height: 0;
		display: flex;
		flex-direction: column;
		border: 1px solid var(--glass-border);
		border-radius: 11px;
		background: rgba(249, 251, 249, 0.34);
		transition: background 0.15s ease, box-shadow 0.15s ease;
	}

	.column.over {
		background: var(--accent-soft);
		box-shadow: inset 0 0 0 1.5px var(--accent-line);
	}

	.column header {
		display: grid;
		grid-template-columns: 6px 1fr auto;
		align-items: center;
		gap: 2px 6px;
		padding: 9px 10px 7px;
	}

	.column header i {
		width: 6px;
		height: 6px;
		border-radius: 50%;
	}

	.column header strong {
		font-size: 8px;
	}

	.column header b {
		padding: 1px 5px;
		border-radius: 6px;
		background: rgba(31, 53, 45, 0.08);
		font-size: 6.5px;
	}

	.column header span {
		grid-column: 2 / -1;
		color: var(--faint);
		font-size: 6.4px;
	}

	.cards {
		min-height: 0;
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 6px;
		padding: 0 6px 8px;
	}

	.deal {
		position: relative;
		border: 1px solid rgba(255, 255, 255, 0.7);
		border-radius: 9px;
		background: rgba(255, 255, 255, 0.78);
		box-shadow: 0 1px 2px rgba(15, 35, 28, 0.06), 0 6px 14px rgba(15, 35, 28, 0.05);
		cursor: grab;
		transition: transform 0.15s ease, box-shadow 0.15s ease;
	}

	.deal:hover {
		transform: translateY(-1px);
		box-shadow: 0 2px 4px rgba(15, 35, 28, 0.07), 0 12px 24px rgba(15, 35, 28, 0.1);
	}

	.deal.dragging {
		opacity: 0.4;
	}

	.deal-main {
		width: 100%;
		display: block;
		padding: 8px;
		text-align: left;
	}

	.deal-top {
		display: grid;
		grid-template-columns: 22px minmax(0, 1fr) 22px;
		align-items: center;
		gap: 6px;
	}

	.deal-top strong,
	.deal-top small {
		display: block;
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
	}

	.deal-top strong {
		font-size: 7.6px;
	}

	.deal-top small {
		margin-top: 1px;
		color: var(--faint);
		font-size: 6.1px;
	}

	.deal p {
		margin: 6px 0;
		color: var(--muted);
		font-size: 6.6px;
		line-height: 1.35;
	}

	.deal-meta {
		display: flex;
		align-items: center;
		gap: 3px;
	}

	.deal-meta .pill {
		height: 13px;
		font-size: 5.6px;
		font-style: normal;
	}

	.days {
		display: flex;
		align-items: center;
		gap: 2px;
		margin-left: auto;
		color: var(--faint);
		font-size: 6px;
	}

	.days :global(svg) {
		font-size: 7px;
	}

	.deal-meta .avatar {
		width: 14px;
		height: 14px;
		font-size: 5px;
	}

	.deal-hover {
		display: none;
		align-items: center;
		justify-content: space-between;
		padding: 5px 8px;
		border-top: 1px solid var(--line);
		color: var(--faint);
		font-size: 9px;
	}

	.deal:hover .deal-hover {
		display: flex;
	}

	.deal-hover button {
		display: flex;
		align-items: center;
		gap: 3px;
		color: var(--accent);
		font-size: 6.4px;
		font-weight: 650;
	}

	.empty {
		display: grid;
		place-items: center;
		height: 60px;
		border: 1px dashed rgba(31, 53, 45, 0.18);
		border-radius: 8px;
		color: var(--faint);
		font-size: 6.6px;
	}

	.table-wrap {
		flex: 1;
		min-height: 0;
	}

	table {
		width: 100%;
		border-collapse: collapse;
		font-size: 7.3px;
	}

	th {
		position: sticky;
		top: 0;
		z-index: 1;
		padding: 8px 10px;
		background: rgba(242, 246, 243, 0.95);
		color: var(--faint);
		font-size: 6.3px;
		font-weight: 650;
		letter-spacing: 0.06em;
		text-align: left;
		text-transform: uppercase;
	}

	th button {
		font-size: inherit;
		font-weight: inherit;
		letter-spacing: inherit;
		text-transform: inherit;
	}

	th button.on {
		color: var(--accent-deep);
	}

	td {
		padding: 6px 10px;
		border-top: 1px solid var(--line);
	}

	tbody tr {
		cursor: pointer;
	}

	tbody tr:hover {
		background: rgba(255, 255, 255, 0.5);
	}

	.cell-co {
		display: flex;
		align-items: center;
		gap: 7px;
	}

	.cell-co strong,
	.cell-co small {
		display: block;
	}

	.cell-co small {
		color: var(--faint);
		font-size: 6.2px;
	}

	.stage-chip {
		padding: 2px 6px;
		border-radius: 6px;
		background: color-mix(in srgb, var(--tone) 14%, transparent);
		color: color-mix(in oklab, var(--tone) 80%, black);
		font-size: 6.4px;
		font-weight: 650;
	}

	td .avatar {
		width: 16px;
		height: 16px;
		font-size: 5.6px;
	}
</style>
