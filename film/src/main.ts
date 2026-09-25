import { mount } from 'svelte';
import Film from './Film.svelte';

export default mount(Film, { target: document.getElementById('film')! });
