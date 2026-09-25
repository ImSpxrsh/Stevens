import { entityById } from './directory';
import { createSignal, initialEvents, type SignalEvent } from './simulation';
import { deals, firmPresets, fitFor, fundFor, portfolioFor, type FirmProfile, type PipelineStage } from './suite-data';

export type View = 'dashboard' | 'radar' | 'pipeline' | 'companies' | 'portfolio' | 'market' | 'copilot' | 'fund' | 'programs' | 'sources';

export const viewLabels: Record<View, string> = {
	dashboard: 'Overview', radar: 'NJ map', pipeline: 'Pipeline', companies: 'Companies', portfolio: 'Portfolio',
	market: 'Market map', copilot: 'Assistant', fund: 'Fund & LPs', programs: 'Programs', sources: 'Sources',
};

type Toast = { id: number; text: string; tone: 'default' | 'success' };

class Suite {
	view = $state<View>('dashboard');
	firmId = $state('59');
	customFirm = $state<FirmProfile | null>(null);
	firm = $derived<FirmProfile>(
		(this.firmId === 'custom' && this.customFirm) || firmPresets.find((f) => f.id === this.firmId) || firmPresets[0],
	);
	portfolio = $derived(portfolioFor(this.firm));
	fund = $derived(fundFor(this.firm));

	pipeline = $state<Record<string, PipelineStage>>(Object.fromEntries(deals.map((d) => [d.id, d.pipeline])));
	owners = $state<Record<string, string>>({});
	saved = $state<string[]>([]);

	selectedId = $state<string | null>(null);
	selectedEvent = $state<SignalEvent | null>(null);
	paletteOpen = $state(false);
	setupOpen = $state(false);
	copilotQueue = $state<string | null>(null);
	radarTarget = $state<string | null>(null);

	events = $state<SignalEvent[]>(initialEvents());
	playing = $state(true);
	fast = $state(false);
	latest = $state<SignalEvent | null>(null);
	latestAt = $state(0);
	now = $state(Date.now());
	sequence = 0;

	toasts = $state<Toast[]>([]);
	#toastId = 0;

	/** Thesis fit for any synthetic company; real profiles are never scored. */
	fit(id: string) {
		const e = entityById.get(id);
		return e && !e.real ? fitFor(e, this.firm).total : null;
	}

	owner(id: string) {
		return this.owners[id] ?? deals.find((d) => d.id === id)?.owner ?? 'sc';
	}

	addToPipeline(id: string) {
		if (this.pipeline[id]) return this.go('pipeline');
		this.pipeline = { ...this.pipeline, [id]: 'Sourced' };
		this.owners = { ...this.owners, [id]: 'sc' };
		this.toast(`${entityById.get(id)?.name} added to pipeline`, 'success');
	}

	go(view: View) {
		this.view = view;
		this.paletteOpen = false;
	}

	open(id: string, event: SignalEvent | null = null) {
		if (!entityById.has(id)) return;
		this.selectedId = id;
		this.selectedEvent = event;
		this.paletteOpen = false;
	}

	close() {
		this.selectedId = null;
		this.selectedEvent = null;
	}

	toast(text: string, tone: Toast['tone'] = 'default') {
		const id = ++this.#toastId;
		this.toasts = [...this.toasts, { id, text, tone }];
		setTimeout(() => (this.toasts = this.toasts.filter((t) => t.id !== id)), 3600);
	}

	toggleSaved(id: string) {
		const on = this.saved.includes(id);
		this.saved = on ? this.saved.filter((item) => item !== id) : [...this.saved, id];
		this.toast(on ? 'Removed from watchlist' : `${entityById.get(id)?.name} added to watchlist`, on ? 'default' : 'success');
	}

	moveDeal(id: string, stage: PipelineStage) {
		if (this.pipeline[id] === stage) return;
		this.pipeline = { ...this.pipeline, [id]: stage };
		this.toast(`${entityById.get(id)?.name} moved to ${stage}`, 'success');
	}

	addSignal() {
		const event = createSignal(this.sequence++);
		this.events = [event, ...this.events].slice(0, 80);
		this.latest = event;
		this.latestAt = this.now = Date.now();
	}

	resetSignals() {
		this.sequence = 0;
		this.events = initialEvents();
		this.latest = null;
		this.now = Date.now();
	}

	ask(prompt: string) {
		this.copilotQueue = prompt;
		this.close();
		this.go('copilot');
	}
}

export const suite = new Suite();

export function age(timestamp: number, now: number) {
	const seconds = Math.max(0, Math.floor((now - timestamp) / 1000));
	if (seconds < 10) return 'Just now';
	if (seconds < 60) return `${seconds}s ago`;
	if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
	return `${Math.floor(seconds / 3600)}h ago`;
}
