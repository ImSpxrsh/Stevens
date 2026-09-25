/**
 * The film's script. Each chapter can reset the app to its own starting state,
 * so the viewer can jump to any chapter and it plays the same way.
 */
import { suite, type View } from '@ivisyx/state.svelte';
import { ease, type Chapter, type Ctx } from './engine.svelte';

const initialPipeline = { ...suite.pipeline };

function baseline(firmId = '59') {
	suite.autoSignals = false;
	suite.playing = true;
	suite.firmId = firmId;
	suite.close();
	suite.paletteOpen = false;
	suite.setupOpen = false;
	suite.copilotQueue = null;
	suite.radarTarget = null;
	suite.pipeline = { ...initialPipeline };
	suite.owners = {};
	suite.saved = [];
	suite.toasts = [];
	suite.resetSignals();
}

/** Shows a view from a clean mount, so components reset their own local state. */
async function show(ctx: Ctx, view: View) {
	if (suite.view === view) {
		suite.go(view === 'dashboard' ? 'companies' : 'dashboard');
		await ctx.frame();
		await ctx.frame();
	}
	suite.go(view);
	await ctx.wait(380);
}

const nav = (ctx: Ctx, label: string) => ctx.find('.ivx nav button', label);

async function open(ctx: Ctx, label: string, view: View) {
	if (suite.view === view) return;
	await ctx.cursor.click(nav(ctx, label));
	await ctx.wait(450);
}

function settle(ctx: Ctx) {
	ctx.camera.set({ ...ctx.stage.rest(), rx: 0, ry: 0, lift: 0 });
	ctx.stage.spot = null;
	const w = ctx.stage.window;
	ctx.cursor.show({ x: w.x + w.w * 0.6, y: w.y + w.h * 0.55 });
}

