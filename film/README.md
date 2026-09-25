# Ivisyx film

A two-minute, Apple-style product film of the Ivisyx demo. It is not a video:
it mounts the real Ivisyx app from [`demo/`](../demo) and a director script
drives it live, clicking real buttons, flying the real NJ map, dragging a real
pipeline card and typing into the real assistant. A camera pushes in on each
feature.

```bash
npm install          # once, at the repo root
npm run film         # http://localhost:4620
npm run film:build   # static build in film/dist
npm run film:preview # serve the build at http://localhost:4621
```

## Chapters (2:20)

Ivisyx · One window · Overview · NJ map · Company profile · Assistant · Pipeline ·
Portfolio · Fund & LPs · Any fund · Search · Finale

## Player

| Key | Action |
| --- | --- |
| Space | Play or pause |
| ← → | Previous or next chapter |
| 1–9, 0 | Jump to a chapter |
| R | Restart |
| E | Explore: pause the film and use the live app yourself |
| C | Captions |
| T | Transcript with presenter notes (click a chapter to jump) |
| S | Speed: 0.5×, 1×, 1.5×, 2× |
| A | Aspect: 16:9, 1:1, 9:16 for social cuts |
| M | Sound (synthesised with WebAudio, no audio files) |
| L | Loop |
| H | Hide controls |
| F | Full screen |

The record button captures the film to a `.webm` file in desktop Chrome. It
restarts the film, records to the end, and crops the capture to the film frame
so the controls are not in the video.

URL options: `#map` (any chapter id) starts at a chapter; `?autoplay`, `?clean`,
`?loop`, `?cut=9:16`, `?cut=1:1`, `?explore`, `?t=42`.

## How it works

- `src/engine.svelte.ts`: a pausable film clock, an animated camera (push-ins,
  tilt, spotlight), a simulated cursor (move, click, type, drag) and the
  director that plays chapters and supports seeking.
- `src/chapters.ts`: the script. Each chapter can reset the app to its own
  starting state, so any chapter can be played on its own.
- `src/Film.svelte`: the stage, window frame, title cards, captions and poster.
- `src/Controls.svelte`: the player bar, transcript and shortcuts.
- `src/audio.ts`, `src/recorder.ts`: sound design and video export.

The film turns off the app's random background signals (`suite.autoSignals`)
and adds signals itself at scripted moments.

Firms, companies and figures are fictional, except six real New Jersey
companies shown with public facts only.
