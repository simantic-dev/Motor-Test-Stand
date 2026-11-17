# Motor Test Stand

Motor test stand software and hardware designs

## Running the firmware in a simulator (`sim/`)

![HX717 playback](sim/screenshots/hx717-playback.gif)

Playback of a captured run (virtual time), not real time: sim 0.10.2 (build 83eb7a66), 4.0 s virtual, 27 s wall, built by `sim/gif.py` from `sim/captures/run4s-*.log`. Top: TIM2 CC3 callbacks (the HX717 clock); middle: the six cell forces from the firmware's USART3 telemetry; bottom: ESC pulse measured on PA7.

This fork adds `sim/`, which runs the **real `firmware/v2` image** (STM32G431CBUx, HAL, unmodified sources) in the
Simantic simulator with the board's other parts as small Python peers. Everything under `sim/` is
an addition of this fork; the upstream files, including the MIT `LICENSE`, are untouched. Configuration A and the 4 s capture were re-run on
`sim 0.10.2 (build 83eb7a66)` on 2026-11-17 (2.6 s virtual in 17.9 s wall; 4 s virtual in 27 s). Rows B and C below are from
`sim 0.10.0 (build f219eb31)`, 2026-11-16, and were not re-run.

What runs, and what is a stand-in:

| Part | In the sim | Status |
| --- | --- | --- |
| STM32G431CB, `firmware/v2` | the firmware as built by `sim/build.sh` (arm-none-eabi-gcc, no source change) | the model is flagged "incomplete" by `sim models`; it runs with a warning |
| ESC command over USART3 (PC10/PC11) | scripted PC peer (`peers/host.py`) sends `P1300`, `P1600`, `P1900`, `P1000` (each twice, as the firmware requires) and `F10.5` | works |
| ESC signal on PA7 (TIM17 CH1) | pulse width measured on the pad by `peers/loadcells.py` | works |
| V and I sense (ADC2 IN17, IN13, DMA) | fixed 915 mV and 307 mV on the pins | works; the inputs are constant (static `channelMillivolts`), so V and A do not follow throttle |
| Calibration EEPROM M24C01 on I2C2 (0x50) | `peers/m24c01.py`, preloaded with an invented calibration image | works: the 64-byte read at boot and the 8-byte write after `F10.5` both happen |
| 6 x HX717 load-cell amplifiers (PB0, PB1, PB2, PB11, PB12, PB13, clock PB10 from TIM2 CH3) | `peers/loadcells.py`, written to the HX717 protocol with an invented thrust model | one read starts and gets 24 clock pulses, it never completes (no 25th pulse), see "Gaps" |

```mermaid
flowchart LR
  dut["dut<br/>STM32G431CB"]
  dut_loadcells(["loadcells<br/>Scripted.ScriptedGpioPeer"])
  dut -- "sysbus" --- dut_loadcells
  dut_eeprom(["eeprom<br/>I2C.ScriptedI2cSlave"])
  dut -- "i2c2 0x50" --- dut_eeprom
  dut_host(["host<br/>UART.ScriptedUartPeer"])
  medium0{{"uart"}}
  dut -- "usart3" --- medium0
  dut_host --- medium0
```

(`sim graph --scenario sim/scenario.yaml`; the load-cell and ESC pin wires are in `sim/stand.board`.)

### Configurations tried

