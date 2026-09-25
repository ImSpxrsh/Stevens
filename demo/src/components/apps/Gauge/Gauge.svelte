<script lang="ts">
	import SearchIcon from '~icons/mdi/magnify';
	import MapIcon from '~icons/mdi/map-marker-radius-outline';
	import DatabaseIcon from '~icons/mdi/database-outline';
	import ChartIcon from '~icons/mdi/chart-box-outline';
	import ArchiveIcon from '~icons/mdi/archive-outline';
	import ShieldIcon from '~icons/mdi/shield-check-outline';
	import CloseIcon from '~icons/mdi/close';
	import ArrowIcon from '~icons/mdi/arrow-right';
	import CheckIcon from '~icons/mdi/check-circle-outline';
	import InfoIcon from '~icons/mdi/information-outline';
	import atlas from 'us-atlas/counties-10m.json';
	import { feature, mesh } from 'topojson-client';
	import { geoMercator, geoPath } from 'd3-geo';
	import { companies, type Company } from './gauge-data';

	const topology = atlas as any;
	const stateGeometry = topology.objects.states.geometries.find((item: any) => String(item.id).padStart(2, '0') === '34');
	const countyGeometries = topology.objects.counties.geometries.filter((item: any) => String(item.id).padStart(5, '0').startsWith('34'));
	const countyObject = { type: 'GeometryCollection', geometries: countyGeometries } as any;
	const newJersey = feature(topology, stateGeometry as any) as any;
	const countyLines = mesh(topology, countyObject, (a: any, b: any) => a !== b) as any;
	const projection = geoMercator().fitExtent([[74, 18], [344, 595]], newJersey);
	const mapPath = geoPath(projection);
	const statePath = mapPath(newJersey) ?? '';
	const countyPath = mapPath(countyLines) ?? '';

	let view = $state<'signals' | 'programs' | 'proof'>('signals');
	let showAll = $state(false);
	let query = $state('');
	let selectedCompany = $state<Company | null>(null);
	let searchResult = $state<{ town: string; company: Company | null } | null>(null);

	const visibleCompanies = $derived(showAll ? companies : companies.filter((company) => company.funded));

	function projectCompany(company: Company): [number, number] {
		return (projection(company.coordinates) ?? [0, 0]) as [number, number];
	}

	function runSearch() {
		const town = query.trim();
		if (!town) return;
		const company = companies.find((item) => item.town.toLowerCase() === town.toLowerCase()) ?? null;
		searchResult = { town, company };
		if (company) {
			showAll = true;
			selectedCompany = company;
		}
	}

	function matchTone(state: string) {
		if (state === 'Strong match') return 'strong';
		if (state === 'Potential match, verify') return 'potential';
		return 'no-match';
	}
</script>

