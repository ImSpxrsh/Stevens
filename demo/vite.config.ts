import { svelte } from '@sveltejs/vite-plugin-svelte';
import UnpluginIcons from 'unplugin-icons/vite';
import { defineConfig } from 'vite';
import { imagetools } from 'vite-imagetools';
import { VitePWA } from 'vite-plugin-pwa';

import { prefetch } from './prefetch-plugin.ts';

export default defineConfig({
	plugins: [
		svelte(),
		prefetch(),

		UnpluginIcons({ autoInstall: true, compiler: 'svelte' }),
		VitePWA({
			// Let vite-plugin-pwa handle the web manifest + registration, but write
			// our own service worker (src/sw.ts) powered by Serwist instead of
			// workbox's generateSW. The precache list is injected as self.__WB_MANIFEST.
			strategies: 'injectManifest',
			srcDir: 'src',
			filename: 'sw.ts',
			includeAssets: [
				'robots.txt',
				'app-icons/ivisyx/32.png',
				'cover-image.png',
				'cursors/(normal|link|text|help)-select.svg',
				'**/*.mp3',
			],
			manifest: {
				name: 'Ivisyx — venture intelligence suite',
				short_name: 'Ivisyx',
				theme_color: '#0f1917',
				description: 'Ivisyx: sourcing, pipeline, portfolio and fund intelligence for venture teams',
				icons: [
					{ src: 'app-icons/ivisyx/128.png', sizes: '128x128', type: 'image/png' },
					{ src: 'app-icons/ivisyx/192.png', sizes: '192x192', type: 'image/png' },
					{ src: 'app-icons/ivisyx/512.png', sizes: '512x512', type: 'image/png' },
					{ src: 'app-icons/ivisyx/512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' },
				],
			},
		}),
		imagetools(),
	],
	resolve: {
		alias: {
			'🍎': new URL('./src/', import.meta.url).pathname,
		},
	},
	// Vite 8 (Rolldown) minifies JS with its built-in minifier and CSS with
	// lightningcss by default — no explicit build/css config needed.
});
