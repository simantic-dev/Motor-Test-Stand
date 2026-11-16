# Sim addition. Renders sim/screenshots/*.png from the captures of sim/run.sh (sim/out/<hse>-<elf>/).
# Needs matplotlib.   usage: python3 sim/plot.py "sim build string"
import re, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BUILD = sys.argv[1] if len(sys.argv) > 1 else ""


def load(tag):
    d = f"sim/out/{tag}/"
    uart = open(d + "uart.log", errors="replace").read().splitlines()
    sim = open(d + "sim.log", errors="replace").read()
    tel = [(float(m[1]), m[2].split()) for l in uart if (m := re.match(r"\[([\d.]+)s\] \(usart3 → host\) (.*)", l))]
    pw = [(float(a) / 1000, int(b)) for a, b in re.findall(r"t=([\d.]+) ms ESC pulse on PA7 now (\d+) us", sim)]
    cmds = [(float(a) / 1000, c) for a, c in re.findall(r"t=([\d.]+) ms send (\S+)", sim)]
    return tel, pw, cmds


A, B = load("25000000-thrust-v2"), load("24000000-thrust-v2")
ta = [t for t, _ in A[0]]

# 1. config A: command in, firmware echo, pad measurement, then the calibration edit
fig, ax = plt.subplots(3, 1, figsize=(7.2, 6.2), sharex=True)
ax[0].step(ta, [int(f[0]) for _, f in A[0]], where="post", lw=1.3, label="ESC pulse echoed by the firmware (telemetry column 1)")
ax[0].step([0] + [t for t, _ in A[1]], [1000] + [w for _, w in A[1]], where="post", lw=1, ls="--", label="pulse width measured on PA7 by the peer")
for t, c in A[2]:
    ax[0].axvline(t, color="gray", lw=0.4)
ax[0].set_ylabel("ESC pulse (us)"); ax[0].legend(fontsize=6, loc="upper left")
ax[1].plot(ta, [float(f[1]) for _, f in A[0]], "o-", ms=2, lw=0.8, label="V (ADC2 IN17 via DMA, 915 mV in)")
ax[1].plot(ta, [float(f[2]) for _, f in A[0]], "s-", ms=2, lw=0.8, label="A (ADC2 IN13, 307 mV in)")
ax[1].set_ylabel("V / A"); ax[1].legend(fontsize=6, loc="center left"); ax[1].set_ylim(-1, 18)
ax[2].plot(ta, [float(f[3]) for _, f in A[0]], lw=1.2, label="cell 1 force (N), raw count 0")
ax[2].plot(ta, [float(f[4]) for _, f in A[0]], lw=0.8, ls="--", label="cell 2 force (N)")
ax[2].set_ylabel("force (N)"); ax[2].set_xlabel("virtual time (s)"); ax[2].legend(fontsize=6, loc="center left")
tf = [t for t, c in A[2] if c.startswith("F")][0]
ax[2].annotate("'F10.5' sent: offset +0.5 N,\nEEPROM write over I2C2", (tf, -1.0), (tf - 1.15, -0.85), fontsize=6, arrowprops=dict(arrowstyle="->", lw=0.5))
for a in ax: a.grid(alpha=0.3)
fig.suptitle(f"Thrust stand v2 firmware, STM32G431CB, HSE 25 MHz, 2.6 s virtual.\n{BUILD}. No HX717 read completes, so cell forces are the EEPROM offset only.", fontsize=6)
fig.tight_layout(); fig.savefig("sim/screenshots/telemetry-25mhz.png", dpi=90)

# 2. A against B: same firmware and commands, only the declared crystal differs
fig, ax = plt.subplots(2, 1, figsize=(7.2, 4.6))
def steps(pw):
    out = [pw[0]]
    for p in pw[1:]:
        if abs(p[1] - out[-1][1]) > 10: out.append(p)
    return out
for (tel, pw, _), lab, st in ((A, "HSE 25 MHz (HAL HSE_VALUE)", "-"), (B, "HSE 24 MHz (sim default)", "--")):
    s = steps(pw)
    ax[0].step([0] + [t for t, _ in s], [s[0][1]] + [w for _, w in s], where="post", ls=st, label=lab)
    ts = [t for t, _ in tel]
    ax[1].plot(ts[1:-1], [(b - a) * 1000 for a, b in zip(ts[1:], ts[2:])][:len(ts) - 2], ls=st, marker="o", ms=2, lw=0.8, label=lab)
ax[0].set_ylabel("PA7 pulse width (us)"); ax[0].set_xlabel("virtual time (s)"); ax[0].legend(fontsize=6)
ax[1].set_ylabel("telemetry period (ms)"); ax[1].set_xlabel("virtual time (s)"); ax[1].legend(fontsize=6)
for a in ax: a.grid(alpha=0.3)
fig.suptitle(f"Same firmware and commands (1000, 1300, 1600, 1900 us), only the declared crystal differs. 2.6 s virtual. {BUILD}", fontsize=6)
fig.tight_layout(); fig.savefig("sim/screenshots/crystal-25-vs-24mhz.png", dpi=90)
