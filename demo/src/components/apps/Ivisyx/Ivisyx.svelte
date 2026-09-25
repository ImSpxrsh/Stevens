<script lang="ts">
	import { onMount } from 'svelte';
	import { fade, fly } from 'svelte/transition';
	import Bell from '~icons/lucide/bell';
	import Briefcase from '~icons/lucide/briefcase';
	import Building from '~icons/lucide/building-2';
	import ChartPie from '~icons/lucide/chart-pie';
	import Check from '~icons/lucide/check';
	import ChevronDown from '~icons/lucide/chevron-down';
	import Database from '~icons/lucide/database';
	import Kanban from '~icons/lucide/kanban';
	import Landmark from '~icons/lucide/landmark';
	import Dashboard from '~icons/lucide/layout-dashboard';
	import Grid from '~icons/lucide/layout-grid';
	import MapPin from '~icons/lucide/map-pinned';
	import Message from '~icons/lucide/message-square';
	import Search from '~icons/lucide/search';
	import Settings from '~icons/lucide/sliders-horizontal';
	import './ivisyx.css';
	import logoUrl from './logo.svg';
	import { entities } from './directory';
	import { age, suite, viewLabels, type View } from './state.svelte';
	import { firmPresets, team } from './suite-data';
	import CommandPalette from './overlays/CommandPalette.svelte';
	import CompanyDrawer from './overlays/CompanyDrawer.svelte';
	import FirmSetup from './overlays/FirmSetup.svelte';
	import CompaniesView from './views/Companies.svelte';
	import CopilotView from './views/Copilot.svelte';
	import DashboardView from './views/Dashboard.svelte';
	import FundView from './views/Fund.svelte';
	import MarketView from './views/MarketMap.svelte';
	import PipelineView from './views/Pipeline.svelte';
	import PortfolioView from './views/Portfolio.svelte';
	import ProgramsView from './views/Programs.svelte';
	import RadarView from './views/Radar.svelte';
	import SourcesView from './views/Sources.svelte';

	let frameW = $state(1180);
	let frameH = $state(720);
	// The whole app is laid out on a ~1000×610 canvas and zoomed to fit the
	// window, so fullscreen scales up instead of scattering the layout.
	const scale = $derived(Math.max(0.72, Math.min(1.7, frameW / 1000, frameH / 610)));

	let workspaceOpen = $state(false);
	let bellOpen = $state(false);
	let seen = $state(0);

	const activeDeals = $derived(Object.values(suite.pipeline).filter((s) => s !== 'Closed').length);
	const unread = $derived(Math.max(0, suite.sequence - seen) + 3);

	const nav: { label?: string; items: { id: View; icon: any; count?: () => string | number }[] }[] = [
		{
			items: [
				{ id: 'dashboard', icon: Dashboard },
				{ id: 'radar', icon: MapPin },
				{ id: 'pipeline', icon: Kanban, count: () => activeDeals },
				{ id: 'companies', icon: Building, count: () => entities.length.toLocaleString() },
				{ id: 'portfolio', icon: Briefcase, count: () => suite.portfolio.length },
			],
		},
		{ label: 'Research', items: [{ id: 'market', icon: Grid }, { id: 'copilot', icon: Message }, { id: 'programs', icon: Landmark }] },
		{ label: 'Fund', items: [{ id: 'fund', icon: ChartPie }, { id: 'sources', icon: Database, count: () => 14 }] },
	];

	const notifications = $derived([
		...suite.events.slice(0, 3).map((e) => ({ title: e.title, body: entities.find((x) => x.id === e.companyId)?.name ?? '', time: age(e.timestamp, suite.now), id: e.companyId })),
		{ title: 'IC vote scheduled', body: 'Aster BioSystems · Thursday 10:00', time: '1h ago', id: 'aster' },
		{ title: 'Portfolio alert: runway under 8 months', body: 'Bramble Health', time: '3h ago', id: null },
		{ title: 'Capital call processed', body: `${suite.firm.fund} · 100% received`, time: 'Yesterday', id: null },
	]);

	function selectFirm(id: string) {
		suite.firmId = id;
		workspaceOpen = false;
		suite.toast(`Switched to ${suite.firm.name}`, 'success');
	}

	onMount(() => {
		try {
			const saved = JSON.parse(localStorage.getItem('ivisyx-v1') || '{}');
			if (saved.customFirm) suite.customFirm = saved.customFirm;
			if (saved.firmId) suite.firmId = saved.firmId;
			if (Array.isArray(saved.saved)) suite.saved = saved.saved.filter((id: string) => entities.some((e) => e.id === id));
		} catch {}

		let timer: ReturnType<typeof setTimeout>;
		let disposed = false;
		const schedule = () => {
			timer = setTimeout(
				() => {
					if (disposed) return;
					if (suite.playing && !document.hidden) suite.addSignal();
					schedule();
				},
				suite.fast ? 2600 + Math.random() * 2400 : 7000 + Math.random() * 7000,
			);
		};
		schedule();
		const clock = setInterval(() => (suite.now = Date.now()), 1000);
		return () => {
			disposed = true;
			clearTimeout(timer);
			clearInterval(clock);
		};
	});

	$effect(() => {
		const data = { firmId: suite.firmId, customFirm: suite.customFirm, saved: suite.saved };
		try {
			localStorage.setItem('ivisyx-v1', JSON.stringify(data));
		} catch {}
	});

	function onkeydown(event: KeyboardEvent) {
		if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
			event.preventDefault();
			suite.paletteOpen = !suite.paletteOpen;
		} else if (event.key === 'Escape') {
			if (suite.paletteOpen) suite.paletteOpen = false;
			else if (suite.setupOpen) suite.setupOpen = false;
			else if (suite.selectedId) suite.close();
			workspaceOpen = bellOpen = false;
		}
	}
