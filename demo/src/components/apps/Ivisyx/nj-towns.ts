/**
 * New Jersey municipalities with approximate town-centre coordinates, plus a
 * seeded generator that gives every town synthetic startups, signals and
 * metrics. Coordinates are for display only; nothing here is real company data.
 */
import type { Sector, Stage } from './suite-data';

/** [name, longitude, latitude, weight 1–10] */
const rawTowns: [string, number, number, number][] = [
	['Newark', -74.1724, 40.7357, 10], ['Jersey City', -74.0431, 40.7178, 10], ['Hoboken', -74.0324, 40.744, 9],
	['Princeton', -74.6672, 40.3573, 10], ['New Brunswick', -74.4518, 40.4862, 9], ['Camden', -75.1196, 39.9259, 7],
	['Trenton', -74.7429, 40.2171, 7], ['Paterson', -74.1718, 40.9168, 6], ['Elizabeth', -74.2107, 40.664, 6],
	['Edison', -74.4121, 40.5187, 8], ['Woodbridge', -74.2846, 40.5576, 6], ['Lakewood', -74.2097, 40.0821, 5],
	['Toms River', -74.1979, 39.9537, 5], ['Hamilton', -74.6797, 40.2115, 5], ['Clifton', -74.1638, 40.8584, 5],
	['Brick', -74.11, 40.06, 4], ['Cherry Hill', -75.0307, 39.9348, 7], ['Passaic', -74.1285, 40.8568, 4],
	['Union City', -74.0238, 40.7795, 4], ['Bayonne', -74.1143, 40.6687, 4], ['East Orange', -74.2049, 40.7673, 4],
	['Vineland', -75.026, 39.4864, 4], ['Perth Amboy', -74.2654, 40.5068, 3], ['West New York', -74.0143, 40.7879, 3],
	['Plainfield', -74.4074, 40.6337, 3], ['Hackensack', -74.0435, 40.8859, 6], ['Sayreville', -74.361, 40.4593, 3],
	['Kearny', -74.1454, 40.7684, 3], ['Linden', -74.2446, 40.622, 3], ['Atlantic City', -74.4229, 39.3643, 5],
	['Fort Lee', -73.9701, 40.8509, 5], ['Fair Lawn', -74.1318, 40.9404, 4], ['Garfield', -74.1132, 40.8815, 3],
	['Paramus', -74.0754, 40.9445, 5], ['Wayne', -74.2765, 40.9254, 5], ['Montclair', -74.209, 40.8259, 7],
	['Morristown', -74.4815, 40.7968, 8], ['Livingston', -74.3149, 40.7959, 6], ['Somerset', -74.4885, 40.4976, 6],
	['Piscataway', -74.4643, 40.5543, 7], ['Parsippany', -74.426, 40.8579, 7], ['Old Bridge', -74.3654, 40.4148, 3],
	['Bloomfield', -74.1854, 40.8068, 4], ['Nutley', -74.1599, 40.8223, 4], ['Belleville', -74.1502, 40.7937, 3],
	['Irvington', -74.2349, 40.7323, 3], ['Union', -74.2632, 40.6976, 4], ['Westfield', -74.3474, 40.659, 5],
	['Summit', -74.3643, 40.7157, 6], ['Millburn', -74.304, 40.7248, 5], ['Maplewood', -74.2735, 40.7312, 4],
	['South Orange', -74.2613, 40.749, 5], ['West Orange', -74.239, 40.7987, 5], ['Orange', -74.2326, 40.7707, 3],
	['Secaucus', -74.0565, 40.7895, 5], ['North Bergen', -74.0121, 40.8043, 4], ['Weehawken', -74.0204, 40.7695, 5],
	['Englewood', -73.9726, 40.8929, 5], ['Teaneck', -74.016, 40.8976, 5], ['Ridgewood', -74.1165, 40.9793, 5],
	['Mahwah', -74.1438, 41.0887, 5], ['Ramsey', -74.141, 41.0573, 3], ['Morris Plains', -74.481, 40.8218, 4],
	['Madison', -74.4171, 40.7598, 5], ['Chatham', -74.3838, 40.7409, 4], ['Dover', -74.5621, 40.8837, 3],
	['Sparta', -74.6388, 41.034, 3], ['Newton', -74.7527, 41.0582, 3], ['Hackettstown', -74.8291, 40.854, 3],
	['Phillipsburg', -75.1902, 40.6937, 3], ['Flemington', -74.8593, 40.5123, 4], ['Somerville', -74.6099, 40.5743, 4],
	['Bridgewater', -74.6049, 40.594, 6], ['Bernardsville', -74.5693, 40.7187, 3], ['Basking Ridge', -74.5493, 40.7062, 5],
	['Warren', -74.5007, 40.634, 5], ['Metuchen', -74.3632, 40.5432, 4], ['East Brunswick', -74.416, 40.4279, 4],
	['North Brunswick', -74.4818, 40.449, 4], ['South Brunswick', -74.531, 40.384, 5], ['Plainsboro', -74.5946, 40.3326, 6],
	['West Windsor', -74.6207, 40.2985, 5], ['Lawrenceville', -74.7296, 40.2973, 5], ['Ewing', -74.7996, 40.2698, 4],
	['Hopewell', -74.7621, 40.389, 4], ['Hightstown', -74.5232, 40.2695, 3], ['Freehold', -74.2738, 40.2601, 4],
	['Red Bank', -74.0643, 40.3471, 5], ['Long Branch', -73.9924, 40.3043, 4], ['Asbury Park', -74.0121, 40.2204, 5],
	['Middletown', -74.08, 40.39, 4], ['Holmdel', -74.1843, 40.3451, 6], ['Marlboro', -74.2463, 40.3154, 3],
	['Manalapan', -74.3432, 40.2807, 3], ['Howell', -74.204, 40.1782, 3], ['Wall', -74.0921, 40.1682, 3],
	['Point Pleasant', -74.0682, 40.0832, 3], ['Seaside Heights', -74.0729, 39.9443, 2], ['Ship Bottom', -74.1804, 39.6432, 2],
	['Tuckerton', -74.3401, 39.6032, 2], ['Manahawkin', -74.2587, 39.6951, 2], ['Ocean City', -74.5746, 39.2776, 3],
	['Cape May', -74.906, 38.9351, 3], ['Wildwood', -74.8149, 38.9918, 2], ['Millville', -75.0393, 39.4021, 3],
	['Bridgeton', -75.2341, 39.4273, 3], ['Salem', -75.4671, 39.5718, 2], ['Glassboro', -75.1118, 39.7029, 5],
	['Pennsville', -75.5166, 39.6537, 2], ['Woodbury', -75.1527, 39.8382, 3], ['Deptford', -75.118, 39.839, 3],
	['Voorhees', -74.961, 39.844, 4], ['Haddonfield', -75.0377, 39.8915, 4], ['Collingswood', -75.0713, 39.9182, 4],
	['Pennsauken', -75.058, 39.9562, 3], ['Moorestown', -74.9488, 39.9689, 5], ['Mount Laurel', -74.891, 39.934, 5],
	['Marlton', -74.9218, 39.8912, 4], ['Willingboro', -74.8693, 40.0276, 3], ['Burlington', -74.8649, 40.0712, 3],
	['Bordentown', -74.7118, 40.1462, 3], ['Medford', -74.8235, 39.9009, 3], ['Hammonton', -74.8024, 39.6365, 3],
	['Egg Harbor', -74.58, 39.41, 4], ['Pleasantville', -74.524, 39.3898, 2], ['Mays Landing', -74.7277, 39.4523, 2],
	['Galloway', -74.48, 39.47, 3], ['Absecon', -74.4957, 39.4284, 2], ['Brigantine', -74.3646, 39.4101, 2],
	['Somers Point', -74.5946, 39.3176, 2], ['Jackson', -74.36, 40.1, 3], ['Manchester', -74.36, 39.99, 2],
	['Forked River', -74.1907, 39.8398, 2], ['Barnegat', -74.2229, 39.7532, 2], ['Rahway', -74.2776, 40.6082, 3],
	['Cranford', -74.2996, 40.6584, 4], ['Kenilworth', -74.2907, 40.6765, 4], ['Scotch Plains', -74.3899, 40.6554, 3],
	['Berkeley Heights', -74.4413, 40.6834, 5], ['New Providence', -74.4015, 40.6984, 5], ['Hillsborough', -74.626, 40.4776, 4],
	['Skillman', -74.6788, 40.4262, 4], ['Rocky Hill', -74.6399, 40.3998, 3], ['Cranbury', -74.5138, 40.3162, 4],
	['Monroe', -74.43, 40.32, 3], ['Jamesburg', -74.4402, 40.3526, 2], ['Carteret', -74.2282, 40.5773, 3],
	['Rutherford', -74.1068, 40.8265, 4], ['Lyndhurst', -74.1243, 40.812, 3], ['Little Falls', -74.2086, 40.869, 3],
	['Totowa', -74.2098, 40.9051, 3], ['Wanaque', -74.294, 41.0382, 2], ['West Milford', -74.3674, 41.131, 2],
	['Vernon', -74.4838, 41.1984, 2], ['Franklin Lakes', -74.2057, 41.0168, 3], ['Oakland', -74.2643, 41.0131, 2],
	['Pompton Lakes', -74.2907, 41.0054, 2], ['Butler', -74.3421, 40.9998, 2], ['Kinnelon', -74.3671, 40.9829, 2],
	['Boonton', -74.4071, 40.9026, 3], ['Denville', -74.4874, 40.8923, 3], ['Rockaway', -74.5143, 40.9012, 3],
	['Randolph', -74.5746, 40.8484, 3], ['Mendham', -74.6007, 40.7759, 2], ['Chester', -74.6968, 40.7843, 2],
	['Budd Lake', -74.7341, 40.8712, 2], ['Succasunna', -74.6404, 40.8687, 2], ['Hopatcong', -74.6594, 40.9329, 2],
	['Blairstown', -74.9571, 40.9829, 2], ['Belvidere', -75.0777, 40.8298, 2], ['Washington', -74.9793, 40.7587, 2],
	['Clinton', -74.9099, 40.6368, 2], ['Lambertville', -74.9429, 40.3659, 3], ['Frenchtown', -75.0616, 40.5262, 2],
	['High Bridge', -74.8957, 40.667, 2], ['Raritan', -74.6329, 40.5695, 3], ['Bound Brook', -74.5385, 40.5684, 3],
	['Manville', -74.5877, 40.5409, 2], ['Hillside', -74.2301, 40.7012, 3], ['Roselle', -74.2632, 40.6645, 2],
	['Clark', -74.311, 40.6409, 3], ['Keansburg', -74.1301, 40.4418, 2], ['Matawan', -74.2296, 40.4148, 3],
	['Keyport', -74.1999, 40.4332, 2], ['Hazlet', -74.1719, 40.4251, 2], ['Rumson', -74.0015, 40.3721, 3],
	['Fair Haven', -74.0382, 40.3604, 2], ['Eatontown', -74.051, 40.2962, 4], ['Neptune', -74.0271, 40.2004, 3],
	['Belmar', -74.0218, 40.1784, 2], ['Spring Lake', -74.0282, 40.1532, 2], ['Manasquan', -74.0493, 40.1262, 2],
	['Beach Haven', -74.2432, 39.5593, 2], ['Lavallette', -74.069, 39.9701, 2], ['Stanhope', -74.7093, 40.9029, 2],
	['Andover', -74.7418, 40.9859, 2], ['Milford', -75.0946, 40.5687, 2], ['Garwood', -74.3229, 40.6515, 2],
	['Aberdeen', -74.2224, 40.4165, 2], ['Sea Bright', -73.9743, 40.3615, 2], ['Island Heights', -74.1499, 39.9429, 2],
	['Harrison', -74.1563, 40.7465, 4], ['Ridgefield Park', -74.0215, 40.8568, 3], ['Tenafly', -73.9629, 40.9254, 4],
	['Closter', -73.9615, 40.973, 3], ['Westwood', -74.0326, 40.9912, 3], ['Park Ridge', -74.0404, 41.0376, 3],
	['Fairfield', -74.3054, 40.8837, 4], ['Caldwell', -74.2765, 40.8398, 3], ['Verona', -74.2401, 40.8298, 3],
	['Cedar Grove', -74.2285, 40.8515, 2], ['Florham Park', -74.3882, 40.7879, 5], ['East Hanover', -74.3649, 40.8201, 4],
	['Whippany', -74.4174, 40.8248, 4], ['Branchburg', -74.7024, 40.5626, 3], ['Readington', -74.7371, 40.5687, 2],
	['Pennington', -74.7907, 40.3284, 3], ['Robbinsville', -74.5935, 40.2146, 3], ['Maple Shade', -74.9924, 39.9526, 3],
	['Sewell', -75.1427, 39.7659, 3], ['Swedesboro', -75.3102, 39.7476, 3], ['Mullica Hill', -75.2241, 39.7393, 2],
];

