<script lang="ts">
	import { geoDistance, geoGraticule, geoMercator, geoPath } from 'd3-geo';
	import { onMount } from 'svelte';
	import { fly } from 'svelte/transition';
	import ArrowLeft from '~icons/lucide/arrow-left';
	import ArrowUpRight from '~icons/lucide/arrow-up-right';
	import Crosshair from '~icons/lucide/crosshair';
	import Flame from '~icons/lucide/flame';
	import Layers from '~icons/lucide/layers';
	import MapPin from '~icons/lucide/map-pin';
	import Maximize from '~icons/lucide/maximize';
	import Minus from '~icons/lucide/minus';
	import Pause from '~icons/lucide/pause';
	import Play from '~icons/lucide/play';
	import Plus from '~icons/lucide/plus';
	import Rotate from '~icons/lucide/rotate-ccw';
	import Search from '~icons/lucide/search';
	import X from '~icons/lucide/x';
	import Zap from '~icons/lucide/zap';
	import { entitiesByTown, entityById, type Entity } from '../directory';
	import { counties, countyMesh, neighbors, newJersey, towns } from '../geo';
	import type { Town } from '../nj-towns';
	import { age, suite } from '../state.svelte';
	import { money } from '../suite-data';
	import Logo from '../ui/Logo.svelte';
	import Ring from '../ui/Ring.svelte';
	import Sparkline from '../ui/Sparkline.svelte';

	let W = $state(640);
	let H = $state(520);
	let svgEl = $state<SVGSVGElement>();

	const pad = 28;
	const projection = $derived(geoMercator().fitExtent([[pad, pad], [W - pad, H - pad]], newJersey));
	const path = $derived(geoPath(projection));
	const statePath = $derived(path(newJersey) ?? '');
	const meshPath = $derived(path(countyMesh) ?? '');
	const graticule = $derived(path(geoGraticule().extent([[-76.2, 38.6], [-73.4, 41.6]]).step([0.2, 0.2])()) ?? '');
	const countyShapes = $derived(counties.map((c) => ({ ...c, d: path(c.feature) ?? '', at: projection(c.centroid) as [number, number], bounds: path.bounds(c.feature) })));
	const neighborShapes = $derived(neighbors.map((n) => ({ name: n.name, d: path(n.feature) ?? '' })));
	const townXY = $derived(new Map(towns.map((t) => [t.id, projection(t.coordinates) as [number, number]])));

	// View transform: screen = t + k * map
	let k = $state(1);
	let tx = $state(0);
	let ty = $state(0);
	let anim = 0;

	let townId = $state<string | null>(null);
	let countyId = $state<string | null>(null);
	let hoverTown = $state<string | null>(null);
	let hoverCounty = $state<string | null>(null);
	let cursor = $state<[number, number] | null>(null);
	let query = $state('');
	let layers = $state({ heat: true, labels: true, companies: true, trails: true, sweep: true });
	let layersOpen = $state(false);

	const town = $derived(townId ? towns.find((t) => t.id === townId) ?? null : null);
	const county = $derived(countyId ? countyShapes.find((c) => c.id === countyId) ?? null : null);
	const countyTowns = $derived(county ? towns.filter((t) => t.county === county.name) : []);
	const townCompanies = $derived(town ? entitiesByTown.get(town.id) ?? [] : []);

	const sx = (x: number) => tx + x * k;
	const sy = (y: number) => ty + y * k;

	const level = $derived(k < 1.8 ? 'State' : k < 5 ? 'County' : k < 14 ? 'Municipal' : 'Street');
	const visibleTowns = $derived(
		towns.filter((t) => {
			const p = townXY.get(t.id)!;
			const x = sx(p[0]);
			const y = sy(p[1]);
			return x > -30 && x < W + 30 && y > -30 && y < H + 30;
		}),
	);

	// Greedy label placement: heaviest towns first, skip any label that would
	// overlap one already placed. Selected and hovered towns always win.
	const labelled = $derived.by(() => {
		const placed: [number, number, number, number][] = [];
		const out = new Set<string>();
		const order = [...visibleTowns].sort((a, b) => Number(b.id === townId) - Number(a.id === townId) || b.weight - a.weight);
		for (const t of order) {
			const forced = t.id === townId || t.id === hoverTown;
			if (!forced && (!layers.labels || k < (t.weight >= 9 ? 1 : t.weight >= 6 ? 1.9 : t.weight >= 4 ? 3.2 : t.weight >= 3 ? 5 : 7.5))) continue;
			const p = townXY.get(t.id)!;
			const x = sx(p[0]) + 6;
			const y = sy(p[1]) - 6;
			const box: [number, number, number, number] = [x, y, x + t.name.length * (t.weight >= 7 ? 4.9 : 4.3) + 4, y + 11];
			if (!forced && placed.some((b) => box[0] < b[2] && box[2] > b[0] && box[1] < b[3] && box[3] > b[1])) continue;
			placed.push(box);
			out.add(t.id);
		}
		return out;
	});

	const companyDots = $derived.by(() => {
		if (!layers.companies || k < 6.5) return [] as { e: Entity; x: number; y: number }[];
		const out: { e: Entity; x: number; y: number }[] = [];
		for (const t of visibleTowns) {
			for (const e of entitiesByTown.get(t.id) ?? []) {
				if (!e.coordinates) continue;
				const p = projection(e.coordinates) as [number, number];
				out.push({ e, x: sx(p[0]), y: sy(p[1]) });
			}
		}
		return out;
	});

	const recent = $derived(suite.events.filter((e) => entityById.get(e.companyId)?.coordinates).slice(0, 7));
	const trailPoints = $derived(
		recent.map((e) => {
			const p = projection(entityById.get(e.companyId)!.coordinates!) as [number, number];
			return { e, x: sx(p[0]), y: sy(p[1]) };
		}),
	);
	const pingActive = $derived(suite.latest && suite.now - suite.latestAt < 7000 ? suite.latest : null);

	const totals = $derived({
		startups: towns.reduce((s, t) => s + t.startups, 0),
		signals: towns.reduce((s, t) => s + t.signals30d, 0),
		raised: towns.reduce((s, t) => s + t.raised, 0),
	});
	const hottest = $derived([...towns].sort((a, b) => b.momentum - a.momentum).slice(0, 7));

	const scaleBar = $derived.by(() => {
		const a = projection.invert!([W / 2, H / 2]);
		const b = projection.invert!([W / 2 + 100 / k, H / 2]);
		const km = (geoDistance(a!, b!) * 6371) / 1;
		const steps = [0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50];
		const nice = steps.find((s) => (s / km) * 100 >= 45) ?? 50;
		return { px: (nice / km) * 100, label: nice < 1 ? `${nice * 1000} m` : `${nice} km` };
	});

	const results = $derived.by(() => {
		const q = query.trim().toLowerCase();
		if (!q) return [];
		const t = towns.filter((x) => x.name.toLowerCase().includes(q)).slice(0, 5).map((x) => ({ kind: 'Town', label: x.name, sub: x.county, go: () => focusTown(x) }));
		const c = countyShapes.filter((x) => x.name.toLowerCase().includes(q)).slice(0, 2).map((x) => ({ kind: 'County', label: x.name, sub: `${towns.filter((tt) => tt.county === x.name).length} towns`, go: () => focusCounty(x.id) }));
		const e = [...entityById.values()].filter((x) => x.townId && x.name.toLowerCase().includes(q)).slice(0, 4).map((x) => ({ kind: 'Company', label: x.name, sub: x.town, go: () => focusCompany(x) }));
		return [...t, ...c, ...e];
	});

	// ————— camera —————
	function constrain() {
		const margin = 0.35;
		tx = Math.min(W * margin, Math.max(W - W * k - W * margin, tx));
		ty = Math.min(H * margin, Math.max(H - H * k - H * margin, ty));
	}

	function zoomAround(px: number, py: number, next: number) {
		cancelAnimationFrame(anim);
		next = Math.max(1, Math.min(90, next));
		const mx = (px - tx) / k;
		const my = (py - ty) / k;
		k = next;
		tx = px - mx * next;
		ty = py - my * next;
		constrain();
	}

	function flyTo(cx: number, cy: number, target: number, duration = 950) {
		cancelAnimationFrame(anim);
		target = Math.max(1, Math.min(90, target));
		const k0 = k;
		const x0 = (W / 2 - tx) / k;
		const y0 = (H / 2 - ty) / k;
		const hop = Math.min(0.55, (Math.hypot(cx - x0, cy - y0) / W) * 1.4);
		const start = performance.now();
		const step = (now: number) => {
			const t = Math.min(1, (now - start) / duration);
			const e = t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2;
			const kk = k0 * (target / k0) ** e * (1 - hop * Math.sin(Math.PI * e));
			k = Math.max(0.6, kk);
			tx = W / 2 - (x0 + (cx - x0) * e) * k;
			ty = H / 2 - (y0 + (cy - y0) * e) * k;
			if (t < 1) anim = requestAnimationFrame(step);
		};
		anim = requestAnimationFrame(step);
	}

	function reset() {
		townId = countyId = null;
		flyTo(W / 2, H / 2, 1, 800);
	}

	function focusCounty(id: string) {
		const c = countyShapes.find((x) => x.id === id);
		if (!c) return;
		countyId = id;
		townId = null;
		const [[x0, y0], [x1, y1]] = c.bounds;
		flyTo((x0 + x1) / 2, (y0 + y1) / 2, 0.8 / Math.max((x1 - x0) / W, (y1 - y0) / H));
	}

	function focusTown(t: Town, zoom = 20) {
		townId = t.id;
		countyId = countyShapes.find((c) => c.name === t.county)?.id ?? null;
		query = '';
		const p = townXY.get(t.id)!;
		flyTo(p[0], p[1], zoom);
	}

	function focusCompany(e: Entity) {
		const t = towns.find((x) => x.id === e.townId);
		if (t) focusTown(t, 30);
		suite.open(e.id);
	}

	// ————— pointer —————
	let drag = $state<{ x: number; y: number; tx: number; ty: number; id: number; moved: boolean } | null>(null);
	let suppressClick = false;

	function local(event: { clientX: number; clientY: number }) {
		const r = svgEl!.getBoundingClientRect();
		return [((event.clientX - r.left) * W) / r.width, ((event.clientY - r.top) * H) / r.height] as [number, number];
	}

	function onpointerdown(event: PointerEvent) {
		if (event.button !== 0) return;
		const [x, y] = local(event);
		drag = { x, y, tx, ty, id: event.pointerId, moved: false };
	}

	function onpointermove(event: PointerEvent) {
		const [x, y] = local(event);
		const ll = projection.invert!([(x - tx) / k, (y - ty) / k]);
		cursor = ll ? [ll[0], ll[1]] : null;
		if (!drag) return;
		if (!drag.moved && Math.hypot(x - drag.x, y - drag.y) > 4) {
			drag.moved = true;
			cancelAnimationFrame(anim);
			svgEl!.setPointerCapture(drag.id);
		}
		if (drag.moved) {
			tx = drag.tx + (x - drag.x);
			ty = drag.ty + (y - drag.y);
			constrain();
		}
	}

	function onpointerup() {
		if (drag?.moved) {
			suppressClick = true;
			setTimeout(() => (suppressClick = false));
		}
		drag = null;
	}

	function guard(fn: () => void) {
		return (event: Event) => {
			event.stopPropagation();
			if (!suppressClick) fn();
		};
	}

	onMount(() => {
		const onwheel = (event: WheelEvent) => {
			event.preventDefault();
			const [x, y] = local(event);
			const factor = Math.exp(-event.deltaY * (event.ctrlKey ? 0.012 : 0.0022));
			zoomAround(x, y, k * factor);
		};
		svgEl!.addEventListener('wheel', onwheel, { passive: false });
		return () => {
			svgEl?.removeEventListener('wheel', onwheel);
			cancelAnimationFrame(anim);
		};
	});

	// Deep links from other screens ("Show on radar").
	$effect(() => {
		const target = suite.radarTarget;
		if (!target || !W) return;
		const t = towns.find((x) => x.id === target);
		suite.radarTarget = null;
		if (t) setTimeout(() => focusTown(t), 120);
	});

	function kindTone(kind: string) {
		return kind === 'Patent' ? 'violet' : kind === 'Funding round' ? 'accent' : kind === 'Hiring spike' ? 'blue' : 'amber';
	}
