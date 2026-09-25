import { companies as legacyCompanies } from './gauge-data';
import { towns } from './geo';
import { realCompanies } from './real-companies';
import { deals, type Deal, type Sector, type Stage } from './suite-data';

/** One company as the UI sees it. `real` profiles never carry simulated metrics. */
export type Entity = {
	id: string;
	name: string;
	real: boolean;
	town: string;
	townId: string | null;
	county: string;
	state: string;
	sector: Sector;
	stage: Stage | null;
	description: string;
	hue: number;
	logo?: string;
	coordinates: [number, number] | null;
	raise?: number;
	founded?: number;
	headcount?: number;
	momentum: number;
	signals: string[];
	website?: string;
	sourceUrl?: string;
	companyType?: string;
	deal?: Deal;
	evidence?: string[];
	unknowns?: string[];
};

const townByName = new Map(towns.map((t) => [t.name, t]));
const legacy = new Map(legacyCompanies.map((c) => [c.id, c]));
const legacyLogos = new Set(['aster', 'lucent', 'harbor', 'delta', 'mosaic', 'common']);

const realSector: Record<string, Sector> = {
	polygone: 'Climate', pcm: 'Deep tech', renewco2: 'Climate', oishii: 'Consumer', pne: 'Climate', coreweave: 'AI & software',
};

const real: Entity[] = realCompanies.map((c, i) => {
	const town = townByName.get(c.town);
	return {
		id: c.id, name: c.name, real: true, town: c.town, townId: town?.id ?? null, county: town?.county ?? '', state: 'NJ',
		sector: realSector[c.id] ?? 'Deep tech', stage: null, description: c.description, hue: 160, logo: c.logo,
		// Nudge off the town node so both stay clickable.
		coordinates: [c.coordinates[0] + Math.cos(i * 2.1) * 0.009, c.coordinates[1] + Math.sin(i * 2.1) * 0.007], momentum: 0, signals: [], website: c.website, sourceUrl: c.sourceUrl, companyType: c.companyType,
	};
});

const dealEntities: Entity[] = deals.map((d, i) => {
	const town = d.state === 'NJ' ? townByName.get(d.city) : undefined;
	const offset = 0.008 + (i % 3) * 0.004;
	const old = legacy.get(d.id);
	return {
		id: d.id, name: d.name, real: false, town: d.city, townId: town?.id ?? null, county: town?.county ?? '', state: d.state,
		sector: d.sector, stage: d.stage, description: d.oneLiner, hue: d.hue, logo: legacyLogos.has(d.id) ? `/brands/${d.id}.svg` : undefined,
		coordinates: town ? [town.coordinates[0] + Math.cos(i) * offset, town.coordinates[1] + Math.sin(i) * offset * 0.8] : null,
		raise: d.raise, headcount: d.headcount, founded: 2019 + (i % 6), momentum: d.momentum, signals: d.signals, deal: d,
		evidence: old?.evidence, unknowns: old?.unknowns,
	};
});

const generated: Entity[] = towns.flatMap((t) =>
	t.companies.map((c) => ({
		id: c.id, name: c.name, real: false, town: t.name, townId: t.id, county: t.county, state: 'NJ', sector: c.sector, stage: c.stage,
		description: c.description, hue: c.hue, coordinates: c.coordinates, raise: c.raise, founded: c.founded, headcount: c.headcount,
		momentum: c.momentum, signals: c.signals,
	})),
);

export const entities: Entity[] = [...real, ...dealEntities, ...generated];
export const entityById = new Map(entities.map((e) => [e.id, e]));
export const syntheticEntities = entities.filter((e) => !e.real);

export const entitiesByTown = new Map<string, Entity[]>();
for (const e of entities) {
	if (!e.townId) continue;
	const list = entitiesByTown.get(e.townId) ?? [];
	list.push(e);
	entitiesByTown.set(e.townId, list);
}
for (const list of entitiesByTown.values()) list.sort((a, b) => Number(b.real) - Number(a.real) || b.momentum - a.momentum);

export { towns };