export type TownCompany = {
	id: string;
	name: string;
	sector: Sector;
	stage: Stage;
	description: string;
	raise: number;
	founded: number;
	headcount: number;
	momentum: number;
	signals: string[];
	hue: number;
	coordinates: [number, number];
};

export type Town = {
	id: string;
	name: string;
	coordinates: [number, number];
	weight: number;
	county: string;
	startups: number;
	signals30d: number;
	raised: number;
	jobs: number;
	momentum: number;
	trend: number[];
	sectorMix: [Sector, number][];
	companies: TownCompany[];
};

export function hash(text: string) {
	let h = 2166136261;
	for (let i = 0; i < text.length; i++) h = Math.imul(h ^ text.charCodeAt(i), 16777619);
	return h >>> 0;
}

export function seeded(seed: number) {
	let a = seed || 1;
	return () => {
		a = (a + 0x6d2b79f5) | 0;
		let t = Math.imul(a ^ (a >>> 15), 1 | a);
		t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
		return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
	};
}

const prefixes = ['Arc', 'Blue', 'Cedar', 'Delta', 'Echo', 'Fern', 'Granite', 'Harbor', 'Iron', 'Juniper', 'Kite', 'Lumen', 'Maple', 'North', 'Onyx', 'Pine', 'Quartz', 'River', 'Salt', 'Tide', 'Vale', 'Willow', 'Zephyr', 'Beacon', 'Copper', 'Drift', 'Ember', 'Flint', 'Grove', 'Halo', 'Indigo', 'Lark', 'Meadow', 'Nova', 'Orbit', 'Prism', 'Ridge', 'Sparrow', 'Terra', 'Atlas', 'Birch', 'Cobalt', 'Dune', 'Fable', 'Glint', 'Heron', 'Kestrel', 'Lattice', 'Mica', 'Nimbus', 'Opal', 'Pylon', 'Quill', 'Rune', 'Sable', 'Tern', 'Umbra', 'Verdant', 'Wren', 'Yarrow'];
const roots = ['wise', 'loop', 'forge', 'grid', 'mint', 'works', 'scale', 'signal', 'path', 'stack', 'shift', 'lane', 'field', 'wave', 'point', 'line', 'craft', 'bloom', 'core', 'light', 'gate', 'spring', 'lab', 'mark'];

