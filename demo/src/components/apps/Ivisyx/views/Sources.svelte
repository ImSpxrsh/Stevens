<script lang="ts">
	import ArrowRight from '~icons/lucide/arrow-right';
	import ArrowUpRight from '~icons/lucide/arrow-up-right';
	import RefreshCw from '~icons/lucide/refresh-cw';
	import { entities } from '../directory';
	import { towns } from '../geo';
	import { age, suite } from '../state.svelte';

	const sources = [
		{ key: 'SEC', title: 'EDGAR filings', desc: 'Company disclosures and exempt-offering notices in the SEC’s official database.', url: 'https://www.sec.gov/edgar/search/', freq: 'Every 15 min' },
		{ key: 'PTO', title: 'Patents & applications', desc: 'Published applications and granted patents. Publication and grant are different events.', url: 'https://www.uspto.gov/patents/search/patent-public-search', freq: 'Daily' },
		{ key: 'SBIR', title: 'Federal research awards', desc: 'The official SBIR/STTR award database for research and development activity.', url: 'https://www.sbir.gov/awards', freq: 'Weekly' },
	];

	let integrations = $state([
		{ name: 'CRM sync', desc: 'Push pipeline stages and notes', on: true },
		{ name: 'Email & calendar', desc: 'Log founder meetings automatically', on: true },
		{ name: 'Team chat alerts', desc: 'Post 80+ fit signals to a channel', on: true },
		{ name: 'Data room', desc: 'Attach diligence files to deals', on: false },
		{ name: 'Cap table', desc: 'Pull ownership into portfolio marks', on: false },
		{ name: 'Fund admin', desc: 'Reconcile capital calls for LP reports', on: true },
	]);

	const pipeline = $derived([
		{ label: 'Ingested', value: (48213 + suite.sequence * 3).toLocaleString(), sub: 'raw records · 30d' },
		{ label: 'Entity-resolved', value: (9870 + suite.sequence).toLocaleString(), sub: '97.4% match confidence' },
		{ label: 'Companies', value: entities.length.toLocaleString(), sub: `${towns.length} municipalities` },
		{ label: 'Scored', value: entities.filter((e) => !e.real).length.toLocaleString(), sub: `vs ${suite.firm.name}` },
		{ label: 'Alerts', value: String(suite.events.length), sub: 'this session' },
	]);

	function toggle(i: number) {
		integrations[i].on = !integrations[i].on;
		suite.toast(`${integrations[i].name} ${integrations[i].on ? 'connected' : 'disconnected'} (demo)`, integrations[i].on ? 'success' : 'default');
	}
</script>

<header class="page-head">
	<div>
		<span class="eyebrow">Evidence pipeline</span>
		<h1>Data sources</h1>
		<p>Where signals come from, how they're resolved, and what's simulated in this demo.</p>
	</div>
	<div class="actions"><button class="btn" onclick={() => suite.toast('Re-sync queued for 14 sources (demo)', 'success')}><RefreshCw /> Sync now</button></div>
</header>

