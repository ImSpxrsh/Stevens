import { create_app_config } from '🍎/helpers/create-app-config.ts';

const ivisyx = create_app_config({
	title: 'Ivisyx',
	resizable: true,
	expandable: true,
	height: 720,
	width: 1180,
});

const wallpapers = create_app_config({
	title: 'Wallpapers',
	resizable: true,

	height: 600,
	width: 800,

	dock_breaks_before: true,
});

const calculator = create_app_config({
	title: 'Calculator',

	expandable: true,
	resizable: false,

	height: 250 * 1.414,
	width: 250,
});

const calendar = create_app_config({
	title: 'Calendar',
	resizable: true,
});

const vscode = create_app_config({
	title: 'VSCode',
	resizable: true,

	height: 600,
	width: 800,
});

const finder = create_app_config({
	title: 'Finder',
	resizable: true,

	// dockBreaksBefore: true,
	should_open_window: false,
});

const safari = create_app_config({
	title: 'Safari',
	resizable: true,
});

const systemPreferences = create_app_config({
	title: 'System Preferences',
	resizable: true,
});

const viewSource = create_app_config({
	title: `View Source`,
	resizable: true,

	dock_breaks_before: true,

	should_open_window: false,
	external_action: () => window.open('https://github.com/ImSpxrsh/Stevens', '_blank'),
});

const appstore = create_app_config({
	title: 'App Store',
	resizable: true,
});

export const apps_config = {
	finder,
	ivisyx,
	wallpapers,
	calculator,
	calendar,
	vscode,
	appstore,
	// safari,

	// 'system-preferences': systemPreferences,

	'view-source': viewSource,
};