const sectorFlavor: Record<Sector, { suffix: string[]; lines: string[]; categories: string[] }> = {
	'AI & software': { suffix: [' AI', ' Labs', '', ' Systems'], lines: ['Agentic workflows for {x} teams.', 'Copilots that automate {x} back-office work.', 'Observability for AI systems in {x}.', 'Secure data infrastructure for {x}.'], categories: ['insurance', 'logistics', 'healthcare', 'public-sector', 'manufacturing', 'legal'] },
	Climate: { suffix: [' Energy', '', ' Climate', ' Power'], lines: ['Grid-scale storage for {x} utilities.', 'Low-carbon {x} using electrochemistry.', 'Software that cuts emissions across {x}.', 'Water reuse systems for {x} plants.'], categories: ['municipal', 'industrial', 'coastal', 'commercial', 'cement', 'food-processing'] },
	'Life sciences': { suffix: [' Bio', ' Therapeutics', ' Biosciences', ''], lines: ['Discovery platform for {x} targets.', 'Lab automation that speeds {x} assays.', 'Precision diagnostics for {x}.', 'Cell-therapy manufacturing for {x}.'], categories: ['oncology', 'rare-disease', 'neurology', 'immunology', 'metabolic', 'cardiology'] },
	Health: { suffix: [' Health', ' Care', ' Medical', ''], lines: ['Virtual care for {x} patients.', 'Remote monitoring built for {x}.', 'Care navigation for {x} clinics.', 'Devices that improve {x} recovery.'], categories: ['cardiac', 'maternal', 'senior', 'behavioral', 'rural', 'pediatric'] },
	Fintech: { suffix: [' Pay', ' Finance', ' Capital', ''], lines: ['Embedded payments for {x} businesses.', 'Credit infrastructure for {x} borrowers.', 'Treasury automation for {x} teams.', 'Compliance software for {x} fintechs.'], categories: ['small', 'cross-border', 'gig', 'mid-market', 'community', 'construction'] },
	'Deep tech': { suffix: [' Materials', ' Photonics', ' Quantum', ' Systems'], lines: ['Novel materials for {x} hardware.', 'Photonic chips for {x} computing.', 'Sensors that bring {x} into the field.', 'Edge compute for {x} satellites.'], categories: ['next-generation', 'high-power', 'low-orbit', 'quantum', 'defense', 'semiconductor'] },
	Industrial: { suffix: [' Robotics', ' Industries', ' Automation', ''], lines: ['Robots that inspect {x} infrastructure.', 'Scheduling software for {x} plants.', 'Autonomous forklifts for {x} warehouses.', 'Predictive maintenance for {x} fleets.'], categories: ['aging', 'regional', 'high-mix', 'cold-chain', 'port', 'municipal'] },
	Consumer: { suffix: [' Co', ' Goods', ' Foods', ''], lines: ['Better-for-you {x} snacks sold nationally.', 'Refillable {x} products by subscription.', 'A marketplace for {x} creators.', 'Direct-to-consumer {x} essentials.'], categories: ['plant-based', 'home', 'pet', 'kids', 'wellness', 'local'] },
};

