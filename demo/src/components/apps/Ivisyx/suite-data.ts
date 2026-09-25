/**
 * Demo data for the Ivisyx venture suite. Every firm preset, deal, portfolio
 * company, fund figure and teammate here is fictional. Real companies live in
 * `real-companies.ts` and never receive simulated deal or portfolio data.
 */

export type Sector =
	| 'AI & software'
	| 'Climate'
	| 'Life sciences'
	| 'Health'
	| 'Fintech'
	| 'Deep tech'
	| 'Industrial'
	| 'Consumer';

export type Stage = 'Pre-seed' | 'Seed' | 'Series A' | 'Series B+';

export type PipelineStage = 'Sourced' | 'First meeting' | 'Diligence' | 'IC review' | 'Term sheet' | 'Closed';

export const sectors: Sector[] = ['AI & software', 'Climate', 'Life sciences', 'Health', 'Fintech', 'Deep tech', 'Industrial', 'Consumer'];
export const stages: Stage[] = ['Pre-seed', 'Seed', 'Series A', 'Series B+'];
export const pipelineStages: PipelineStage[] = ['Sourced', 'First meeting', 'Diligence', 'IC review', 'Term sheet', 'Closed'];

export type FirmProfile = {
	id: string;
	name: string;
	initials: string;
	thesis: string;
	sectors: Sector[];
	stages: Stage[];
	check: string;
	geography: 'New Jersey' | 'US East Coast' | 'North America' | 'Global';
	fund: string;
	fundSize: number;
	vintage: number;
	accent: string;
	example?: boolean;
};

export const firmPresets: FirmProfile[] = [
	{
		id: '59', name: '59 Capital', initials: '59', thesis: 'Pre-seed and seed technology companies building in New Jersey.',
		sectors: ['Deep tech', 'Life sciences', 'Climate', 'AI & software'], stages: ['Pre-seed', 'Seed'], check: '$250K–$1.5M',
		geography: 'New Jersey', fund: 'Fund I', fundSize: 50, vintage: 2024, accent: '#1d6751',
	},
	{
		id: 'lanternfish', name: 'Lanternfish Ventures', initials: 'LV', thesis: 'Seed-stage software and fintech teams with early revenue.',
		sectors: ['AI & software', 'Fintech', 'Consumer', 'Health'], stages: ['Seed', 'Series A'], check: '$1M–$4M',
		geography: 'US East Coast', fund: 'Fund II', fundSize: 180, vintage: 2023, accent: '#2b5f9e', example: true,
	},
	{
		id: 'saltmarsh', name: 'Saltmarsh Climate Fund', initials: 'SC', thesis: 'Hardware and software that decarbonise heavy industry.',
		sectors: ['Climate', 'Industrial', 'Deep tech'], stages: ['Seed', 'Series A'], check: '$2M–$8M',
		geography: 'North America', fund: 'Fund I', fundSize: 240, vintage: 2025, accent: '#1f7a73', example: true,
	},
	{
		id: 'quillwort', name: 'Quillwort Bio Partners', initials: 'QB', thesis: 'Platform biology and clinical-stage health companies.',
		sectors: ['Life sciences', 'Health'], stages: ['Series A', 'Series B+'], check: '$5M–$15M',
		geography: 'Global', fund: 'Fund III', fundSize: 420, vintage: 2022, accent: '#6a4fa3', example: true,
	},
];

export const accentChoices = ['#1d6751', '#1f7a73', '#2b5f9e', '#6a4fa3', '#a8671f', '#9b3d4f'];

export type Teammate = { id: string; name: string; initials: string; role: string; color: string };

export const team: Teammate[] = [
	{ id: 'al', name: 'Avery Lin', initials: 'AL', role: 'Managing partner', color: '#1d6751' },
	{ id: 'jm', name: 'Jordan Mehta', initials: 'JM', role: 'Partner', color: '#a8671f' },
	{ id: 'ro', name: 'Riley Okafor', initials: 'RO', role: 'Principal', color: '#6a4fa3' },
	{ id: 'sc', name: 'Sam Castillo', initials: 'SC', role: 'Associate', color: '#2b5f9e' },
];

