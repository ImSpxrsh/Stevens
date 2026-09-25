/**
 * Curated public company profiles, checked 2026-09-25.
 * Coordinates are approximate town centres, not verified office geocodes.
 * These profiles do not imply a recent filing, investment or program eligibility.
 */
export type RealCompany = {
	id: string;
	name: string;
	town: string;
	sector: string;
	coordinates: [number, number];
	description: string;
	website: string;
	sourceUrl: string;
	logo: string;
	real: true;
	companyType: 'Startup' | 'Public company';
	locationLabel: string;
};

export const realCompanies: RealCompany[] = [
	{
		id: 'polygone', name: 'PolyGone Systems', town: 'Princeton', sector: 'Water technology',
		coordinates: [-74.6672, 40.3573],
		description: 'Builds filtration systems that intercept and recover microplastics from water.',
		website: 'https://www.polygonesystems.com/',
		sourceUrl: 'https://paw.princeton.edu/sites/default/files/2026-02/March2026_issue_compressed.pdf',
		logo: '/brands/polygone.webp', real: true, companyType: 'Startup', locationLabel: 'Princeton base',
	},
	{
		id: 'pcm', name: 'Princeton Critical Minerals', town: 'Newark', sector: 'Critical minerals',
		coordinates: [-74.1724, 40.7357],
		description: 'Develops extraction technologies to improve lithium production from brine sources.',
		website: 'https://www.pcmtech.com/', sourceUrl: 'https://www.pcmtech.com/about',
		logo: '/brands/pcm.png', real: true, companyType: 'Startup', locationLabel: 'Newark headquarters',
	},
	{
		id: 'renewco2', name: 'RenewCO₂', town: 'Somerset', sector: 'Carbon utilization',
		coordinates: [-74.4885, 40.4976],
		description: 'Uses electrochemistry to convert carbon dioxide into useful industrial chemicals.',
		website: 'https://www.renewco2.com/', sourceUrl: 'https://www.renewco2.com/news-features',
		logo: '/brands/renewco2.webp', real: true, companyType: 'Startup', locationLabel: 'Somerset research facility',
	},
	{
		id: 'oishii', name: 'Oishii', town: 'Jersey City', sector: 'Vertical farming',
		coordinates: [-74.0435, 40.7178],
		description: 'Operates indoor vertical farms growing strawberries and other produce in New Jersey.',
		website: 'https://oishii.com/', sourceUrl: 'https://oishii.com/pages/nj',
		logo: '/brands/oishii.png', real: true, companyType: 'Startup', locationLabel: 'Jersey City farm presence',
	},
	{
		id: 'pne', name: 'Princeton NuEnergy', town: 'Princeton', sector: 'Battery materials',
		coordinates: [-74.655, 40.365],
		description: 'Develops closed-loop recycling processes that recover and rejuvenate lithium-ion battery materials.',
		website: 'https://pnecycle.com/',
		sourceUrl: 'https://www.prnewswire.com/news-releases/princeton-nuenergy-launches-flagship-facility-in-south-carolina-302178157.html',
		logo: '/brands/pne.png', real: true, companyType: 'Startup', locationLabel: 'Princeton company location',
	},
	{
		id: 'coreweave', name: 'CoreWeave', town: 'Livingston', sector: 'AI infrastructure',
		coordinates: [-74.3149, 40.7959],
		description: 'Provides cloud infrastructure for AI workloads. Included as an established public-company reference.',
		website: 'https://www.coreweave.com/', sourceUrl: 'https://www.coreweave.com/contact-us',
		logo: '/brands/coreweave.png', real: true, companyType: 'Public company', locationLabel: 'Livingston headquarters',
	},
];
