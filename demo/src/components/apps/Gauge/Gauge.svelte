<script lang="ts">
  import { onMount } from 'svelte';
  import { fly } from 'svelte/transition';
  import Search from '~icons/lucide/search';
  import MapPin from '~icons/lucide/map-pin';
  import Layers from '~icons/lucide/layers';
  import Radio from '~icons/lucide/radio';
  import Bookmark from '~icons/lucide/bookmark';
  import ArrowUpRight from '~icons/lucide/arrow-up-right';
  import ArrowRight from '~icons/lucide/arrow-right';
  import X from '~icons/lucide/x';
  import Pause from '~icons/lucide/pause';
  import Play from '~icons/lucide/play';
  import Rotate from '~icons/lucide/rotate-ccw';
  import Plus from '~icons/lucide/plus';
  import FileText from '~icons/lucide/file-text';
  import Flask from '~icons/lucide/flask-conical';
  import Fingerprint from '~icons/lucide/fingerprint';
  import Check from '~icons/lucide/check';
  import atlas from 'us-atlas/counties-10m.json';
  import { feature, mesh } from 'topojson-client';
  import { geoMercator, geoPath } from 'd3-geo';
  import { companies, type Company } from './gauge-data';
  import { realCompanies } from './real-companies';
  import { createSignal, initialEvents, initialCompanyIds, signalKinds, type SignalEvent } from './simulation';
  import './gauge.css';

  type Profile = { id: string; name: string; town: string; sector: string; coordinates: [number, number]; description: string; real: boolean; logo?: string; website?: string; sourceUrl?: string; synthetic?: Company };
  const syntheticProfiles: Profile[] = companies.map((c) => ({ ...c, real: false, synthetic: c, logo: `/brands/${['aster','lucent','harbor','delta','mosaic','common'].includes(c.id) ? c.id : 'lucent'}.svg` }));
  const directory: Profile[] = [...realCompanies, ...syntheticProfiles];
  const topology = atlas as any;
  const stateGeometry = topology.objects.states.geometries.find((g: any) => +g.id === 34);
  const countyObject = { type: 'GeometryCollection', geometries: topology.objects.counties.geometries.filter((g: any) => String(g.id).padStart(5, '0').startsWith('34')) } as any;
  const newJersey = feature(topology, stateGeometry) as any;
  const projection = geoMercator().fitExtent([[110, 42], [422, 536]], newJersey);
  const path = geoPath(projection);
  const statePath = path(newJersey) ?? '';
  const countyPath = path(mesh(topology, countyObject, (a: any, b: any) => a !== b)) ?? '';
  const neighbors = topology.objects.states.geometries.filter((g: any) => [36, 42, 10].includes(+g.id)).map((g: any) => path(feature(topology, g) as any));

  let view = $state<'explore' | 'companies' | 'saved' | 'programs' | 'sources'>('explore');
  let query = $state('');
  let dataset = $state<'all' | 'real' | 'synthetic'>('all');
  let source = $state('All signals');
  let activeIds = $state([...initialCompanyIds]);
  let events = $state<SignalEvent[]>(initialEvents());
  let selected = $state<Profile | null>(null);
  let selectedEvent = $state<SignalEvent | null>(null);
  let saved = $state<string[]>([]);
  let playing = $state(true);
  let sequence = $state(0);
  let now = $state(Date.now());
  let latest = $state<SignalEvent | null>(null);
  let latestAt = $state(0);
  let hovered = $state<string | null>(null);
  let speed = $state('normal');
  const filtered = $derived(directory.filter((c) => {
    const text = `${c.name} ${c.town} ${c.sector}`.toLowerCase();
    return text.includes(query.trim().toLowerCase()) && (dataset === 'all' || (dataset === 'real' ? c.real : !c.real)) && (view !== 'saved' || saved.includes(c.id));
  }));
  const mapCompanies = $derived(filtered.filter((c) => (c.real || activeIds.includes(c.id)) && (source === 'All signals' || events.some((e) => e.companyId === c.id && e.kind === source))));
  const feed = $derived(events.filter((e) => filtered.some((c) => c.id === e.companyId) && (source === 'All signals' || e.kind === source)));
  const latestVisible = $derived(latest && now - latestAt < 6500);
  const towns = $derived(new Set(mapCompanies.map((c) => c.town)).size);
  const selectedSignals = $derived(events.filter((e) => e.companyId === selected?.id));
  function getProfile(id: string) { return directory.find((c) => c.id === id)!; }
  function point(c: Profile): [number, number] { return projection(c.coordinates) as [number, number]; }
  function age(timestamp: number) { const seconds = Math.max(0, Math.floor((now - timestamp) / 1000)); return seconds < 10 ? 'Just now' : seconds < 60 ? `${seconds}s ago` : `${Math.floor(seconds / 60)}m ago`; }
  function toggleSaved(id: string) { saved = saved.includes(id) ? saved.filter((item) => item !== id) : [...saved, id]; }
  function openCompany(c: Profile, event: SignalEvent | null = null) { selected = c; selectedEvent = event; }
  function addSignal() {
    const event = createSignal(sequence++);
    events = [event, ...events].slice(0, 60);
    activeIds = [...new Set([...activeIds, event.companyId])];
    latest = event; latestAt = Date.now(); now = latestAt;
  }
  function reset() { sequence = 0; activeIds = [...initialCompanyIds]; events = initialEvents(); latest = null; now = Date.now(); }
  function navigate(next: typeof view) { view = next; query = ''; }
  onMount(() => {
    let timer: ReturnType<typeof setTimeout>;
    let disposed = false;
    function schedule() {
      timer = setTimeout(() => {
        if (disposed) return;
        if (playing && !document.hidden) addSignal();
        schedule();
      }, speed === 'fast' ? 3500 + Math.random() * 2500 : 9000 + Math.random() * 9000);
    }
    schedule();
    const clock = setInterval(() => { now = Date.now(); }, 1000);
    try { saved = JSON.parse(localStorage.getItem('gauge-saved-v2') || '[]').filter((id: string) => directory.some((c) => c.id === id)); } catch { saved = []; }
    return () => { disposed = true; clearTimeout(timer); clearInterval(clock); };
  });
  $effect(() => { try { localStorage.setItem('gauge-saved-v2', JSON.stringify(saved)); } catch {} });
