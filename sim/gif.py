# Sim addition. Playback of a captured run: reads sim/captures/run4s-*.log (sim run --timeout 4 --trace-symbol
# HAL_TIM_PWM_PulseFinishedCallback, USART3 telemetry, peer logs) and reveals the recorded events in time order.
# uv run --with matplotlib --with pillow python sim/gif.py   -> sim/screenshots/hx717-playback.gif
import re, io
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
out = open("sim/captures/run4s-stdout.log", errors="replace").read().splitlines()
err = open("sim/captures/run4s-stderr.log", errors="replace").read()
cb = [float(m[1]) for l in out if (m := re.match(r"\[([\d.]+)s\] \(TRACE\) HAL_TIM_PWM_PulseFinishedCallback", l))]
tel = [(float(m[1]), m[2].split()) for l in out if (m := re.match(r"\[([\d.]+)s\] \(usart3 → host\) (.*)", l))]
pa7 = [(float(a) / 1000, int(b)) for a, b in re.findall(r"t=([\d.]+) ms ESC pulse on PA7 now (\d+) us", err)]
ev = sorted([(t, "cb", i) for i, t in enumerate(cb)] + [(t, "tel", i) for i, (t, _) in enumerate(tel)] + [(t, "pa7", i) for i, (t, _) in enumerate(pa7)])
N = 96; idx = [round(k * (len(ev) - 1) / (N - 1)) for k in range(N)]
frames = []
for n in idx:
    tcur = ev[n][0]
    fig, ax = plt.subplots(3, 1, figsize=(8, 6.4), dpi=100)
    a = ax[0]; fig.suptitle(f"Motor-Test-Stand firmware v2 on STM32G431 (sim 0.10.2): playback of a captured run, virtual t = {tcur*1000:7.1f} ms", fontsize=9)
    seen = [t for t in cb if t <= tcur]
    a.set_xlim(cb[0] * 1000 - 5, cb[-1] * 1000 + 5); a.set_ylim(0, 1.2); a.set_yticks([])
    a.set_xlabel("TIM2 CC3 callbacks (ms): 1 stale at Start_IT, then 24 at 16 us", fontsize=8)
    a.vlines([t * 1000 for t in seen], 0, 1, color="C3" if False else "C0", lw=1)
    a.text(0.3, 0.8, f"{len(seen)}/{len(cb)} callbacks (a read needs 25)", transform=a.transAxes, fontsize=8)
    b = ax[1]; v = [(t, f) for t, f in tel if t <= tcur]
    b.set_xlim(0, tel[-1][0]); b.set_ylim(-1.0, 0.0); b.set_ylabel("force N", fontsize=8)
    for c in range(6):
        b.step([t for t, _ in v], [float(f[3 + c]) for _, f in v], where="post", lw=1.5, label=f"cell {c+1}")
    b.legend(fontsize=6, ncol=6, loc="lower right"); b.set_xlabel("telemetry on USART3 (s)", fontsize=8)
    d = ax[2]; p = [(t, w) for t, w in pa7 if t <= tcur]
    d.set_xlim(0, tel[-1][0]); d.set_ylim(900, 2000); d.set_ylabel("ESC us (PA7)", fontsize=8)
    if p: d.step([t for t, _ in p] + [tcur], [w for _, w in p] + [p[-1][1]], where="post", color="C2")
    d.set_xlabel("virtual time (s)", fontsize=8)
    for x in ax: x.tick_params(labelsize=7)
    fig.tight_layout(); buf = io.BytesIO(); fig.savefig(buf, format="png"); plt.close(fig)
    frames.append(Image.open(io.BytesIO(buf.getvalue())).convert("P", palette=Image.ADAPTIVE, colors=64))
frames[0].save("sim/screenshots/hx717-playback.gif", save_all=True, append_images=frames[1:], duration=[120] * (N - 1) + [2500], loop=0, optimize=True)
