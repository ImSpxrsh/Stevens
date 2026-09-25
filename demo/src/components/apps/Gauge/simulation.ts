import { companies } from './gauge-data';

export type SignalKind = 'SEC filing' | 'Patent' | 'Federal award';
export type SignalEvent = {
  id: string;
  companyId: string;
  kind: SignalKind;
  title: string;
  summary: string;
  timestamp: number;
  simulated: true;
};

export const signalKinds: SignalKind[] = ['SEC filing', 'Patent', 'Federal award'];
export const initialCompanyIds = ['aster', 'lucent', 'delta', 'mosaic'];

export function createSignal(sequence: number, timestamp = Date.now()): SignalEvent {
  // Introduce each remaining synthetic company before rotating through updates.
  const order = ['harbor', 'common', 'kinetic', 'silk', 'forge', ...initialCompanyIds];
  const companyId = order[sequence % order.length];
  const kind = signalKinds[sequence % signalKinds.length];
  const company = companies.find((item) => item.id === companyId)!;
  const content: Record<SignalKind, [string, string]> = {
    'SEC filing': ['New Form D filing', `A simulated private offering notice for ${company.name}. Offering terms and amounts require review.`],
    Patent: ['Patent application published', `A simulated application linked to ${company.name}. Publication does not establish a granted patent.`],
    'Federal award': ['New SBIR award signal', `A simulated research award associated with ${company.name}. Program eligibility remains unverified.`],
  };
  return { id: `demo-${sequence}-${timestamp}`, companyId, kind, title: content[kind][0], summary: content[kind][1], timestamp, simulated: true };
}

export function initialEvents(now = Date.now()): SignalEvent[] {
  return [
    { id: 'seed-1', companyId: 'aster', kind: 'SEC filing', title: 'Form D filing indexed', summary: 'Illustrative private offering record. Open the company to review the synthetic evidence.', timestamp: now - 45000, simulated: true },
    { id: 'seed-2', companyId: 'mosaic', kind: 'Patent', title: 'Patent application published', summary: 'Illustrative photonic materials application. This is a synthetic record.', timestamp: now - 150000, simulated: true },
    { id: 'seed-3', companyId: 'lucent', kind: 'Federal award', title: 'SBIR research award indexed', summary: 'Illustrative technical research award. This is a synthetic record.', timestamp: now - 280000, simulated: true },
  ];
}