const allSectors = Object.keys(sectorFlavor) as Sector[];
const stageList: Stage[] = ['Pre-seed', 'Seed', 'Seed', 'Series A', 'Series A', 'Series B+'];
const signalPool = ['Form D', 'SBIR award', 'Patent filed', 'Hiring spike', 'New office', 'Trademark', 'Grant', 'Founder repeat', 'Web traffic +80%', 'Pilot signed'];

const usedNames = new Set<string>();
function makeName(rand: () => number, sector: Sector) {
	const flavor = sectorFlavor[sector];
	for (let i = 0; i < 20; i++) {
		const base = prefixes[Math.floor(rand() * prefixes.length)] + roots[Math.floor(rand() * roots.length)];
		const name = base + flavor.suffix[Math.floor(rand() * flavor.suffix.length)];
		if (!usedNames.has(name)) { usedNames.add(name); return name; }
	}
	return `${prefixes[Math.floor(rand() * prefixes.length)]} ${sector.split(' ')[0]} ${usedNames.size}`;
}

function makeTown([name, lon, lat, weight]: (typeof rawTowns)[number]): Town {
	const rand = seeded(hash(name));
	const lead = allSectors[Math.floor(rand() * allSectors.length)];
	const count = Math.max(2, Math.round(weight * 1.3 + rand() * 3));
	const companies: TownCompany[] = Array.from({ length: count }, (_, i) => {
		const sector = rand() < 0.45 ? lead : allSectors[Math.floor(rand() * allSectors.length)];
		const flavor = sectorFlavor[sector];
		const stage = stageList[Math.floor(rand() * stageList.length)];
		const angle = rand() * Math.PI * 2;
		const radius = 0.006 + rand() * 0.016;
		const line = flavor.lines[Math.floor(rand() * flavor.lines.length)].replace('{x}', flavor.categories[Math.floor(rand() * flavor.categories.length)]);
		const stageScale = { 'Pre-seed': 0.8, Seed: 2.6, 'Series A': 9, 'Series B+': 24 }[stage];
		return {
			id: `${name.toLowerCase().replace(/[^a-z]+/g, '-')}-${i}`,
			name: makeName(rand, sector),
			sector, stage, description: line,
			raise: +(stageScale * (0.6 + rand() * 0.9)).toFixed(1),
			founded: 2016 + Math.floor(rand() * 10),
			headcount: Math.round(stageScale * (2 + rand() * 3) + 2),
			momentum: Math.round(35 + rand() * 60),
			signals: [...new Set([signalPool[Math.floor(rand() * signalPool.length)], signalPool[Math.floor(rand() * signalPool.length)]])],
			hue: Math.floor(rand() * 360),
			coordinates: [lon + Math.cos(angle) * radius * 1.3, lat + Math.sin(angle) * radius],
		};
	});
	const mix = new Map<Sector, number>();
	for (const c of companies) mix.set(c.sector, (mix.get(c.sector) ?? 0) + 1);
	const base = weight * 3 + rand() * 6;
	return {
		id: name.toLowerCase().replace(/[^a-z]+/g, '-'),
		name, coordinates: [lon, lat], weight, county: '',
		startups: Math.round(count * (4 + weight * 1.6) + rand() * 12),
		signals30d: Math.round(base * 1.4 + rand() * 9),
		raised: +(companies.reduce((sum, c) => sum + c.raise, 0) * (2.2 + rand() * 2)).toFixed(1),
		jobs: Math.round(companies.reduce((sum, c) => sum + c.headcount, 0) * (3 + rand() * 2)),
		momentum: Math.round(40 + weight * 4 + rand() * 18),
		trend: Array.from({ length: 12 }, (_, i) => Math.round(base * (0.55 + i * 0.05) + rand() * base * 0.5)),
		sectorMix: [...mix.entries()].sort((a, b) => b[1] - a[1]),
		companies,
	};
}

export const towns: Town[] = rawTowns.map(makeTown).sort((a, b) => b.weight - a.weight || a.name.localeCompare(b.name));