export type Deal = {
	id: string;
	name: string;
	sector: Sector;
	category: string;
	stage: Stage;
	city: string;
	state: string;
	oneLiner: string;
	raise: number;
	valuation: number;
	pipeline: PipelineStage;
	owner: string;
	daysInStage: number;
	momentum: number;
	headcount: number;
	growth: string;
	signals: string[];
	nextStep: string;
	hue: number;
};

const deal = (d: Deal) => d;

export const deals: Deal[] = [
	deal({ id: 'aster', name: 'Aster BioSystems', sector: 'Life sciences', category: 'Tools', stage: 'Seed', city: 'Princeton', state: 'NJ', oneLiner: 'Lab automation that shortens cell-therapy quality checks.', raise: 4.5, valuation: 22, pipeline: 'IC review', owner: 'al', daysInStage: 3, momentum: 88, headcount: 14, growth: '+3 pilots', signals: ['SBIR Phase II', 'Form D', 'Hiring'], nextStep: 'IC vote Thursday', hue: 150 }),
	deal({ id: 'lucent', name: 'Lucent Grid Works', sector: 'Climate', category: 'Grid & storage', stage: 'Seed', city: 'Newark', state: 'NJ', oneLiner: 'Grid-edge sensing for aging urban electrical infrastructure.', raise: 3.2, valuation: 16, pipeline: 'Diligence', owner: 'jm', daysInStage: 9, momentum: 81, headcount: 11, growth: '+2 utilities', signals: ['DOE SBIR', 'Form D'], nextStep: 'Utility reference calls', hue: 42 }),
	deal({ id: 'harbor', name: 'Harbor Robotics', sector: 'Industrial', category: 'Robotics', stage: 'Pre-seed', city: 'Camden', state: 'NJ', oneLiner: 'Compact inspection robots for municipal water systems.', raise: 1.1, valuation: 7, pipeline: 'First meeting', owner: 'ro', daysInStage: 2, momentum: 64, headcount: 5, growth: '1 paid pilot', signals: ['Form D', 'Trademark'], nextStep: 'Founder meeting Monday', hue: 205 }),
	deal({ id: 'delta', name: 'Delta Neuro Devices', sector: 'Health', category: 'Devices', stage: 'Series A', city: 'New Brunswick', state: 'NJ', oneLiner: 'Wearable neuromodulation hardware for outpatient rehabilitation.', raise: 12, valuation: 58, pipeline: 'Term sheet', owner: 'al', daysInStage: 5, momentum: 92, headcount: 31, growth: '+41% QoQ', signals: ['NIH SBIR II', 'Patent', 'Form D'], nextStep: 'Confirmatory diligence', hue: 268 }),
	deal({ id: 'mosaic', name: 'Mosaic Quantum Materials', sector: 'Deep tech', category: 'Photonics', stage: 'Seed', city: 'Hoboken', state: 'NJ', oneLiner: 'Low-temperature materials for compact photonic systems.', raise: 3.8, valuation: 19, pipeline: 'Closed', owner: 'jm', daysInStage: 21, momentum: 76, headcount: 9, growth: '2 JDAs', signals: ['NSF SBIR', 'Patent'], nextStep: 'Board onboarding', hue: 190 }),
	deal({ id: 'common', name: 'Common Thread Health', sector: 'Health', category: 'Digital health', stage: 'Seed', city: 'Jersey City', state: 'NJ', oneLiner: 'Care-navigation tools for multilingual community clinics.', raise: 2.4, valuation: 12, pipeline: 'Sourced', owner: 'sc', daysInStage: 1, momentum: 58, headcount: 8, growth: '+11 clinics', signals: ['Form D', 'Trademarks'], nextStep: 'Request deck', hue: 340 }),
	deal({ id: 'kinetic', name: 'Kinetic Capture', sector: 'AI & software', category: 'Vertical AI', stage: 'Pre-seed', city: 'Montclair', state: 'NJ', oneLiner: 'Workflow software for physical production teams.', raise: 0.8, valuation: 6, pipeline: 'Sourced', owner: 'sc', daysInStage: 4, momentum: 47, headcount: 4, growth: '6 design partners', signals: ['New Form D'], nextStep: 'Warm intro via LP', hue: 25 }),
	deal({ id: 'silk', name: 'Silk City Circular', sector: 'Climate', category: 'Materials', stage: 'Seed', city: 'Paterson', state: 'NJ', oneLiner: 'Textile recovery hardware for regional manufacturers.', raise: 2.1, valuation: 11, pipeline: 'First meeting', owner: 'ro', daysInStage: 6, momentum: 69, headcount: 7, growth: '3 LOIs', signals: ['EPA SBIR'], nextStep: 'Site visit', hue: 95 }),
	deal({ id: 'forge', name: 'Forge Vision', sector: 'Industrial', category: 'Manufacturing', stage: 'Seed', city: 'Trenton', state: 'NJ', oneLiner: 'Visual inspection software for precision manufacturers.', raise: 3, valuation: 15, pipeline: 'Diligence', owner: 'jm', daysInStage: 12, momentum: 73, headcount: 12, growth: '+28% QoQ', signals: ['DOD SBIR', 'Form D'], nextStep: 'Customer calls', hue: 12 }),
	deal({ id: 'quarry', name: 'Quarry Labs', sector: 'AI & software', category: 'Dev tools', stage: 'Seed', city: 'Hoboken', state: 'NJ', oneLiner: 'Agentic QA that writes and maintains end-to-end tests.', raise: 4, valuation: 24, pipeline: 'Diligence', owner: 'al', daysInStage: 7, momentum: 90, headcount: 10, growth: '+22% MoM', signals: ['Hiring +60%', 'Repeat founder'], nextStep: 'Technical deep dive', hue: 222 }),
	deal({ id: 'ledgerline', name: 'Ledgerline', sector: 'Fintech', category: 'Treasury', stage: 'Series A', city: 'New York', state: 'NY', oneLiner: 'Treasury automation for mid-market finance teams.', raise: 14, valuation: 70, pipeline: 'First meeting', owner: 'jm', daysInStage: 3, momentum: 83, headcount: 34, growth: '$2.1M ARR', signals: ['Form D', 'Hiring'], nextStep: 'Partner meeting', hue: 160 }),
	deal({ id: 'tern', name: 'Tern Health', sector: 'Health', category: 'Care delivery', stage: 'Seed', city: 'Philadelphia', state: 'PA', oneLiner: 'Remote cardiac rehab with clinician-in-the-loop coaching.', raise: 3.5, valuation: 18, pipeline: 'IC review', owner: 'ro', daysInStage: 4, momentum: 79, headcount: 16, growth: '+9 health systems', signals: ['NIH SBIR', 'Trademark'], nextStep: 'IC memo final', hue: 355 }),
	deal({ id: 'brine', name: 'Brineworks', sector: 'Climate', category: 'Water', stage: 'Series A', city: 'Newark', state: 'NJ', oneLiner: 'Modular desalination powered by industrial waste heat.', raise: 11, valuation: 52, pipeline: 'Sourced', owner: 'sc', daysInStage: 2, momentum: 71, headcount: 22, growth: '2 plants live', signals: ['DOE award', 'Form D'], nextStep: 'Intro from co-investor', hue: 196 }),
	deal({ id: 'halcyon', name: 'Halcyon Bio', sector: 'Life sciences', category: 'Discovery', stage: 'Series A', city: 'Cambridge', state: 'MA', oneLiner: 'Programmable antibody discovery on a microfluidic platform.', raise: 18, valuation: 95, pipeline: 'Diligence', owner: 'al', daysInStage: 15, momentum: 86, headcount: 29, growth: '2 pharma partners', signals: ['Patent', 'Form D'], nextStep: 'Scientific advisor review', hue: 280 }),
	deal({ id: 'arbor', name: 'Arbor Freight OS', sector: 'Industrial', category: 'Logistics', stage: 'Seed', city: 'Edison', state: 'NJ', oneLiner: 'Dispatch software for regional freight carriers.', raise: 2.6, valuation: 14, pipeline: 'First meeting', owner: 'sc', daysInStage: 5, momentum: 61, headcount: 9, growth: '$640K ARR', signals: ['Form D'], nextStep: 'Pipeline review', hue: 30 }),
	deal({ id: 'petal', name: 'Petal & Pine', sector: 'Consumer', category: 'Home', stage: 'Seed', city: 'Brooklyn', state: 'NY', oneLiner: 'Refillable home-care products sold by subscription.', raise: 3, valuation: 17, pipeline: 'Sourced', owner: 'jm', daysInStage: 3, momentum: 55, headcount: 12, growth: '+14% MoM', signals: ['Trademarks'], nextStep: 'Cohort data request', hue: 330 }),
	deal({ id: 'vector', name: 'Vectorbound', sector: 'Deep tech', category: 'Space', stage: 'Pre-seed', city: 'Princeton', state: 'NJ', oneLiner: 'Radiation-hardened edge compute for small satellites.', raise: 1.5, valuation: 9, pipeline: 'First meeting', owner: 'al', daysInStage: 1, momentum: 77, headcount: 6, growth: '1 launch slot', signals: ['NASA SBIR', 'Patent'], nextStep: 'Technical call', hue: 240 }),
	deal({ id: 'clearwater', name: 'Clearwater Credit', sector: 'Fintech', category: 'Credit', stage: 'Seed', city: 'Jersey City', state: 'NJ', oneLiner: 'Credit-building accounts for newly arrived workers.', raise: 3.3, valuation: 16, pipeline: 'Diligence', owner: 'ro', daysInStage: 8, momentum: 72, headcount: 13, growth: '18K accounts', signals: ['Form D', 'Hiring'], nextStep: 'Compliance review', hue: 185 }),
	deal({ id: 'lumen', name: 'Lumenfold', sector: 'AI & software', category: 'Vertical AI', stage: 'Series A', city: 'New York', state: 'NY', oneLiner: 'Document intelligence for insurance claims teams.', raise: 16, valuation: 80, pipeline: 'Term sheet', owner: 'jm', daysInStage: 2, momentum: 89, headcount: 41, growth: '$3.4M ARR', signals: ['Form D', 'Hiring +40%'], nextStep: 'Negotiate pro rata', hue: 48 }),
	deal({ id: 'corvid', name: 'Corvid Security', sector: 'AI & software', category: 'Security', stage: 'Seed', city: 'Newark', state: 'NJ', oneLiner: 'Autonomous threat hunting for hospital networks.', raise: 3.6, valuation: 20, pipeline: 'Sourced', owner: 'sc', daysInStage: 1, momentum: 80, headcount: 8, growth: '4 hospital pilots', signals: ['Repeat founder'], nextStep: 'Screen call', hue: 0 }),
	deal({ id: 'gridmint', name: 'Gridmint', sector: 'Climate', category: 'Grid & storage', stage: 'Seed', city: 'Trenton', state: 'NJ', oneLiner: 'Turns commercial HVAC into grid flexibility.', raise: 2.8, valuation: 13, pipeline: 'Closed', owner: 'ro', daysInStage: 34, momentum: 68, headcount: 10, growth: '31 MW enrolled', signals: ['State grant'], nextStep: 'Quarterly check-in', hue: 120 }),
	deal({ id: 'wrenfield', name: 'Wrenfield Bio', sector: 'Life sciences', category: 'Therapeutics', stage: 'Series B+', city: 'Boston', state: 'MA', oneLiner: 'Oral peptide therapeutics for metabolic disease.', raise: 38, valuation: 210, pipeline: 'Sourced', owner: 'al', daysInStage: 6, momentum: 74, headcount: 52, growth: 'Phase 1 readout', signals: ['Form D', 'Patent'], nextStep: 'Data room access', hue: 300 }),
	deal({ id: 'tollgate', name: 'Tollgate Robotics', sector: 'Industrial', category: 'Robotics', stage: 'Series A', city: 'Camden', state: 'NJ', oneLiner: 'Autonomous inspection for bridges and tunnels.', raise: 9, valuation: 44, pipeline: 'IC review', owner: 'jm', daysInStage: 2, momentum: 84, headcount: 27, growth: '4 DOT contracts', signals: ['DOT award', 'Form D'], nextStep: 'IC vote Thursday', hue: 210 }),
	deal({ id: 'emberline', name: 'Emberline Foods', sector: 'Consumer', category: 'Food', stage: 'Series A', city: 'Paterson', state: 'NJ', oneLiner: 'Shelf-stable meals made from upcycled produce.', raise: 8, valuation: 38, pipeline: 'First meeting', owner: 'sc', daysInStage: 4, momentum: 63, headcount: 24, growth: '1,100 doors', signals: ['Form D'], nextStep: 'Retail velocity data', hue: 18 }),
	deal({ id: 'kiteway', name: 'Kiteway Payments', sector: 'Fintech', category: 'Payments', stage: 'Pre-seed', city: 'Hoboken', state: 'NJ', oneLiner: 'Cross-border payroll for small manufacturers.', raise: 1.2, valuation: 8, pipeline: 'Sourced', owner: 'ro', daysInStage: 2, momentum: 66, headcount: 4, growth: '9 employers', signals: ['New Form D'], nextStep: 'Screen call', hue: 170 }),
	deal({ id: 'heliotrope', name: 'Heliotrope Materials', sector: 'Deep tech', category: 'Materials', stage: 'Seed', city: 'New Brunswick', state: 'NJ', oneLiner: 'Perovskite coatings that raise solar module yield.', raise: 4.2, valuation: 21, pipeline: 'Diligence', owner: 'al', daysInStage: 10, momentum: 82, headcount: 11, growth: '2 OEM pilots', signals: ['NSF SBIR', 'Patent'], nextStep: 'Lab visit', hue: 58 }),
];

