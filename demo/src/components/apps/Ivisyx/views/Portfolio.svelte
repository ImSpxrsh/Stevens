<script lang="ts">
	import { slide } from 'svelte/transition';
	import ChevronRight from '~icons/lucide/chevron-right';
	import Download from '~icons/lucide/download';
	import Mail from '~icons/lucide/mail';
	import FileText from '~icons/lucide/file-text';
	import { suite } from '../state.svelte';
	import { money, type Health } from '../suite-data';
	import AreaChart from '../ui/AreaChart.svelte';
	import Logo from '../ui/Logo.svelte';
	import Sparkline from '../ui/Sparkline.svelte';

	let expanded = $state<string | null>(null);
	let filter = $state<Health | 'All'>('All');

	const months = ['Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep'];
	const tone: Record<Health, string> = { Breakout: 'accent', 'On track': 'blue', Watch: 'amber', 'At risk': 'red' };

	const list = $derived(suite.portfolio.filter((p) => filter === 'All' || p.health === filter));
	const invested = $derived(suite.portfolio.reduce((s, p) => s + p.check, 0));
	const value = $derived(suite.portfolio.reduce((s, p) => s + p.fairValue, 0));
	const bySector = $derived.by(() => {
		const m = new Map<string, number>();
		for (const p of suite.portfolio) m.set(p.sector, (m.get(p.sector) ?? 0) + p.fairValue);
		return [...m.entries()].sort((a, b) => b[1] - a[1]);
	});
	const runwayWatch = $derived([...suite.portfolio].sort((a, b) => a.runway - b.runway).slice(0, 5));

	function growth(arr: number[]) {
		return Math.round((arr[arr.length - 1] / arr[arr.length - 4] - 1) * 100);
	}
</script>

<header class="page-head">
	<div>
		<h1>Portfolio</h1>
		<p>{suite.firm.fund}, {suite.firm.vintage} vintage. Monthly numbers from founder updates, marked to the latest round. All figures are synthetic.</p>
	</div>
	<div class="actions">
		<button class="btn" onclick={() => suite.toast(`Update requests sent to ${suite.portfolio.length} founders`, 'success')}><Mail /> Request updates</button>
		<button class="btn" onclick={() => suite.toast('Portfolio export ready (demo)', 'success')}><Download /> Export</button>
	</div>
</header>

<div class="kpis">
	<div class="card kpi"><small>Companies</small><strong>{suite.portfolio.length}</strong><span>{suite.portfolio.filter((p) => p.board).length} board seats</span></div>
	<div class="card kpi"><small>Invested</small><strong>{money(invested)}</strong><span>initial checks</span></div>
	<div class="card kpi"><small>Fair value</small><strong>{money(value)}</strong><span><b class="delta-up">▲ {money(value - invested)}</b> unrealised</span></div>
	<div class="card kpi"><small>Gross MOIC</small><strong>{(value / invested).toFixed(2)}×</strong><span>since first close</span></div>
	<div class="card kpi"><small>Reserves</small><strong>{money(suite.fund.reserves)}</strong><span>for follow-ons</span></div>
</div>

