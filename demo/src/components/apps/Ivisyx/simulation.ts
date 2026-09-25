import { entityById, syntheticEntities } from './directory';
import { deals } from './suite-data';
import { seeded } from './nj-towns';

export type SignalKind = 'SEC filing' | 'Patent' | 'Federal award' | 'Hiring spike' | 'Funding round';
export type SignalEvent = {
	id: string;
	companyId: string;
	kind: SignalKind;
	title: string;
	summary: string;
	timestamp: number;
	simulated: true;
};

export const signalKinds: SignalKind[] = ['SEC filing', 'Patent', 'Federal award', 'Hiring spike', 'Funding round'];

// Pipeline companies first so the demo opens on familiar names, then the wider NJ graph.
const pool = [...deals.filter((d) => d.state === 'NJ').map((d) => d.id), ...syntheticEntities.filter((e) => !e.deal && e.townId).map((e) => e.id)];

export function createSignal(sequence: number, timestamp = Date.now()): SignalEvent {
	const rand = seeded(sequence * 7919 + 17);
	const companyId = sequence < 12 ? pool[(sequence * 3) % 20] : pool[Math.floor(rand() * pool.length)];
	const kind = signalKinds[Math.floor(rand() * signalKinds.length)];
	const name = entityById.get(companyId)!.name;
	const amount = (1 + rand() * 9).toFixed(1);
	const content: Record<SignalKind, [string, string]> = {
		'SEC filing': ['New Form D filing', `A simulated private offering notice for ${name}. Offering terms and amounts require review.`],
		Patent: ['Patent application published', `A simulated application linked to ${name}. Publication does not establish a granted patent.`],
		'Federal award': ['New SBIR award signal', `A simulated research award associated with ${name}. Program eligibility remains unverified.`],
		'Hiring spike': [`Engineering hiring up ${Math.round(30 + rand() * 90)}%`, `Simulated job-posting growth at ${name} over the last 30 days.`],
		'Funding round': [`$${amount}M round reported`, `A simulated financing announcement for ${name}. Terms are illustrative.`],
	};
	return { id: `demo-${sequence}-${timestamp}`, companyId, kind, title: content[kind][0], summary: content[kind][1], timestamp, simulated: true };
}

export function initialEvents(now = Date.now()): SignalEvent[] {
	return Array.from({ length: 9 }, (_, i) => ({ ...createSignal(1000 + i, now - (i + 1) * 47000), id: `seed-${i}` }));
}