export const marketCategories: Record<Sector, string[]> = {
	'AI & software': ['Dev tools', 'Security', 'Vertical AI', 'Data infra'],
	Climate: ['Grid & storage', 'Water', 'Materials', 'Carbon'],
	'Life sciences': ['Discovery', 'Tools', 'Therapeutics'],
	Health: ['Care delivery', 'Devices', 'Digital health'],
	Fintech: ['Payments', 'Credit', 'Treasury'],
	'Deep tech': ['Photonics', 'Space', 'Materials', 'Quantum'],
	Industrial: ['Robotics', 'Manufacturing', 'Logistics'],
	Consumer: ['Food', 'Home', 'Commerce'],
};

export type Health = 'Breakout' | 'On track' | 'Watch' | 'At risk';

export type PortfolioCompany = {
	id: string;
	name: string;
	sector: Sector;
	round: Stage;
	invested: string;
	check: number;
	ownership: number;
	fairValue: number;
	arr: number[];
	runway: number;
	health: Health;
	headcount: number;
	board: boolean;
	update: string;
	hue: number;
};

const arr = (start: number, growth: number, wobble = 0.03) =>
	Array.from({ length: 12 }, (_, i) => Math.round(start * (1 + growth) ** i * (1 + Math.sin(i * 1.7) * wobble)));

