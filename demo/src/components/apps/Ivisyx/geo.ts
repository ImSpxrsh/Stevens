import atlas from 'us-atlas/counties-10m.json';
import { feature, mesh } from 'topojson-client';
import { geoCentroid, geoContains, geoDistance } from 'd3-geo';
import { towns } from './nj-towns';

const topology = atlas as any;

export const newJersey = feature(topology, topology.objects.states.geometries.find((g: any) => +g.id === 34)) as any;

export const counties = topology.objects.counties.geometries
	.filter((g: any) => String(g.id).startsWith('34'))
	.map((g: any) => {
		const f = feature(topology, g) as any;
		return { id: String(g.id), name: `${g.properties.name} County`, feature: f, centroid: geoCentroid(f) as [number, number] };
	})
	.sort((a: { name: string }, b: { name: string }) => a.name.localeCompare(b.name)) as {
	id: string;
	name: string;
	feature: any;
	centroid: [number, number];
}[];

export const countyMesh = mesh(
	topology,
	{ type: 'GeometryCollection', geometries: topology.objects.counties.geometries.filter((g: any) => String(g.id).startsWith('34')) } as any,
	(a: any, b: any) => a !== b,
) as any;

export const neighbors = topology.objects.states.geometries
	.filter((g: any) => [36, 42, 10].includes(+g.id))
	.map((g: any) => ({ name: g.properties.name as string, feature: feature(topology, g) as any }));

// Barrier-island towns can fall just outside the 1:10m coastline, so fall back
// to the nearest county centroid.
for (const town of towns) {
	const inside = counties.find((c) => geoContains(c.feature, town.coordinates));
	town.county = (inside ?? counties.reduce((best, c) => (geoDistance(c.centroid, town.coordinates) < geoDistance(best.centroid, town.coordinates) ? c : best))).name;
}

export { towns };