<section class="flow hero-dark">
	{#each pipeline as step, i}
		<div class="flow-step rise" style:animation-delay="{i * 70}ms">
			<small>{step.label.toUpperCase()}</small>
			<strong class="num">{step.value}</strong>
			<span>{step.sub}</span>
		</div>
		{#if i < pipeline.length - 1}<span class="flow-arrow"><ArrowRight /></span>{/if}
	{/each}
</section>

<div class="split">
	<div class="list">
		<div class="section-label">Public records</div>
		{#each sources as s}
			<article class="card source">
				<span class="mono">{s.key}</span>
				<div><h2>{s.title}</h2><p>{s.desc}</p><span class="status"><i class="live-dot"></i>Reference link · live ingestion simulated · {s.freq}</span></div>
				<a href={s.url} target="_blank" rel="noreferrer" aria-label="Open {s.title}"><ArrowUpRight /></a>
			</article>
		{/each}
		<div class="section-label">Workspace integrations</div>
		<div class="integrations">
			{#each integrations as it, i}
				<button class="card integ" class:on={it.on} onclick={() => toggle(i)}>
					<span><strong>{it.name}</strong><small>{it.desc}</small></span>
					<i class="switch"><b></b></i>
				</button>
			{/each}
		</div>
	</div>
	<aside class="card log">
		<header class="card-head"><div><h3>Ingestion log</h3><small>Latest resolved records</small></div><i class="live-dot" class:paused={!suite.playing}></i></header>
		<div class="log-rows">
			{#each suite.events.slice(0, 12) as ev (ev.id)}
				{@const e = entities.find((x) => x.id === ev.companyId)}
				<button onclick={() => suite.open(ev.companyId, ev)}>
					<time>{age(ev.timestamp, suite.now)}</time>
					<span><strong>{ev.kind}</strong><small>{e?.name} · {e?.town}</small></span>
					<em>resolved</em>
				</button>
			{/each}
		</div>
	</aside>
</div>

<section class="explainer hero-dark">
	<h2>A clear line between fact and demo.</h2>
	<div>
		<p><strong>Real company profiles</strong>Six companies with names, towns and descriptions linked to official sources. Logos belong to their owners. They never receive simulated metrics or events.</p>
		<p><strong>Everything else is synthetic</strong>Every other company, deal, portfolio mark, fund figure, LP and signal is generated locally for the demo. Town coordinates are approximate centres.</p>
	</div>
</section>

<style>
	.flow {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 16px;
	}

	.flow-step {
		flex: 1;
		padding: 10px;
		border: 1px solid rgba(255, 255, 255, 0.1);
		border-radius: 9px;
		background: rgba(255, 255, 255, 0.05);
	}

	.flow-step small,
	.flow-step strong,
	.flow-step span {
		display: block;
	}

	.flow-step small {
		color: #8fb0a2;
		font-size: 5.8px;
		letter-spacing: 0.1em;
	}

	.flow-step strong {
		margin: 5px 0 3px;
		font-size: 17px;
		letter-spacing: -0.03em;
	}

	.flow-step span {
		color: rgba(200, 225, 214, 0.55);
		font-size: 6.2px;
	}

	.flow-arrow {
		color: #d6a957;
		font-size: 11px;
	}

	.split {
		display: grid;
		grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr);
		gap: 10px;
		margin-top: 4px;
	}

	.list {
		display: grid;
		align-content: start;
		gap: 7px;
	}

	.source {
		display: grid;
		grid-template-columns: 38px 1fr 22px;
		align-items: start;
		gap: 11px;
		padding: 12px;
	}

	.mono {
		width: 38px;
		height: 38px;
		display: grid;
		place-items: center;
		border-radius: 10px;
		background: linear-gradient(145deg, color-mix(in oklab, var(--accent) 80%, white), var(--accent-deep));
		color: white;
		font-size: 8px;
		font-weight: 800;
		letter-spacing: 0.04em;
	}

	.source h2 {
		font-size: 10px;
	}

	.source p {
		margin: 3px 0 6px;
		color: var(--muted);
		font-size: 7.2px;
		line-height: 1.4;
	}

	.status {
		display: flex;
		align-items: center;
		gap: 6px;
		color: var(--faint);
		font-size: 6.4px;
	}

	.status .live-dot {
		width: 5px;
		height: 5px;
	}

	.source a {
		width: 22px;
		height: 22px;
		display: grid;
		place-items: center;
		border-radius: 6px;
		color: var(--accent);
	}

	.source a:hover {
		background: var(--accent-soft);
	}

	.integrations {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 7px;
	}

	.integ {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
		padding: 10px;
		text-align: left;
	}

	.integ strong,
	.integ small {
		display: block;
	}

	.integ strong {
		font-size: 7.8px;
	}

	.integ small {
		margin-top: 2px;
		color: var(--faint);
		font-size: 6.4px;
	}

	.switch {
		position: relative;
		width: 22px;
		height: 13px;
		flex: 0 0 auto;
		border-radius: 7px;
		background: rgba(31, 53, 45, 0.18);
		transition: background 0.2s ease;
	}

	.switch b {
		position: absolute;
		left: 2px;
		top: 2px;
		width: 9px;
		height: 9px;
		border-radius: 50%;
		background: white;
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
		transition: translate 0.2s ease;
	}

	.integ.on .switch {
		background: var(--accent);
	}

	.integ.on .switch b {
		translate: 9px 0;
	}

	.log {
		align-self: start;
		overflow: hidden;
	}

	.log-rows {
		display: grid;
		padding: 4px 6px 8px;
	}

	.log-rows button {
		display: grid;
		grid-template-columns: 40px minmax(0, 1fr) auto;
		align-items: center;
		gap: 7px;
		padding: 5px;
		border-radius: 6px;
		font-family: ui-monospace, 'SF Mono', Menlo, monospace;
		text-align: left;
	}

	.log-rows button:hover {
		background: rgba(255, 255, 255, 0.55);
	}

	.log-rows time {
		color: var(--faint);
		font-size: 6.2px;
	}

	.log-rows strong,
	.log-rows small {
		display: block;
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
	}

	.log-rows strong {
		font-size: 7px;
	}

	.log-rows small {
		color: var(--muted);
		font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
		font-size: 6.4px;
	}

	.log-rows em {
		color: #2f7a5d;
		font-size: 6px;
		font-style: normal;
	}

	.explainer {
		margin-top: 10px;
		padding: 16px 18px;
	}

	.explainer h2 {
		font-size: 15px;
		letter-spacing: -0.03em;
	}

	.explainer div {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 16px;
		margin-top: 10px;
	}

	.explainer p {
		color: rgba(220, 238, 230, 0.66);
		font-size: 7.4px;
		line-height: 1.5;
	}

	.explainer strong {
		display: block;
		margin-bottom: 3px;
		color: white;
		font-size: 8px;
	}
</style>