| # | Configuration | Result (A: sim 0.10.2 83eb7a66, 2026-11-17; B, C: sim 0.10.0 f219eb31, 2026-11-16) |
| --- | --- | --- |
| A | stock `firmware/v2`, HSE 25 MHz (the HAL's `HSE_VALUE`), `sh sim/run.sh` | 52 telemetry lines at 50.010 ms (TIM6 = 50 ms at the 150 MHz timer clock the PLL settings give from 25 MHz). Firmware echoes the pulse 1000, 1300, 1600, 1900. PA7 measures 1300, 1600, 1900 us for those commands. ADC reads 15.983 V and 10.010 A. Cell 1 reads -0.500 N until the one HX717 read at 120 ms, then -0.250 N; after `F10.5` cell 1 reads -0.750 N (on 0.10.0: -1.000, raw 0) and 8 bytes are written to the EEPROM at 0x10. All run.sh assertions pass. |
| B | same ELF, HSE 24 MHz (what the sim assumes when a board declares no crystal), `HSE=24000000 sh sim/run.sh` | The PLL gives 144 MHz, so every timer derived from the 150 MHz assumption runs 4.17 % slow: telemetry period 52.094 ms, PA7 pulses 1354, 1666, 1979 us for the same 1300, 1600, 1900 commands, idle 1041 to 1044 us. The firmware code is correct for 25 MHz; this row shows what a wrong crystal declaration costs. Assertions that do not depend on the crystal pass. |
| C | A plus `sim/firmware-cnt-preset.patch` (clock counter preset 15 instead of 0xFFFF), `ELF=thrust-v2-patched.elf sh sim/run.sh` | Same as A for everything above. On 0.10.0 the load-cell clock stopped after two pulses; not re-run on 0.10.2. |

Not run: the first firmware (`firmware/v1`, USART2/ADC2/TIM15/16, no EEPROM), the C# Thrustlink application, any real stand.
The crystal on the real board was not checked: the HAL's `HSE_VALUE` is 25 MHz and `hardware/v2/main.SchDoc` contains the string `25MHz` (which part it labels was not checked); `sim/stand.board` declares 25 MHz.

### Screenshots

The two figures are drawn by `sim/plot.py` from the captures of `sim/run.sh`; nothing is mocked.

![telemetry](sim/screenshots/telemetry-25mhz.png)

Configuration A, 2.6 s virtual, sim 0.10.0 (build f219eb31), not regenerated. Top: ESC pulse as the firmware echoes it in its telemetry and as measured on PA7 (vertical lines: the commands the PC peer sent). Middle: V and A from ADC2. Bottom: cell forces; cell 1 steps by -0.5 N when `F10.5` raises its offset. The forces are only the EEPROM offset because no HX717 read completes.

![crystal](sim/screenshots/crystal-25-vs-24mhz.png)

Configurations A and B, 2.6 s virtual each, sim 0.10.0 (build f219eb31): measured PA7 pulse width and telemetry period for the two crystal declarations.

### Gaps (found, not worked around)

* **HX717 read gets 24 clock pulses, not 25 (sim 0.10.2).** The 0.10.0 failure (no CC3 callback after the first) is gone after the down-counting timer compare fix. In the 4 s capture (`sim/captures/run4s-stdout.log`, `--trace-symbol HAL_TIM_PWM_PulseFinishedCallback`): `HAL_TIM_PWM_Start_IT` at 54.159 ms, a CC3 callback 1 us later (before the first PWM period), the next callback at 119.679 ms (65.5 ms after the start) and then one every 16.0 us (the first interval is 25.7 us), 25 callbacks in total. The firmware counts that early callback as pulse 1, so the read has 24 real PD_SCK pulses; `PulseCounter` reaches 25, the clock is stopped, and the peer, which counts PD_SCK rising edges, sees 24 and never returns DOUT high ("HX717 reads completed: none"). The cell raw value is 2500 for the peer's 5000, which is the 24-bit sample shifted right by one, consistent with an early first sample. No second `HAL_TIM_PWM_Start_IT` occurs in 4 s: `main.c` starts a read only when all six DOUT pins are low, and after the 24th pulse they hold the last data bit. A firmware change that would give 25 real pulses is clearing CC3IF before `HAL_TIM_PWM_Start_IT`; not tried here, and not checked against silicon (the early callback is consistent with CC3IF left set by the init-time `HAL_TIM_PWM_Start`/`Stop` at `main.c` lines 580-583). `sim/check.py` expectations for cell 1 changed from -1.000 (raw 0) to -0.750 (raw 2500) for this reason; the "reads completed" line still prints `none`.
* ADC inputs are constant; a current sensor that follows thrust needs a dynamic source.
* The thrust model in `peers/loadcells.py` and the calibration image in `peers/m24c01.py` are invented (marked `MODELED SIMPLIFICATION`); no value is from a real stand.

### Run it

```sh
sh sim/build.sh              # firmware/v2 -> sim/build/thrust-v2.elf (needs arm-none-eabi-gcc)
sh sim/build.sh patched      # optional: configuration C's ELF
sh sim/run.sh                # configuration A, asserts on the UART output and peer reports
HSE=24000000 sh sim/run.sh   # configuration B
python3 sim/plot.py "build string"   # screenshots, needs matplotlib
```

`sim` is the Simantic simulator CLI. `sim/peers/` holds the peers (`host.py`, `loadcells.py`, `m24c01.py`).

### Changes to the firmware

None for configurations A and B: `firmware/v2` is built as committed, only the build is driven by `sim/build.sh`
instead of STM32CubeIDE (float printf/scanf are linked because the code formats and parses floats).
Configuration C applies `sim/firmware-cnt-preset.patch` to a scratch copy under `sim/build/`: two lines,
`__HAL_TIM_SET_COUNTER(&CELLAMP_CLK_HTIM, 0xffff)` becomes `15`. It exists only to test the gap above and is not part of the default run.

### Licence

Upstream is MIT (see `LICENSE`). The files under `sim/` are additions of this fork, offered under the same licence.