export const chapters: Chapter[] = [
	{
		id: 'open',
		title: 'Ivisyx',
		duration: 7000,
		captions: [],
		notes: 'Let the logo land. No talking yet.',
		async setup(ctx) {
			baseline();
			await show(ctx, 'dashboard');
			const r = ctx.stage.rest();
			ctx.camera.set({ ...r, s: r.s * 0.62, rx: 24, ry: 0, lift: 180 });
			ctx.cursor.hide();
		},
		async run(ctx) {
			await ctx.wait(300);
			await ctx.titleCard({ logo: true, lines: ['Ivisyx'], sub: 'Venture intelligence for every fund.', backdrop: 'black', size: 'hero' }, 5600);
			ctx.clearTitle();
		},
	},
	{
		id: 'reveal',
		title: 'One window',
		duration: 8500,
		captions: ['Sourcing, pipeline, portfolio and LP reporting, together.'],
		notes: 'Ivisyx replaces the spreadsheet, the CRM tab and the quarterly scramble.',
		async setup(ctx, fresh) {
			if (!fresh) return;
			baseline();
			await show(ctx, 'dashboard');
			const r = ctx.stage.rest();
			ctx.camera.set({ ...r, s: r.s * 0.62, rx: 24, ry: 0, lift: 180 });
			ctx.cursor.hide();
		},
		async run(ctx) {
			await ctx.camera.to({ ...ctx.stage.rest(), rx: 0, lift: 0 }, 2600, ease.out);
			await ctx.titleCard({ lines: ['Your whole fund.', 'In one window.'], backdrop: 'dim', size: 'statement' }, 2400);
			ctx.clearTitle();
			await ctx.wait(500);
			ctx.say('Sourcing, pipeline, portfolio and LP reporting, together.');
		},
	},
	{
		id: 'overview',
		title: 'Overview',
		duration: 11500,
		captions: ['Start the day with what changed.', 'New signals, deals waiting on IC, and the companies that need you.'],
		notes: 'Everything on the overview is live: scores re-rank when the thesis changes.',
		async setup(ctx, fresh) {
			if (fresh) {
				baseline();
				await show(ctx, 'dashboard');
				settle(ctx);
			} else ctx.cursor.show();
		},
		async run(ctx) {
			ctx.say('Start the day with what changed.');
			await ctx.camera.focus('.hero', { pad: 0.8, max: 2 });
			await ctx.cursor.move('.hero-stats', 800);
			await ctx.wait(700);
			await ctx.camera.focus('.kpis', { pad: 0.88, max: 2.2 });
			ctx.say('New signals, deals waiting on IC, and the companies that need you.');
			await ctx.wait(600);
			const chart = ctx.q('.row-a .card');
			await ctx.camera.focus(chart, { pad: 0.8, max: 2.2 });
			await ctx.cursor.scrub(chart?.querySelector('svg') ?? null, 2200);
			await ctx.camera.focus('.row-b', { pad: 0.9, max: 1.8 });
			await ctx.wait(900);
		},
	},
	{
		id: 'map',
		title: 'NJ map',
		duration: 20000,
		captions: ['Fly from the whole state to a single county.', 'Then into one town, and the startups on its streets.'],
		notes: '222 municipalities, each with its own startups and signals. Everything except six real companies is synthetic.',
		async setup(ctx, fresh) {
			if (!fresh) return;
			baseline();
			await show(ctx, 'dashboard');
			settle(ctx);
		},
		async run(ctx) {
			ctx.say(null);
			await ctx.camera.rest(900);
			await ctx.titleCard({ kicker: 'NJ map', lines: ['Every town.', 'Every signal.'], backdrop: 'dim', size: 'statement' }, 2300);
			ctx.clearTitle();
			await open(ctx, 'NJ map', 'radar');
			const map = await ctx.waitFor(() => ctx.q('section.map'));
			await ctx.camera.focus(map, { pad: 0.9, max: 1.9 });
			ctx.say('Fly from the whole state to a single county.');
			suite.addSignal();
			await ctx.wait(1400);
			const county = await ctx.waitFor(() => ctx.q('path.county[aria-label="Mercer County"]'));
			await ctx.cursor.click(county, 900);
			await ctx.wait(1500);
			const town = await ctx.waitFor(() => ctx.q('g.town[aria-label="Princeton, Mercer County"]'));
			await ctx.cursor.move(town, 800);
			ctx.cursor.hover(town);
			await ctx.wait(900);
			ctx.cursor.unhover(town);
			await ctx.cursor.press();
			town?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
			ctx.say('Then into one town, and the startups on its streets.');
			await ctx.wait(1700);
			await ctx.camera.focus('.radar .panel', { pad: 0.86, max: 2.3 });
			await ctx.cursor.move('.radar .panel .company-row', 700);
			await ctx.wait(900);
		},
	},
	{
		id: 'company',
		title: 'Company profile',
		duration: 12000,
		captions: ['Every company explains its own fit score.', 'Move it forward without leaving the page.'],
		notes: 'Fit is sector, stage, geography and signal momentum, weighted for the active fund.',
		async setup(ctx, fresh) {
			if (!fresh) return;
			baseline();
			await show(ctx, 'radar');
			suite.radarTarget = 'princeton';
			await ctx.wait(1500);
			settle(ctx);
			await ctx.camera.focus('.radar .panel', { pad: 0.86, max: 2.3, ms: 10 });
		},
		async run(ctx) {
			const row = await ctx.waitFor(() => ctx.find('.radar .panel .company-row', 'Aster BioSystems'));
			row?.scrollIntoView({ block: 'nearest' });
			await ctx.cursor.click(row, 700);
			const drawer = await ctx.waitFor(() => ctx.q('.drawer'));
			await ctx.wait(350);
			await ctx.camera.focus(drawer, { pad: 0.92, max: 1.7 });
			ctx.say('Every company explains its own fit score.');
			await ctx.wait(500);
			await ctx.camera.focus('.drawer .fit', { pad: 0.62, max: 3, spot: true });
			await ctx.wait(1900);
			ctx.say('Move it forward without leaving the page.');
			await ctx.camera.focus('.drawer .stages', { pad: 0.66, max: 2.7 });
			await ctx.cursor.click(ctx.find('.drawer .stages button', 'Term sheet'), 800);
			await ctx.wait(1300);
		},
	},
	{
		id: 'assistant',
		title: 'Assistant',
		duration: 14500,
		captions: ['Ask for an IC memo. Get a first draft in seconds.'],
		notes: 'The demo assistant is scripted from the synthetic records; it does not call a model.',
		async setup(ctx, fresh) {
			if (!fresh) return;
			baseline();
			await show(ctx, 'dashboard');
			settle(ctx);
		},
		async run(ctx) {
			suite.close();
			await ctx.camera.rest(900);
			await open(ctx, 'Assistant', 'copilot');
			const chat = await ctx.waitFor(() => ctx.q('.chat'));
			await ctx.camera.focus(chat, { pad: 0.88, max: 1.6 });
			const input = await ctx.waitFor(() => ctx.q('.composer input'));
			await ctx.cursor.click(input, 700);
			ctx.say('Ask for an IC memo. Get a first draft in seconds.');
			await ctx.cursor.type(input, 'Draft an IC memo for Quarry Labs', 17);
			await ctx.cursor.click('.send', 500);
			await ctx.wait(1600);
			await ctx.camera.focus(await ctx.waitFor(() => ctx.q('.ai .metrics')), { pad: 0.7, max: 2.6 });
			await ctx.wait(1700);
			await ctx.camera.focus('.ai .ai-body', { pad: 0.94, max: 1.9, dy: 0 });
			await ctx.wait(1500);
		},
	},
	{
		id: 'pipeline',
		title: 'Pipeline',
		duration: 11500,
		captions: ['Drag a deal to IC. The whole team sees it.'],
		notes: 'Pipeline stages, owners and days-in-stage. Fit scores sit on every card.',
		async setup(ctx, fresh) {
			if (!fresh) return;
			baseline();
			await show(ctx, 'dashboard');
			settle(ctx);
		},
		async run(ctx) {
			await ctx.camera.rest(900);
			await open(ctx, 'Pipeline', 'pipeline');
			const board = await ctx.waitFor(() => ctx.q('.board'));
			await ctx.camera.focus(board, { pad: 0.94, max: 1.5 });
			ctx.say('Drag a deal to IC. The whole team sees it.');
			const from = ctx.q('.column[aria-label="Diligence"]');
			const to = ctx.q('.column[aria-label="IC review"]');
			if (from && to) {
				const a = ctx.stage.toWorld(from)!;
				const b = ctx.stage.toWorld(to)!;
				const x = Math.min(a.x, b.x);
				const rect = { x, y: a.y, w: Math.max(a.x + a.w, b.x + b.w) - x, h: Math.max(a.h, b.h) * 0.75 };
				await ctx.camera.to(ctx.stage.framing(rect, { pad: 0.9, max: 2.4 }), 1200);
			}
			const card = ctx.find('.deal', 'Quarry Labs');
			await ctx.cursor.drag(card, to, () => suite.moveDeal('quarry', 'IC review'));
			await ctx.wait(1400);
			await ctx.camera.focus(to, { pad: 0.8, max: 2.5 });
			await ctx.wait(1200);
		},
	},
	{
		id: 'portfolio',
		title: 'Portfolio',
		duration: 9500,
		captions: ['Revenue, runway and the latest founder update, in one row.'],
		notes: 'Marks are scaled to the active fund size.',
		async setup(ctx, fresh) {
			if (!fresh) return;
			baseline();
			await show(ctx, 'dashboard');
			settle(ctx);
		},
		async run(ctx) {
			await ctx.camera.rest(900);
			await open(ctx, 'Portfolio', 'portfolio');
			await ctx.camera.focus(await ctx.waitFor(() => ctx.q('.kpis')), { pad: 0.9, max: 1.8 });
			ctx.say('Revenue, runway and the latest founder update, in one row.');
			await ctx.cursor.click(ctx.q('button.row'), 700);
			await ctx.wait(600);
			await ctx.camera.focus(await ctx.waitFor(() => ctx.q('.detail')), { pad: 0.86, max: 2 });
			await ctx.wait(1600);
		},
	},
	{
		id: 'fund',
		title: 'Fund & LPs',
		duration: 12000,
		captions: ['Returns, the J-curve and every capital call.', 'The quarterly LP letter drafts itself from the latest marks.'],
		notes: 'TVPI, DPI, RVPI and net IRR, plus a one-click LP report draft.',
		async setup(ctx, fresh) {
			if (!fresh) return;
			baseline();
			await show(ctx, 'dashboard');
			settle(ctx);
		},
		async run(ctx) {
			await ctx.camera.rest(900);
			await open(ctx, 'Fund & LPs', 'fund');
			await ctx.camera.focus(await ctx.waitFor(() => ctx.q('.hero')), { pad: 0.86, max: 1.7 });
			ctx.say('Returns, the J-curve and every capital call.');
			await ctx.wait(1200);
			const button = ctx.find('.btn.primary', 'Generate Q3 LP report');
			await ctx.camera.focus(ctx.q('.hero-top'), { pad: 0.8, max: 2.4 });
			await ctx.cursor.click(button, 700);
			ctx.say('The quarterly LP letter drafts itself from the latest marks.');
			await ctx.wait(2800);
			await ctx.camera.focus(await ctx.waitFor(() => ctx.q('.report'), 4000), { pad: 0.86, max: 2.2 });
			await ctx.wait(1500);
		},
	},
	{
		id: 'any-fund',
		title: 'Any fund',
		duration: 13500,
		captions: ['Switch funds, and every score, color and number follows.'],
		notes: 'Presets are fictional firms. "Set up your firm" accepts any thesis, stage, geography and brand color.',
		async setup(ctx, fresh) {
			if (!fresh) return;
			baseline();
			await show(ctx, 'dashboard');
			settle(ctx);
		},
		async run(ctx) {
			await ctx.camera.rest(900);
			await open(ctx, 'Overview', 'dashboard');
			await ctx.titleCard({ lines: ['Built for your thesis.', 'Whatever it is.'], backdrop: 'dim', size: 'statement' }, 2300);
			ctx.clearTitle();
			ctx.say('Switch funds, and every score, color and number follows.');
			await ctx.cursor.click('.workspace', 800);
			await ctx.wait(350);
			await ctx.cursor.click(await ctx.waitFor(() => ctx.find('.workspace-menu button', 'Saltmarsh')), 600);
			await ctx.wait(700);
			await ctx.camera.focus('.hero', { pad: 0.82, max: 1.7 });
			await ctx.wait(1300);
			await ctx.camera.rest(900);
			await ctx.cursor.click('.workspace', 700);
			await ctx.wait(350);
			await ctx.cursor.click(await ctx.waitFor(() => ctx.find('.workspace-menu button', 'Quillwort')), 600);
			await ctx.wait(700);
			await ctx.camera.focus('.hero', { pad: 0.82, max: 1.7 });
			await ctx.wait(1200);
		},
	},
	{
		id: 'search',
		title: 'Search',
		duration: 10500,
		captions: ['Press ⌘K to jump anywhere.'],
		notes: 'Companies, towns, screens and actions are one keystroke away.',
		async setup(ctx, fresh) {
			if (fresh) {
				baseline();
				await show(ctx, 'dashboard');
				settle(ctx);
			} else suite.firmId = '59';
		},
		async run(ctx) {
			await ctx.camera.rest(900);
			ctx.say('Press ⌘K to jump anywhere.');
			await ctx.keycaps(['⌘', 'K'], 1000);
			suite.paletteOpen = true;
			const input = await ctx.waitFor(() => ctx.q('.palette input'));
			await ctx.camera.focus(ctx.q('.palette'), { pad: 0.78, max: 2 });
			await ctx.cursor.type(input, 'Hoboken', 9);
			await ctx.wait(500);
			await ctx.cursor.click(ctx.find('.palette .results button', 'Hudson County'), 700);
			await ctx.wait(500);
			await ctx.camera.focus(await ctx.waitFor(() => ctx.q('section.map')), { pad: 0.92, max: 1.8 });
			await ctx.wait(2000);
		},
	},
	{
		id: 'finale',
		title: 'Finale',
		duration: 9500,
		captions: [],
		notes: 'Close on the name. Offer the live demo.',
		async setup(ctx, fresh) {
			if (!fresh) return;
			baseline();
			await show(ctx, 'radar');
			settle(ctx);
		},
		async run(ctx) {
			ctx.say(null);
			ctx.cursor.hide();
			const r = ctx.stage.rest();
			await ctx.camera.to({ ...r, s: r.s * 0.74, rx: 16, lift: 90 }, 2200, ease.inOut);
			await ctx.titleCard(
				{
					logo: true,
					lines: ['Ivisyx'],
					sub: 'Venture intelligence for every fund.',
					backdrop: 'black',
					size: 'hero',
					fine: 'Firms, companies and figures in this film are fictional, except six real New Jersey companies shown with public facts only.',
				},
				6800,
			);
		},
	},
];
