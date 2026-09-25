<script lang="ts">
	import { fade, fly } from 'svelte/transition';
	import ArrowUpRight from '~icons/lucide/arrow-up-right';
	import Bookmark from '~icons/lucide/bookmark';
	import Check from '~icons/lucide/check';
	import FileText from '~icons/lucide/file-text';
	import Info from '~icons/lucide/info';
	import MapPin from '~icons/lucide/map-pin';
	import Plus from '~icons/lucide/plus';
	import Radar from '~icons/lucide/radar';
	import X from '~icons/lucide/x';
	import { entityById } from '../directory';
	import { age, suite } from '../state.svelte';
	import { fitFor, money, pipelineStages, team } from '../suite-data';
	import Logo from '../ui/Logo.svelte';
	import Ring from '../ui/Ring.svelte';

	const e = $derived(entityById.get(suite.selectedId!)!);
	const fit = $derived(e && !e.real ? fitFor(e, suite.firm) : null);
	const stage = $derived(suite.pipeline[e.id]);
	const owner = $derived(team.find((t) => t.id === suite.owner(e.id)));
	const activity = $derived(suite.events.filter((ev) => ev.companyId === e.id).slice(0, 5));
	const questions = $derived(e.unknowns ?? ['Team track record is not established from current sources', 'Revenue and customer concentration are not disclosed', 'Technical differentiation requires a deep dive']);
</script>

