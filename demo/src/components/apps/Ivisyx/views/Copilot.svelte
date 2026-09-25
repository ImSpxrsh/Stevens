<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { fly } from 'svelte/transition';
	import ArrowUp from '~icons/lucide/arrow-up';
	import Check from '~icons/lucide/check';
	import Database from '~icons/lucide/database';
	import { entities, entityById, syntheticEntities, type Entity } from '../directory';
	import { towns } from '../geo';
	import { suite } from '../state.svelte';
	import { fitFor, money } from '../suite-data';
	import logoUrl from '../logo.svg';
	import Logo from '../ui/Logo.svelte';
	import Score from '../ui/Score.svelte';

	type Block =
		| { type: 'h'; text: string }
		| { type: 'p'; text: string }
		| { type: 'metrics'; items: { label: string; value: string }[] }
		| { type: 'list'; items: { title: string; sub: string; id?: string; fit?: number }[] }
		| { type: 'note'; text: string };
	type Message = { role: 'user' | 'ai'; text?: string; blocks?: Block[]; shown: number; typed: number; steps?: string[]; step: number };

	let messages = $state<Message[]>([]);
	let input = $state('');
	let busy = $state(false);
	let scroller = $state<HTMLElement>();

	const suggestions = $derived([
		`Draft an IC memo for ${topMatch().name}`,
		'Which portfolio companies need attention?',
		"Summarize this week's signals for me",
		`Find companies similar to ${entityById.get('quarry')!.name}`,
		'Prep me for my next meeting',
	]);

	function topMatch(): Entity {
		return syntheticEntities.reduce((best, e) => (fitFor(e, suite.firm).total > fitFor(best, suite.firm).total ? e : best));
	}

	function mentioned(prompt: string) {
		const p = prompt.toLowerCase();
		return entities.filter((e) => p.includes(e.name.toLowerCase())).sort((a, b) => b.name.length - a.name.length)[0] ?? null;
	}

	function answer(prompt: string): Block[] {
		const p = prompt.toLowerCase();
		const firm = suite.firm;
		const named = mentioned(prompt);

		if (p.includes('memo') && !p.includes('board')) {
			const e = named && !named.real ? named : topMatch();
			const fit = fitFor(e, firm);
			return [
				{ type: 'h', text: `Investment memo: ${e.name}` },
				{ type: 'metrics', items: [{ label: 'Round', value: e.stage ?? '—' }, { label: 'Raising', value: e.raise ? money(e.raise) : '—' }, { label: 'Thesis fit', value: `${fit.total}/100` }, { label: 'Momentum', value: `${e.momentum}` }] },
				{ type: 'p', text: `${e.name} (${e.town}${e.state !== 'NJ' ? `, ${e.state}` : ''}) ${e.description.charAt(0).toLowerCase()}${e.description.slice(1)} It matches ${firm.name}'s focus on ${firm.sectors.slice(0, 2).join(' and ').toLowerCase()} at ${firm.stages.join('/')}, and public signals have accelerated over the last 90 days.` },
				{ type: 'h', text: 'Why now' },
				{ type: 'list', items: (e.evidence ?? e.signals.map((s) => `${s} detected in the last 60 days`)).map((s) => ({ title: s, sub: 'Linked source record · synthetic' })) },
				{ type: 'h', text: 'Open questions for the partner meeting' },
				{ type: 'list', items: (e.unknowns ?? ['Team track record is not established from current sources', 'Revenue quality and concentration are unknown', 'Competitive moat needs a technical deep dive']).map((s) => ({ title: s, sub: 'Not established from current sources' })) },
				{ type: 'h', text: 'Recommendation' },
				{ type: 'p', text: fit.total >= 75 ? `Advance to a partner meeting. At ${e.raise ? money(e.raise) : 'this round size'}, a ${firm.check} check fits reserves. Pressure-test the open questions before IC.` : `Monitor. The company scores ${fit.total}/100 against the current thesis; revisit if stage or sector focus changes.` },
				{ type: 'note', text: 'Drafted from synthetic demo records. Verify every fact before sharing.' },
			];
		}

		if (p.includes('portfolio') || p.includes('attention') || p.includes('board memo') || p.includes('runway')) {
			const risky = [...suite.portfolio].sort((a, b) => a.runway - b.runway).slice(0, 4);
			return [
				{ type: 'h', text: 'Portfolio companies to prioritise' },
				{ type: 'p', text: `${risky.filter((r) => r.runway < 12).length} companies are under 12 months of runway. Two are growing fast enough to raise; one likely needs a bridge conversation this month.` },
				{ type: 'list', items: risky.map((r) => ({ title: `${r.name} · ${r.runway} months runway`, sub: `${r.health} · ${r.update}` })) },
				{ type: 'metrics', items: [{ label: 'Reserves', value: money(suite.fund.reserves) }, { label: 'Bridge ask (est.)', value: money(risky[0].check * 0.5) }, { label: 'Board seats', value: `${suite.portfolio.filter((x) => x.board).length}` }] },
				{ type: 'note', text: 'Figures are synthetic and scaled to the active fund size.' },
			];
		}

		if (p.includes('similar') || p.includes('like')) {
			const base = named && !named.real ? named : entityById.get('quarry')!;
			const peers = syntheticEntities
				.filter((e) => e.id !== base.id && e.sector === base.sector)
				.map((e) => ({ e, fit: fitFor(e, firm).total }))
				.sort((a, b) => b.fit - a.fit)
				.slice(0, 5);
			return [
				{ type: 'h', text: `Companies similar to ${base.name}` },
				{ type: 'p', text: `Matched on sector (${base.sector}), stage and signal pattern, then ranked by fit for ${firm.name}.` },
				{ type: 'list', items: peers.map(({ e, fit }) => ({ title: e.name, sub: `${e.stage} · ${e.town} · ${e.description}`, id: e.id, fit })) },
			];
		}

		if (p.includes('meeting') || p.includes('prep')) {
			const e = entityById.get('quarry')!;
			return [
				{ type: 'h', text: `09:30 · Partner meeting with ${e.name}` },
				{ type: 'metrics', items: [{ label: 'Raising', value: money(e.raise ?? 0) }, { label: 'Headcount', value: `${e.headcount}` }, { label: 'Fit', value: `${fitFor(e, firm).total}` }] },
				{ type: 'p', text: `${e.name} ${e.description.charAt(0).toLowerCase()}${e.description.slice(1)} Engineering hiring is up sharply and the founder has a prior exit. Your associate flagged strong design-partner references.` },
				{ type: 'h', text: 'Ask about' },
				{ type: 'list', items: [{ title: 'Net revenue retention across design partners', sub: 'Not disclosed' }, { title: 'How the agent handles flaky test suites', sub: 'Technical moat' }, { title: 'Use of funds and 18-month hiring plan', sub: 'Round sizing' }] },
			];
		}

		const hotTowns = [...towns].sort((a, b) => b.signals30d - a.signals30d).slice(0, 3);
		const kinds = new Map<string, number>();
		for (const ev of suite.events) kinds.set(ev.kind, (kinds.get(ev.kind) ?? 0) + 1);
		const found = named ? [named] : entities.filter((e) => p.split(/\s+/).some((w) => w.length > 3 && `${e.name} ${e.sector} ${e.town}`.toLowerCase().includes(w))).slice(0, 5);
		return [
			{ type: 'h', text: found.length && !p.includes('signal') ? 'Matching companies' : "This week's signals" },
			{ type: 'metrics', items: [...kinds.entries()].slice(0, 4).map(([k, v]) => ({ label: k, value: `${v * 7}` })) },
			{ type: 'p', text: `Activity is concentrated in ${hotTowns.map((t) => t.name).join(', ')}. ${syntheticEntities.filter((e) => fitFor(e, firm).total >= 80).length} companies now score 80+ against ${firm.name}'s thesis.` },
			{ type: 'list', items: (found.length ? found : [topMatch(), ...syntheticEntities.slice(0, 3)]).map((e) => ({ title: e.name, sub: `${e.real ? 'Real company' : `${e.sector} · ${e.stage}`} · ${e.town}`, id: e.id, fit: e.real ? undefined : fitFor(e, firm).total })) },
		];
	}

	async function send(text = input) {
		const prompt = text.trim();
		if (!prompt || busy) return;
		input = '';
		busy = true;
		messages.push({ role: 'user', text: prompt, shown: 0, typed: 0, step: 0 });
		const steps = ['Working'];
		messages.push({ role: 'ai', blocks: answer(prompt), shown: 0, typed: 0, steps, step: 0 });
		const msg = messages[messages.length - 1];
		await scroll();
		for (let i = 0; i < steps.length; i++) {
			msg.step = i;
			await wait(650);
		}
		msg.step = steps.length;
		for (let b = 0; b < msg.blocks!.length; b++) {
			msg.shown = b + 1;
			const block = msg.blocks![b];
			if (block.type === 'p') {
				for (let c = 0; c <= block.text.length; c += 4) {
					msg.typed = c;
					await wait(12);
				}
			}
			msg.typed = Infinity;
			await scroll();
			await wait(block.type === 'h' ? 90 : 160);
		}
		busy = false;
	}

	const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));
	async function scroll() {
		await tick();
		scroller?.scrollTo({ top: scroller.scrollHeight, behavior: 'smooth' });
	}

	onMount(() => {
		if (suite.copilotQueue) {
			const q = suite.copilotQueue;
			suite.copilotQueue = null;
			send(q);
		}
	});
