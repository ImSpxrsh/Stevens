/**
 * Records the film to a video file with the browser's own screen capture.
 * In Chrome the capture is cropped to the film frame (Region Capture), so the
 * player controls never appear in the video.
 */
type DisplayMediaOptions = DisplayMediaStreamOptions & { preferCurrentTab?: boolean; selfBrowserSurface?: 'include' | 'exclude' };
type CroppableTrack = MediaStreamTrack & { cropTo?: (target: unknown) => Promise<void> };

export type Recording = { stop: () => void; done: Promise<Blob>; ended: Promise<void>; ext: string };

export function canRecord() {
	return typeof MediaRecorder !== 'undefined' && !!navigator.mediaDevices?.getDisplayMedia;
}

export async function startRecording(frame: HTMLElement, audio: MediaStream | null): Promise<Recording> {
	const display = await navigator.mediaDevices.getDisplayMedia({
		video: { frameRate: 60, width: { ideal: 3840 }, height: { ideal: 2160 } },
		audio: false,
		preferCurrentTab: true,
		selfBrowserSurface: 'include',
	} as DisplayMediaOptions);
	const [track] = display.getVideoTracks() as CroppableTrack[];
	const CropTarget = (window as unknown as { CropTarget?: { fromElement: (el: Element) => Promise<unknown> } }).CropTarget;
	if (CropTarget && track.cropTo) {
		try {
			await track.cropTo(await CropTarget.fromElement(frame));
		} catch {
			// Cropping is optional; the full tab is still recorded.
		}
	}
	const stream = new MediaStream([track, ...(audio?.getAudioTracks() ?? [])]);
	const mime = ['video/webm;codecs=vp9,opus', 'video/webm;codecs=vp8,opus', 'video/webm', 'video/mp4'].find((m) => MediaRecorder.isTypeSupported(m)) ?? '';
	const recorder = new MediaRecorder(stream, mime ? { mimeType: mime, videoBitsPerSecond: 16_000_000 } : undefined);
	const chunks: Blob[] = [];
	recorder.ondataavailable = (e) => e.data.size && chunks.push(e.data);
	const done = new Promise<Blob>((resolve) => {
		recorder.onstop = () => {
			for (const t of display.getTracks()) t.stop();
			resolve(new Blob(chunks, { type: mime || 'video/webm' }));
		};
	});
	const ended = new Promise<void>((resolve) => track.addEventListener('ended', () => resolve(), { once: true }));
	recorder.start(500);
	return { stop: () => recorder.state !== 'inactive' && recorder.stop(), done, ended, ext: mime.includes('mp4') ? 'mp4' : 'webm' };
}

export function download(blob: Blob, name: string) {
	const url = URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download = name;
	a.click();
	setTimeout(() => URL.revokeObjectURL(url), 5000);
}