export const portfolio: PortfolioCompany[] = [
	{ id: 'copperleaf', name: 'Copperleaf Energy', sector: 'Climate', round: 'Seed', invested: 'Mar 2024', check: 2, ownership: 9.8, fairValue: 7.4, arr: arr(210, 0.11), runway: 26, health: 'Breakout', headcount: 23, board: true, update: 'Signed second utility contract; Series A process opens in Q1.', hue: 140 },
	{ id: 'stackwise', name: 'Stackwise', sector: 'AI & software', round: 'Seed', invested: 'Jun 2024', check: 1.5, ownership: 8.1, fairValue: 3.9, arr: arr(320, 0.08), runway: 19, health: 'On track', headcount: 17, board: false, update: 'Net revenue retention reached 131%.', hue: 220 },
	{ id: 'bramble', name: 'Bramble Health', sector: 'Health', round: 'Seed', invested: 'Sep 2024', check: 1.8, ownership: 10.5, fairValue: 1.9, arr: arr(90, 0.02, 0.05), runway: 7, health: 'At risk', headcount: 12, board: true, update: 'Bridge discussion underway; burn cut 18%.', hue: 350 },
	{ id: 'northgate', name: 'Northgate Robotics', sector: 'Industrial', round: 'Series A', invested: 'Jan 2024', check: 3.5, ownership: 7.2, fairValue: 6.1, arr: arr(640, 0.05), runway: 22, health: 'On track', headcount: 38, board: true, update: 'Two new warehouse deployments live.', hue: 30 },
	{ id: 'sablepay', name: 'Sable Pay', sector: 'Fintech', round: 'Seed', invested: 'Nov 2023', check: 2.2, ownership: 8.9, fairValue: 8.8, arr: arr(410, 0.1), runway: 31, health: 'Breakout', headcount: 29, board: true, update: 'Processing volume up 3.2× year over year.', hue: 175 },
	{ id: 'fernhill', name: 'Fernhill Genomics', sector: 'Life sciences', round: 'Series A', invested: 'Apr 2023', check: 4, ownership: 6.4, fairValue: 5.2, arr: arr(150, 0.04), runway: 15, health: 'Watch', headcount: 33, board: false, update: 'Pharma pilot extended; hiring VP Sales.', hue: 290 },
	{ id: 'quietharbor', name: 'Quiet Harbor', sector: 'Consumer', round: 'Seed', invested: 'Feb 2025', check: 1.2, ownership: 7.5, fairValue: 1.4, arr: arr(260, 0.06), runway: 17, health: 'On track', headcount: 14, board: false, update: 'Wholesale launch with 140 retailers.', hue: 250 },
	{ id: 'parcelloop', name: 'Parcel Loop', sector: 'Industrial', round: 'Pre-seed', invested: 'May 2025', check: 0.8, ownership: 11.2, fairValue: 0.9, arr: arr(40, 0.12), runway: 12, health: 'Watch', headcount: 6, board: false, update: 'Pilot with regional 3PL converting to paid.', hue: 45 },
	{ id: 'ridgeline', name: 'Ridgeline AI', sector: 'AI & software', round: 'Series A', invested: 'Aug 2023', check: 5, ownership: 6.8, fairValue: 14.6, arr: arr(1150, 0.07), runway: 34, health: 'Breakout', headcount: 61, board: true, update: 'Pre-empted Series B term sheet at 3.1× step-up.', hue: 200 },
	{ id: 'waveform', name: 'Waveform Bio', sector: 'Life sciences', round: 'Seed', invested: 'Oct 2024', check: 2.5, ownership: 9.1, fairValue: 2.7, arr: arr(60, 0.05, 0.08), runway: 20, health: 'On track', headcount: 15, board: true, update: 'Lead program cleared IND-enabling milestone.', hue: 310 },
	{ id: 'tallow', name: 'Tallow Materials', sector: 'Deep tech', round: 'Seed', invested: 'Jul 2024', check: 1.6, ownership: 8.4, fairValue: 2.4, arr: arr(70, 0.09), runway: 16, health: 'On track', headcount: 11, board: false, update: 'First production run shipped to OEM partner.', hue: 60 },
	{ id: 'kindred', name: 'Kindred Clinics', sector: 'Health', round: 'Series A', invested: 'Dec 2023', check: 3, ownership: 5.9, fairValue: 3.1, arr: arr(880, 0.03), runway: 11, health: 'Watch', headcount: 47, board: false, update: 'Two clinics consolidated to improve margins.', hue: 10 },
];

