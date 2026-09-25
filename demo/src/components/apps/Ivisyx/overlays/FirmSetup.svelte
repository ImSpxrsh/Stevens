<script lang="ts">
	import { fade, scale } from 'svelte/transition';
	import Check from '~icons/lucide/check';
	import X from '~icons/lucide/x';
	import { suite } from '../state.svelte';
	import { accentChoices, firmPresets, sectors, stages, type FirmProfile, type Sector, type Stage } from '../suite-data';

	const base = suite.firm;
	let draft = $state<FirmProfile>({ ...base, id: 'custom', sectors: [...base.sectors], stages: [...base.stages], example: false });

	const initials = $derived(
		draft.name
			.split(/\s+/)
			.filter(Boolean)
			.slice(0, 2)
			.map((w) => w[0].toUpperCase())
			.join('') || 'VC',
	);

	function toggle<T>(list: T[], value: T) {
		return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
	}

	function usePreset(f: FirmProfile) {
		draft = { ...f, id: 'custom', sectors: [...f.sectors], stages: [...f.stages], example: false, name: f.name };
	}

	function save() {
		if (!draft.sectors.length || !draft.stages.length) return;
		suite.customFirm = { ...draft, initials, name: draft.name.trim() || 'My Fund' };
		suite.firmId = 'custom';
		suite.setupOpen = false;
		suite.toast(`Workspace tuned for ${suite.customFirm.name}. Scores updated.`, 'success');
	}
</script>

