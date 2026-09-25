export type ProgramMatch = {
	name: string;
	state: 'Strong match' | 'Potential match, verify' | 'Not a match';
	detail: string;
};

export type Company = {
	id: string;
	name: string;
	town: string;
	county: string;
	sector: string;
	year: number;
	coordinates: [number, number];
	funded: boolean;
	tier: 'Review first' | 'Worth a look' | 'Monitor';
	signal: string;
	raised: string;
	description: string;
	evidence: string[];
	unknowns: string[];
	programs: ProgramMatch[];
};

const standardPrograms = (sbir: boolean, lifeScience: boolean): ProgramMatch[] => [
	{
		name: 'CSIT SBIR/STTR Direct Financial Assistance',
		state: sbir ? 'Strong match' : 'Not a match',
		detail: sbir ? 'NJ base and an SBIR award appear in the demo snapshot. Verify the current round.' : 'No qualifying SBIR/STTR signal appears in the snapshot.',
	},
	{
		name: 'Angel Investor Tax Credit',
		state: 'Potential match, verify',
		detail: 'No material requirement fails. Ask about headcount and qualifying-business criteria.',
	},
	{
		name: 'Life Sciences & Healthcare Fund',
		state: lifeScience ? 'Potential match, verify' : 'Not a match',
		detail: lifeScience ? 'Sector and round size fit. Ask about employees, co-investors, and timing.' : 'Current sector evidence is not life sciences or healthcare.',
	},
];

export const companies: Company[] = [
	{
		id: 'aster', name: 'Aster BioSystems', town: 'Princeton', county: 'Mercer', sector: 'Life sciences', year: 2022,
		coordinates: [-74.6672, 40.3573], funded: true, tier: 'Review first', signal: 'SBIR Phase II', raised: '$2.4M reported sold',
		description: 'Lab automation that shortens cell-therapy quality checks.',
		evidence: ['NJ principal office agrees across two demo sources', 'NSF SBIR Phase II technical award', 'Delaware corporation with two recent trademark filings'],
		unknowns: ['Team track record is not established from current sources', 'Commercial revenue is not available from current sources'],
		programs: standardPrograms(true, true),
	},
	{
		id: 'lucent', name: 'Lucent Grid Works', town: 'Newark', county: 'Essex', sector: 'Climate tech', year: 2023,
		coordinates: [-74.1724, 40.7357], funded: true, tier: 'Review first', signal: 'DOE SBIR Phase I', raised: '$1.7M reported sold',
		description: 'Grid-edge sensing for aging urban electrical infrastructure.',
		evidence: ['Newark office agrees across two demo records', 'DOE SBIR Phase I technical award', 'Recent Delaware incorporation and trademark filing'],
		unknowns: ['Team track record is not established from current sources', 'Customer contracts are not visible in current sources'],
		programs: standardPrograms(true, false),
	},
	{
		id: 'harbor', name: 'Harbor Robotics', town: 'Camden', county: 'Camden', sector: 'Advanced manufacturing', year: 2024,
		coordinates: [-75.1196, 39.9259], funded: false, tier: 'Worth a look', signal: 'Recent Form D', raised: '$640K offered',
		description: 'Compact inspection robots for municipal water systems.',
		evidence: ['Camden principal office on a recent demo Form D', 'Delaware corporation', 'Industrial-equipment trademark filed in 2025'],
		unknowns: ['Technical moat is not established from current sources', 'Amount sold and customer revenue are not disclosed'],
		programs: standardPrograms(false, false),
	},
	{
		id: 'delta', name: 'Delta Neuro Devices', town: 'New Brunswick', county: 'Middlesex', sector: 'Medical devices', year: 2021,
		coordinates: [-74.4518, 40.4862], funded: true, tier: 'Review first', signal: 'NIH SBIR Phase II', raised: '$3.1M reported sold',
		description: 'Wearable neuromodulation hardware for outpatient rehabilitation.',
		evidence: ['NJ address agrees across Form D and SBIR demo records', 'NIH SBIR Phase II technical award', 'Repeat federal signals and two recent filings'],
		unknowns: ['Team track record is not established from current sources', 'Regulatory status and commercial traction require verification'],
		programs: standardPrograms(true, true),
	},
	{
		id: 'mosaic', name: 'Mosaic Quantum Materials', town: 'Hoboken', county: 'Hudson', sector: 'Deep tech', year: 2023,
		coordinates: [-74.0301, 40.744], funded: false, tier: 'Worth a look', signal: 'NSF SBIR Phase I', raised: '$850K reported sold',
		description: 'Low-temperature materials for compact photonic systems.',
		evidence: ['Hoboken principal office on a recent demo filing', 'NSF SBIR Phase I technical award', 'Delaware corporation with a high-confidence entity match'],
		unknowns: ['Founder experience is not established from current sources', 'Commercial evidence is not available from current sources'],
		programs: standardPrograms(true, false),
	},
	{
		id: 'common', name: 'Common Thread Health', town: 'Jersey City', county: 'Hudson', sector: 'Digital health', year: 2022,
		coordinates: [-74.0435, 40.7178], funded: true, tier: 'Worth a look', signal: 'Form D + trademarks', raised: '$1.2M reported sold',
		description: 'Care-navigation tools for multilingual community clinics.',
		evidence: ['Jersey City office on a recent demo Form D', 'Recent corporation', 'Two trademark applications as entrepreneurial-intent signals'],
		unknowns: ['Technical moat is not established from current sources', 'Revenue range was declined on the filing'],
		programs: standardPrograms(false, true),
	},
	{
		id: 'kinetic', name: 'Kinetic Capture', town: 'Montclair', county: 'Essex', sector: 'Enterprise software', year: 2024,
		coordinates: [-74.209, 40.8259], funded: false, tier: 'Monitor', signal: 'New Form D', raised: '$300K offered',
		description: 'Workflow software for physical production teams.',
		evidence: ['Montclair office on one demo Form D', 'Recent incorporation', 'One software trademark filing'],
		unknowns: ['Team track record is not established', 'Revenue and proprietary technology are not established'],
		programs: standardPrograms(false, false),
	},
	{
		id: 'silk', name: 'Silk City Circular', town: 'Paterson', county: 'Passaic', sector: 'Climate tech', year: 2023,
		coordinates: [-74.1718, 40.9168], funded: false, tier: 'Worth a look', signal: 'EPA SBIR Phase I', raised: '$725K offered',
		description: 'Textile recovery hardware for regional manufacturers.',
		evidence: ['Paterson address agrees across two demo records', 'EPA SBIR Phase I technical award', 'Matching trademark owner'],
		unknowns: ['Team track record is not established from current sources', 'Commercial purchase orders are not visible'],
		programs: standardPrograms(true, false),
	},
	{
		id: 'forge', name: 'Forge Vision', town: 'Trenton', county: 'Mercer', sector: 'Industrial AI', year: 2022,
		coordinates: [-74.7429, 40.2171], funded: true, tier: 'Review first', signal: 'DOD SBIR Phase I', raised: '$1.4M reported sold',
		description: 'Visual inspection software for precision manufacturers.',
		evidence: ['Trenton office agrees across demo filing sources', 'DOD SBIR Phase I technical award', 'Delaware corporation and recent trademark'],
		unknowns: ['The public record does not establish how AI is used in production', 'Revenue range is not disclosed'],
		programs: standardPrograms(true, false),
	},
];