export const dealFlowWeeks = ['Jul 7', 'Jul 14', 'Jul 21', 'Jul 28', 'Aug 4', 'Aug 11', 'Aug 18', 'Aug 25', 'Sep 1', 'Sep 8', 'Sep 15', 'Sep 22'];
export const dealFlowSourced = [38, 42, 35, 51, 47, 58, 62, 55, 71, 68, 79, 84];
export const dealFlowAdvanced = [6, 8, 5, 9, 8, 11, 12, 10, 14, 13, 16, 18];

/** Net cumulative cash flow to LPs as a share of commitments, by quarter since first close. */
export const jCurve = [-3, -8, -14, -19, -23, -25, -24, -21, -15, -8, 1, 9];
export const tvpiSeries = [0.96, 0.94, 0.97, 1.05, 1.12, 1.18, 1.27, 1.39, 1.48, 1.61, 1.74, 1.86];

const stageIndex = (stage: Stage) => stages.indexOf(stage);

const eastCoast = ['NJ', 'NY', 'PA', 'MA', 'CT', 'MD', 'DE', 'VA', 'DC'];
function geographyFit(geography: FirmProfile['geography'], state: string) {
	if (geography === 'New Jersey') return state === 'NJ' ? 1 : eastCoast.includes(state) ? 0.45 : 0.1;
	if (geography === 'US East Coast') return eastCoast.includes(state) ? 1 : 0.4;
	return 1;
}

