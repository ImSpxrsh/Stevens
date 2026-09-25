<script lang="ts">
	import ArrowUpRight from '~icons/lucide/arrow-up-right';
	import Check from '~icons/lucide/check';
	import Flask from '~icons/lucide/flask-conical';
	import HeartPulse from '~icons/lucide/heart-pulse';
	import Landmark from '~icons/lucide/landmark';
	import { syntheticEntities } from '../directory';
	import { suite } from '../state.svelte';
	import Logo from '../ui/Logo.svelte';

	// Official program pages are real links; match counts come from synthetic records.
	const programs = [
		{ label: 'Research & development', name: 'SBIR / STTR support', org: 'CSIT', icon: Flask, tone: 'var(--accent)', text: 'Support for New Jersey businesses participating in federal small-business research programs.', url: 'https://www.njeda.gov/csit/', match: (s: string[]) => s.some((x) => /SBIR|award|Grant/i.test(x)) },
		{ label: 'Early-stage investment', name: 'Angel Investor Tax Credit', org: 'NJEDA', icon: Landmark, tone: '#c88b33', text: 'Tax credit program for qualifying investments in New Jersey technology businesses.', url: 'https://www.njeda.gov/angeltaxcredit/', match: (s: string[]) => s.some((x) => /Form D|round/i.test(x)) },
		{ label: 'Life sciences', name: 'Life Sciences & Healthcare Fund', org: 'NJEDA', icon: HeartPulse, tone: '#7d6eb4', text: 'A funding conversation for New Jersey life sciences and healthcare companies.', url: 'https://www.njeda.gov/', match: (_: string[], sector?: string) => sector === 'Life sciences' || sector === 'Health' },
	];

	const nj = syntheticEntities.filter((e) => e.state === 'NJ');
	const matched = programs.map((p) => nj.filter((e) => p.match(e.signals, e.sector)));
</script>

<header class="page-head">
	<div>
		<h1>Programs</h1>
		<p>Start with the program, then verify the fit. Eligibility must be confirmed with the program administrator.</p>
	</div>
</header>

<div class="grid">
	{#each programs as program, i}
		{@const Icon = program.icon}
		<article class="card program" style:--tone={program.tone}>
			<div class="top"><span class="icon"><Icon /></span><span class="org">{program.org}<b>{String(i + 1).padStart(2, '0')}</b></span></div>
			<small class="eyebrow">{program.label}</small>
			<h2>{program.name}</h2>
			<p>{program.text}</p>
			<div class="stats">
				<div><strong class="num">{matched[i].length}</strong><small>possible matches</small></div>
				<div><strong class="num">{Math.round(matched[i].length * 0.38)}</strong><small>verify on call</small></div>
			</div>
			<div class="faces">
				{#each matched[i].slice(0, 6) as e (e.id)}<button onclick={() => suite.open(e.id)} title={e.name}><Logo name={e.name} hue={e.hue} src={e.logo} seed={e.id} size={20} /></button>{/each}
				{#if matched[i].length > 6}<span>+{matched[i].length - 6}</span>{/if}
			</div>
			<a href={program.url} target="_blank" rel="noreferrer">Visit administrator <ArrowUpRight /></a>
		</article>
	{/each}
</div>

<div class="card semantics">
	<div><small class="eyebrow">Match labels</small><h2>How we label a program match</h2></div>
	<span class="strong"><i></i><strong>Strong match</strong><small>Material requirements established</small></span>
	<span class="potential"><i></i><strong>Potential match, verify</strong><small>At least one fact is unknown</small></span>
	<span><i></i><strong>Not a match</strong><small>A material requirement fails</small></span>
</div>

<div class="note"><Check /><span>Match counts are computed from synthetic company records. Program names and links point to official pages; re-verify current rules before making claims.</span></div>

<style>
	.grid {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: 10px;
	}

	.program {
		display: flex;
		flex-direction: column;
		overflow: hidden;
		padding: 16px 14px 13px;
	}

	.program::before {
		content: '';
		position: absolute;
		inset: 0 0 auto;
		height: 3px;
		background: var(--tone);
	}

	.top {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 14px;
	}

	.icon {
		width: 30px;
		height: 30px;
		display: grid;
		place-items: center;
		border-radius: 9px;
		background: color-mix(in srgb, var(--tone) 14%, transparent);
		color: var(--tone);
		font-size: 15px;
	}

	.org {
		display: flex;
		gap: 6px;
		color: var(--muted);
		font-size: 7px;
		font-weight: 700;
	}

	.org b {
		color: var(--faint);
		font-weight: 500;
	}

	h2 {
		margin: 5px 0 6px;
		font-size: 12.5px;
		line-height: 1.25;
		letter-spacing: -0.025em;
	}

	.program p {
		min-height: 36px;
		color: var(--muted);
		font-size: 7.2px;
		line-height: 1.45;
	}

	.stats {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 4px;
		margin-top: 12px;
		padding: 10px;
		border-radius: 8px;
		background: rgba(255, 255, 255, 0.4);
	}

	.stats strong,
	.stats small {
		display: block;
	}

	.stats strong {
		color: color-mix(in oklab, var(--tone) 80%, black);
		font-size: 19px;
	}

	.stats small {
		color: var(--faint);
		font-size: 6.2px;
	}

	.faces {
		display: flex;
		align-items: center;
		margin: 11px 0;
	}

	.faces button {
		margin-right: -4px;
		border-radius: 6px;
		transition: transform 0.12s ease;
	}

	.faces button:hover {
		z-index: 1;
		transform: translateY(-2px);
	}

	.faces span {
		margin-left: 8px;
		color: var(--faint);
		font-size: 6.6px;
	}

	a {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-top: auto;
		padding-top: 9px;
		border-top: 1px solid var(--line);
		color: var(--accent-deep);
		font-size: 7.3px;
		font-weight: 650;
	}

	.semantics {
		display: grid;
		grid-template-columns: 1.25fr 1fr 1.1fr 1fr;
		gap: 10px;
		align-items: center;
		margin-top: 10px;
		padding: 14px;
	}

	.semantics h2 {
		margin: 4px 0 0;
		font-size: 13px;
	}

	.semantics > span {
		display: grid;
		grid-template-columns: 8px 1fr;
		padding-left: 10px;
		border-left: 1px solid var(--line);
	}

	.semantics > span i {
		width: 6px;
		height: 6px;
		margin-top: 3px;
		border-radius: 50%;
		background: #7b8781;
	}

	.semantics > span.strong i {
		background: #46a07d;
	}

	.semantics > span.potential i {
		background: #d39a42;
	}

	.semantics > span strong {
		font-size: 7.5px;
	}

	.semantics > span small {
		grid-column: 2;
		margin-top: 2px;
		color: var(--faint);
		font-size: 6.3px;
	}

	.note {
		display: flex;
		align-items: center;
		gap: 7px;
		margin-top: 10px;
		padding: 9px 11px;
		border-radius: 9px;
		background: rgba(222, 237, 229, 0.6);
		color: #3c6958;
		font-size: 7.2px;
	}

	.note :global(svg) {
		flex: 0 0 auto;
		font-size: 12px;
	}
</style>
