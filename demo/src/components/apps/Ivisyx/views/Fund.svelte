<script lang="ts">
	import { fly } from 'svelte/transition';
	import Check from '~icons/lucide/check';
	import FileText from '~icons/lucide/file-text';
	import Loader from '~icons/lucide/loader-circle';
	import Share from '~icons/lucide/share-2';
	import { suite } from '../state.svelte';
	import { jCurve, money } from '../suite-data';
	import AreaChart from '../ui/AreaChart.svelte';

	const quarters = ['Q4 23', 'Q1 24', 'Q2 24', 'Q3 24', 'Q4 24', 'Q1 25', 'Q2 25', 'Q3 25', 'Q4 25', 'Q1 26', 'Q2 26', 'Q3 26'];
	const lps = [
		{ name: 'Pinelands Public Retirement Fund', type: 'Public pension', share: 0.24 },
		{ name: 'Kittatinny College Endowment', type: 'Endowment', share: 0.18 },
		{ name: 'Palisade Family Office', type: 'Family office', share: 0.14 },
		{ name: 'Meridian Fund of Funds', type: 'Fund of funds', share: 0.12 },
		{ name: 'Founder & operator LPs (38)', type: 'Individuals', share: 0.19 },
		{ name: 'GP commitment', type: 'General partner', share: 0.13 },
	];
	const steps = ['Pulling latest marks', 'Reconciling capital accounts', 'Drafting partner letter', 'Rendering PDF'];

	let generating = $state(-1);
	let report = $state(false);

	const f = $derived(suite.fund);
	const flows = $derived([
		{ date: 'Sep 12, 2026', kind: 'Capital call', amount: f.committed * 0.06, note: 'Follow-ons: Copperleaf, Ridgeline' },
		{ date: 'Jul 30, 2026', kind: 'Distribution', amount: f.committed * 0.035, note: 'Secondary sale, Sable Pay' },
		{ date: 'Jun 03, 2026', kind: 'Capital call', amount: f.committed * 0.08, note: 'New: Mosaic, Gridmint' },
		{ date: 'Mar 18, 2026', kind: 'Capital call', amount: f.committed * 0.07, note: 'Management fee + 2 initial checks' },
	]);

	async function generate() {
		report = false;
		for (let i = 0; i < steps.length; i++) {
			generating = i;
			await new Promise((r) => setTimeout(r, 650));
		}
		generating = -1;
		report = true;
		suite.toast(`Q3 2026 LP report ready for ${lps.length} investor groups`, 'success');
	}
</script>

