# Sim addition. M24C01-W class I2C EEPROM (1 Kbit = 128 bytes, 8-bit word address, 16-byte page; the part
# on the thrust stand board, datasheet in doc/). Structure follows the AT24C512 scripted peer in the
# sim-fixtures peer library, adapted to a one-byte word address.
# Behaviour modelled: write = address byte then data, page write wraps inside the 16-byte page,
# sequential read wraps at 128, no acknowledge during the write cycle.
# MODELED SIMPLIFICATION: tWR is 3 ms (datasheet maximum 5 ms). The calibration image below is invented
# for the demo (the real image lives in each stand's EEPROM): V and A multipliers are the constants the
# v1 firmware hard-coded, force multiplier 1e-4 N/count, force offset 0.5 N on every cell.
import struct

SIZE, PAGE, TWR_US = 128, 16, 3000
V_PER_ADC, A_PER_ADC = 1.40822486624e-2, 2.6271654212e-2
F_PER_COUNT, F_OFFSET_N = 1.0e-4, 0.5


def image():
    words = [V_PER_ADC, 0.0, A_PER_ADC, 0.0]
    for _ in range(6):
        words += [F_PER_COUNT, F_OFFSET_N]
    mem = bytearray(b"\xff" * SIZE)
    mem[0:64] = struct.pack("<16f", *words)
    return mem


class Slave:
    def __init__(self, ctx):
        self.ctx = ctx
        self.mem = image()
        self.ptr = 0
        self.need_addr = True
        self.writes = 0

    def on_address(self, addr, is_read):
        if not is_read:
            self.need_addr = True
        return True

    def on_write(self, data):
        wrote = []
        for b in data:
            if self.need_addr:
                self.ptr, self.need_addr = b % SIZE, False
            else:
                self.mem[self.ptr] = b
                wrote.append(self.ptr)
                self.ptr = (self.ptr & ~(PAGE - 1)) | ((self.ptr + 1) & (PAGE - 1))
        if wrote:
            self.writes += 1
            self.ctx.busy_until(self.ctx.now_us + TWR_US)
            lo = wrote[0]
            self.ctx.info(f"[eeprom] t={self.ctx.now_us/1000:.1f} ms write {len(wrote)} bytes at 0x{lo:02x}: "
                          + " ".join(f"{self.mem[a]:02x}" for a in wrote[:8]))
        return len(data)

    def on_read(self, count):
        out = bytes(self.mem[(self.ptr + i) % SIZE] for i in range(count))
        self.ptr = (self.ptr + count) % SIZE
        return out