<div class="backdrop" role="presentation" transition:fade={{ duration: 150 }} onclick={(ev) => ev.target === ev.currentTarget && suite.close()}>
	<div class="drawer scroll" role="dialog" aria-modal="true" aria-label="{e.name} details" transition:fly={{ x: 30, duration: 200 }}>
		<header class="bar">
			<span class="pill {e.real ? 'accent' : 'amber'}">{e.real ? 'Real company' : 'Synthetic company'}</span>
			<button class="btn icon ghost" onclick={() => suite.close()} aria-label="Close"><X /></button>
		</header>

		<div class="identity">
			<Logo name={e.name} hue={e.hue} src={e.logo} seed={e.id} size={46} />
			<div>
				<h2>{e.name}</h2>
				<p class="loc"><MapPin />{e.town}{e.county ? `, ${e.county}` : ''} · {e.state}</p>
				<div class="tags">
					<i class="pill">{e.sector}</i>
					{#if e.stage}<i class="pill">{e.stage}</i>{/if}
					{#if e.companyType}<i class="pill">{e.companyType}</i>{/if}
				</div>
			</div>
			<button class="save" class:saved={suite.saved.includes(e.id)} onclick={() => suite.toggleSaved(e.id)} aria-label="Toggle watchlist"><Bookmark /></button>
		</div>

		<p class="desc">{e.description}</p>

		{#if e.real}
			<a class="btn primary wide" href={e.sourceUrl || e.website} target="_blank" rel="noreferrer">View official source <ArrowUpRight /></a>
			<div class="fact"><Check /><p>This profile references a real company. No simulated funding, patent, pipeline or scoring data is attached to it.</p></div>
			{#if e.townId}<button class="btn wide" onclick={() => { suite.radarTarget = e.townId; suite.close(); suite.go('radar'); }}><Radar /> Show {e.town} on the radar</button>{/if}
		{:else}
			{#if suite.selectedEvent}
				<div class="event">
					<span class="eyebrow">Simulated · {suite.selectedEvent.kind}</span>
					<h3>{suite.selectedEvent.title}</h3>
					<p>{suite.selectedEvent.summary}</p>
				</div>
			{/if}

			<div class="metrics">
				<div class="kpi"><small>Raising</small><strong>{e.raise ? money(e.raise) : '—'}</strong></div>
				<div class="kpi"><small>{e.deal ? 'Post-money' : 'Founded'}</small><strong>{e.deal ? money(e.deal.valuation) : e.founded}</strong></div>
				<div class="kpi"><small>Headcount</small><strong>{e.headcount}</strong></div>
				<div class="kpi"><small>Momentum</small><strong>{e.momentum}</strong></div>
			</div>

			{#if fit}
				<section class="fit">
					<Ring value={fit.total} size={54} stroke={4.5} />
					<div class="fit-bars">
						<span class="eyebrow">Fit for {suite.firm.name}</span>
						{#each [['Thesis sector', fit.thesis, 34], ['Stage', fit.stage, 26], ['Geography', fit.geography, 14], ['Signal momentum', fit.momentum, 26]] as [label, v, max]}
							<div><span>{label}</span><div class="bar"><i style:width="{(+v / +max) * 100}%"></i></div><b class="num">{v}/{max}</b></div>
						{/each}
					</div>
				</section>
			{/if}

			<section class="block">
				<h3>Pipeline</h3>
				{#if stage}
					<div class="stages">
						{#each pipelineStages as s}<button class:on={stage === s} onclick={() => suite.moveDeal(e.id, s)}>{s}</button>{/each}
					</div>
					<p class="owner"><span class="avatar" style:background={owner?.color}>{owner?.initials}</span>{owner?.name} · next: {e.deal?.nextStep ?? 'Schedule intro call'}</p>
				{:else}
					<button class="btn wide" onclick={() => suite.addToPipeline(e.id)}><Plus /> Add to pipeline</button>
				{/if}
			</section>

			<section class="block">
				<h3>Evidence</h3>
				{#each e.evidence ?? e.signals.map((s) => `${s} detected in a linked record`) as item}
					<div class="evidence"><FileText /><p>{item}<small>View linked demo source ↗</small></p></div>
				{/each}
			</section>

			<section class="block">
				<h3 class="warn"><Info /> Not established from current sources</h3>
				{#each questions as q}<p class="question">{q}</p>{/each}
			</section>

			<section class="block">
				<h3>Recent simulated activity <span>{activity.length}</span></h3>
				{#each activity as ev (ev.id)}
					<button class="activity" onclick={() => (suite.selectedEvent = ev)}><i class="pill amber">{ev.kind}</i><span>{ev.title}</span><time>{age(ev.timestamp, suite.now)}</time></button>
				{:else}
					<p class="muted small">No simulated signals for this company yet.</p>
				{/each}
			</section>

			<div class="actions">
				<button class="btn primary" onclick={() => suite.ask(`Draft an IC memo for ${e.name}`)}><FileText /> Draft IC memo</button>
				{#if e.townId}<button class="btn" onclick={() => { suite.radarTarget = e.townId; suite.close(); suite.go('radar'); }}><Radar /> Radar</button>{/if}
			</div>
		{/if}
	</div>
</div>

<style>
	.backdrop {
		position: absolute;
		inset: 0;
		z-index: 40;
		display: flex;
		justify-content: flex-end;
		background: rgba(8, 18, 15, 0.28);
		color: var(--ink);
		backdrop-filter: blur(2px);
	}

	.drawer {
		width: min(330px, 62%);
		height: 100%;
		padding: 20px 16px 20px;
		border-left: 1px solid rgba(255, 255, 255, 0.55);
		background: rgba(246, 247, 243, 0.985);
		box-shadow: -22px 0 60px rgba(6, 22, 16, 0.24);
		backdrop-filter: blur(26px);
	}

	.bar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 12px;
	}

	.identity {
		display: grid;
		grid-template-columns: 46px 1fr 24px;
		align-items: start;
		gap: 11px;
	}

	.identity h2 {
		font-size: 17px;
		line-height: 1.1;
		letter-spacing: -0.04em;
	}

	.loc {
		display: flex;
		align-items: center;
		gap: 3px;
		margin-top: 3px;
		color: var(--muted);
		font-size: 7px;
	}

	.tags {
		display: flex;
		flex-wrap: wrap;
		gap: 3px;
		margin-top: 6px;
	}

	.tags .pill {
		font-style: normal;
	}

	.save {
		width: 24px;
		height: 24px;
		display: grid;
		place-items: center;
		border-radius: 7px;
		color: var(--faint);
		font-size: 12px;
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

	.desc {
		margin: 12px 0;
		color: var(--ink-2);
		font-size: 8.2px;
		line-height: 1.55;
	}

	.wide {
		width: 100%;
		height: 28px;
		margin-bottom: 7px;
	}

	.fact {
		display: flex;
		gap: 7px;
		margin-bottom: 8px;
		padding: 9px;
		border-radius: 8px;
		background: var(--accent-soft);
		color: var(--accent-deep);
		font-size: 7.2px;
		line-height: 1.45;
	}

	.fact :global(svg) {
		flex: 0 0 auto;
		font-size: 11px;
	}

	.event {
		margin-bottom: 10px;
		padding: 10px;
		border: 1px solid rgba(200, 139, 51, 0.25);
		border-radius: 9px;
		background: rgba(255, 244, 218, 0.7);
	}

	.event h3 {
		margin: 3px 0;
		font-size: 9.5px;
	}

	.event p {
		color: #6f5a36;
		font-size: 7px;
		line-height: 1.45;
	}

	.metrics {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 5px;
	}

	.metrics .kpi {
		padding: 7px;
		border: 1px solid var(--line);
		border-radius: 8px;
		background: rgba(255, 255, 255, 0.6);
	}

	.metrics .kpi strong {
		font-size: 12px;
	}

	.fit {
		display: flex;
		align-items: center;
		gap: 12px;
		margin-top: 10px;
		padding: 11px;
		border-radius: 10px;
		background: linear-gradient(135deg, var(--accent-soft), rgba(255, 255, 255, 0.5));
	}

	.fit-bars {
		display: grid;
		flex: 1;
		gap: 4px;
	}

	.fit-bars > div {
		display: grid;
		grid-template-columns: 62px 1fr 30px;
		align-items: center;
		gap: 6px;
		font-size: 6.6px;
	}

	.fit-bars b {
		color: var(--muted);
		font-weight: 500;
		text-align: right;
	}

	.block {
		margin-top: 14px;
	}

	.block h3 {
		display: flex;
		align-items: center;
		gap: 5px;
		margin-bottom: 7px;
		color: var(--accent-deep);
		font-size: 8px;
	}

	.block h3.warn {
		color: #8b652c;
	}

	.block h3 span {
		color: var(--faint);
	}

	.stages {
		display: flex;
		flex-wrap: wrap;
		gap: 3px;
	}

	.stages button {
		padding: 4px 7px;
		border: 1px solid var(--line);
		border-radius: 6px;
		background: rgba(255, 255, 255, 0.5);
		color: var(--muted);
		font-size: 6.8px;
	}

	.stages button.on {
		border-color: transparent;
		background: var(--accent-deep);
		color: white;
		font-weight: 650;
	}

	.owner {
		display: flex;
		align-items: center;
		gap: 6px;
		margin-top: 7px;
		color: var(--muted);
		font-size: 7px;
	}

	.owner .avatar {
		width: 16px;
		height: 16px;
		font-size: 5.6px;
	}

	.evidence {
		display: flex;
		gap: 7px;
		margin-bottom: 4px;
		padding: 8px;
		border: 1px solid var(--line);
		border-radius: 7px;
		background: rgba(255, 255, 255, 0.5);
		font-size: 7.2px;
	}

	.evidence :global(svg) {
		flex: 0 0 auto;
		color: var(--accent);
		font-size: 10px;
	}

	.evidence small {
		display: block;
		margin-top: 3px;
		color: var(--accent);
		font-size: 6px;
	}

	.question {
		margin-bottom: 3px;
		padding: 5px 8px;
		border-left: 2px solid #cfa253;
		background: rgba(250, 239, 220, 0.55);
		color: #786c57;
		font-size: 7px;
	}

	.activity {
		width: 100%;
		display: grid;
		grid-template-columns: auto 1fr auto;
		align-items: center;
		gap: 6px;
		padding: 5px;
		border-radius: 6px;
		font-size: 7px;
		text-align: left;
	}

	.activity:hover {
		background: rgba(255, 255, 255, 0.6);
	}

	.activity .pill {
		font-style: normal;
	}

	.activity time {
		color: var(--faint);
		font-size: 6.2px;
	}

	.small {
		font-size: 7px;
	}

	.actions {
		display: flex;
		gap: 6px;
		margin-top: 16px;
	}
</style>