<div class="backdrop" role="presentation" transition:fade={{ duration: 120 }} onclick={(e) => e.target === e.currentTarget && (suite.setupOpen = false)}>
	<div class="modal" role="dialog" aria-modal="true" aria-label="Set up your firm" transition:scale={{ start: 0.97, duration: 160 }}>
		<header>
			<div><span class="eyebrow">Works for any fund</span><h2>Set up your firm</h2><p>Ivisyx re-scores every company, re-weights the radar and re-cuts fund reporting around your thesis.</p></div>
			<button class="btn icon ghost" onclick={() => (suite.setupOpen = false)} aria-label="Close"><X /></button>
		</header>

		<div class="presets">
			<span>Start from</span>
			{#each firmPresets as f}<button onclick={() => usePreset(f)}><i style:background={f.accent}>{f.initials}</i>{f.name}</button>{/each}
		</div>

		<div class="form scroll">
			<div class="row two">
				<label><span>Firm name</span><input bind:value={draft.name} placeholder="Acme Ventures" /></label>
				<label><span>Fund</span><input bind:value={draft.fund} placeholder="Fund I" /></label>
			</div>
			<label><span>Thesis</span><textarea rows="2" bind:value={draft.thesis}></textarea></label>
			<div class="row">
				<span class="label">Sectors</span>
				<div class="chips">{#each sectors as s}<button class:on={draft.sectors.includes(s)} onclick={() => (draft.sectors = toggle<Sector>(draft.sectors, s))}>{#if draft.sectors.includes(s)}<Check />{/if}{s}</button>{/each}</div>
			</div>
			<div class="row">
				<span class="label">Stages</span>
				<div class="chips">{#each stages as s}<button class:on={draft.stages.includes(s)} onclick={() => (draft.stages = toggle<Stage>(draft.stages, s))}>{#if draft.stages.includes(s)}<Check />{/if}{s}</button>{/each}</div>
			</div>
			<div class="row three">
				<label><span>Geography</span><select class="select" bind:value={draft.geography}><option>New Jersey</option><option>US East Coast</option><option>North America</option><option>Global</option></select></label>
				<label><span>Check size</span><input bind:value={draft.check} /></label>
				<label><span>Fund size ($M)</span><input type="number" min="5" max="5000" bind:value={draft.fundSize} /></label>
			</div>
			<div class="row">
				<span class="label">Brand color</span>
				<div class="swatches">{#each accentChoices as c}<button class:on={draft.accent === c} style:background={c} onclick={() => (draft.accent = c)} aria-label="Accent {c}"></button>{/each}</div>
			</div>
		</div>

		<footer>
			<div class="preview"><i style:background={draft.accent}>{initials}</i><span><strong>{draft.name || 'My Fund'}</strong><small>{draft.fund} · ${draft.fundSize}M · {draft.sectors.length} sectors</small></span></div>
			<button class="btn" onclick={() => (suite.setupOpen = false)}>Cancel</button>
			<button class="btn primary" style:--accent={draft.accent} disabled={!draft.sectors.length || !draft.stages.length} onclick={save}>Save & re-score</button>
		</footer>
	</div>
</div>

<style>
	.backdrop {
		position: absolute;
		inset: 0;
		z-index: 55;
		display: grid;
		place-items: center;
		background: rgba(8, 18, 15, 0.34);
		color: var(--ink);
		backdrop-filter: blur(4px);
	}

	.modal {
		width: min(470px, 90%);
		max-height: 90%;
		display: flex;
		flex-direction: column;
		overflow: hidden;
		border: 1px solid rgba(255, 255, 255, 0.7);
		border-radius: 14px;
		background: rgba(248, 250, 248, 0.97);
		box-shadow: 0 30px 80px rgba(5, 20, 14, 0.35);
	}

	header {
		display: flex;
		justify-content: space-between;
		gap: 12px;
		padding: 16px 16px 10px;
	}

	h2 {
		margin: 3px 0 4px;
		font-size: 17px;
		letter-spacing: -0.04em;
	}

	header p {
		color: var(--muted);
		font-size: 7.6px;
		line-height: 1.45;
	}

	.presets {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 4px;
		padding: 0 16px 10px;
		color: var(--faint);
		font-size: 6.8px;
	}

	.presets button {
		display: flex;
		align-items: center;
		gap: 4px;
		padding: 3px 7px 3px 3px;
		border: 1px solid var(--line);
		border-radius: 7px;
		background: white;
		color: var(--ink-2);
		font-size: 7px;
	}

	.presets i,
	.preview i {
		width: 15px;
		height: 15px;
		display: grid;
		place-items: center;
		border-radius: 4px;
		color: white;
		font-size: 5.6px;
		font-style: normal;
		font-weight: 750;
	}

	.form {
		display: grid;
		gap: 10px;
		padding: 12px 16px;
		border-top: 1px solid var(--line);
		border-bottom: 1px solid var(--line);
	}

	.row {
		display: grid;
		gap: 5px;
	}

	.row.two {
		grid-template-columns: 2fr 1fr;
		gap: 8px;
	}

	.row.three {
		grid-template-columns: 1.2fr 1fr 1fr;
		gap: 8px;
	}

	label {
		display: grid;
		gap: 4px;
	}

	label > span,
	.label {
		color: var(--muted);
		font-size: 6.8px;
		font-weight: 650;
	}

	input,
	textarea {
		width: 100%;
		padding: 6px 8px;
		border: 1px solid rgba(31, 48, 42, 0.14);
		border-radius: 7px;
		outline: 0;
		background: white;
		font-size: 8px;
		resize: none;
	}

	input:focus,
	textarea:focus {
		border-color: var(--accent);
		box-shadow: 0 0 0 3px var(--accent-soft);
	}

	.select {
		width: 100%;
		height: 27px;
		background-color: white;
	}

	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
	}

	.chips button {
		display: flex;
		align-items: center;
		gap: 3px;
		padding: 4px 8px;
		border: 1px solid var(--line);
		border-radius: 12px;
		background: white;
		color: var(--muted);
		font-size: 7.2px;
	}

	.chips button.on {
		border-color: transparent;
		background: var(--accent-deep);
		color: white;
	}

	.chips :global(svg) {
		font-size: 8px;
	}

	.swatches {
		display: flex;
		gap: 6px;
	}

	.swatches button {
		width: 20px;
		height: 20px;
		border-radius: 50%;
		box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.1);
	}

	.swatches button.on {
		box-shadow: 0 0 0 2px white, 0 0 0 3.5px currentColor;
		outline: 2px solid rgba(0, 0, 0, 0.6);
		outline-offset: 2px;
	}

	footer {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 12px 16px;
	}

	.preview {
		display: flex;
		flex: 1;
		align-items: center;
		gap: 7px;
	}

	.preview i {
		width: 24px;
		height: 24px;
		font-size: 7.5px;
	}

	.preview strong,
	.preview small {
		display: block;
	}

	.preview strong {
		font-size: 8px;
	}

	.preview small {
		color: var(--faint);
		font-size: 6.5px;
	}
</style>
