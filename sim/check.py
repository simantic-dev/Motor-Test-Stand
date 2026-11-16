# Sim addition. Asserts on the run's captures (sim/out) and prints the measured numbers. Exit 1 on a failed
# assertion. Checks that apply only to the load-cell path run only when the peer reported a completed read.
import re, sys
hse, elf, out = sys.argv[1:4]
uart = open(out + "/uart.log", errors="replace").read().splitlines()
sim = open(out + "/sim.log", errors="replace").read()
tel = [(float(m[1]), m[2].split()) for l in uart if (m := re.match(r"\[([\d.]+)s\] \(usart3 → host\) (.*)", l))]
fail = []
def need(ok, msg):
    print(("ok   " if ok else "FAIL ") + msg)
    if not ok: fail.append(msg)
need(len(tel) > 40, f"{len(tel)} telemetry lines on USART3")
ts = [t for t, _ in tel]
per = (ts[-1] - ts[1]) / (len(ts) - 2) * 1000
print(f"     telemetry period {per:.3f} ms (TIM6: 5000 ticks of 10 us = 50 ms at an exact 150 MHz timer clock)")
esc = [int(f[0]) for _, f in tel]
need(all(v in esc for v in (1000, 1300, 1600, 1900)), "firmware echoes ESC pulse 1000, 1300, 1600 and 1900 (applied after the second identical P command)")
volts = [float(f[1]) for _, f in tel[2:]]; amps = [float(f[2]) for _, f in tel[2:]]
need(all(15.9 < v < 16.1 for v in volts) and all(9.9 < a < 10.1 for a in amps), f"ADC2 via DMA: V {min(volts):.3f}..{max(volts):.3f}, A {min(amps):.3f}..{max(amps):.3f} (inputs 915 mV and 307 mV, EEPROM multipliers)")
c1 = [float(f[3]) for _, f in tel]
need(abs(c1[2] + 0.5) < 1e-3 and abs(c1[-1] + 1.0) < 1e-3, f"cell 1 reads -0.500 (EEPROM offset 0.5 N, zero raw) then {c1[-1]:.3f} after 'F10.5' moved the offset")
need("[eeprom]" in sim and "write 8 bytes at 0x10" in sim, "firmware wrote the cell 1 calibration to the EEPROM over I2C2 (8 bytes at 0x10)")
pw = [(float(a), int(b)) for a, b in re.findall(r"t=([\d.]+) ms ESC pulse on PA7 now (\d+) us", sim)]
steps = [pw[0]] + [b for a, b in zip(pw, pw[1:]) if abs(b[1] - a[1]) > 10]
print("     ESC pulse width measured on PA7:", ", ".join(f"{w} us @ {t:.0f} ms" for t, w in steps))
if hse == "25000000":
    got = [w for _, w in pw if w in (1300, 1600, 1900)]
    need(got == [1300, 1600, 1900], "PA7 pulse widths equal the commands (1300, 1600, 1900 us)")
reads = re.search(r"read #(\d+)", sim)
print(f"     HX717 reads completed (25 clock pulses): {'yes' if reads else 'none'}")
sys.exit(1 if fail else 0)
