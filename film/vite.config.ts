import { svelte } from '@sveltejs/vite-plugin-svelte';
import { readdirSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import UnpluginIcons from 'unplugin-icons/vite';
import { defineConfig, type Plugin } from 'vite';

const demo = fileURLToPath(new URL('../demo/', import.meta.url));
const brands = `${demo}public/brands/`;

/** Serve and ship the demo's company logos at /brands without duplicating them in this folder. */
function demoBrands(): Plugin {
	return {
		name: 'ivisyx-film-brands',
		configureServer(server) {
			server.middlewares.use('/brands', (req, res, next) => {
				const file = decodeURIComponent((req.url ?? '').split('?')[0]).replace(/^\/+/, '');
				if (!file || file.includes('..')) return next();
				try {
					const body = readFileSync(brands + file);
					const type = file.endsWith('.svg') ? 'image/svg+xml' : file.endsWith('.webp') ? 'image/webp' : 'image/png';
					res.setHeader('Content-Type', type);
					res.end(body);
				} catch {
					next();
				}
			});
		},
		generateBundle() {
			for (const file of readdirSync(brands)) {
				if (file.endsWith('.md')) continue;
				this.emitFile({ type: 'asset', fileName: `brands/${file}`, source: readFileSync(brands + file) });
			}
		},
	};
}

/**
 * The map only draws New Jersey's counties and the outlines of NJ, NY, PA and DE,
 * but us-atlas/counties-10m.json holds every US county (840 KB). Keep just those
 * geometries and the arcs they use, in their original order, so the shapes are identical.
 */
function njAtlas(): Plugin {
	const states = new Set(['34', '36', '42', '10']);
	return {
		name: 'ivisyx-film-nj-atlas',
		enforce: 'pre',
		load(id) {
			const file = id.split('?')[0];
			if (!file.endsWith('/us-atlas/counties-10m.json')) return;
			const topology = JSON.parse(readFileSync(file, 'utf8'));
			const keep = {
				states: topology.objects.states.geometries.filter((g: any) => states.has(g.id)),
				counties: topology.objects.counties.geometries.filter((g: any) => String(g.id).startsWith('34')),
			};
			const used = new Set<number>();
			const collect = (arcs: any) => (typeof arcs === 'number' ? used.add(arcs < 0 ? ~arcs : arcs) : arcs?.forEach(collect));
			for (const g of [...keep.states, ...keep.counties]) collect(g.arcs);
			const order = [...used].sort((a, b) => a - b);
			const index = new Map(order.map((arc, i) => [arc, i]));
			const remap = (arcs: any): any => (typeof arcs === 'number' ? (arcs < 0 ? ~index.get(~arcs)! : index.get(arcs)) : arcs.map(remap));
			const collection = (geometries: any[]) => ({
				type: 'GeometryCollection',
				geometries: geometries.map((g) => (g.arcs ? { ...g, arcs: remap(g.arcs) } : g)),
			});
			return JSON.stringify({
				type: 'Topology',
				bbox: topology.bbox,
				transform: topology.transform,
				objects: { states: collection(keep.states), counties: collection(keep.counties) },
				arcs: order.map((arc) => topology.arcs[arc]),
			});
		},
	};
}

export default defineConfig({
	plugins: [njAtlas(), svelte(), UnpluginIcons({ compiler: 'svelte' }), demoBrands()],
	resolve: {
		alias: { '@ivisyx': `${demo}src/components/apps/Ivisyx` },
		// The Ivisyx components live under demo/, which may have its own install.
		// One copy of the Svelte runtime is required for shared reactive state.
		dedupe: ['svelte', 'd3-geo', 'topojson-client'],
	},
	server: { port: 4620, fs: { allow: ['..'] } },
	preview: { port: 4621 },
});
