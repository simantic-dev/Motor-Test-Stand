# Sim addition. Six HX717 load-cell amplifiers (one per cell, DOUT on PB0 PB1 PB2 PB11 PB12 PB13, shared
# PD_SCK on PB10 driven by TIM2 CH3) plus the ESC signal on PA7 (TIM17 CH1), as one Scripted.ScriptedGpioPeer.
# Lines: 0..5 out = DOUT of cells 1..6, 6 in = PD_SCK, 7 in = ESC signal.
#
# HX717 protocol (datasheet in doc/): DOUT low = conversion ready; each PD_SCK rising edge shifts the next
# data bit out, MSB first, 24 bits two's complement; the 25th pulse selects the next gain and DOUT returns high.
# The firmware samples DOUT after each pulse's compare match, so the bit must be valid by the falling edge.
# The ESC input is the pulse width of PA7: high time between rising and falling edge, in us.
#
# MODELED SIMPLIFICATION (invented, not measured on a stand): the motor and propeller. Thrust is a first-order
# lag (tau 150 ms) toward 9 N * ((pulse-1000)/1000)^2; cell 1 carries all of it, cell 2 carries 10 % as
# cross-talk, cells 3..6 read zero. Each cell has a deterministic +-3 count noise. Conversion rate 80 SPS
# (HX717 80 Hz mode), 12.5 ms between ready flags. The raw count is (force + calibration offset) / per-count
# multiplier, so the firmware's EEPROM calibration (peers/m24c01.py) returns the modelled force.
import struct

F_PER_COUNT, F_OFFSET_N = 1.0e-4, 0.5       # must match the EEPROM image
TAU_US, T_MAX_N, PERIOD_US = 150_000, 9.0, 12_500
CELL_SHARE = [1.0, 0.1, 0.0, 0.0, 0.0, 0.0]


class Slave:
    def __init__(self, ctx):
        self.ctx = ctx
        self.pulse_us, self.rise = 1000, None
        self.thrust, self.last = 0.0, 0
        self.seed = 1
        self.sample = [0] * 6
        self.nbit = 0
        self.ready = False
        self.reads = 0
        for i in range(6):
            ctx.gpio(i).set(True)
        self.armed = False  # timers armed in __init__ are lost: arm on the first pin event

    def noise(self):
        self.seed = (self.seed * 1103515245 + 12345) & 0x7FFFFFFF
        return (self.seed >> 16) % 7 - 3

    def advance(self):
        now = self.ctx.now_us
        dt = max(0, now - self.last)
        self.last = now
        target = T_MAX_N * (max(0, min(1000, self.pulse_us - 1000)) / 1000.0) ** 2
        self.thrust += (target - self.thrust) * min(1.0, dt / TAU_US)

    def on_timer(self):
        if self.ready:
            return
        self.advance()
        self.sample = [round((self.thrust * s + F_OFFSET_N) / F_PER_COUNT) + self.noise() for s in CELL_SHARE]
        self.nbit, self.ready = 0, True
        for i in range(6):
            self.ctx.gpio(i).set(False)

    def on_gpio(self, line, level):
        now = self.ctx.now_us
        if not self.armed:
            self.armed = True
            self.ctx.schedule_periodic(PERIOD_US)
        if line == 7:
            if level:
                self.rise = now
            elif self.rise is not None:
                w = now - self.rise
                if w != self.pulse_us:
                    self.ctx.info(f"[loadcells] t={now/1000:.1f} ms ESC pulse on PA7 now {w} us (was {self.pulse_us})")
                self.pulse_us = w
            return
        if line != 6 or not level or not self.ready:
            return
        self.nbit += 1
        if self.nbit <= 24:
            for i in range(6):
                self.ctx.gpio(i).set(bool((self.sample[i] >> (24 - self.nbit)) & 1))
        else:
            self.ready = False
            self.reads += 1
            for i in range(6):
                self.ctx.gpio(i).set(True)
            if self.reads in (1, 40, 160):
                self.ctx.info(f"[loadcells] t={now/1000:.1f} ms read #{self.reads}: esc {self.pulse_us} us, "
                              f"thrust {self.thrust:.3f} N, cell1 raw {self.sample[0]}")
