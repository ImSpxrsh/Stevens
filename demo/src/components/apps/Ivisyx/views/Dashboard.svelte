<script lang="ts">
	import ArrowRight from '~icons/lucide/arrow-right';
	import ArrowUpRight from '~icons/lucide/arrow-up-right';
	import Calendar from '~icons/lucide/calendar-clock';
	import FileText from '~icons/lucide/file-text';
	import MapPinned from '~icons/lucide/map-pinned';
	import TrendingUp from '~icons/lucide/trending-up';
	import TriangleAlert from '~icons/lucide/triangle-alert';
	import { entityById, syntheticEntities } from '../directory';
	import { suite } from '../state.svelte';
	import { dealFlowAdvanced, dealFlowSourced, dealFlowWeeks, fitFor, money, pipelineStages, team, type Health } from '../suite-data';
	import AreaChart from '../ui/AreaChart.svelte';
	import Logo from '../ui/Logo.svelte';
	import NjMini from '../ui/NjMini.svelte';
	import Score from '../ui/Score.svelte';
	import Sparkline from '../ui/Sparkline.svelte';

	const hour = new Date().getHours();
	const greeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
	const today = new Date().toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' });

	const matches = $derived(
		syntheticEntities
			.map((e) => ({ e, fit: fitFor(e, suite.firm).total }))
			.sort((a, b) => b.fit - a.fit || b.e.momentum - a.e.momentum)
			.slice(0, 6),
	);
	const strongMatches = $derived(syntheticEntities.filter((e) => fitFor(e, suite.firm).total >= 80).length);
	const active = $derived(Object.entries(suite.pipeline).filter(([, s]) => s !== 'Closed'));
	const activeRaise = $derived(active.reduce((sum, [id]) => sum + (entityById.get(id)?.raise ?? 0), 0));
	const funnel = $derived(pipelineStages.map((stage) => ({ stage, n: Object.values(suite.pipeline).filter((s) => s === stage).length })));
	const funnelMax = $derived(Math.max(...funnel.map((f) => f.n), 1));
	const nav = $derived(suite.portfolio.reduce((s, p) => s + p.fairValue, 0));
	const health = $derived(
		(['Breakout', 'On track', 'Watch', 'At risk'] as Health[]).map((h) => ({ h, n: suite.portfolio.filter((p) => p.health === h).length })),
	);
	const healthColor: Record<Health, string> = { Breakout: 'var(--accent)', 'On track': '#7fb8a0', Watch: '#d49a43', 'At risk': '#c0573f' };
	const attention = $derived(suite.portfolio.filter((p) => p.health === 'At risk' || p.health === 'Watch').slice(0, 3));
	const latest = $derived(suite.events[0] ? entityById.get(suite.events[0].companyId) : null);
	const icCount = $derived(funnel.find((f) => f.stage === 'IC review')?.n ?? 0);

	const agenda = [
		{ time: '09:30', title: 'Partner meeting', who: 'quarry', kind: 'Pitch' },
		{ time: '11:00', title: 'Investment committee', who: 'aster', kind: 'IC' },
		{ time: '13:30', title: 'Founder intro call', who: 'harbor', kind: 'Intro' },
		{ time: '15:00', title: 'Reference calls', who: 'lucent', kind: 'Diligence' },
		{ time: '16:30', title: 'LP quarterly update', who: null, kind: 'LPs' },
	];

	function donut(items: { h: Health; n: number }[]) {
		const total = items.reduce((s, i) => s + i.n, 0) || 1;
		let angle = -Math.PI / 2;
		return items.map((i) => {
			const a0 = angle;
			angle += (i.n / total) * Math.PI * 2;
			const a1 = angle - 0.04;
			const r = 26;
			const large = a1 - a0 > Math.PI ? 1 : 0;
			return { ...i, d: `M${32 + r * Math.cos(a0)},${32 + r * Math.sin(a0)} A${r},${r} 0 ${large} 1 ${32 + r * Math.cos(a1)},${32 + r * Math.sin(a1)}` };
		});
	}
</script>