<section class="gauge-app">
	<div class="drag-strip app-window-drag-handle" aria-hidden="true"></div>
	<aside class="sidebar">
		<div class="brand">
			<div class="brand-mark"><span></span><span></span><i></i><i></i><i></i></div>
			<div><strong>Gauge</strong><small>1435 Capital · Demo</small></div>
		</div>

		<nav>
			<button class:active={view === 'signals'} onclick={() => (view = 'signals')}><MapIcon /><span>Signals</span><b>118</b></button>
			<button class:active={view === 'programs'} onclick={() => (view = 'programs')}><ArchiveIcon /><span>Programs</span><b>3</b></button>
			<button class:active={view === 'proof'} onclick={() => (view = 'proof')}><ChartIcon /><span>Proof</span></button>
		</nav>

		<div class="sidebar-label">Saved views</div>
		<button class="saved" onclick={() => { view = 'signals'; showAll = true; }}><span class="saved-dot amber"></span>Review first<b>24</b></button>
		<button class="saved" onclick={() => { view = 'signals'; showAll = false; }}><span class="saved-dot green"></span>$1M+ reported sold<b>42</b></button>

		<div class="sidebar-spacer"></div>
		<div class="snapshot">
			<DatabaseIcon />
			<div><strong>Demo snapshot</strong><small>Frozen Sep 18, 2026</small></div>
		</div>
		<div class="offline"><i></i> Offline ready</div>
	</aside>

	<main class="surface">
		{#if view === 'signals'}
			<header class="toolbar">
				<div><small>GARDEN STATE INNOVATION FUND</small><h1>New Jersey signals</h1></div>
				<div class="search">
					<SearchIcon />
					<input bind:value={query} onkeydown={(event) => event.key === 'Enter' && runSearch()} placeholder="Search any NJ town" aria-label="Search any New Jersey town" />
					<kbd>↵</kbd>
				</div>
				<div class="avatar">14</div>
			</header>

			<div class="demo-warning"><InfoIcon /><strong>Fictional demo data</strong><span>Product logic is real; companies and results are illustrative.</span></div>

			{#if searchResult && !searchResult.company}
				<div class="empty-result"><SearchIcon /><span><strong>No federal signal in {searchResult.town}</strong><small>That does not mean there are no startups there. Public records have real coverage limits.</small></span><button onclick={() => (searchResult = null)}><CloseIcon /></button></div>
			{/if}

			<div class="signal-grid">
				<section class="map-card">
					<div class="map-toolbar">
						<div class="segmented">
							<button class:active={!showAll} onclick={() => (showAll = false)}>Already funded <b>42</b></button>
							<button class:active={showAll} onclick={() => (showAll = true)}>All public signals <b>118</b></button>
						</div>
						<span><i></i> 3 sources connected</span>
					</div>

					<div class="map-wrap">
						<div class="map-number"><small>SHOWING</small><strong>{showAll ? 118 : 42}</strong><span>likely startups<br />with public evidence</span></div>
						<svg viewBox="0 0 420 620" aria-label="Accurate map of New Jersey counties and demo startup signals">
							<defs>
								<linearGradient id="nj-fill" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#dce7e3" stop-opacity=".74"/><stop offset="1" stop-color="#9dbab1" stop-opacity=".54"/></linearGradient>
								<filter id="nj-shadow" x="-40%" y="-30%" width="180%" height="180%"><feDropShadow dx="0" dy="10" stdDeviation="13" flood-color="#00140e" flood-opacity=".3"/></filter>
							</defs>
							<path d={statePath} class="state-shadow" filter="url(#nj-shadow)" />
							<path d={statePath} class="state-fill" />
							<path d={countyPath} class="county-lines" />
							<path d={statePath} class="state-outline" />
							{#each visibleCompanies as company}
								{@const point = projectCompany(company)}
								<g class="marker-group" role="button" tabindex="0" aria-label="Open {company.name}" onclick={() => (selectedCompany = company)} onkeydown={(event) => (event.key === 'Enter' || event.key === ' ') && (selectedCompany = company)}>
									{#if selectedCompany?.id === company.id}<circle cx={point[0]} cy={point[1]} r="17" class="pulse" />{/if}
									<circle cx={point[0]} cy={point[1]} r="6.5" class:funded={company.funded} class="marker" />
								</g>
							{/each}
							<text x="34" y="188" class="place-label">PENNSYLVANIA</text>
							<text x="343" y="176" class="place-label">NEW YORK</text>
							<text x="355" y="490" class="ocean-label" transform="rotate(72 355 490)">ATLANTIC OCEAN</text>
						</svg>
						<div class="legend"><span><i class="funded"></i>$1M+ sold</span>{#if showAll}<span><i></i>Other evidence</span>{/if}</div>
					</div>
				</section>

				<aside class="insights">
					<div class="metric-row">
						<div><small>MUNICIPALITIES</small><strong>{showAll ? 47 : 24}</strong><span>with a visible signal</span></div>
						<div><small>PROGRAM MATCHES</small><strong>{showAll ? 29 : 16}</strong><span>strong matches</span></div>
					</div>

					<div class="company-list">
						<div class="list-head"><span><strong>Priority signals</strong><small>Ranked within sector</small></span><button>···</button></div>
						{#each visibleCompanies.slice(0, 5) as company, index}
							<button class="company-row" onclick={() => (selectedCompany = company)}>
								<em>{String(index + 1).padStart(2, '0')}</em>
								<span><strong>{company.name}</strong><small>{company.town} · {company.sector}</small></span>
								<i class:review={company.tier === 'Review first'}>{company.tier}</i>
								<ArrowIcon />
							</button>
						{/each}
					</div>

					<div class="honesty"><ShieldIcon /><span><strong>Evidence, not certainty</strong><small>Gauge does not claim to show every NJ startup or prove program eligibility.</small></span></div>
				</aside>
			</div>
		{:else if view === 'programs'}
			<header class="toolbar standalone"><div><small>RULES ENGINE</small><h1>Program opportunities</h1><p>Unknown facts become first-call questions, not invented eligibility.</p></div><div class="avatar">14</div></header>
			<div class="demo-warning"><InfoIcon /><strong>Illustrative rules</strong><span>Re-verify official pages before making factual eligibility claims.</span></div>
			<div class="program-grid">
				<article class="program-card green"><span>01</span><ArchiveIcon /><h2>CSIT SBIR/STTR Direct Financial Assistance</h2><p>Phase-based support for New Jersey companies with qualifying federal awards.</p><div><strong>18</strong><small>strong matches</small><strong>11</strong><small>verify on call</small></div><footer><CheckIcon /> Reviewed Sep 18, 2026</footer></article>
				<article class="program-card amber"><span>02</span><ArchiveIcon /><h2>Angel Investor Tax Credit</h2><p>Refundable investor tax credit for qualifying New Jersey businesses.</p><div><strong>7</strong><small>strong matches</small><strong>46</strong><small>verify on call</small></div><footer><CheckIcon /> Reviewed Sep 20, 2026</footer></article>
				<article class="program-card violet"><span>03</span><ArchiveIcon /><h2>Life Sciences & Healthcare Fund</h2><p>Matching capital for qualifying seed through Series B rounds.</p><div><strong>4</strong><small>strong matches</small><strong>19</strong><small>verify on call</small></div><footer><CheckIcon /> Reviewed Sep 19, 2026</footer></article>
			</div>
			<div class="semantics"><div><small>CLEAN SEMANTICS</small><h2>Three states. No eligibility theater.</h2></div><span class="strong"><i></i><strong>Strong match</strong><small>Material requirements established</small></span><span class="potential"><i></i><strong>Potential match, verify</strong><small>At least one fact is unknown</small></span><span><i></i><strong>Not a match</strong><small>A material requirement fails</small></span></div>
		{:else}
			<div class="proof-view">
				<div class="proof-top"><small>THE PROOF · SIMULATED DEMO RESULTS</small><span>Illustrative, not validated</span></div>
				<div class="proof-title"><p>Does the evidence add information?</p><h1>More qualified signals.<br /><em>Fewer analyst hours.</em></h1></div>
				<div class="proof-cards">
					<article><small>01 · BACKTEST</small><div><strong>44%</strong><span>vs 24%</span></div><h3>1.8× lift over the strongest baseline</h3><p>Top-25 companies reaching a later financing or grant milestone.</p></article>
					<article><small>02 · COLD START</small><div><strong>31%</strong><span>vs 17%</span></div><h3>Evidence beyond prior activity</h3><p>First institutional signal among companies with no prior raise or award.</p></article>
					<article><small>03 · QUALIFICATION</small><div><strong>9</strong><span>of 18</span></div><h3>Advanced after a ten-minute screen</h3><p>Illustrative analyst screens of previously unknown companies.</p></article>
				</div>
				<div class="proof-note"><InfoIcon /><span><strong>Later financing and grant progress, not investment return.</strong> A real pilot measures cost per qualified first meeting against 1435's current process.</span></div>
				<div class="rail-close"><div class="mini-mark"><span></span><span></span><i></i><i></i><i></i></div><span><small>1,435 MILLIMETERS · STANDARD GAUGE</small><strong>One common track for New Jersey's startup signals.</strong><p>A 90-day pilot with the Garden State Innovation Fund.</p></span></div>
			</div>
		{/if}

		{#if selectedCompany}
			<div class="detail-backdrop" role="presentation" onclick={(event) => event.target === event.currentTarget && (selectedCompany = null)} onkeydown={(event) => event.key === 'Escape' && (selectedCompany = null)}>
				<article class="detail-panel">
					<header><span>FICTIONAL DEMO COMPANY</span><button onclick={() => (selectedCompany = null)}><CloseIcon /></button></header>
					<div class="company-title"><div>{selectedCompany.name.split(' ').map((word) => word[0]).slice(0,2).join('')}</div><span><small>{selectedCompany.town}, NEW JERSEY · FOUNDED {selectedCompany.year}</small><h2>{selectedCompany.name}</h2><p>{selectedCompany.description}</p></span></div>
					<div class="pills"><span><CheckIcon /> Likely startup</span><span>High-confidence match</span><span>{selectedCompany.tier} in {selectedCompany.sector}</span></div>
					<section><h3><CheckIcon /> ESTABLISHED FROM PUBLIC RECORDS</h3>{#each selectedCompany.evidence as item}<div class="evidence"><CheckIcon /><span>{item}<small>View linked demo source ↗</small></span></div>{/each}</section>
					<section><h3 class="unknown"><InfoIcon /> NOT ESTABLISHED FROM CURRENT SOURCES</h3>{#each selectedCompany.unknowns as item}<p class="unknown-row">— {item}</p>{/each}</section>
					<section><h3><ArchiveIcon /> PROGRAM MATCHES</h3>{#each selectedCompany.programs as program}<div class="match {matchTone(program.state)}"><span>{program.state}</span><strong>{program.name}</strong><p>{program.detail}</p></div>{/each}</section>
				</article>
			</div>
		{/if}
	</main>
</section>

<style>
	.gauge-app { position: relative; width: 100%; height: 100%; overflow: hidden; display: grid; grid-template-columns: 158px minmax(0, 1fr); border-radius: inherit; color: #f6f8f7; background: rgba(15, 25, 23, .48); backdrop-filter: blur(36px) saturate(125%); box-shadow: inset 0 0 0 1px rgba(255,255,255,.22); font-family: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif; }
	.drag-strip { position: absolute; z-index: 2; left: 0; right: 0; top: 0; height: 29px; }
	.sidebar { min-width: 0; display: flex; flex-direction: column; padding: 48px 10px 13px; background: linear-gradient(180deg, rgba(13,18,17,.76), rgba(18,25,22,.66)); border-right: 1px solid rgba(255,255,255,.08); }
	.brand { display: flex; align-items: center; gap: 9px; padding: 0 7px 22px; }.brand strong,.brand small{display:block}.brand strong{font-size:16px;letter-spacing:-.03em}.brand small{margin-top:2px;color:rgba(255,255,255,.42);font-size:7px}
	.brand-mark,.mini-mark{position:relative;width:34px;height:34px;flex:0 0 auto;border-radius:9px;overflow:hidden;background:linear-gradient(145deg,#296a59,#0b2e27);box-shadow:0 5px 13px rgba(0,0,0,.26)}.brand-mark>span,.mini-mark>span{position:absolute;top:5px;bottom:5px;width:3px;border-radius:3px;background:#e2ac54;transform:rotate(-7deg)}.brand-mark>span:first-child,.mini-mark>span:first-child{left:10px}.brand-mark>span:nth-child(2),.mini-mark>span:nth-child(2){right:10px}.brand-mark i,.mini-mark i{position:absolute;left:7px;right:7px;height:2px;background:rgba(255,255,255,.77);transform:rotate(-7deg)}.brand-mark i:nth-of-type(1),.mini-mark i:nth-of-type(1){top:9px}.brand-mark i:nth-of-type(2),.mini-mark i:nth-of-type(2){top:16px}.brand-mark i:nth-of-type(3),.mini-mark i:nth-of-type(3){top:23px}
	nav{display:grid;gap:3px}nav button,.saved{width:100%;min-height:31px;display:grid;grid-template-columns:18px 1fr auto;align-items:center;gap:7px;padding:0 8px;border-radius:7px;color:rgba(255,255,255,.63);font-size:9px;text-align:left}nav button :global(svg){font-size:14px}nav button b,.saved b{font-size:7px;font-weight:500;color:rgba(255,255,255,.34)}nav button:hover,.saved:hover{background:rgba(255,255,255,.07)}nav button.active{background:rgba(255,255,255,.14);color:#fff;box-shadow:inset 0 0 0 .5px rgba(255,255,255,.12)}
	.sidebar-label{margin:22px 8px 8px;color:rgba(255,255,255,.3);font-size:7px;font-weight:700;letter-spacing:.11em;text-transform:uppercase}.saved{grid-template-columns:9px 1fr auto;min-height:28px;padding:0 10px}.saved-dot{width:6px;height:6px;border-radius:50%}.saved-dot.amber{background:#d9a252}.saved-dot.green{background:#5cac8d}.sidebar-spacer{flex:1}.snapshot{display:flex;align-items:center;gap:8px;padding:9px;border:1px solid rgba(255,255,255,.08);border-radius:9px;background:rgba(255,255,255,.06)}.snapshot :global(svg){font-size:16px;color:#75c0a3}.snapshot strong,.snapshot small{display:block}.snapshot strong{font-size:8px}.snapshot small{margin-top:2px;color:rgba(255,255,255,.38);font-size:6.5px}.offline{display:flex;align-items:center;gap:6px;padding:11px 8px 0;color:rgba(255,255,255,.35);font-size:7px}.offline i{width:5px;height:5px;border-radius:50%;background:#55c092;box-shadow:0 0 8px #55c092}
	.surface{position:relative;min-width:0;min-height:0;overflow:hidden;padding:29px 18px 18px;background:linear-gradient(145deg,rgba(232,237,233,.66),rgba(186,200,194,.43));color:#17201d}.toolbar{height:45px;display:grid;grid-template-columns:minmax(180px,1fr) minmax(220px,340px) 30px;align-items:center;gap:14px}.toolbar.standalone{height:57px;grid-template-columns:1fr 30px}.toolbar small{color:#47665b;font-size:6.5px;font-weight:700;letter-spacing:.11em}.toolbar h1{margin:2px 0 0;font-size:20px;line-height:1;letter-spacing:-.045em}.toolbar p{margin:4px 0 0;color:#68766f;font-size:8px}.search{position:relative;z-index:3;height:31px;display:flex;align-items:center;gap:7px;padding:0 8px;border:1px solid rgba(31,48,42,.11);border-radius:8px;background:rgba(255,255,255,.54);box-shadow:0 4px 12px rgba(20,42,34,.05)}.search :global(svg){font-size:14px;color:#6d7b75}.search input{min-width:0;flex:1;border:0;outline:0;background:transparent;color:#25312d;font:inherit;font-size:8.5px}.search input::placeholder{color:#79847f}.search kbd{padding:2px 4px;border:1px solid rgba(26,50,42,.12);border-radius:4px;background:rgba(255,255,255,.44);color:#75817b;font-size:7px}.avatar{width:27px;height:27px;display:grid;place-items:center;border-radius:50%;background:#173f34;color:white;font-size:8px;font-weight:700;box-shadow:0 4px 9px rgba(20,53,43,.23)}
	.demo-warning{height:27px;display:flex;align-items:center;gap:6px;margin:2px 0 10px;padding:0 9px;border:1px solid rgba(140,105,45,.18);border-radius:7px;background:rgba(255,244,216,.65);color:#685a40;font-size:7px}.demo-warning :global(svg){font-size:12px}.demo-warning span{opacity:.74}.empty-result{height:43px;display:flex;align-items:center;gap:8px;margin:-2px 0 8px;padding:0 10px;border:1px solid rgba(165,117,50,.24);border-radius:8px;background:rgba(255,244,218,.78);color:#6f5a36}.empty-result>span{flex:1}.empty-result strong,.empty-result small{display:block}.empty-result strong{font-size:8px}.empty-result small{margin-top:2px;font-size:6.5px;opacity:.72}.empty-result button{font-size:12px}
	.signal-grid{height:calc(100% - 91px);display:grid;grid-template-columns:minmax(390px,1.45fr) minmax(250px,.8fr);gap:10px}.empty-result+.signal-grid{height:calc(100% - 142px)}.map-card,.metric-row,.company-list,.honesty,.program-card,.semantics{border:1px solid rgba(255,255,255,.32);background:rgba(249,251,249,.49);box-shadow:inset 0 0 0 .5px rgba(22,48,39,.08),0 8px 22px rgba(13,35,28,.06)}.map-card{min-width:0;overflow:hidden;border-radius:11px}.map-toolbar{height:39px;display:flex;align-items:center;justify-content:space-between;padding:0 10px;border-bottom:1px solid rgba(37,58,50,.1)}.segmented{display:flex;padding:2px;border-radius:6px;background:rgba(52,72,64,.1)}.segmented button{height:23px;padding:0 8px;border-radius:5px;color:#68756f;font-size:7px}.segmented button b{margin-left:4px;color:#829089}.segmented button.active{background:rgba(255,255,255,.82);color:#234b3e;font-weight:600;box-shadow:0 1px 4px rgba(28,50,42,.12)}.map-toolbar>span{display:flex;align-items:center;gap:5px;color:#68776f;font-size:6.5px}.map-toolbar>span i{width:5px;height:5px;border-radius:50%;background:#57ad8b;box-shadow:0 0 0 3px rgba(87,173,139,.12)}
	.map-wrap{position:relative;height:calc(100% - 39px);overflow:hidden;background:linear-gradient(145deg,rgba(240,244,241,.22),rgba(202,215,209,.14))}.map-wrap::before{content:'';position:absolute;inset:0;background-image:linear-gradient(rgba(33,78,62,.045) 1px,transparent 1px),linear-gradient(90deg,rgba(33,78,62,.045) 1px,transparent 1px);background-size:21px 21px}.map-wrap svg{position:relative;width:100%;height:100%;overflow:visible}.state-shadow{fill:rgba(13,45,35,.32)}.state-fill{fill:url(#nj-fill)}.county-lines{fill:none;stroke:rgba(43,78,66,.28);stroke-width:.85;vector-effect:non-scaling-stroke}.state-outline{fill:none;stroke:rgba(35,75,61,.54);stroke-width:1.5;vector-effect:non-scaling-stroke}.marker-group{cursor:pointer}.marker{fill:#d49a43;stroke:white;stroke-width:1.8;transition:r .15s ease}.marker.funded{fill:#1d6751}.marker-group:hover .marker{r:9}.pulse{fill:none;stroke:#276f59;stroke-width:2;opacity:.4;animation:pulse 1.5s infinite}@keyframes pulse{70%{r:25;opacity:0}}.place-label,.ocean-label{fill:rgba(53,78,68,.5);font-size:7px;font-weight:600;letter-spacing:.14em}.ocean-label{font-size:6px}.map-number{position:absolute;z-index:2;left:12px;top:12px;padding:9px 10px;border:1px solid rgba(24,56,45,.1);border-radius:8px;background:rgba(246,249,247,.78);backdrop-filter:blur(12px);box-shadow:0 6px 18px rgba(20,47,38,.09)}.map-number small,.map-number strong,.map-number span{display:block}.map-number small{color:#74827b;font-size:6px;letter-spacing:.08em}.map-number strong{margin:1px 0;color:#1f5a48;font-size:24px;line-height:1}.map-number span{margin-top:3px;color:#627069;font-size:6.5px;line-height:1.3}.legend{position:absolute;right:11px;bottom:9px;display:flex;gap:10px;color:#617169;font-size:6.5px}.legend span{display:flex;align-items:center;gap:4px}.legend i{width:6px;height:6px;border-radius:50%;background:#d49a43;border:1px solid white}.legend i.funded{background:#1d6751}
	.insights{min-height:0;display:flex;flex-direction:column;gap:9px}.metric-row{height:67px;display:grid;grid-template-columns:1fr 1fr;border-radius:10px}.metric-row>div{padding:10px;border-right:1px solid rgba(31,53,45,.1)}.metric-row>div:last-child{border:0}.metric-row small,.metric-row strong,.metric-row span{display:block}.metric-row small{color:#718078;font-size:6px;letter-spacing:.06em}.metric-row strong{margin:2px 0;color:#204f40;font-size:19px;line-height:1}.metric-row span{color:#718078;font-size:6.5px}.company-list{min-height:0;flex:1;overflow:hidden;border-radius:10px}.list-head{height:45px;display:flex;align-items:center;justify-content:space-between;padding:0 11px;border-bottom:1px solid rgba(31,53,45,.1)}.list-head strong,.list-head small{display:block}.list-head strong{font-size:9px}.list-head small{margin-top:2px;color:#748078;font-size:6.5px}.list-head button{font-size:11px;color:#6b7771}.company-row{width:100%;height:47px;display:grid;grid-template-columns:20px minmax(0,1fr) auto 11px;align-items:center;gap:5px;padding:0 9px;border-bottom:1px solid rgba(31,53,45,.08);text-align:left}.company-row:hover{background:rgba(255,255,255,.26)}.company-row em{color:#84908a;font-size:6px;font-style:normal}.company-row>span{min-width:0}.company-row strong,.company-row small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.company-row strong{font-size:7.7px}.company-row small{margin-top:2px;color:#718078;font-size:6.2px}.company-row>i{padding:3px 5px;border-radius:5px;background:rgba(103,116,109,.1);color:#68756f;font-size:5.5px;font-style:normal;white-space:nowrap}.company-row>i.review{background:rgba(56,138,105,.13);color:#327258}.company-row :global(svg){font-size:9px;color:#7d8983}.honesty{display:flex;align-items:flex-start;gap:7px;padding:8px 9px;border-radius:9px;background:rgba(222,237,229,.56);color:#3c6958}.honesty :global(svg){font-size:14px;flex:0 0 auto}.honesty strong,.honesty small{display:block}.honesty strong{font-size:7px}.honesty small{margin-top:2px;color:#61776d;font-size:6px;line-height:1.3}
	.program-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:12px}.program-card{position:relative;min-height:248px;padding:18px 14px 13px;border-radius:11px;overflow:hidden}.program-card::before{content:'';position:absolute;inset:0 0 auto;height:3px;background:#4c9678}.program-card.amber::before{background:#c88b33}.program-card.violet::before{background:#7d6eb4}.program-card>span{position:absolute;right:12px;top:12px;color:#7b8882;font-size:7px}.program-card>:global(svg){font-size:22px;color:#3c8267}.program-card.amber>:global(svg){color:#a77029}.program-card.violet>:global(svg){color:#7666ac}.program-card h2{min-height:42px;margin:15px 0 7px;font-size:12px;line-height:1.3;letter-spacing:-.025em}.program-card>p{min-height:38px;margin:0;color:#65746d;font-size:7px;line-height:1.45}.program-card>div{display:grid;grid-template-columns:1fr 1fr;gap:4px;margin-top:15px;padding:10px;border-radius:8px;background:rgba(255,255,255,.3)}.program-card>div strong{font-size:19px;color:#2c6853}.program-card>div small{font-size:6px;color:#77837d}.program-card footer{position:absolute;left:14px;right:14px;bottom:13px;display:flex;align-items:center;gap:5px;padding-top:9px;border-top:1px solid rgba(35,58,49,.09);color:#69766f;font-size:6.5px}.semantics{display:grid;grid-template-columns:1.25fr 1fr 1.1fr 1fr;gap:10px;align-items:center;margin-top:11px;padding:14px;border-radius:10px}.semantics>div small{color:#46745f;font-size:6px;font-weight:700;letter-spacing:.08em}.semantics h2{margin:4px 0 0;font-size:14px;letter-spacing:-.035em}.semantics>span{display:grid;grid-template-columns:8px 1fr;padding-left:10px;border-left:1px solid rgba(31,53,45,.11)}.semantics>span i{width:6px;height:6px;margin-top:3px;border-radius:50%;background:#7b8781}.semantics>span.strong i{background:#46a07d}.semantics>span.potential i{background:#d39a42}.semantics>span strong{font-size:7px}.semantics>span small{grid-column:2;color:#738079;font-size:6px;margin-top:2px}
	.proof-view{height:calc(100% + 47px);margin:-29px -18px -18px;padding:40px 20px 18px;display:flex;flex-direction:column;color:#eaf2ee;background:radial-gradient(circle at 84% 8%,rgba(96,163,135,.26),transparent 32%),linear-gradient(rgba(255,255,255,.025) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.025) 1px,transparent 1px),#103d31;background-size:auto,28px 28px,28px 28px}.proof-top{display:flex;align-items:center;justify-content:space-between;padding-top:8px}.proof-top small{color:#a8c1b6;font-size:6.5px;font-weight:700;letter-spacing:.1em}.proof-top>span{padding:4px 7px;border:1px solid rgba(255,255,255,.13);border-radius:10px;color:#b3c6be;font-size:6px}.proof-title{margin:21px 0 18px}.proof-title p{margin:0 0 4px;color:#a4bcb2;font-size:8px}.proof-title h1{margin:0;font-size:34px;line-height:1.03;letter-spacing:-.055em}.proof-title em{color:#d6a957;font-style:normal}.proof-cards{display:grid;grid-template-columns:repeat(3,1fr);gap:9px}.proof-cards article{min-height:156px;padding:13px;border:1px solid rgba(255,255,255,.12);border-radius:10px;background:rgba(255,255,255,.055)}.proof-cards article>small{color:#8fb0a2;font-size:6px;letter-spacing:.08em}.proof-cards article>div{display:flex;align-items:baseline;gap:6px;margin:12px 0 8px}.proof-cards article>div strong{font-size:30px;line-height:1}.proof-cards article>div span{color:#d9ae60;font-size:8px}.proof-cards h3{margin:0 0 5px;font-size:9px}.proof-cards p{margin:0;color:#9fb6ac;font-size:6.7px;line-height:1.45}.proof-note{display:flex;align-items:center;gap:7px;margin-top:9px;padding:9px 10px;border-radius:8px;background:rgba(255,255,255,.06);color:#a9beb5;font-size:7px}.proof-note strong{color:white}.rail-close{display:flex;align-items:center;gap:13px;margin-top:auto;padding:12px 14px;border:1px solid rgba(219,175,93,.25);border-radius:10px;background:linear-gradient(90deg,rgba(212,167,82,.12),rgba(255,255,255,.035))}.mini-mark{width:35px;height:35px}.rail-close>span small,.rail-close>span strong,.rail-close>span p{display:block}.rail-close>span small{color:#d6b16b;font-size:6px;letter-spacing:.09em}.rail-close>span strong{margin:3px 0;font-size:12px}.rail-close>span p{margin:0;color:#a9bdb4;font-size:7px}
	.detail-backdrop{position:absolute;z-index:20;inset:0;display:flex;justify-content:flex-end;background:rgba(8,18,15,.26);backdrop-filter:blur(2px)}.detail-panel{width:min(430px,62%);height:100%;overflow:auto;padding:35px 17px 25px;background:rgba(246,247,243,.93);backdrop-filter:blur(26px);border-left:1px solid rgba(255,255,255,.55);box-shadow:-22px 0 60px rgba(6,22,16,.22);animation:drawer-in .25s ease}@keyframes drawer-in{from{transform:translateX(24px);opacity:.5}}.detail-panel>header{display:flex;justify-content:space-between;align-items:center}.detail-panel>header>span{padding:4px 6px;border-radius:5px;background:#f2e8d2;color:#805d27;font-size:5.5px;font-weight:700;letter-spacing:.08em}.detail-panel>header button{width:24px;height:24px;border-radius:50%;background:rgba(40,57,50,.08);font-size:13px}.company-title{display:flex;align-items:flex-start;gap:10px;margin-top:11px}.company-title>div{width:39px;height:39px;display:grid;place-items:center;flex:0 0 auto;border-radius:9px;background:linear-gradient(145deg,#397662,#173f34);color:white;font-size:11px;font-weight:700;box-shadow:0 6px 14px rgba(19,59,46,.2)}.company-title>span{min-width:0}.company-title small{color:#76827c;font-size:5.5px;letter-spacing:.06em}.company-title h2{margin:3px 0;font-size:17px;letter-spacing:-.04em}.company-title p{margin:0;color:#64716b;font-size:7px;line-height:1.4}.pills{display:flex;flex-wrap:wrap;gap:5px;margin:11px 0 15px}.pills span{display:flex;align-items:center;gap:3px;padding:4px 6px;border:1px solid rgba(33,60,49,.13);border-radius:10px;background:rgba(255,255,255,.5);color:#5f6c66;font-size:5.8px}.pills span:first-child{color:#2d7359;background:#e3f1e9}.pills :global(svg){font-size:8px}.detail-panel section{margin-top:14px}.detail-panel h3{display:flex;align-items:center;gap:5px;margin:0 0 7px;color:#2e7056;font-size:6px;letter-spacing:.08em}.detail-panel h3.unknown{color:#8b652c}.detail-panel h3 :global(svg){font-size:10px}.evidence{display:flex;align-items:flex-start;gap:7px;padding:8px;border:1px solid rgba(35,60,50,.1);border-bottom:0;background:rgba(255,255,255,.45);font-size:7px}.evidence:nth-last-child(1){border-bottom:1px solid rgba(35,60,50,.1);border-radius:0 0 7px 7px}.evidence:nth-child(2){border-radius:7px 7px 0 0}.evidence>:global(svg){font-size:11px;color:#3d8769;flex:0 0 auto}.evidence span small{display:block;margin-top:3px;color:#3e7c65;font-size:5.5px}.unknown-row{margin:0;padding:5px 8px;border-left:2px solid #cfa253;background:rgba(250,239,220,.52);color:#786c57;font-size:6.5px}.match{display:grid;gap:3px;margin-top:6px;padding:8px;border:1px solid rgba(35,60,50,.1);border-left:3px solid #7a8780;border-radius:7px;background:rgba(255,255,255,.45)}.match.strong{border-left-color:#3e9673}.match.potential{border-left-color:#d39b42}.match>span{color:#69756f;font-size:5.5px;font-weight:700;text-transform:uppercase;letter-spacing:.06em}.match.strong>span{color:#31775b}.match.potential>span{color:#966a27}.match strong{font-size:7px}.match p{margin:0;color:#68756f;font-size:6px;line-height:1.35}
	@media (max-width: 900px){.gauge-app{grid-template-columns:130px 1fr}.surface{padding:29px 14px 14px}.signal-grid{grid-template-columns:1fr}.insights{display:none}.toolbar{grid-template-columns:1fr minmax(160px,260px) 28px}.program-card{min-height:235px;padding-left:11px;padding-right:11px}.semantics{display:none}.detail-panel{width:75%}}
</style>