<div class="card table">
	<header class="card-head">
		<h3>Holdings</h3>
		<div class="seg">
			{#each ['All', 'Breakout', 'On track', 'Watch', 'At risk'] as h}
				<button class:on={filter === h} onclick={() => (filter = h as Health | 'All')}>{h}<b>{h === 'All' ? suite.portfolio.length : suite.portfolio.filter((p) => p.health === h).length}</b></button>
			{/each}
		</div>
	</header>
	<div class="row head">
		<span>Company</span><span>Entry</span><span>Check</span><span>Own.</span><span>Fair value</span><span>MOIC</span><span>ARR trend</span><span>Runway</span><span>Health</span><span></span>
	</div>
	{#each list as p (p.id)}
		{@const moic = p.fairValue / p.check}
		<button class="row" class:open={expanded === p.id} onclick={() => (expanded = expanded === p.id ? null : p.id)}>
			<span class="co"><Logo name={p.name} hue={p.hue} seed={p.id} size={22} /><span><strong>{p.name}</strong><small>{p.sector}{p.board ? ' · Board seat' : ''}</small></span></span>
			<span><b>{p.round}</b><small>{p.invested}</small></span>
			<span class="num">{money(p.check)}</span>
			<span class="num">{p.ownership.toFixed(1)}%</span>
			<span class="num">{money(p.fairValue)}</span>
			<span class="num moic" class:up={moic >= 1.5} class:down={moic < 1}>{moic.toFixed(2)}×</span>
			<span class="arr"><Sparkline values={p.arr} width={54} height={18} dot={false} color={p.health === 'At risk' ? '#c0573f' : 'var(--accent)'} /><small class="num">${(p.arr[11] / 1000).toFixed(2)}M <b class:delta-up={growth(p.arr) > 0} class:delta-down={growth(p.arr) <= 0}>{growth(p.arr) > 0 ? '+' : ''}{growth(p.arr)}%</b></small></span>
			<span class="runway"><div class="bar"><i style:width="{Math.min(100, (p.runway / 36) * 100)}%" style:background={p.runway < 9 ? '#c0573f' : p.runway < 15 ? '#d49a43' : undefined}></i></div><small class="num">{p.runway} mo</small></span>
			<span><i class="pill {tone[p.health]}">{p.health}</i></span>
			<span class="chev"><ChevronRight /></span>
		</button>
		{#if expanded === p.id}
			<div class="detail" transition:slide={{ duration: 220 }}>
				<div class="detail-chart">
					<span class="eyebrow">Annual recurring revenue · $K</span>
					<AreaChart labels={months} series={[{ name: 'ARR', values: p.arr, color: 'var(--accent)' }]} height={120} format={(v) => `$${Math.round(v)}K`} />
				</div>
				<div class="detail-side">
					<div class="stat-grid">
						<div class="kpi"><small>Headcount</small><strong>{p.headcount}</strong></div>
						<div class="kpi"><small>Burn / mo</small><strong>{money(p.arr[11] / 1000 / 7)}</strong></div>
						<div class="kpi"><small>Net retention</small><strong>{108 + (p.hue % 30)}%</strong></div>
						<div class="kpi"><small>Pro-rata</small><strong>{money(p.check * 0.6)}</strong></div>
					</div>
					<div class="update"><span class="eyebrow">Latest founder update</span><p>"{p.update}"</p></div>
					<div class="detail-actions">
						<button class="btn primary" onclick={() => suite.ask(`Prepare a board memo for ${p.name}`)}><FileText /> Board memo</button>
						<button class="btn" onclick={() => suite.toast(`Check-in scheduled with ${p.name}`, 'success')}>Schedule check-in</button>
					</div>
				</div>
			</div>
		{/if}
	{/each}
</div>

<div class="lower">
	<article class="card">
		<header class="card-head"><div><h3>Exposure by sector</h3><small>Share of portfolio fair value</small></div></header>
		<div class="sectors">
			{#each bySector as [sector, v]}
				<div><span>{sector}</span><div class="bar"><i style:width="{(v / value) * 100}%"></i></div><b class="num">{Math.round((v / value) * 100)}%</b></div>
			{/each}
		</div>
	</article>
	<article class="card">
		<header class="card-head"><div><h3>Runway watch</h3><small>Shortest runway first</small></div></header>
		<div class="sectors">
			{#each runwayWatch as p}
				<div><span>{p.name}</span><div class="bar"><i style:width="{Math.min(100, (p.runway / 36) * 100)}%" style:background={p.runway < 9 ? '#c0573f' : p.runway < 15 ? '#d49a43' : undefined}></i></div><b class="num">{p.runway} mo</b></div>
			{/each}
		</div>
	</article>
</div>

<style>
	.kpis {
		display: grid;
		grid-template-columns: repeat(5, minmax(0, 1fr));
		gap: 8px;
		margin-bottom: 10px;
	}

	.kpis .kpi {
		padding: 10px 12px;
	}

	.kpis .kpi strong {
		font-size: 17px;
	}

	.table {
		overflow: hidden;
	}

	.row {
		width: 100%;
		display: grid;
		grid-template-columns: minmax(130px, 1.6fr) 0.8fr 0.6fr 0.5fr 0.7fr 0.55fr 1.2fr 0.9fr 0.7fr 12px;
		align-items: center;
		gap: 8px;
		padding: 7px 12px;
		border-top: 1px solid var(--line);
		font-size: 7.3px;
		text-align: left;
		transition: background 0.15s ease;
	}

	.row.head {
		padding-top: 7px;
		padding-bottom: 7px;
		border-top: 0;
		color: var(--faint);
		font-size: 7px;
		font-weight: 600;
	}

	button.row:hover,
	.row.open {
		background: rgba(255, 255, 255, 0.5);
	}

	.co {
		display: flex;
		align-items: center;
		gap: 7px;
		min-width: 0;
	}

	.row strong,
	.row small,
	.row b {
		display: block;
	}

	.row strong {
		font-size: 7.8px;
	}

	.row small {
		margin-top: 1px;
		color: var(--faint);
		font-size: 6.2px;
	}

	.moic.up {
		color: #2f7a5d;
		font-weight: 700;
	}

	.moic.down {
		color: var(--red);
		font-weight: 700;
	}

	.arr {
		display: flex;
		align-items: center;
		gap: 6px;
	}

	.arr small b {
		display: inline;
	}

	.runway {
		display: grid;
		gap: 3px;
	}

	.pill {
		font-style: normal;
	}

	.chev {
		color: var(--faint);
		transition: rotate 0.2s ease;
	}

	.row.open .chev {
		rotate: 90deg;
	}

	.detail {
		display: grid;
		grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
		gap: 14px;
		padding: 12px 14px 14px;
		border-top: 1px solid var(--line);
		background: rgba(255, 255, 255, 0.36);
	}

	.detail-chart .eyebrow {
		display: block;
		margin-bottom: 6px;
	}

	.stat-grid {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 6px;
	}

	.stat-grid .kpi strong {
		font-size: 13px;
	}

	.update {
		margin: 10px 0;
		padding: 9px;
		border-left: 2px solid var(--accent);
		border-radius: 0 7px 7px 0;
		background: var(--accent-soft);
	}

	.update p {
		margin-top: 3px;
		color: var(--ink-2);
		font-size: 7.6px;
		line-height: 1.45;
	}

	.detail-actions {
		display: flex;
		gap: 6px;
	}

	.lower {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 10px;
		margin-top: 10px;
	}

	.sectors {
		display: grid;
		gap: 7px;
		padding: 11px 12px;
	}

	.sectors > div {
		display: grid;
		grid-template-columns: 96px 1fr 34px;
		align-items: center;
		gap: 8px;
		font-size: 7.2px;
	}

	.sectors b {
		text-align: right;
	}
</style>