export type FitBreakdown = { total: number; thesis: number; stage: number; geography: number; momentum: number };
type FitInput = { sector: Sector; stage: Stage | null; state: string; momentum: number };

/** Thesis fit out of 100, re-weighted for whichever firm profile is active. */
export function fitFor(d: FitInput, firm: FirmProfile): FitBreakdown {
	const thesis = firm.sectors.includes(d.sector) ? 34 : 8;
	const gap = d.stage ? Math.min(...firm.stages.map((s) => Math.abs(stageIndex(s) - stageIndex(d.stage)))) : 3;
	const stage = gap === 0 ? 26 : gap === 1 ? 12 : 3;
	const geography = Math.round(14 * geographyFit(firm.geography, d.state));
	const momentum = Math.round(d.momentum * 0.26);
	return { total: Math.max(12, Math.min(98, thesis + stage + geography + momentum)), thesis, stage, geography, momentum };
}

export function portfolioFor(firm: FirmProfile) {
	const scale = firm.fundSize / 100;
	const inThesis = portfolio.filter((p) => firm.sectors.includes(p.sector));
	const list = inThesis.length >= 5 ? inThesis : portfolio;
	return list.map((p) => ({ ...p, check: +(p.check * scale).toFixed(2), fairValue: +(p.fairValue * scale).toFixed(2) }));
}

export function fundFor(firm: FirmProfile) {
	const seed = [...firm.id].reduce((sum, ch) => sum + ch.charCodeAt(0), 0) % 7;
	const called = firm.fundSize * (0.58 + seed * 0.02);
	const tvpi = 1.74 + seed * 0.04;
	const dpi = 0.22 + seed * 0.03;
	return {
		committed: firm.fundSize,
		called,
		distributed: called * dpi,
		nav: called * (tvpi - dpi),
		tvpi,
		dpi,
		rvpi: tvpi - dpi,
		irr: 21.4 + seed * 1.3,
		reserves: firm.fundSize * 0.31,
		tvpiSeries: tvpiSeries.map((v) => +(v * (tvpi / 1.86)).toFixed(2)),
	};
}

export function money(millions: number) {
	if (millions >= 1000) return `$${(millions / 1000).toFixed(1)}B`;
	if (millions >= 10) return `$${Math.round(millions)}M`;
	if (millions >= 1) return `$${millions.toFixed(1)}M`;
	return `$${Math.round(millions * 1000)}K`;
}