</script>

<svelte:window onkeydown={(e) => { if (e.key === 'Escape') { selected = null; selectedEvent = null; } }} />

{#snippet logo(c: Profile, large = false)}
  <span class:large class="company-logo" style={`--logo-color: ${c.real ? '#eef1f7' : '#edf3ed'}`}>
    {#if c.logo}<img src={c.logo} alt="" onerror={(e) => { e.currentTarget.style.display = 'none'; }} />{/if}
    <span>{c.name.slice(0, 1)}</span>
  </span>
{/snippet}
{#snippet signalIcon(kind: string)}
  {#if kind === 'SEC filing'}<FileText />{:else if kind === 'Patent'}<Fingerprint />{:else}<Flask />{/if}
{/snippet}

<section class="gauge-app">
  <div class="drag-strip app-window-drag-handle" aria-hidden="true"></div>
  <aside class="sidebar">
    <div class="brand"><span class="gauge-mark">g<span></span></span><strong>gauge<span>THE GARDEN STATE, DISCOVERED.</span></strong></div>
    <div class="workspace-label">WORKSPACE</div>
    <nav aria-label="Main navigation">
      <button class:active={view === 'explore'} onclick={() => navigate('explore')} title="Explore"><MapPin /><span>Explore</span></button>
      <button class:active={view === 'companies'} onclick={() => navigate('companies')} title="Companies"><Layers /><span>Companies</span><b>{directory.length}</b></button>
      <button class:active={view === 'saved'} onclick={() => navigate('saved')} title="Saved companies"><Bookmark /><span>Saved</span>{#if saved.length}<b>{saved.length}</b>{/if}</button>
      <button class:active={view === 'programs'} onclick={() => navigate('programs')} title="Programs"><Flask /><span>Programs</span></button>
    </nav>
    <div class="sidebar-bottom">
      <div class="region-card"><span class="region-shape"><svg viewBox="90 30 340 520" aria-hidden="true"><path d={statePath}/></svg></span><div><strong>Built for New Jersey</strong><span>21 counties. One place.</span></div></div>
      <button class="source-nav" class:active={view === 'sources'} onclick={() => navigate('sources')} title="Data sources"><Radio /><span>Data sources</span><ArrowUpRight /></button>
      <div class="account"><span>14</span><div><strong>1435 Capital</strong><small>Research workspace</small></div></div>
    </div>
  </aside>

  <main class="surface">
    <header class="topbar">
      <div class="breadcrumb">Workspace <span>/</span> <strong>{view === 'explore' ? 'Explore' : view === 'saved' ? 'Saved companies' : view.charAt(0).toUpperCase() + view.slice(1)}</strong></div>
      <span class="demo-badge"><i></i> Interactive demo</span>
    </header>
    <div class="page">
      <header class="page-heading">
        <div><p class="eyebrow">NEW JERSEY · STARTUP INTELLIGENCE</p><h1>{view === 'explore' ? 'Find the next signal.' : view === 'companies' ? 'Good companies start here.' : view === 'saved' ? 'Your shortlist.' : view === 'programs' ? 'A little help to go further.' : 'Follow the evidence.'}</h1><p class="subtitle">{view === 'explore' ? 'A closer look at what’s being built around you.' : view === 'companies' ? 'Real New Jersey companies alongside our synthetic demo portfolio.' : view === 'saved' ? 'The companies you want to come back to.' : view === 'programs' ? 'A starting point for New Jersey funding conversations.' : 'Real company profiles. Clearly labeled simulated activity.'}</p></div>
        {#if view === 'explore'}<button class="secondary heading-action" onclick={() => navigate('companies')}>All companies <ArrowUpRight /></button>{/if}
      </header>

      {#if view === 'explore' || view === 'companies' || view === 'saved'}
        <div class="filter-bar">
          <label class="search"><Search /><input bind:value={query} aria-label="Search companies, towns, or sectors" placeholder="Search companies, towns, sectors…" />{#if query}<button onclick={() => query = ''} aria-label="Clear search"><X /></button>{/if}</label>
          <div class="dataset-tabs" aria-label="Company dataset">
            <button class:chosen={dataset === 'all'} onclick={() => dataset = 'all'}>All</button><button class:chosen={dataset === 'real'} onclick={() => dataset = 'real'}>Real companies</button><button class:chosen={dataset === 'synthetic'} onclick={() => dataset = 'synthetic'}>Synthetic</button>
          </div>
        </div>
      {/if}

      {#if view === 'explore'}
        <div class="explore-grid">
          <section class="map-card" aria-label="New Jersey company map">
            <header class="map-header"><span><i class="status-dot"></i> Garden State radar</span><select bind:value={source} aria-label="Filter map and activity by signal"><option>All signals</option>{#each signalKinds as kind}<option>{kind}</option>{/each}</select></header>
            <div class="map-canvas">
              <div class="map-summary"><strong>{mapCompanies.length}<span>companies on the map</span></strong><small>{towns} towns · 21 counties</small></div>
              <svg class="nj-map" viewBox="0 0 540 590" role="img" aria-label="New Jersey and its 21 counties with company locations">
                <defs><pattern id="map-grid" width="26" height="26" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r=".7" fill="#b9c9c1" opacity=".6"/></pattern><linearGradient id="land" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#e5eee7"/><stop offset="1" stop-color="#d1e1d6"/></linearGradient></defs>
                <rect width="540" height="590" fill="url(#map-grid)"/>
                {#each neighbors as d}<path {d} class="neighbor"/>{/each}
                <path d={statePath} class="state-fill"/><path d={countyPath} class="county-lines"/><path d={statePath} class="state-outline"/>
                <text x="36" y="272" class="map-place">PENNSYLVANIA</text><text x="387" y="115" class="map-place">NEW YORK</text><text x="355" y="468" class="ocean">Atlantic Ocean</text>
                <text x="312" y="554" class="state-label">NEW JERSEY</text>
                {#each mapCompanies as c (c.id)}
                  {@const p = point(c)}
                  <g class="map-marker" class:real={c.real} class:highlight={latestVisible && latest?.companyId === c.id} role="button" tabindex="0" aria-label={`Open ${c.name}, ${c.town}`} onmouseenter={() => hovered = c.id} onmouseleave={() => hovered = null} onfocus={() => hovered = c.id} onblur={() => hovered = null} onclick={() => openCompany(c)} onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openCompany(c); } }}>
                    <title>{c.name} · {c.town} · {c.real ? 'Real company' : 'Synthetic company'}</title>
                    {#if latestVisible && latest?.companyId === c.id}<circle class="arrival-ring" cx={p[0]} cy={p[1]} r="12"/>{/if}
                    <circle class="hit-area" cx={p[0]} cy={p[1]} r="12"/><circle class="dot-halo" cx={p[0]} cy={p[1]} r="8"/><circle class="map-dot" cx={p[0]} cy={p[1]} r="4.5"/>
                  </g>
                {/each}
                {#if hovered && mapCompanies.some((c) => c.id === hovered)}
                  {@const c = getProfile(hovered)}{@const p = point(c)}
                  <g class="map-tooltip" transform={`translate(${Math.min(350, Math.max(10, p[0] - 80))},${p[1] - 49})`}><rect width="174" height="33" rx="7"/><text x="10" y="21">{c.name}</text></g>
                {/if}
              </svg>
              {#if mapCompanies.length === 0}<div class="map-empty">No companies match these filters.<button onclick={() => { query = ''; dataset = 'all'; source = 'All signals'; }}>Clear filters</button></div>{/if}
              {#if latestVisible && latest && mapCompanies.some((c) => c.id === latest.companyId)}<button class="arrival-toast" onclick={() => openCompany(getProfile(latest!.companyId), latest)} transition:fly={{ y: 8, duration: 220 }}><span class={`signal-symbol ${latest.kind === 'Patent' ? 'patent' : ''}`}>{@render signalIcon(latest.kind)}</span><span><strong>{latest.title}</strong><small>{getProfile(latest.companyId).name} · Simulated</small></span><ArrowUpRight /></button>{/if}
              <div class="map-legend"><span><i></i>Real company</span><span><i class="synthetic-dot"></i>Simulated signal</span></div>
              <div class="map-compass">N<span>↑</span></div>
            </div>
            <footer class="map-footer"><span>New Jersey, United States</span><span>Town-level locations</span></footer>
          </section>

          <aside class="activity-panel">
            <header class="activity-heading"><div><span class="eyebrow">THE LATEST</span><h2>Signal stream <span>{feed.length}</span></h2></div><span class:paused={!playing} class="live-pill"><i></i>{playing ? 'Simulating' : 'Paused'}</span></header>
            <p class="stream-note">Fictional filings, patents, and awards arrive at random intervals.</p>
            <div class="activity-list" aria-label="Simulated signal activity">
              {#each feed.slice(0, 20) as event (event.id)}
                {@const c = getProfile(event.companyId)}
                <button class="event-row" onclick={() => openCompany(c, event)} in:fly={{ y: -8, duration: 240 }}>
                  {@render logo(c)}<span class="event-copy"><span class="event-meta"><b class:patent={event.kind === 'Patent'}>{event.kind}</b><time>{age(event.timestamp)}</time></span><strong>{c.name}</strong><span class="event-title">{event.title}</span><span class="event-place"><MapPin />{c.town}<i>Simulated</i></span></span><ArrowUpRight class="event-arrow" />
                </button>
              {:else}<div class="empty-feed"><Radio /><strong>No matching activity</strong><p>{dataset === 'real' ? 'Real profiles have source links. The event simulator only creates fictional company activity.' : 'Adjust your filters or add a demo event.'}</p></div>{/each}
            </div>
            <div class="simulation-controls"><button onclick={() => playing = !playing} aria-label={playing ? 'Pause simulation' : 'Resume simulation'} title={playing ? 'Pause simulation' : 'Resume simulation'}>{#if playing}<Pause />{:else}<Play />{/if}</button><button onclick={reset} aria-label="Reset simulation" title="Reset simulation"><Rotate /></button><select bind:value={speed} aria-label="Simulation speed"><option value="normal">Natural pace</option><option value="fast">Fast pace</option></select><button class="add-event" onclick={addSignal} aria-label="Add simulated signal" title="Add a signal now"><Plus /></button></div>
          </aside>
        </div>
        <footer class="page-foot"><span><span class="tiny-dot"></span> {realCompanies.length} real company profiles · {activeIds.length} synthetic companies discovered</span><button onclick={() => navigate('sources')}>About the data <ArrowRight /></button></footer>
      {:else if view === 'companies' || view === 'saved'}
        <div class="directory-heading"><span>{filtered.length} companies</span><small>Company profiles · New Jersey</small></div>
        <div class="company-grid">
          {#each filtered as c}
            <article class="profile-card"><div class="profile-top">{@render logo(c, true)}<button class:saved={saved.includes(c.id)} class="save-button" onclick={() => toggleSaved(c.id)} aria-label={`${saved.includes(c.id) ? 'Unsave' : 'Save'} ${c.name}`}><Bookmark /></button></div><span class:real={c.real} class="profile-type">{c.real ? 'Real company' : 'Synthetic company'}</span><h2>{c.name}</h2><p>{c.description}</p><div class="profile-location"><MapPin />{c.town}<span>{c.sector}</span></div><button class="profile-open" onclick={() => openCompany(c)}>View company <ArrowUpRight /></button></article>
          {:else}<div class="empty-directory"><Bookmark /><h2>{view === 'saved' ? 'Make room for what’s next.' : 'No companies found.'}</h2><p>{view === 'saved' ? 'Save a company using its bookmark to build your shortlist.' : 'Try a different company, town, or sector.'}</p><button class="primary" onclick={() => { navigate('companies'); dataset = 'all'; }}>Explore companies <ArrowRight /></button></div>{/each}
        </div>
      {:else if view === 'programs'}
        <div class="program-intro"><Flask /><p>Start with the program, then verify the fit. Eligibility and availability must be checked with the program administrator.</p></div>
        <div class="program-grid">
          {#each [{ label: 'RESEARCH & DEVELOPMENT', name: 'SBIR / STTR support', org: 'CSIT', text: 'Explore support for New Jersey businesses participating in federal small-business research programs.', url: 'https://www.njeda.gov/csit/' }, { label: 'EARLY-STAGE INVESTMENT', name: 'Angel Investor Tax Credit', org: 'NJEDA', text: 'Review the tax credit program for qualifying investments in New Jersey technology businesses.', url: 'https://www.njeda.gov/angeltaxcredit/' }, { label: 'LIFE SCIENCES', name: 'Life Sciences & Healthcare Fund', org: 'NJEDA', text: 'A funding conversation for New Jersey life sciences and healthcare companies.', url: 'https://www.njeda.gov/' }] as program, index}
            <article class="program-card"><div class="program-logo">{program.org}<span>{String(index + 1).padStart(2, '0')}</span></div><small>{program.label}</small><h2>{program.name}</h2><p>{program.text}</p><a href={program.url} target="_blank" rel="noreferrer">Visit administrator <ArrowUpRight /></a></article>
          {/each}
        </div>
        <div class="program-note"><Check /><span>Company profiles keep unknown requirements visible. A source signal is a starting point for research.</span></div>
      {:else}
        <div class="source-grid">
          {#each [{ key: 'SEC', title: 'EDGAR filings', icon: 'SEC filing', desc: 'Search company disclosures and exempt offering notices in the SEC’s official database.', url: 'https://www.sec.gov/edgar/search/' }, { key: 'USPTO', title: 'Patents & applications', icon: 'Patent', desc: 'Search published patent applications and granted patents. Publication and grant are different events.', url: 'https://www.uspto.gov/patents/search/patent-public-search' }, { key: 'SBIR', title: 'Federal research awards', icon: 'Federal award', desc: 'Explore the official SBIR/STTR award database for research and development activity.', url: 'https://www.sbir.gov/awards' }] as item}
            <article class="source-card"><span class="source-monogram">{item.key}</span><div><h2>{item.title}</h2><p>{item.desc}</p><span class="source-status">Reference link · live ingestion not connected</span></div><a href={item.url} target="_blank" rel="noreferrer" aria-label={`Open ${item.title}`}><ArrowUpRight /></a></article>
          {/each}
        </div>
        <section class="data-explainer"><h2>A clear line between fact and demo.</h2><div><p><strong>Real company profiles</strong>Names, locations, and descriptions link to official company sources. Logos belong to their respective owners. Town-level markers are approximate.</p><p><strong>Simulated signal stream</strong>Every timed filing, patent, and award belongs to a fictional company. These events are created locally for the demo; they are not SEC or USPTO notifications.</p></div></section>
      {/if}
    </div>
  </main>

  {#if selected}
    <div class="drawer-backdrop" role="presentation" onclick={(e) => { if (e.target === e.currentTarget) selected = null; }}>
      <section class="company-drawer" role="dialog" aria-modal="true" aria-label={`${selected.name} company details`} tabindex="-1" transition:fly={{ x: 30, duration: 180 }}>
        <header class="drawer-header"><span>{selected.real ? 'Company profile' : 'Synthetic company profile'}</span><button class="icon-button" onclick={() => selected = null} aria-label="Close company details"><X /></button></header>
        <div class="drawer-body"><div class="drawer-brand">{@render logo(selected, true)}<button class:saved={saved.includes(selected.id)} class="save-button" onclick={() => toggleSaved(selected!.id)} aria-label={`${saved.includes(selected.id) ? 'Unsave' : 'Save'} ${selected.name}`}><Bookmark /></button></div><span class:real={selected.real} class="profile-type">{selected.real ? 'Real company' : 'Synthetic demo'}</span><h2>{selected.name}</h2><div class="drawer-location"><MapPin />{selected.town}, New Jersey<span>·</span>{selected.sector}</div><p class="drawer-description">{selected.description}</p>
          {#if selected.real}<a class="primary" href={selected.sourceUrl || selected.website} target="_blank" rel="noreferrer">View official source <ArrowUpRight /></a><div class="fact-note"><Check /><p>This profile references a real company. No simulated funding, patent, or award claims are attached to it.</p></div>
          {:else}
            {#if selectedEvent}<div class="selected-event"><span class="eyebrow">SIMULATED · {selectedEvent.kind.toUpperCase()}</span><h3>{selectedEvent.title}</h3><p>{selectedEvent.summary}</p><time>{new Date(selectedEvent.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} · demo event time</time></div>{/if}
            <section class="drawer-section"><h3>Demo evidence</h3>{#each selected.synthetic?.evidence ?? [] as item}<div class="evidence-row"><FileText /><p>{item}</p></div>{/each}</section>
            <section class="drawer-section"><h3>Questions for the first call</h3>{#each selected.synthetic?.unknowns ?? [] as item}<p class="question-row">{item}</p>{/each}</section>
            <section class="drawer-section"><h3>Recent simulated activity <span>{selectedSignals.length}</span></h3>{#each selectedSignals.slice(0, 5) as event}<button class="drawer-event" onclick={() => selectedEvent = event}>{@render signalIcon(event.kind)}<span>{event.title}<small>{age(event.timestamp)} · simulated</small></span><ArrowRight /></button>{:else}<p class="muted">Waiting for this company’s first simulated event.</p>{/each}</section>
          {/if}
        </div>
      </section>
    </div>
  {/if}
</section>