<section class="hero hero-dark rise">
	<div class="hero-top">
		<div>
			<span class="label">{suite.firm.name.toUpperCase()} · {suite.firm.fund.toUpperCase()} · {suite.firm.vintage} VINTAGE</span>
			<h1>{money(f.committed)} fund, <em>{f.tvpi.toFixed(2)}× TVPI</em></h1>
			<p>Net of fees and carry. Marks as of September 30, 2026. Synthetic demo figures.</p>
		</div>
		<div class="hero-actions">
			<button class="btn on-dark" onclick={() => suite.toast('Secure LP portal link copied (demo)', 'success')}><Share /> LP portal</button>
			<button class="btn primary" onclick={generate} disabled={generating >= 0}>{#if generating >= 0}<span class="spin"><Loader /></span> {steps[generating]}…{:else}<FileText /> Generate Q3 LP report{/if}</button>
		</div>
	</div>
	<div class="metrics">
		<div><small>TVPI</small><strong class="num">{f.tvpi.toFixed(2)}×</strong><span>Total value / paid-in</span></div>
		<div><small>DPI</small><strong class="num">{f.dpi.toFixed(2)}×</strong><span>Distributions / paid-in</span></div>
		<div><small>RVPI</small><strong class="num">{f.rvpi.toFixed(2)}×</strong><span>Residual value / paid-in</span></div>
		<div><small>NET IRR</small><strong class="num">{f.irr.toFixed(1)}%</strong><span>Top quartile for vintage*</span></div>
		<div><small>CALLED</small><strong class="num">{Math.round((f.called / f.committed) * 100)}%</strong><span>{money(f.called)} of {money(f.committed)}</span></div>
	</div>
	<div class="charts">
		<div>
			<span class="label">TVPI BY QUARTER</span>
			<AreaChart dark labels={quarters} height={120} series={[{ name: 'TVPI', values: f.tvpiSeries, color: '#ffd27a' }]} format={(v) => `${v.toFixed(2)}×`} />
		</div>
		<div>
			<span class="label">J-CURVE · NET CASH FLOW, % OF COMMITMENTS</span>
			<AreaChart dark zero labels={quarters} height={120} series={[{ name: 'Net cash flow', values: jCurve, color: '#7fe3b5' }]} format={(v) => `${v}%`} />
		</div>
	</div>
</section>

{#if report}
	<article class="card report" transition:fly={{ y: 8, duration: 240 }}>
		<div class="doc">
			<span class="eyebrow">Q3 2026 · Partner letter · Draft</span>
			<h2>Dear partners,</h2>
			<p>{suite.firm.fund} ended the quarter at <b>{f.tvpi.toFixed(2)}× TVPI</b> and <b>{f.irr.toFixed(1)}% net IRR</b>. We called {money(f.committed * 0.06)} for follow-ons in our two breakout companies and returned {money(f.committed * 0.035)} from a partial secondary. Our pipeline added {Object.keys(suite.pipeline).length} companies, with {Object.values(suite.pipeline).filter((s) => s === 'IC review').length} at investment committee…</p>
		</div>
		<div class="doc-actions">
			<span class="pill accent"><Check /> 12 pages · 4 exhibits</span>
			<button class="btn" onclick={() => suite.toast('Report sent for GP review', 'success')}>Send for review</button>
			<button class="btn primary" onclick={() => suite.toast('PDF downloaded (demo)', 'success')}><FileText /> Download PDF</button>
		</div>
	</article>
{/if}

<div class="lower">
	<article class="card">
		<header class="card-head"><div><h3>Capital account</h3><small>Commitments vs. called and returned</small></div></header>
		<div class="account">
			<div class="stack">
				<i style:width="{(f.called / f.committed) * 100}%" class="called"></i>
				<i style:width="{(f.distributed / f.committed) * 100}%" class="dist"></i>
			</div>
			<div class="account-legend">
				<span><i class="called"></i>Called <b>{money(f.called)}</b></span>
				<span><i class="dist"></i>Distributed <b>{money(f.distributed)}</b></span>
				<span><i class="nav"></i>NAV <b>{money(f.nav)}</b></span>
				<span><i class="dry"></i>Dry powder <b>{money(f.committed - f.called)}</b></span>
			</div>
		</div>
		<div class="flows">
			{#each flows as flow}
				<div><time>{flow.date}</time><i class="pill {flow.kind === 'Distribution' ? 'accent' : 'amber'}">{flow.kind}</i><span>{flow.note}</span><b class="num">{flow.kind === 'Distribution' ? '+' : '−'}{money(flow.amount)}</b></div>
			{/each}
		</div>
	</article>
	<article class="card">
		<header class="card-head"><div><h3>Limited partners</h3><small>{lps.length} investor groups · all fictional</small></div></header>
		<div class="lps">
			{#each lps as lp}
				<div>
					<span><strong>{lp.name}</strong><small>{lp.type}</small></span>
					<div class="bar"><i style:width="{lp.share * 300}%"></i></div>
					<b class="num">{money(f.committed * lp.share)}</b>
				</div>
			{/each}
		</div>
		<p class="foot">*Benchmark comparison is illustrative and not based on a real dataset.</p>
	</article>
</div>

<style>
	.hero {
		padding: 20px 22px 16px;
	}

	.hero-top {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 16px;
	}

	.label {
		color: rgba(200, 240, 222, 0.55);
		font-size: 6.3px;
		font-weight: 700;
		letter-spacing: 0.11em;
	}

	h1 {
		margin: 7px 0 5px;
		font-size: 27px;
		line-height: 1;
		letter-spacing: -0.055em;
	}

	h1 em {
		color: #d6a957;
		font-style: normal;
	}

	.hero p {
		color: rgba(220, 238, 230, 0.6);
		font-size: 7.6px;
	}

	.hero-actions {
		display: flex;
		gap: 6px;
	}

	.spin {
		display: inline-grid;
		animation: spin 0.9s linear infinite;
	}

	@keyframes spin {
		to {
			rotate: 360deg;
		}
	}

	.metrics {
		display: grid;
		grid-template-columns: repeat(5, 1fr);
		gap: 9px;
		margin: 18px 0 14px;
	}

	.metrics > div {
		padding: 11px;
		border: 1px solid rgba(255, 255, 255, 0.1);
		border-radius: 9px;
		background: rgba(255, 255, 255, 0.05);
	}

	.metrics small,
	.metrics strong,
	.metrics span {
		display: block;
	}

	.metrics small {
		color: #8fb0a2;
		font-size: 6px;
		letter-spacing: 0.09em;
	}

	.metrics strong {
		margin: 6px 0 4px;
		font-size: 22px;
		line-height: 1;
		letter-spacing: -0.04em;
	}

	.metrics span {
		color: rgba(200, 225, 214, 0.55);
		font-size: 6.3px;
	}

	.charts {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 14px;
	}

	.charts .label {
		display: block;
		margin-bottom: 4px;
	}

	.report {
		display: flex;
		align-items: flex-end;
		justify-content: space-between;
		gap: 14px;
		margin-top: 10px;
		padding: 14px;
		background: var(--glass-strong);
	}

	.doc h2 {
		margin: 5px 0 4px;
		font-family: 'New York', 'Iowan Old Style', Georgia, serif;
		font-size: 13px;
	}

	.doc p {
		max-width: 520px;
		color: var(--ink-2);
		font-family: 'New York', 'Iowan Old Style', Georgia, serif;
		font-size: 8px;
		line-height: 1.55;
	}

	.doc-actions {
		display: flex;
		align-items: center;
		gap: 6px;
	}

	.lower {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 10px;
		margin-top: 10px;
	}

	.account {
		padding: 12px;
	}

	.stack {
		position: relative;
		display: flex;
		height: 16px;
		overflow: hidden;
		border-radius: 5px;
		background: repeating-linear-gradient(135deg, rgba(31, 53, 45, 0.06) 0 4px, rgba(31, 53, 45, 0.02) 4px 8px);
	}

	.stack i {
		height: 100%;
	}

	.called {
		background: var(--accent);
	}

	.dist {
		background: #d6a957;
	}

	.nav {
		background: #6a4fa3;
	}

	.dry {
		background: rgba(31, 53, 45, 0.15);
	}

	.account-legend {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 5px 12px;
		margin-top: 9px;
		font-size: 7px;
	}

	.account-legend span {
		display: flex;
		align-items: center;
		gap: 5px;
		color: var(--muted);
	}

	.account-legend i {
		width: 7px;
		height: 7px;
		border-radius: 2px;
	}

	.account-legend b {
		margin-left: auto;
		color: var(--ink);
	}

	.flows,
	.lps {
		display: grid;
		padding: 0 12px 10px;
	}

	.flows > div {
		display: grid;
		grid-template-columns: 58px 62px 1fr auto;
		align-items: center;
		gap: 7px;
		padding: 6px 0;
		border-top: 1px solid var(--line);
		font-size: 7px;
	}

	.flows time,
	.flows span {
		color: var(--muted);
	}

	.flows .pill {
		justify-content: center;
		font-style: normal;
	}

	.lps {
		padding-top: 6px;
	}

	.lps > div {
		display: grid;
		grid-template-columns: minmax(0, 1.4fr) 1fr 44px;
		align-items: center;
		gap: 9px;
		padding: 5px 0;
		font-size: 7px;
	}

	.lps strong,
	.lps small {
		display: block;
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
	}

	.lps small {
		margin-top: 1px;
		color: var(--faint);
		font-size: 6.2px;
	}

	.lps b {
		text-align: right;
	}

	.foot {
		padding: 0 12px 10px;
		color: var(--faint);
		font-size: 6px;
	}
</style>