</script>

<div class="copilot">
	<section class="chat card">
		<div class="thread scroll" bind:this={scroller}>
			{#if !messages.length}
				<div class="welcome">
					<h1>Assistant</h1>
					<p>Ask about a company, your pipeline or the portfolio. Answers are built from the demo data in this workspace.</p>
					<div class="suggestions">
						{#each suggestions as s}<button onclick={() => send(s)}>{s}</button>{/each}
					</div>
				</div>
			{/if}
			{#each messages as m}
				{#if m.role === 'user'}
					<div class="user" in:fly={{ y: 6, duration: 180 }}><p>{m.text}</p></div>
				{:else}
					<div class="ai" in:fly={{ y: 6, duration: 180 }}>
						<span class="ai-mark"><img src={logoUrl} alt="" /></span>
						<div class="ai-body">
							{#if m.steps && m.step < m.steps.length}
								<div class="steps">
									{#each m.steps as s, i}
										{#if i <= m.step}<span class:done={i < m.step}>{#if i < m.step}<Check />{:else}<i class="spinner"></i>{/if}{s}…</span>{/if}
									{/each}
								</div>
							{/if}
							{#each (m.blocks ?? []).slice(0, m.shown) as b, bi}
								{#if b.type === 'h'}<h3>{b.text}</h3>
								{:else if b.type === 'p'}<p>{bi === m.shown - 1 && m.typed !== Infinity ? b.text.slice(0, m.typed) : b.text}{#if bi === m.shown - 1 && m.typed !== Infinity}<i class="caret"></i>{/if}</p>
								{:else if b.type === 'metrics'}
									<div class="metrics" in:fly={{ y: 4, duration: 180 }}>{#each b.items as item}<div class="kpi"><small>{item.label}</small><strong>{item.value}</strong></div>{/each}</div>
								{:else if b.type === 'list'}
									<div class="list" in:fly={{ y: 4, duration: 180 }}>
										{#each b.items as item}
											{@const e = item.id ? entityById.get(item.id) : null}
											<button disabled={!e} onclick={() => e && suite.open(e.id)}>
												{#if e}<Logo name={e.name} hue={e.hue} src={e.logo} seed={e.id} size={20} />{:else}<i class="bullet"></i>{/if}
												<span><strong>{item.title}</strong><small>{item.sub}</small></span>
												{#if item.fit !== undefined}<Score value={item.fit} />{/if}
											</button>
										{/each}
									</div>
								{:else}<div class="note">{b.text}</div>{/if}
							{/each}
						</div>
					</div>
				{/if}
			{/each}
		</div>
		<form class="composer" onsubmit={(e) => { e.preventDefault(); send(); }}>
			<input bind:value={input} placeholder="Ask a question" aria-label="Message the assistant" disabled={busy} />
			<button class="send" disabled={!input.trim() || busy} aria-label="Send"><ArrowUp /></button>
		</form>
	</section>

	<aside class="context">
		<div class="card ctx">
			<span class="eyebrow">Data used</span>
			<div class="ctx-row"><Database /><span><strong>{entities.length.toLocaleString()} companies</strong><small>{towns.length} NJ municipalities</small></span></div>
			<div class="ctx-row"><Database /><span><strong>{suite.events.length} live signals</strong><small>SEC, USPTO, SBIR (simulated)</small></span></div>
			<div class="ctx-row"><Database /><span><strong>{suite.portfolio.length} portfolio companies</strong><small>{suite.firm.fund} marks</small></span></div>
		</div>
		<div class="card ctx">
			<span class="eyebrow">Thesis</span>
			<p>{suite.firm.thesis}</p>
			<div class="tags">{#each suite.firm.sectors as s}<i class="pill accent">{s}</i>{/each}{#each suite.firm.stages as s}<i class="pill">{s}</i>{/each}</div>
			<button class="btn" onclick={() => (suite.setupOpen = true)}>Edit thesis</button>
		</div>
		<div class="card ctx demo">
			<strong>Scripted demo responses</strong>
			<p>Answers are generated from the synthetic records in this demo. It does not call a language model.</p>
		</div>
	</aside>
</div>

<style>
	.copilot {
		flex: 1;
		min-height: 0;
		display: grid;
		grid-template-columns: minmax(0, 1fr) 200px;
		gap: 10px;
	}

	.chat {
		min-height: 0;
		display: flex;
		flex-direction: column;
		overflow: hidden;
		background: var(--glass-strong);
	}

	.thread {
		flex: 1;
		min-height: 0;
		padding: 18px 22px;
	}

	.welcome {
		max-width: 440px;
		margin: 22px auto 0;
		text-align: center;
	}




	.welcome h1 {
		margin: 0 0 6px;
		font-size: 21px;
		letter-spacing: -0.045em;
	}

	.welcome p {
		color: var(--muted);
		font-size: 8px;
		line-height: 1.5;
	}

	.suggestions {
		display: grid;
		gap: 5px;
		margin-top: 16px;
	}

	.suggestions button {
		display: flex;
		align-items: center;
		gap: 7px;
		padding: 8px 10px;
		border: 1px solid rgba(255, 255, 255, 0.7);
		border-radius: 9px;
		background: rgba(255, 255, 255, 0.6);
		font-size: 7.8px;
		text-align: left;
		transition: background 0.15s ease;
	}

	.suggestions button:hover {
		background: white;
	}


	.user {
		display: flex;
		justify-content: flex-end;
		margin: 10px 0;
	}

	.user p {
		max-width: 70%;
		padding: 8px 11px;
		border-radius: 12px 12px 3px 12px;
		background: var(--accent-deep);
		color: white;
		font-size: 8px;
	}

	.ai {
		display: grid;
		grid-template-columns: 22px 1fr;
		gap: 9px;
		margin: 12px 0 18px;
	}

	.ai-mark {
		width: 22px;
		height: 22px;
		display: grid;
		place-items: center;
		border-radius: 7px;
		background: linear-gradient(180deg, #fff, #dfe5e7);
		box-shadow: 0 3px 8px rgba(0, 0, 0, 0.12);
	}

	.ai-mark img {
		width: 15px;
	}

	.ai-body {
		min-width: 0;
		max-width: 560px;
	}

	.steps {
		display: grid;
		gap: 4px;
		color: var(--muted);
		font-size: 7.3px;
	}

	.steps span {
		display: flex;
		align-items: center;
		gap: 5px;
	}

	.steps span.done {
		color: var(--faint);
	}

	.steps :global(svg) {
		color: var(--accent);
		font-size: 9px;
	}

	.spinner {
		width: 8px;
		height: 8px;
		border: 1.5px solid var(--accent-line);
		border-top-color: var(--accent);
		border-radius: 50%;
		animation: spin 0.7s linear infinite;
	}

	@keyframes spin {
		to {
			rotate: 360deg;
		}
	}

	.ai h3 {
		margin: 10px 0 5px;
		font-size: 10px;
		letter-spacing: -0.015em;
	}

	.ai h3:first-of-type {
		margin-top: 0;
	}

	.ai p {
		color: var(--ink-2);
		font-size: 8px;
		line-height: 1.6;
	}

	.caret {
		display: inline-block;
		width: 5px;
		height: 9px;
		margin-left: 1px;
		vertical-align: -1px;
		background: var(--accent);
		animation: blink 0.8s steps(2) infinite;
	}

	@keyframes blink {
		50% {
			opacity: 0;
		}
	}

	.metrics {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(90px, 1fr));
		gap: 6px;
		margin: 6px 0;
	}

	.metrics .kpi {
		padding: 8px;
		border: 1px solid var(--line);
		border-radius: 8px;
		background: rgba(255, 255, 255, 0.6);
	}

	.metrics .kpi strong {
		font-size: 13px;
	}

	.list {
		display: grid;
		gap: 2px;
		margin: 4px 0;
	}

	.list button {
		display: grid;
		grid-template-columns: 20px minmax(0, 1fr) auto;
		align-items: center;
		gap: 8px;
		padding: 5px 6px;
		border-radius: 7px;
		text-align: left;
	}

	.list button:not(:disabled):hover {
		background: rgba(255, 255, 255, 0.8);
	}

	.list button:disabled {
		cursor: default;
	}

	.bullet {
		width: 6px;
		height: 6px;
		justify-self: center;
		border-radius: 50%;
		background: var(--accent);
	}

	.list strong,
	.list small {
		display: block;
	}

	.list strong {
		font-size: 7.8px;
	}

	.list small {
		margin-top: 1px;
		overflow: hidden;
		color: var(--faint);
		font-size: 6.5px;
		white-space: nowrap;
		text-overflow: ellipsis;
	}

	.note {
		margin-top: 8px;
		padding: 6px 8px;
		border-radius: 7px;
		background: var(--amber-soft);
		color: #7a5520;
		font-size: 6.8px;
	}

	.composer {
		display: flex;
		align-items: center;
		gap: 8px;
		margin: 0 14px 14px;
		padding: 6px 6px 6px 12px;
		border: 1px solid rgba(31, 48, 42, 0.12);
		border-radius: 12px;
		background: white;
		box-shadow: 0 8px 24px rgba(13, 35, 28, 0.08);
	}


	.composer input {
		flex: 1;
		border: 0;
		outline: 0;
		background: transparent;
		font-size: 8.3px;
	}

	.send {
		width: 26px;
		height: 26px;
		display: grid;
		place-items: center;
		border-radius: 8px;
		background: var(--accent-deep);
		color: white;
		font-size: 12px;
		transition: opacity 0.15s ease;
	}

	.send:disabled {
		opacity: 0.35;
	}

	.context {
		display: grid;
		align-content: start;
		gap: 8px;
		min-height: 0;
		overflow: auto;
	}

	.ctx {
		display: grid;
		gap: 7px;
		padding: 11px;
	}

	.ctx p {
		color: var(--muted);
		font-size: 7.2px;
		line-height: 1.45;
	}

	.ctx-row {
		display: flex;
		align-items: center;
		gap: 7px;
		color: var(--accent);
		font-size: 11px;
	}

	.ctx-row strong,
	.ctx-row small {
		display: block;
	}

	.ctx-row strong {
		color: var(--ink);
		font-size: 7.6px;
	}

	.ctx-row small {
		color: var(--faint);
		font-size: 6.3px;
	}

	.tags {
		display: flex;
		flex-wrap: wrap;
		gap: 3px;
	}

	.tags .pill {
		font-style: normal;
	}

	.ctx .btn {
		justify-self: start;
	}

	.demo {
		background: rgba(255, 244, 216, 0.6);
	}

	.demo strong {
		font-size: 7.6px;
	}
</style>