</script>

<svelte:window {onkeydown} />

<div class="frame" bind:clientWidth={frameW} bind:clientHeight={frameH}>
	<section class="ivx app" style:--accent={suite.firm.accent} style:zoom={scale} style:width="{frameW / scale}px" style:height="{frameH / scale}px">
		<aside class="sidebar">
			<div class="side-top app-window-drag-handle"></div>
			<div class="brand">
				<span class="mark"><img src={logoUrl} alt="" /></span>
				<strong>Ivisyx</strong>
			</div>

			{#each nav as group}
				{#if group.label}<div class="nav-label">{group.label}</div>{/if}
				<nav>
					{#each group.items as item}
						{@const Icon = item.icon}
						<button class:active={suite.view === item.id} onclick={() => suite.go(item.id)}>
							<Icon />
							<span>{viewLabels[item.id]}</span>
							{#if item.count}<b>{item.count()}</b>{/if}
						</button>
					{/each}
				</nav>
			{/each}

			<div class="spacer"></div>

			<div class="status">
				<i class="live-dot" class:paused={!suite.playing}></i>
				<span><strong>14 sources connected</strong><small>{suite.playing ? `Updated ${suite.events[0] ? age(suite.events[0].timestamp, suite.now).toLowerCase() : 'just now'}` : 'Updates paused'}</small></span>
			</div>

			<div class="workspace-wrap">
				{#if workspaceOpen}
					<div class="workspace-menu" transition:fly={{ y: 6, duration: 160 }}>
						<small>Switch workspace</small>
						{#each firmPresets as f}
							<button onclick={() => selectFirm(f.id)}>
								<span class="ws-avatar" style:background={f.accent}>{f.initials}</span>
								<span><strong>{f.name}</strong><small>{f.fund} · ${f.fundSize}M · {f.geography}</small></span>
								{#if suite.firmId === f.id}<Check />{/if}
							</button>
						{/each}
						{#if suite.customFirm}
							<button onclick={() => selectFirm('custom')}>
								<span class="ws-avatar" style:background={suite.customFirm.accent}>{suite.customFirm.initials}</span>
								<span><strong>{suite.customFirm.name}</strong><small>Custom · ${suite.customFirm.fundSize}M</small></span>
								{#if suite.firmId === 'custom'}<Check />{/if}
							</button>
						{/if}
						<button class="customize" onclick={() => { workspaceOpen = false; suite.setupOpen = true; }}><Settings /> Set up your firm…</button>
					</div>
				{/if}
				<button class="workspace" onclick={() => (workspaceOpen = !workspaceOpen)}>
					<span class="ws-avatar" style:background={suite.firm.accent}>{suite.firm.initials}</span>
					<span><strong>{suite.firm.name}</strong><small>{suite.firm.fund} · ${suite.firm.fundSize}M</small></span>
					<ChevronDown />
				</button>
			</div>
		</aside>

		<main class="surface">
			<header class="topbar app-window-drag-handle">
				<div class="crumbs">{suite.firm.name}<span>/</span><strong>{viewLabels[suite.view]}</strong></div>
				<div class="top-actions">
					<button class="search-pill" onclick={() => (suite.paletteOpen = true)}><Search /><span>Search companies, towns, actions</span><kbd>⌘K</kbd></button>
					<div class="bell-wrap">
						<button class="bell" aria-label="Notifications" onclick={() => { bellOpen = !bellOpen; seen = suite.sequence; }}><Bell />{#if unread}<i>{unread}</i>{/if}</button>
						{#if bellOpen}
							<div class="bell-menu" transition:fly={{ y: -6, duration: 160 }}>
								<header><strong>Notifications</strong><button onclick={() => (bellOpen = false)}>Mark all read</button></header>
								{#each notifications as n}
									<button onclick={() => { if (n.id) suite.open(n.id); bellOpen = false; }}>
										<i></i><span><strong>{n.title}</strong><small>{n.body}</small></span><time>{n.time}</time>
									</button>
								{/each}
							</div>
						{/if}
					</div>
					<div class="team">
						{#each team as t}<span class="avatar" style:background={t.color} title="{t.name}, {t.role}">{t.initials}</span>{/each}
					</div>
					<span class="demo-pill">Demo data</span>
				</div>
			</header>

			{#key suite.view}
				<div class="page scroll" class:fill={['radar', 'pipeline', 'copilot'].includes(suite.view)} in:fade={{ duration: 160 }}>
					{#if suite.view === 'dashboard'}<DashboardView />
					{:else if suite.view === 'radar'}<RadarView />
					{:else if suite.view === 'pipeline'}<PipelineView />
					{:else if suite.view === 'companies'}<CompaniesView />
					{:else if suite.view === 'portfolio'}<PortfolioView />
					{:else if suite.view === 'market'}<MarketView />
					{:else if suite.view === 'copilot'}<CopilotView />
					{:else if suite.view === 'fund'}<FundView />
					{:else if suite.view === 'programs'}<ProgramsView />
					{:else}<SourcesView />{/if}
				</div>
			{/key}
		</main>

		{#if suite.selectedId}<CompanyDrawer />{/if}
		{#if suite.paletteOpen}<CommandPalette />{/if}
		{#if suite.setupOpen}<FirmSetup />{/if}

		<div class="toasts" aria-live="polite">
			{#each suite.toasts as t (t.id)}
				<div class="toast" class:success={t.tone === 'success'} in:fly={{ y: 10, duration: 200 }} out:fade={{ duration: 160 }}>
					{#if t.tone === 'success'}<Check />{/if}{t.text}
				</div>
			{/each}
		</div>
	</section>
</div>

<style>
	.frame {
		width: 100%;
		height: 100%;
		overflow: hidden;
		border-radius: inherit;
	}

	.app {
		position: relative;
		display: grid;
		grid-template-columns: 172px minmax(0, 1fr);
		overflow: hidden;
		border-radius: inherit;
		color: #f6f8f7;
		background: rgba(15, 25, 23, 0.5);
		backdrop-filter: blur(36px) saturate(125%);
		box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.22);
		isolation: isolate;
	}

	/* Sidebar */
	.sidebar {
		position: relative;
		z-index: 3;
		min-width: 0;
		min-height: 0;
		display: flex;
		flex-direction: column;
		padding: 0 10px 11px;
		background: linear-gradient(180deg, rgba(13, 18, 17, 0.8), rgba(18, 25, 22, 0.7));
		border-right: 1px solid rgba(255, 255, 255, 0.08);
	}

	.side-top {
		flex: 0 0 34px;
		margin: 0 -10px;
	}

	.brand {
		display: flex;
		align-items: center;
		gap: 9px;
		padding: 0 5px 12px;
	}

	.mark {
		width: 32px;
		height: 32px;
		display: grid;
		place-items: center;
		flex: 0 0 auto;
		border-radius: 9px;
		background: linear-gradient(180deg, #ffffff, #dfe5e7);
		box-shadow: 0 5px 13px rgba(0, 0, 0, 0.3), inset 0 0 0 0.5px rgba(0, 0, 0, 0.1);
	}

	.mark img {
		width: 23px;
		height: 23px;
		filter: drop-shadow(0 2px 3px rgba(10, 20, 23, 0.25));
	}

	.brand strong {
		font-size: 16px;
		font-weight: 650;
		letter-spacing: -0.03em;
	}





	.nav-label {
		margin: 14px 8px 5px;
		color: rgba(255, 255, 255, 0.36);
		font-size: 7px;
		font-weight: 600;
	}

	nav {
		display: grid;
		gap: 2px;
	}

	nav button {
		position: relative;
		width: 100%;
		min-height: 27px;
		display: grid;
		grid-template-columns: 16px 1fr auto;
		align-items: center;
		gap: 7px;
		padding: 0 8px;
		border-radius: 7px;
		color: rgba(255, 255, 255, 0.62);
		font-size: 8.5px;
		text-align: left;
		transition: background 0.15s ease, color 0.15s ease;
	}

	nav button :global(svg) {
		font-size: 13px;
	}

	nav button b {
		color: rgba(255, 255, 255, 0.34);
		font-size: 6.5px;
		font-weight: 500;
	}



	nav button:hover {
		background: rgba(255, 255, 255, 0.07);
		color: rgba(255, 255, 255, 0.85);
	}

	nav button.active {
		background: rgba(255, 255, 255, 0.14);
		color: #fff;
		box-shadow: inset 0 0 0 0.5px rgba(255, 255, 255, 0.12);
	}

	.spacer {
		flex: 1;
	}

	.status {
		display: flex;
		align-items: center;
		gap: 7px;
		margin-bottom: 7px;
		padding: 8px 9px;
		border: 1px solid rgba(255, 255, 255, 0.08);
		border-radius: 9px;
		background: rgba(255, 255, 255, 0.05);
	}

	.status strong,
	.status small {
		display: block;
	}

	.status strong {
		font-size: 7.5px;
	}

	.status small {
		margin-top: 2px;
		color: rgba(255, 255, 255, 0.4);
		font-size: 6.3px;
	}

	.workspace-wrap {
		position: relative;
	}

	.workspace {
		width: 100%;
		display: grid;
		grid-template-columns: 22px minmax(0, 1fr) 10px;
		align-items: center;
		gap: 7px;
		padding: 6px 7px;
		border-radius: 9px;
		text-align: left;
		transition: background 0.15s ease;
	}

	.workspace:hover {
		background: rgba(255, 255, 255, 0.07);
	}

	.workspace :global(svg) {
		color: rgba(255, 255, 255, 0.4);
		font-size: 10px;
	}

	.workspace strong,
	.workspace small,
	.workspace-menu button strong,
	.workspace-menu button small {
		display: block;
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
	}

	.workspace strong {
		font-size: 8px;
	}

	.workspace small {
		margin-top: 1px;
		color: rgba(255, 255, 255, 0.4);
		font-size: 6.3px;
	}

	.ws-avatar {
		width: 22px;
		height: 22px;
		display: grid;
		place-items: center;
		border-radius: 6px;
		color: white;
		font-size: 7px;
		font-weight: 750;
		box-shadow: inset 0 0 0 0.5px rgba(255, 255, 255, 0.3), 0 3px 8px rgba(0, 0, 0, 0.25);
	}

	.workspace-menu {
		position: absolute;
		left: 0;
		right: -40px;
		bottom: calc(100% + 6px);
		z-index: 10;
		padding: 6px;
		border: 1px solid rgba(255, 255, 255, 0.12);
		border-radius: 10px;
		background: rgba(20, 28, 25, 0.96);
		box-shadow: 0 18px 40px rgba(0, 0, 0, 0.4);
		backdrop-filter: blur(20px);
	}

	.workspace-menu > small {
		display: block;
		padding: 3px 6px 5px;
		color: rgba(255, 255, 255, 0.45);
		font-size: 7px;
	}

	.workspace-menu button {
		width: 100%;
		display: grid;
		grid-template-columns: 22px minmax(0, 1fr) 10px;
		align-items: center;
		gap: 7px;
		padding: 5px 6px;
		border-radius: 7px;
		text-align: left;
	}

	.workspace-menu button:hover {
		background: rgba(255, 255, 255, 0.08);
	}

	.workspace-menu button strong {
		font-size: 7.8px;
	}

	.workspace-menu button small {
		margin-top: 1px;
		color: rgba(255, 255, 255, 0.42);
		font-size: 6.2px;
	}

	.workspace-menu button :global(svg) {
		color: #7fe3b5;
		font-size: 10px;
	}

	.workspace-menu .customize {
		display: flex;
		gap: 6px;
		margin-top: 4px;
		padding: 7px 6px;
		border-top: 1px solid rgba(255, 255, 255, 0.08);
		border-radius: 0 0 7px 7px;
		color: rgba(255, 255, 255, 0.75);
		font-size: 7.5px;
	}

	.workspace-menu .customize :global(svg) {
		color: inherit;
	}

	/* Main surface */
	.surface {
		position: relative;
		min-width: 0;
		min-height: 0;
		display: flex;
		flex-direction: column;
		background: linear-gradient(145deg, rgba(232, 237, 233, 0.7), rgba(186, 200, 194, 0.48));
		color: var(--ink);
	}

	.topbar {
		position: relative;
		z-index: 4;
		flex: 0 0 38px;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 10px;
		padding: 0 16px;
		border-bottom: 1px solid rgba(31, 53, 45, 0.07);
	}

	.crumbs {
		overflow: hidden;
		color: var(--muted);
		font-size: 8px;
		white-space: nowrap;
		text-overflow: ellipsis;
	}

	.crumbs span {
		margin: 0 5px;
		opacity: 0.45;
	}

	.crumbs strong {
		color: var(--ink);
		font-weight: 650;
	}

	.top-actions {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.search-pill {
		width: 210px;
		height: 24px;
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 0 7px;
		border: 1px solid rgba(31, 48, 42, 0.11);
		border-radius: 7px;
		background: rgba(255, 255, 255, 0.5);
		color: #7d8883;
		font-size: 7.5px;
		box-shadow: 0 3px 10px rgba(20, 42, 34, 0.04);
	}

	.search-pill:hover {
		background: rgba(255, 255, 255, 0.8);
	}

	.search-pill :global(svg) {
		font-size: 11px;
	}

	.search-pill span {
		flex: 1;
		text-align: left;
	}

	.bell-wrap {
		position: relative;
	}

	.bell {
		position: relative;
		width: 24px;
		height: 24px;
		border-radius: 7px;
		color: var(--ink-2);
		font-size: 12px;
	}

	.bell:hover {
		background: rgba(31, 53, 45, 0.07);
	}

	.bell i {
		position: absolute;
		top: 1px;
		right: 0;
		min-width: 11px;
		height: 11px;
		display: grid;
		place-items: center;
		padding: 0 3px;
		border-radius: 6px;
		background: #d0503c;
		color: white;
		font-size: 6px;
		font-style: normal;
		font-weight: 700;
		box-shadow: 0 0 0 1.5px rgba(240, 244, 241, 0.9);
	}

	.bell-menu {
		position: absolute;
		right: -6px;
		top: calc(100% + 6px);
		width: 250px;
		padding: 5px;
		border: 1px solid rgba(255, 255, 255, 0.6);
		border-radius: 11px;
		background: rgba(247, 249, 247, 0.95);
		box-shadow: 0 18px 44px rgba(10, 30, 22, 0.22);
		backdrop-filter: blur(24px);
	}

	.bell-menu header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 5px 6px 7px;
		font-size: 8.5px;
	}

	.bell-menu header button {
		color: var(--accent);
		font-size: 7px;
	}

	.bell-menu > button {
		width: 100%;
		display: grid;
		grid-template-columns: 6px 1fr auto;
		align-items: start;
		gap: 7px;
		padding: 6px;
		border-radius: 7px;
		text-align: left;
	}

	.bell-menu > button:hover {
		background: rgba(31, 53, 45, 0.06);
	}

	.bell-menu > button i {
		width: 5px;
		height: 5px;
		margin-top: 3px;
		border-radius: 50%;
		background: var(--accent);
	}

	.bell-menu strong,
	.bell-menu small {
		display: block;
	}

	.bell-menu strong {
		font-size: 7.6px;
	}

	.bell-menu small {
		margin-top: 2px;
		color: var(--muted);
		font-size: 6.6px;
	}

	.bell-menu time {
		color: var(--faint);
		font-size: 6.2px;
		white-space: nowrap;
	}

	.team {
		display: flex;
	}

	.team .avatar {
		width: 19px;
		height: 19px;
		margin-left: -5px;
	}

	.demo-pill {
		height: 18px;
		display: inline-flex;
		align-items: center;
		padding: 0 7px;
		border: 1px solid rgba(140, 105, 45, 0.2);
		border-radius: 9px;
		background: rgba(255, 244, 216, 0.7);
		color: #6f5a36;
		font-size: 6.5px;
		font-weight: 650;
		white-space: nowrap;
	}

	.page {
		position: relative;
		min-height: 0;
		flex: 1;
		padding: 14px 16px 18px;
	}

	.page.fill {
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}

	.toasts {
		position: absolute;
		right: 16px;
		bottom: 16px;
		z-index: 60;
		display: grid;
		justify-items: end;
		gap: 6px;
		pointer-events: none;
	}

	.toast {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 8px 11px;
		border: 1px solid rgba(255, 255, 255, 0.1);
		border-radius: 9px;
		background: rgba(17, 27, 24, 0.92);
		color: white;
		font-size: 7.8px;
		box-shadow: 0 12px 30px rgba(5, 18, 13, 0.3);
		backdrop-filter: blur(14px);
	}

	.toast :global(svg) {
		color: #7fe3b5;
		font-size: 11px;
	}

	@media (max-width: 900px) {
		.search-pill span,
		.team,
		.demo-pill {
			display: none;
		}

		.search-pill {
			width: auto;
		}
	}
</style>