<div class="dash">
	<section class="hero hero-dark">
		<div class="hero-copy">
			<span class="hero-eyebrow">{today}</span>
			<h1>{greeting}, {suite.firm.name}.</h1>
			<p>{strongMatches} companies score 80 or higher against your thesis. {icCount} {icCount === 1 ? 'deal is' : 'deals are'} waiting on IC, and {attention.length} portfolio {attention.length === 1 ? 'company needs' : 'companies need'} a check-in.</p>
			<div class="hero-actions">
				<button class="btn primary" onclick={() => suite.go('radar')}><MapPinned /> Open NJ map</button>
				<button class="btn on-dark" onclick={() => suite.ask("Summarize this week's signals for me")}><FileText /> Weekly summary</button>
			</div>
			<div class="thesis"><span>Thesis:</span>{suite.firm.thesis}</div>
		</div>
		<div class="hero-map">
			<NjMini width={150} height={188} pulse={latest?.coordinates ?? null} />
		</div>
		<div class="hero-stats">
			<div><small>Signals, last 7 days</small><strong class="num">{(dealFlowSourced[11] * 4 + suite.sequence).toLocaleString()}</strong><span class="up">up 18% on last week</span></div>
			<div><small>Thesis matches</small><strong class="num">{strongMatches}</strong><span>fit score 80+</span></div>
			<div><small>Dry powder</small><strong class="num">{money(suite.fund.committed - suite.fund.called)}</strong><span>{Math.round((1 - suite.fund.called / suite.fund.committed) * 100)}% of fund</span></div>
		</div>
	</section>


	<section class="kpis">
		<article class="card kpi-card">
			<div class="kpi"><small>New signals · 30d</small><strong>{(dealFlowSourced.slice(-4).reduce((a, b) => a + b, 0) + suite.sequence).toLocaleString()}</strong><span><b class="delta-up">▲ 21%</b> vs prior 30d</span></div>
			<Sparkline values={dealFlowSourced} width={78} height={30} />
		</article>
		<article class="card kpi-card">
			<div class="kpi"><small>Active pipeline</small><strong>{active.length}</strong><span>{money(activeRaise)} in open rounds</span></div>
			<Sparkline values={[9, 11, 10, 13, 14, 13, 16, 18, 17, 19, 21, active.length]} width={78} height={30} color="#c88b33" />
		</article>
		<article class="card kpi-card">
			<div class="kpi"><small>Portfolio fair value</small><strong>{money(nav)}</strong><span><b class="delta-up">{(nav / suite.portfolio.reduce((s, p) => s + p.check, 0)).toFixed(2)}×</b> on invested</span></div>
			<Sparkline values={suite.fund.tvpiSeries} width={78} height={30} color="#6a4fa3" />
		</article>
		<article class="card kpi-card">
			<div class="kpi"><small>Net IRR</small><strong>{suite.fund.irr.toFixed(1)}%</strong><span>TVPI <b>{suite.fund.tvpi.toFixed(2)}×</b> · DPI {suite.fund.dpi.toFixed(2)}×</span></div>
			<Sparkline values={[-4, -8, -6, 2, 6, 9, 13, 15, 17, 19, 21, suite.fund.irr]} width={78} height={30} color="#2b5f9e" />
		</article>
	</section>

	<section class="row-a">
		<article class="card">
			<header class="card-head">
				<div><h3><TrendingUp /> Deal flow</h3><small>Companies sourced vs. advanced to first meeting · last 12 weeks</small></div>
				<div class="legend"><span><i style:background="var(--accent)"></i>Sourced</span><span><i style:background="#d49a43"></i>Advanced</span></div>
			</header>
			<div class="chart-pad">
				<AreaChart labels={dealFlowWeeks} height={150} series={[{ name: 'Sourced', values: dealFlowSourced, color: 'var(--accent)' }, { name: 'Advanced', values: dealFlowAdvanced.map((v) => v * 3), color: '#d49a43' }]} />
			</div>
		</article>
		<article class="card">
			<header class="card-head"><div><h3>Pipeline funnel</h3><small>Conversion by stage</small></div><button class="btn ghost" onclick={() => suite.go('pipeline')}>Board <ArrowRight /></button></header>
			<div class="funnel">
				{#each funnel as f, i}
					<button onclick={() => suite.go('pipeline')}>
						<span>{f.stage}</span>
						<div class="funnel-bar"><i style:width="{Math.max(6, (f.n / funnelMax) * 100)}%" style:opacity={1 - i * 0.11}></i></div>
						<b class="num">{f.n}</b>
						<em class="num">{i === 0 ? '—' : `${Math.round((f.n / Math.max(1, funnel[i - 1].n)) * 100)}%`}</em>
					</button>
				{/each}
			</div>
		</article>
	</section>

	<section class="row-b">
		<article class="card">
			<header class="card-head"><div><h3>Top thesis matches</h3><small>Scored against {suite.firm.name}'s sectors, stages and geography</small></div><button class="btn ghost" onclick={() => suite.go('companies')}>All <ArrowRight /></button></header>
			<div class="matches">
				{#each matches as { e, fit }, i (e.id)}
					<button onclick={() => suite.open(e.id)}>
						<em>{String(i + 1).padStart(2, '0')}</em>
						<Logo name={e.name} hue={e.hue} src={e.logo} seed={e.id} size={24} />
						<span><strong>{e.name}</strong><small>{e.sector} · {e.stage} · {e.town}</small></span>
						<Score value={fit} />
					</button>
				{/each}
			</div>
		</article>
		<article class="card">
			<header class="card-head"><div><h3><Calendar /> Today</h3><small>{agenda.length} meetings · synced from calendar</small></div></header>
			<div class="agenda">
				{#each agenda as a}
					{@const e = a.who ? entityById.get(a.who) : null}
					<button onclick={() => (e ? suite.open(e.id) : suite.go('fund'))}>
						<time>{a.time}</time>
						<span class="agenda-line"></span>
						<span><strong>{a.title}</strong><small>{e?.name ?? `${suite.firm.fund} investors`}</small></span>
						<i class="pill {a.kind === 'IC' ? 'accent' : a.kind === 'LPs' ? 'violet' : ''}">{a.kind}</i>
					</button>
				{/each}
			</div>
		</article>
		<article class="card">
			<header class="card-head"><div><h3>Portfolio health</h3><small>{suite.portfolio.length} companies · {suite.firm.fund}</small></div><button class="btn ghost" onclick={() => suite.go('portfolio')}><ArrowUpRight /></button></header>
			<div class="health">
				<svg viewBox="0 0 64 64" width="64" height="64" aria-hidden="true">
					{#each donut(health) as seg}{#if seg.n}<path d={seg.d} fill="none" style:stroke={healthColor[seg.h]} stroke-width="7" stroke-linecap="round" />{/if}{/each}
					<text x="32" y="35" text-anchor="middle" class="donut-num">{suite.portfolio.length}</text>
				</svg>
				<div class="health-legend">
					{#each health as h}<span><i style:background={healthColor[h.h]}></i>{h.h}<b>{h.n}</b></span>{/each}
				</div>
			</div>
			<div class="attention">
				{#each attention as p}
					<button onclick={() => suite.go('portfolio')}><TriangleAlert /><span><strong>{p.name}</strong><small>{p.runway} mo runway · {p.update}</small></span></button>
				{/each}
			</div>
		</article>
	</section>

	<footer class="team-strip">
		{#each team as t}
			<span><i class="avatar" style:background={t.color}>{t.initials}</i><b>{t.name}</b>{Object.keys(suite.pipeline).filter((id) => suite.owner(id) === t.id && suite.pipeline[id] !== 'Closed').length} active deals</span>
		{/each}
	</footer>
</div>

<style>
	.dash {
		display: grid;
		gap: 10px;
	}

	.hero {
		display: grid;
		grid-template-columns: minmax(0, 1fr) 150px 140px;
		gap: 18px;
		padding: 20px 22px;
		min-height: 212px;
	}

	.hero-eyebrow {
		color: rgba(200, 240, 222, 0.6);
		font-size: 7.5px;
	}

	.hero h1 {
		margin: 8px 0 8px;
		font-size: 25px;
		line-height: 1.05;
		letter-spacing: -0.05em;
	}

	.hero p {
		max-width: 380px;
		color: rgba(220, 238, 230, 0.72);
		font-size: 8.5px;
		line-height: 1.55;
	}

	.hero-actions {
		display: flex;
		gap: 6px;
		margin-top: 14px;
	}

	.thesis {
		display: flex;
		gap: 7px;
		margin-top: 16px;
		padding-top: 10px;
		border-top: 1px solid rgba(255, 255, 255, 0.08);
		color: rgba(220, 238, 230, 0.62);
		font-size: 7px;
	}

	.thesis span {
		color: rgba(220, 238, 230, 0.9);
		font-weight: 600;
	}

	.hero-map {
		position: relative;
		display: grid;
		place-items: center;
	}







	.hero-stats {
		display: grid;
		align-content: center;
		gap: 12px;
		padding-left: 16px;
		border-left: 1px solid rgba(255, 255, 255, 0.08);
	}

	.hero-stats small,
	.hero-stats strong,
	.hero-stats span {
		display: block;
	}

	.hero-stats small {
		color: rgba(200, 240, 222, 0.55);
		font-size: 7px;
	}

	.hero-stats strong {
		margin: 2px 0 1px;
		font-size: 21px;
		letter-spacing: -0.04em;
	}

	.hero-stats span {
		color: rgba(220, 238, 230, 0.5);
		font-size: 6.3px;
	}

	.hero-stats .up {
		color: #7fe3b5;
	}











	.kpis {
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		gap: 10px;
	}

	.kpi-card {
		display: flex;
		align-items: flex-end;
		justify-content: space-between;
		gap: 6px;
		padding: 12px;
	}

	.row-a {
		display: grid;
		grid-template-columns: minmax(0, 1.6fr) minmax(0, 1fr);
		gap: 10px;
	}

	.row-b {
		display: grid;
		grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr) minmax(0, 1fr);
		gap: 10px;
	}

	.chart-pad {
		padding: 10px 12px 8px;
	}

	.legend {
		display: flex;
		gap: 9px;
		color: var(--muted);
		font-size: 6.6px;
	}

	.legend span {
		display: flex;
		align-items: center;
		gap: 4px;
	}

	.legend i {
		width: 6px;
		height: 6px;
		border-radius: 2px;
	}

	.funnel {
		display: grid;
		gap: 3px;
		padding: 9px 11px;
	}

	.funnel button {
		display: grid;
		grid-template-columns: 62px 1fr 16px 26px;
		align-items: center;
		gap: 7px;
		padding: 4px 3px;
		border-radius: 6px;
		font-size: 7.3px;
		text-align: left;
	}

	.funnel button:hover {
		background: rgba(255, 255, 255, 0.5);
	}

	.funnel-bar {
		height: 14px;
		border-radius: 4px;
		background: rgba(31, 53, 45, 0.06);
	}

	.funnel-bar i {
		display: block;
		height: 100%;
		border-radius: 4px;
		background: var(--accent);
	}


	.funnel b {
		text-align: right;
	}

	.funnel em {
		color: var(--faint);
		font-size: 6.3px;
		font-style: normal;
		text-align: right;
	}

	.matches,
	.agenda,
	.attention {
		display: grid;
		padding: 5px 7px 8px;
	}

	.matches button,
	.agenda button,
	.attention button {
		width: 100%;
		display: grid;
		align-items: center;
		gap: 7px;
		padding: 5px 5px;
		border-radius: 7px;
		text-align: left;
		transition: background 0.15s ease;
	}

	.matches button {
		grid-template-columns: 12px 24px minmax(0, 1fr) auto;
	}

	.matches button:hover,
	.agenda button:hover,
	.attention button:hover {
		background: rgba(255, 255, 255, 0.55);
	}

	.matches em {
		color: var(--faint);
		font-size: 6px;
		font-style: normal;
	}

	.matches strong,
	.matches small,
	.agenda strong,
	.agenda small,
	.attention strong,
	.attention small {
		display: block;
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
	}

	.matches strong,
	.agenda strong,
	.attention strong {
		font-size: 7.8px;
	}

	.matches small,
	.agenda small,
	.attention small {
		margin-top: 1px;
		color: var(--faint);
		font-size: 6.4px;
	}

	.agenda button {
		grid-template-columns: 24px 2px minmax(0, 1fr) auto;
	}

	.agenda time {
		color: var(--muted);
		font-size: 6.8px;
		font-variant-numeric: tabular-nums;
	}

	.agenda-line {
		height: 18px;
		border-radius: 2px;
		background: var(--accent-line);
	}

	.health {
		display: flex;
		align-items: center;
		gap: 14px;
		padding: 10px 12px 4px;
	}

	.donut-num {
		fill: var(--ink);
		font-size: 13px;
		font-weight: 700;
	}

	.health-legend {
		display: grid;
		flex: 1;
		gap: 4px;
	}

	.health-legend span {
		display: flex;
		align-items: center;
		gap: 5px;
		font-size: 7px;
	}

	.health-legend i {
		width: 6px;
		height: 6px;
		border-radius: 2px;
	}

	.health-legend b {
		margin-left: auto;
	}

	.attention button {
		grid-template-columns: 12px minmax(0, 1fr);
	}

	.attention :global(svg) {
		color: #c0573f;
		font-size: 10px;
	}

	.team-strip {
		display: flex;
		flex-wrap: wrap;
		gap: 16px;
		padding: 6px 4px;
		color: var(--muted);
		font-size: 7px;
	}

	.team-strip span {
		display: flex;
		align-items: center;
		gap: 5px;
	}

	.team-strip b {
		color: var(--ink);
	}
</style>
