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

export default defineConfig({
	plugins: [svelte(), UnpluginIcons({ compiler: 'svelte' }), demoBrands()],
	resolve: {
		alias: { '@ivisyx': `${demo}src/components/apps/Ivisyx` },
		// The Ivisyx components live under demo/, which may have its own install.
		// One copy of the Svelte runtime is required for shared reactive state.
		dedupe: ['svelte', 'd3-geo', 'topojson-client'],
	},
	server: { port: 4620, fs: { allow: ['..'] } },
	preview: { port: 4621 },
	build: { chunkSizeWarningLimit: 2000 },
});
