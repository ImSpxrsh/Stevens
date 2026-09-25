<div class="background-cover" aria-hidden="true">
	<div class="aurora aurora-one"></div>
	<div class="aurora aurora-two"></div>
	<div class="aurora aurora-three"></div>
	<div class="grain"></div>
</div>

<style>
	.background-cover {
		position: fixed;
		inset: 0;
		z-index: -1;
		overflow: hidden;
		background:
			radial-gradient(circle at 17% 15%, rgba(61, 147, 139, 0.68), transparent 30%),
			radial-gradient(circle at 82% 35%, rgba(45, 91, 120, 0.78), transparent 34%),
			linear-gradient(142deg, #071a21 0%, #0c3b38 45%, #07131a 100%);
	}
	.aurora { position: absolute; border-radius: 42% 58% 68% 32% / 52% 38% 62% 48%; mix-blend-mode: screen; opacity: 0.72; transform: rotate(-18deg); }
	.aurora-one { width: 75vw; height: 90vh; left: -22vw; bottom: -54vh; background: linear-gradient(135deg, rgba(255, 118, 54, 0.88), rgba(205, 77, 36, 0.08)); box-shadow: 0 -12vh 18vh rgba(239, 127, 58, 0.22); }
	.aurora-two { width: 72vw; height: 75vh; right: -26vw; top: -43vh; background: linear-gradient(145deg, rgba(36, 125, 112, 0.72), rgba(27, 77, 93, 0.04)); box-shadow: -9vw 13vh 24vh rgba(50, 138, 130, 0.19); }
	.aurora-three { width: 62vw; height: 46vh; right: -15vw; bottom: -30vh; background: linear-gradient(110deg, rgba(223, 155, 63, 0.52), rgba(32, 96, 93, 0.03)); }
	.grain { position: absolute; inset: 0; opacity: 0.18; background-image: linear-gradient(rgba(255,255,255,.025) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.025) 1px, transparent 1px); background-size: 38px 38px; mask-image: radial-gradient(circle at center, black, transparent 88%); }
</style>