</script>

<div class="radar">
	<section class="map" bind:clientWidth={W} bind:clientHeight={H}>
		<svg
			bind:this={svgEl}
			viewBox="0 0 {W} {H}"
			role="application"
			aria-label="Interactive New Jersey map. Drag to pan, scroll to zoom."
			class:grabbing={drag?.moved}
			{onpointerdown}
			{onpointermove}
			{onpointerup}
			onpointercancel={onpointerup}
			onpointerleave={() => (cursor = null)}
			ondblclick={(e) => { const [x, y] = local(e); zoomAround(x, y, k * 2.2); }}
		>
			<defs>
				<radialGradient id="rd-heat">
					<stop offset="0" style:stop-color="var(--accent-glow)" stop-opacity=".75" />
					<stop offset=".45" style:stop-color="var(--accent-glow)" stop-opacity=".22" />
					<stop offset="1" style:stop-color="var(--accent-glow)" stop-opacity="0" />
				</radialGradient>
				<radialGradient id="rd-heat-hot">
					<stop offset="0" stop-color="#ffd27a" stop-opacity=".8" />
					<stop offset=".5" stop-color="#f1a54a" stop-opacity=".2" />
					<stop offset="1" stop-color="#f1a54a" stop-opacity="0" />
				</radialGradient>
				<linearGradient id="rd-land" x1="0" y1="0" x2=".4" y2="1">
					<stop offset="0" stop-color="#123b31" />
					<stop offset="1" stop-color="#0a231c" />
				</linearGradient>
				<filter id="rd-glow" x="-20%" y="-20%" width="140%" height="140%">
					<feGaussianBlur stdDeviation="3" result="b" />
					<feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
				</filter>
			</defs>

			<g transform="translate({tx},{ty}) scale({k})">
				<path d={graticule} class="graticule" />
				{#each neighborShapes as n}<path d={n.d} class="neighbor" />{/each}
				<path d={statePath} class="land-glow" />
				<path d={statePath} class="land" />
				{#each countyShapes as c (c.id)}
					<path
						d={c.d}
						class="county"
						class:hover={hoverCounty === c.id}
						class:selected={countyId === c.id}
						role="button"
						tabindex="-1"
						aria-label={c.name}
						onpointerenter={() => (hoverCounty = c.id)}
						onpointerleave={() => (hoverCounty = null)}
						onclick={guard(() => focusCounty(c.id))}
						onkeydown={() => {}}
					/>
				{/each}
				<path d={meshPath} class="mesh" />
				<path d={statePath} class="outline" filter="url(#rd-glow)" />
			</g>

			{#if layers.heat}
				<g class="heat">
					{#each visibleTowns as t (t.id)}
						{@const p = townXY.get(t.id)!}
						<circle cx={sx(p[0])} cy={sy(p[1])} r={(5 + t.signals30d * 0.55) * Math.min(k, 7) ** 0.55} fill={t.momentum > 82 ? 'url(#rd-heat-hot)' : 'url(#rd-heat)'} />
					{/each}
				</g>
			{/if}

			{#if k < 3.2}
				{#each countyShapes as c (c.id)}
					<text x={sx(c.at[0])} y={sy(c.at[1])} class="county-label" class:hot={hoverCounty === c.id || countyId === c.id}>{c.name.replace(' County', '').toUpperCase()}</text>
				{/each}
			{/if}
			{#if k < 2.4}
				<text x={sx(W * 0.08)} y={sy(H * 0.46)} class="region-label">PENNSYLVANIA</text>
				<text x={sx(W * 0.74)} y={sy(H * 0.12)} class="region-label">NEW YORK</text>
				<text x={sx(W * 0.2)} y={sy(H * 0.93)} class="region-label">DELAWARE</text>
				<text x={sx(W * 0.8)} y={sy(H * 0.74)} class="region-label ocean">ATLANTIC OCEAN</text>
			{/if}

			{#if layers.trails && trailPoints.length > 1}
				<g class="trails">
					{#each trailPoints.slice(0, -1) as a, i (a.e.id)}
						{@const b = trailPoints[i + 1]}
						{@const mx = (a.x + b.x) / 2}
						{@const my = (a.y + b.y) / 2 - Math.hypot(b.x - a.x, b.y - a.y) * 0.25}
						<path d="M{a.x},{a.y} Q{mx},{my} {b.x},{b.y}" style:opacity={1 - i * 0.13} />
					{/each}
				</g>
			{/if}

			{#each companyDots as d (d.e.id)}
				<g
					class="company"
					class:real={d.e.real}
					transform="translate({d.x},{d.y})"
					role="button"
					tabindex="-1"
					aria-label={d.e.name}
					onclick={guard(() => suite.open(d.e.id))}
					onkeydown={() => {}}
				>
					<circle r="9" class="hit" />
					{#if d.e.real}
						<rect x="-4" y="-4" width="8" height="8" rx="1.5" transform="rotate(45)" class="real-mark" />
					{:else}
						<circle r={k > 14 ? 5.2 : 3.4} fill="hsl({d.e.hue} 70% 62%)" class="dot" />
						{#if k > 14}<text y="2.2" class="initial">{d.e.name.charAt(0)}</text>{/if}
					{/if}
					{#if k > 17}<text x="9" y="2.5" class="company-label">{d.e.name}</text>{/if}
				</g>
			{/each}

			<g class="towns">
				{#each visibleTowns as t (t.id)}
					{@const p = townXY.get(t.id)!}
					{@const x = sx(p[0])}
					{@const y = sy(p[1])}
					{@const r = 1.4 + t.weight * 0.32}
					<g
						class="town"
						class:selected={townId === t.id}
						class:major={t.weight >= 7}
						transform="translate({x},{y})"
						role="button"
						tabindex="0"
						aria-label="{t.name}, {t.county}"
						onpointerenter={() => (hoverTown = t.id)}
						onpointerleave={() => (hoverTown = null)}
						onclick={guard(() => focusTown(t))}
						onkeydown={(e) => e.key === 'Enter' && focusTown(t)}
					>
						<circle r={r + 7} class="hit" />
						{#if townId === t.id}
							<circle r="16" class="lock" /><circle r="26" class="lock outer" />
							<path d="M-34 0h-10M34 0h10M0-34v-10M0 34v10" class="reticle" />
						{/if}
						{#if t.weight >= 7}<circle r={r + 3.2} class="halo" />{/if}
						<circle {r} class="node" />
						{#if labelled.has(t.id)}
							<text x={r + 5} y="2.6" class="town-label">{t.name}</text>
						{/if}
					</g>
				{/each}
			</g>


			{#if pingActive}
				{@const e = entityById.get(pingActive.companyId)}
				{#if e?.coordinates}
					{@const p = projection(e.coordinates) as [number, number]}
					<g transform="translate({sx(p[0])},{sy(p[1])})" class="ping">
						<circle r="6" /><circle r="6" class="late" />
					</g>
				{/if}
			{/if}
		</svg>

		{#if layers.sweep}<div class="sweep" aria-hidden="true"></div>{/if}
		<div class="scanlines" aria-hidden="true"></div>
		<div class="frame-corners" aria-hidden="true"><i></i><i></i><i></i><i></i></div>

		<!-- HUD: title -->
		<div class="hud top-left">
			<div class="hud-title"><i class="live-dot" class:paused={!suite.playing}></i><strong>NJ SIGNAL RADAR</strong><span>v4.2</span></div>
			<div class="hud-stats">
				<span><b class="num">{towns.length}</b>municipalities</span>
				<span><b class="num">{totals.startups.toLocaleString()}</b>startups indexed</span>
				<span><b class="num">{totals.signals.toLocaleString()}</b>signals · 30d</span>
			</div>
			{#if county || town}
				<div class="crumb" transition:fly={{ y: -4, duration: 150 }}>
					<button onclick={reset}>New Jersey</button>
					{#if county}<span>›</span><button onclick={() => focusCounty(county.id)}>{county.name}</button>{/if}
					{#if town}<span>›</span><strong>{town.name}</strong>{/if}
				</div>
			{/if}
		</div>

		<!-- HUD: search + layers -->
		<div class="hud top-right">
			<label class="map-search">
				<Search />
				<input bind:value={query} placeholder="Fly to a town, county or company" aria-label="Search the map" />
				{#if query}<button onclick={() => (query = '')} aria-label="Clear"><X /></button>{/if}
			</label>
			{#if results.length}
				<div class="results" transition:fly={{ y: -4, duration: 140 }}>
					{#each results as r}
						<button onclick={r.go}><em>{r.kind}</em><span>{r.label}</span><small>{r.sub}</small></button>
					{/each}
				</div>
			{/if}
			<div class="layer-wrap">
				<button class="hud-btn" class:on={layersOpen} onclick={() => (layersOpen = !layersOpen)} aria-label="Map layers"><Layers /></button>
				{#if layersOpen}
					<div class="layers" transition:fly={{ y: -4, duration: 140 }}>
						{#each [['heat', 'Signal heat'], ['labels', 'Town labels'], ['companies', 'Company nodes'], ['trails', 'Signal trails'], ['sweep', 'Radar sweep']] as [key, label]}
							<label><input type="checkbox" bind:checked={layers[key as keyof typeof layers]} /><span>{label}</span></label>
						{/each}
					</div>
				{/if}
			</div>
		</div>

		<!-- HUD: tooltip for hovered town -->
		{#if hoverTown && hoverTown !== townId}
			{@const t = towns.find((x) => x.id === hoverTown)!}
			{@const p = townXY.get(t.id)!}
			<div class="tooltip" style:left="{Math.min(W - 150, sx(p[0]) + 12)}px" style:top="{Math.max(8, sy(p[1]) - 58)}px">
				<strong>{t.name}</strong><small>{t.county}</small>
				<div><span><b>{t.startups}</b>startups</span><span><b>{t.signals30d}</b>signals</span><span><b>{money(t.raised)}</b>raised</span></div>
			</div>
		{/if}

		<!-- HUD: readouts -->
		<div class="hud bottom-left">
			<div class="readout">
				<span>LAT <b class="num">{cursor ? cursor[1].toFixed(4) : '—'}°</b></span>
				<span>LON <b class="num">{cursor ? cursor[0].toFixed(4) : '—'}°</b></span>
				<span>ZOOM <b class="num">{k.toFixed(1)}×</b></span>
				<span>LEVEL <b>{level.toUpperCase()}</b></span>
			</div>
			<div class="scalebar"><i style:width="{scaleBar.px}px"></i><span>{scaleBar.label}</span></div>
			<div class="legend">
				<span><i class="lg-node"></i>Municipality</span>
				<span><i class="lg-heat"></i>Signal density</span>
				<span><i class="lg-real"></i>Real company</span>
				<span><i class="lg-synth"></i>Synthetic company</span>
			</div>
		</div>

		<!-- HUD: zoom controls + minimap -->
		<div class="hud bottom-right">
			<div class="zoom-controls">
				<button class="hud-btn" onclick={() => zoomAround(W / 2, H / 2, k * 1.8)} aria-label="Zoom in"><Plus /></button>
				<button class="hud-btn" onclick={() => zoomAround(W / 2, H / 2, k / 1.8)} aria-label="Zoom out"><Minus /></button>
				<button class="hud-btn" onclick={reset} aria-label="Reset view"><Maximize /></button>
				<button class="hud-btn" onclick={() => { const t = towns.find((x) => x.name === 'Princeton'); if (t) focusTown(t); }} aria-label="Center on Princeton"><Crosshair /></button>
			</div>
			<button class="minimap" aria-label="Minimap" onclick={(e) => {
				const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
				const mx = ((e.clientX - r.left) / r.width) * W;
				const my = ((e.clientY - r.top) / r.height) * H;
				flyTo(mx, my, Math.max(k, 3), 700);
			}}>
				<svg viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet">
					<path d={statePath} class="mini-land" />
					<rect x={-tx / k} y={-ty / k} width={W / k} height={H / k} class="mini-view" />
				</svg>
			</button>
		</div>

		{#if pingActive && entityById.get(pingActive.companyId)}
			{@const e = entityById.get(pingActive.companyId)!}
			<button class="arrival" onclick={() => focusCompany(e)} transition:fly={{ y: 10, duration: 220 }}>
				<span class="arrival-icon"><Zap /></span>
				<span><small>INCOMING · {pingActive.kind.toUpperCase()}</small><strong>{pingActive.title}</strong><em>{e.name} · {e.town} · simulated</em></span>
				<ArrowUpRight />
			</button>
		{/if}
	</section>

	<aside class="panel card scroll">
		{#if town}
			<div class="panel-head">
				<button class="back" onclick={() => (county ? focusCounty(county.id) : reset())}><ArrowLeft /> {county?.name ?? 'New Jersey'}</button>
				<span class="eyebrow">Municipality</span>
				<h2>{town.name}</h2>
				<p class="coords num"><MapPin /> {town.coordinates[1].toFixed(4)}° N · {Math.abs(town.coordinates[0]).toFixed(4)}° W</p>
			</div>
			<div class="metrics">
				<div class="kpi"><small>Startups</small><strong>{town.startups}</strong></div>
				<div class="kpi"><small>Signals · 30d</small><strong>{town.signals30d}</strong></div>
				<div class="kpi"><small>Capital raised</small><strong>{money(town.raised)}</strong></div>
				<div class="kpi"><small>Startup jobs</small><strong>{town.jobs.toLocaleString()}</strong></div>
			</div>
			<div class="trend">
				<div><span class="eyebrow">Signal momentum</span><strong>{town.momentum}<small>/100</small></strong></div>
				<Sparkline values={town.trend} width={120} height={30} />
			</div>
			<div class="section-label">Sector mix</div>
			<div class="mix">
				{#each town.sectorMix as [sector, n]}
					<div><span>{sector}</span><div class="bar"><i style:width="{(n / town.companies.length) * 100}%"></i></div><b>{n}</b></div>
				{/each}
			</div>
			<div class="section-label">Companies in {town.name} · {townCompanies.length}</div>
			<div class="company-list">
				{#each townCompanies as e (e.id)}
					{@const fit = suite.fit(e.id)}
					<button class="company-row" onclick={() => suite.open(e.id)}>
						<Logo name={e.name} hue={e.hue} src={e.logo} seed={e.id} size={24} />
						<span><strong>{e.name}</strong><small>{e.real ? 'Real company · official source' : `${e.sector} · ${e.stage}`}</small></span>
						{#if fit !== null}<Ring value={fit} size={22} stroke={2.4} />{:else}<em class="pill">Real</em>{/if}
					</button>
				{/each}
			</div>
		{:else if county}
			<div class="panel-head">
				<button class="back" onclick={reset}><ArrowLeft /> New Jersey</button>
				<span class="eyebrow">County</span>
				<h2>{county.name}</h2>
				<p class="coords">{countyTowns.length} municipalities tracked</p>
			</div>
			<div class="metrics">
				<div class="kpi"><small>Startups</small><strong>{countyTowns.reduce((s, t) => s + t.startups, 0)}</strong></div>
				<div class="kpi"><small>Signals · 30d</small><strong>{countyTowns.reduce((s, t) => s + t.signals30d, 0)}</strong></div>
				<div class="kpi"><small>Capital raised</small><strong>{money(countyTowns.reduce((s, t) => s + t.raised, 0))}</strong></div>
				<div class="kpi"><small>Avg momentum</small><strong>{Math.round(countyTowns.reduce((s, t) => s + t.momentum, 0) / Math.max(1, countyTowns.length))}</strong></div>
			</div>
			<div class="section-label">Towns by activity</div>
			<div class="town-list">
				{#each [...countyTowns].sort((a, b) => b.signals30d - a.signals30d) as t (t.id)}
					<button onclick={() => focusTown(t)}>
						<span><strong>{t.name}</strong><small>{t.startups} startups · {money(t.raised)}</small></span>
						<Sparkline values={t.trend} width={46} height={16} dot={false} />
						<b class="num">{t.signals30d}</b>
					</button>
				{/each}
			</div>
		{:else}
			<div class="panel-head">
				<span class="eyebrow">Statewide</span>
				<h2>New Jersey</h2>
				<p class="coords">21 counties · {towns.length} municipalities</p>
			</div>
			<div class="metrics">
				<div class="kpi"><small>Startups</small><strong>{totals.startups.toLocaleString()}</strong></div>
				<div class="kpi"><small>Signals · 30d</small><strong>{totals.signals.toLocaleString()}</strong></div>
				<div class="kpi"><small>Capital raised</small><strong>{money(totals.raised)}</strong></div>
				<div class="kpi"><small>Counties</small><strong>21</strong></div>
			</div>
			<div class="section-label"><Flame /> Hottest towns</div>
			<div class="town-list">
				{#each hottest as t, i (t.id)}
					<button onclick={() => focusTown(t)}>
						<em>{i + 1}</em>
						<span><strong>{t.name}</strong><small>{t.county}</small></span>
						<Sparkline values={t.trend} width={46} height={16} dot={false} />
						<b class="num">{t.momentum}</b>
					</button>
				{/each}
			</div>
		{/if}

		<div class="section-label stream-label">
			<span>Live stream</span>
			<span class="stream-controls">
				<button onclick={() => (suite.playing = !suite.playing)} aria-label={suite.playing ? 'Pause' : 'Resume'}>{#if suite.playing}<Pause />{:else}<Play />{/if}</button>
				<button onclick={() => suite.resetSignals()} aria-label="Reset stream"><Rotate /></button>
				<button onclick={() => suite.addSignal()} aria-label="Add a signal"><Plus /></button>
			</span>
		</div>
		<div class="stream">
			{#each suite.events.slice(0, 8) as ev (ev.id)}
				{@const e = entityById.get(ev.companyId)}
				{#if e}
					<button class="event" onclick={() => focusCompany(e)} in:fly={{ y: -6, duration: 220 }}>
						<i class="pill {kindTone(ev.kind)}">{ev.kind}</i>
						<span><strong>{e.name}</strong><small>{ev.title} · {e.town}</small></span>
						<time>{age(ev.timestamp, suite.now)}</time>
					</button>
				{/if}
			{/each}
		</div>
	</aside>
</div>

<style>
	.radar {
		flex: 1;
		min-height: 0;
		display: grid;
		grid-template-columns: minmax(0, 1fr) 238px;
		gap: 10px;
	}

	/* ————— map canvas ————— */
	.map {
		--mint: color-mix(in oklab, var(--accent-glow) 60%, #b9ffe4);
		position: relative;
		min-width: 0;
		min-height: 0;
		overflow: hidden;
		border: 1px solid rgba(120, 240, 190, 0.18);
		border-radius: 12px;
		background:
			radial-gradient(circle at 55% 38%, color-mix(in srgb, var(--accent) 34%, transparent), transparent 55%),
			radial-gradient(circle at 20% 100%, rgba(214, 169, 87, 0.12), transparent 40%),
			#051310;
		box-shadow: 0 18px 40px rgba(4, 18, 13, 0.35), inset 0 0 60px rgba(0, 0, 0, 0.45);
		color: #d8f5e8;
	}

	.map > svg {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		cursor: grab;
		touch-action: none;
		user-select: none;
	}

	.map > svg.grabbing {
		cursor: grabbing;
	}

	.graticule {
		fill: none;
		stroke: rgba(140, 240, 200, 0.07);
		stroke-width: 0.6;
		vector-effect: non-scaling-stroke;
	}

	.neighbor {
		fill: rgba(255, 255, 255, 0.022);
		stroke: rgba(160, 230, 200, 0.13);
		stroke-width: 0.8;
		vector-effect: non-scaling-stroke;
	}

	.land-glow {
		fill: none;
		stroke: var(--mint);
		stroke-width: 14;
		opacity: 0.07;
		vector-effect: non-scaling-stroke;
	}

	.land {
		fill: url(#rd-land);
	}

	.county {
		fill: transparent;
		cursor: pointer;
		transition: fill 0.2s ease;
	}

	.county.hover {
		fill: rgba(140, 240, 200, 0.07);
	}

	.county.selected {
		fill: color-mix(in srgb, var(--accent-glow) 16%, transparent);
	}

	.mesh {
		fill: none;
		stroke: rgba(140, 240, 200, 0.26);
		stroke-width: 0.7;
		stroke-dasharray: 3 2;
		vector-effect: non-scaling-stroke;
		pointer-events: none;
	}

	.outline {
		fill: none;
		stroke: var(--mint);
		stroke-width: 1.3;
		vector-effect: non-scaling-stroke;
		pointer-events: none;
	}

	.heat {
		mix-blend-mode: screen;
		opacity: 0.72;
		pointer-events: none;
	}

	.county-label {
		fill: rgba(190, 240, 215, 0.34);
		font-size: 6.2px;
		font-weight: 700;
		letter-spacing: 0.16em;
		text-anchor: middle;
		pointer-events: none;
		transition: fill 0.2s ease;
	}

	.county-label.hot {
		fill: rgba(220, 255, 238, 0.9);
	}

	.region-label {
		fill: rgba(190, 240, 215, 0.2);
		font-size: 7px;
		font-weight: 600;
		letter-spacing: 0.3em;
		pointer-events: none;
	}

	.region-label.ocean {
		fill: rgba(140, 200, 230, 0.26);
		font-style: italic;
	}

	.trails path {
		fill: none;
		stroke: #ffd27a;
		stroke-width: 1;
		stroke-dasharray: 3 4;
		animation: dash 1.2s linear infinite;
		pointer-events: none;
	}

	@keyframes dash {
		to {
			stroke-dashoffset: -14;
		}
	}

	.town {
		cursor: pointer;
	}

	.town .hit {
		fill: transparent;
	}

	.town .node {
		fill: #c9fbe6;
		stroke: #051310;
		stroke-width: 0.8;
		filter: drop-shadow(0 0 3px var(--mint));
		transition: r 0.2s ease;
	}

	.town:hover .node {
		fill: white;
	}

	.town .halo {
		fill: none;
		stroke: var(--mint);
		stroke-width: 0.8;
		opacity: 0.45;
	}

	.town.selected .node {
		fill: #ffd27a;
		filter: drop-shadow(0 0 5px #ffb347);
	}

	.lock {
		fill: none;
		stroke: #ffd27a;
		stroke-width: 1;
		stroke-dasharray: 4 3;
		animation: spin 6s linear infinite;
	}

	.lock.outer {
		stroke-opacity: 0.35;
		stroke-dasharray: 2 5;
		animation-direction: reverse;
	}

	.reticle {
		stroke: #ffd27a;
		stroke-width: 1;
		opacity: 0.8;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.town-label {
		fill: #e6fff4;
		font-size: 7.5px;
		font-weight: 600;
		letter-spacing: 0.02em;
		paint-order: stroke;
		stroke: rgba(3, 15, 11, 0.85);
		stroke-width: 2.6px;
		stroke-linejoin: round;
		pointer-events: none;
	}

	.town.major .town-label {
		font-size: 8.5px;
		font-weight: 700;
	}

	.town.selected .town-label {
		fill: #ffe3a6;
	}

	.company {
		cursor: pointer;
	}

	.company .hit {
		fill: transparent;
	}

	.company .dot {
		stroke: rgba(255, 255, 255, 0.85);
		stroke-width: 1;
		filter: drop-shadow(0 0 4px rgba(255, 255, 255, 0.35));
	}

	.company:hover .dot {
		stroke-width: 2;
	}

	.real-mark {
		fill: white;
		stroke: var(--mint);
		stroke-width: 1.5;
		filter: drop-shadow(0 0 5px var(--mint));
	}

	.initial {
		fill: white;
		font-size: 5.8px;
		font-weight: 800;
		text-anchor: middle;
		pointer-events: none;
	}

	.company-label {
		fill: rgba(235, 255, 246, 0.85);
		font-size: 6.3px;
		paint-order: stroke;
		stroke: rgba(3, 15, 11, 0.85);
		stroke-width: 2.2px;
		pointer-events: none;
	}

	.ping circle {
		fill: none;
		stroke: #ffd27a;
		stroke-width: 1.5;
		animation: ping 1.6s ease-out infinite;
	}

	.ping .late {
		animation-delay: 0.8s;
	}

	@keyframes ping {
		from {
			r: 4;
			opacity: 1;
		}
		to {
			r: 34;
			opacity: 0;
		}
	}

	.sweep {
		position: absolute;
		left: 50%;
		top: 50%;
		width: 160%;
		aspect-ratio: 1;
		translate: -50% -50%;
		border-radius: 50%;
		background: conic-gradient(from 0deg, transparent 0deg, color-mix(in srgb, var(--accent-glow) 16%, transparent) 40deg, transparent 42deg);
		mix-blend-mode: screen;
		animation: sweep 7s linear infinite;
		pointer-events: none;
	}

	@keyframes sweep {
		to {
			rotate: 360deg;
		}
	}

	.scanlines {
		position: absolute;
		inset: 0;
		background: repeating-linear-gradient(0deg, rgba(255, 255, 255, 0.018) 0 1px, transparent 1px 3px);
		pointer-events: none;
	}

	.frame-corners i {
		position: absolute;
		width: 14px;
		height: 14px;
		border-color: rgba(160, 250, 210, 0.5);
		border-style: solid;
		pointer-events: none;
	}

	.frame-corners i:nth-child(1) {
		left: 8px;
		top: 8px;
		border-width: 1px 0 0 1px;
	}

	.frame-corners i:nth-child(2) {
		right: 8px;
		top: 8px;
		border-width: 1px 1px 0 0;
	}

	.frame-corners i:nth-child(3) {
		left: 8px;
		bottom: 8px;
		border-width: 0 0 1px 1px;
	}

	.frame-corners i:nth-child(4) {
		right: 8px;
		bottom: 8px;
		border-width: 0 1px 1px 0;
	}

	/* ————— HUD ————— */
	.hud {
		position: absolute;
		z-index: 2;
	}

	.top-left {
		left: 16px;
		top: 14px;
	}

	.hud-title {
		display: flex;
		align-items: center;
		gap: 7px;
		font-size: 9px;
		letter-spacing: 0.16em;
	}

	.hud-title span {
		padding: 1px 4px;
		border: 1px solid rgba(160, 250, 210, 0.3);
		border-radius: 3px;
		color: rgba(200, 250, 225, 0.6);
		font-size: 5.8px;
		letter-spacing: 0.08em;
	}

	.hud-stats {
		display: flex;
		gap: 9px;
		margin-top: 6px;
		color: rgba(200, 240, 222, 0.55);
		font-size: 6.5px;
	}

	.hud-stats b {
		margin-right: 3px;
		color: #eafff5;
		font-size: 9px;
	}

	.crumb {
		display: flex;
		align-items: center;
		gap: 5px;
		margin-top: 8px;
		padding: 4px 8px;
		width: max-content;
		border: 1px solid rgba(160, 250, 210, 0.2);
		border-radius: 6px;
		background: rgba(5, 20, 15, 0.7);
		font-size: 7px;
		backdrop-filter: blur(8px);
	}

	.crumb button {
		color: rgba(200, 250, 225, 0.7);
	}

	.crumb button:hover {
		color: white;
		text-decoration: underline;
	}

	.crumb span {
		opacity: 0.4;
	}

	.top-right {
		right: 14px;
		top: 12px;
		display: grid;
		grid-template-columns: 158px auto;
		gap: 6px;
		align-items: start;
	}

	.map-search {
		height: 26px;
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 0 8px;
		border: 1px solid rgba(160, 250, 210, 0.22);
		border-radius: 7px;
		background: rgba(5, 20, 15, 0.72);
		color: rgba(200, 250, 225, 0.6);
		font-size: 11px;
		backdrop-filter: blur(10px);
	}

	.map-search input {
		min-width: 0;
		flex: 1;
		border: 0;
		outline: 0;
		background: transparent;
		color: white;
		font-size: 7.8px;
	}

	.map-search input::placeholder {
		color: rgba(200, 240, 222, 0.45);
	}

	.map-search button {
		color: inherit;
		font-size: 10px;
	}

	.results {
		grid-column: 1;
		overflow: hidden;
		border: 1px solid rgba(160, 250, 210, 0.2);
		border-radius: 8px;
		background: rgba(6, 22, 17, 0.94);
		backdrop-filter: blur(12px);
	}

	.results button {
		width: 100%;
		display: grid;
		grid-template-columns: 38px 1fr;
		gap: 0 6px;
		padding: 6px 8px;
		text-align: left;
		color: #eafff5;
	}

	.results button:hover {
		background: rgba(160, 250, 210, 0.08);
	}

	.results em {
		grid-row: span 2;
		align-self: center;
		color: #ffd27a;
		font-size: 5.8px;
		font-style: normal;
		font-weight: 700;
		letter-spacing: 0.08em;
		text-transform: uppercase;
	}

	.results span {
		font-size: 7.8px;
	}

	.results small {
		color: rgba(200, 240, 222, 0.5);
		font-size: 6.3px;
	}

	.layer-wrap {
		position: relative;
		grid-column: 2;
		grid-row: 1;
	}

	.hud-btn {
		width: 26px;
		height: 26px;
		display: grid;
		place-items: center;
		border: 1px solid rgba(160, 250, 210, 0.22);
		border-radius: 7px;
		background: rgba(5, 20, 15, 0.72);
		color: #c9fbe6;
		font-size: 11px;
		backdrop-filter: blur(10px);
		transition: background 0.15s ease;
	}

	.hud-btn:hover,
	.hud-btn.on {
		background: rgba(40, 90, 70, 0.8);
	}

	.layers {
		position: absolute;
		right: 0;
		top: 30px;
		width: 128px;
		padding: 6px;
		border: 1px solid rgba(160, 250, 210, 0.2);
		border-radius: 8px;
		background: rgba(6, 22, 17, 0.94);
	}

	.layers label {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 4px 3px;
		color: #d8f5e8;
		font-size: 7.5px;
		cursor: pointer;
	}

	.layers input {
		accent-color: #4fc08f;
	}

	.tooltip {
		position: absolute;
		z-index: 3;
		width: 140px;
		padding: 7px 8px;
		border: 1px solid rgba(160, 250, 210, 0.25);
		border-radius: 8px;
		background: rgba(6, 22, 17, 0.92);
		pointer-events: none;
		backdrop-filter: blur(10px);
	}

	.tooltip strong,
	.tooltip small {
		display: block;
	}

	.tooltip strong {
		font-size: 9px;
	}

	.tooltip small {
		margin-top: 1px;
		color: rgba(200, 240, 222, 0.5);
		font-size: 6.4px;
	}

	.tooltip div {
		display: flex;
		justify-content: space-between;
		margin-top: 6px;
		color: rgba(200, 240, 222, 0.55);
		font-size: 5.8px;
	}

	.tooltip b {
		display: block;
		color: #ffd27a;
		font-size: 8.5px;
	}

	.bottom-left {
		left: 16px;
		bottom: 14px;
		display: grid;
		gap: 6px;
		pointer-events: none;
	}

	.readout {
		display: flex;
		gap: 10px;
		color: rgba(200, 240, 222, 0.45);
		font-family: ui-monospace, 'SF Mono', Menlo, monospace;
		font-size: 6.3px;
		letter-spacing: 0.06em;
	}

	.readout b {
		color: #c9fbe6;
		font-weight: 600;
	}

	.scalebar {
		display: flex;
		align-items: center;
		gap: 6px;
		color: rgba(200, 240, 222, 0.6);
		font-family: ui-monospace, 'SF Mono', Menlo, monospace;
		font-size: 6.3px;
	}

	.scalebar i {
		height: 5px;
		border: 1px solid rgba(200, 250, 225, 0.6);
		border-top: 0;
	}

	.legend {
		display: flex;
		gap: 10px;
		color: rgba(200, 240, 222, 0.55);
		font-size: 6.3px;
	}

	.legend span {
		display: flex;
		align-items: center;
		gap: 4px;
	}

	.legend i {
		width: 6px;
		height: 6px;
		border-radius: 50%;
	}

	.lg-node {
		background: #c9fbe6;
		box-shadow: 0 0 4px var(--mint);
	}

	.lg-heat {
		background: radial-gradient(#ffd27a, transparent 70%);
	}

	.lg-real {
		border-radius: 1px !important;
		background: white;
		rotate: 45deg;
		scale: 0.8;
	}

	.lg-synth {
		background: hsl(200 70% 62%);
	}

	.bottom-right {
		right: 14px;
		bottom: 14px;
		display: flex;
		align-items: flex-end;
		gap: 8px;
	}

	.zoom-controls {
		display: grid;
		gap: 4px;
	}

	.minimap {
		width: 78px;
		height: 96px;
		padding: 5px;
		border: 1px solid rgba(160, 250, 210, 0.22);
		border-radius: 8px;
		background: rgba(5, 20, 15, 0.72);
		backdrop-filter: blur(10px);
	}

	.minimap svg {
		width: 100%;
		height: 100%;
		overflow: hidden;
	}

	.mini-land {
		fill: rgba(140, 240, 200, 0.18);
		stroke: var(--mint);
		stroke-width: 3;
	}

	.mini-view {
		fill: rgba(255, 210, 122, 0.12);
		stroke: #ffd27a;
		stroke-width: 6;
	}

	.arrival {
		position: absolute;
		z-index: 3;
		left: 50%;
		bottom: 64px;
		width: 250px;
		translate: -50% 0;
		display: grid;
		grid-template-columns: 26px 1fr 12px;
		align-items: center;
		gap: 8px;
		padding: 8px 10px;
		border: 1px solid rgba(255, 210, 122, 0.35);
		border-radius: 10px;
		background: rgba(10, 26, 20, 0.9);
		color: white;
		text-align: left;
		box-shadow: 0 0 30px rgba(255, 190, 90, 0.18), 0 14px 30px rgba(0, 0, 0, 0.35);
		backdrop-filter: blur(12px);
	}

	.arrival-icon {
		width: 26px;
		height: 26px;
		display: grid;
		place-items: center;
		border-radius: 7px;
		background: rgba(255, 210, 122, 0.16);
		color: #ffd27a;
		font-size: 12px;
	}

	.arrival small,
	.arrival strong,
	.arrival em {
		display: block;
	}

	.arrival small {
		color: #ffd27a;
		font-size: 5.8px;
		font-weight: 700;
		letter-spacing: 0.1em;
	}

	.arrival strong {
		margin: 2px 0;
		font-size: 8.3px;
	}

	.arrival em {
		color: rgba(200, 240, 222, 0.6);
		font-size: 6.5px;
		font-style: normal;
	}

	.arrival > :global(svg) {
		color: rgba(255, 255, 255, 0.5);
		font-size: 11px;
	}

	/* ————— side panel ————— */
	.panel {
		min-height: 0;
		padding: 12px;
		background: var(--glass-strong);
	}

	.panel-head h2 {
		margin-top: 3px;
		font-size: 17px;
		letter-spacing: -0.04em;
	}

	.back {
		display: flex;
		align-items: center;
		gap: 3px;
		margin-bottom: 8px;
		color: var(--accent);
		font-size: 7px;
		font-weight: 600;
	}

	.coords {
		display: flex;
		align-items: center;
		gap: 3px;
		margin-top: 3px;
		color: var(--faint);
		font-size: 6.6px;
	}

	.metrics {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 6px;
		margin-top: 10px;
	}

	.metrics .kpi {
		padding: 8px;
		border: 1px solid var(--line);
		border-radius: 8px;
		background: rgba(255, 255, 255, 0.5);
	}

	.metrics .kpi strong {
		font-size: 14px;
	}

	.trend {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-top: 8px;
		padding: 8px;
		border-radius: 8px;
		background: var(--accent-soft);
	}

	.trend strong {
		display: block;
		margin-top: 2px;
		color: var(--accent-deep);
		font-size: 16px;
	}

	.trend strong small {
		color: var(--faint);
		font-size: 7px;
	}

	.section-label {
		display: flex;
		align-items: center;
		gap: 4px;
	}

	.mix {
		display: grid;
		gap: 5px;
	}

	.mix > div {
		display: grid;
		grid-template-columns: 70px 1fr 12px;
		align-items: center;
		gap: 6px;
		font-size: 6.8px;
	}

	.mix b {
		text-align: right;
	}

	.company-list,
	.town-list,
	.stream {
		display: grid;
		gap: 2px;
	}

	.company-row,
	.town-list button,
	.event {
		width: 100%;
		display: grid;
		align-items: center;
		gap: 7px;
		padding: 5px 6px;
		border-radius: 7px;
		text-align: left;
		transition: background 0.15s ease;
	}

	.company-row {
		grid-template-columns: 24px minmax(0, 1fr) auto;
	}

	.town-list button {
		grid-template-columns: auto minmax(0, 1fr) 46px 18px;
	}

	.event {
		grid-template-columns: 52px minmax(0, 1fr) auto;
	}

	.company-row:hover,
	.town-list button:hover,
	.event:hover {
		background: rgba(255, 255, 255, 0.65);
	}

	.company-row strong,
	.company-row small,
	.town-list strong,
	.town-list small,
	.event strong,
	.event small {
		display: block;
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
	}

	.company-row strong,
	.town-list strong,
	.event strong {
		font-size: 7.8px;
	}

	.company-row small,
	.town-list small,
	.event small {
		margin-top: 1px;
		color: var(--faint);
		font-size: 6.4px;
	}

	.town-list em {
		width: 12px;
		color: var(--faint);
		font-size: 6.5px;
		font-style: normal;
	}

	.town-list b {
		color: var(--accent-deep);
		font-size: 7.5px;
		text-align: right;
	}

	.event .pill {
		justify-content: center;
		font-size: 5.4px;
		font-style: normal;
		overflow: hidden;
	}

	.event time {
		color: var(--faint);
		font-size: 6px;
		white-space: nowrap;
	}

	.stream-label {
		justify-content: space-between;
	}

	.stream-controls {
		display: flex;
		gap: 2px;
	}

	.stream-controls button {
		width: 18px;
		height: 18px;
		display: grid;
		place-items: center;
		border-radius: 5px;
		color: var(--ink-2);
		font-size: 9px;
	}

	.stream-controls button:hover {
		background: rgba(31, 53, 45, 0.08);
	}

	@container (max-width: 760px) {
		.radar {
			grid-template-columns: 1fr;
		}
	}
</style>
