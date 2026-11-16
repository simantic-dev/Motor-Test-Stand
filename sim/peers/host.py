# Sim addition. The PC side of the stand's UART (PC10/PC11, USART3): stands in for the UAS Thrustlink
# application. Sends the ESC throttle commands and one calibration command on a fixed script, and logs
# every reply line to the run's stderr. The firmware only applies "Pnnnn" after seeing the same value
# twice in a row, so each throttle step is sent twice, 60 ms apart (one telemetry line apart).
# Script (virtual ms -> command):
SCRIPT = [(150, b"P1000\n"), (210, b"P1000\n"),
          (400, b"P1300\n"), (460, b"P1300\n"),
          (900, b"P1600\n"), (960, b"P1600\n"),
          (1500, b"P1900\n"), (1560, b"P1900\n"),
          (2000, b"F10.5\n"),          # cell 1 offset += 0.5 N, firmware writes it to the EEPROM
          (2200, b"P1000\n"), (2260, b"P1000\n")]


class Peer:
    def __init__(self, ctx):
        self.ctx = ctx
        self.line = bytearray()
        self.i = 0
        self.arm()

    def arm(self):
        if self.i < len(SCRIPT):
            self.ctx.schedule_oneshot(max(1, SCRIPT[self.i][0] * 1000 - self.ctx.now_us))

    def on_timer(self):
        while self.i < len(SCRIPT) and SCRIPT[self.i][0] * 1000 <= self.ctx.now_us:
            self.ctx.info(f"[host] t={self.ctx.now_us/1000:.1f} ms send {SCRIPT[self.i][1].decode().strip()}")
            self.ctx.send(SCRIPT[self.i][1])
            self.i += 1
        self.arm()

    def on_byte(self, b):
        pass
