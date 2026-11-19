#!/bin/sh
# Runs the stock thrust-stand firmware (prebuilt stripped ELF sim/fw/thrust-v2.elf, STM32G431CB, 25 MHz crystal)
# for 2.6 virtual seconds against the scripted PC, load-cell and EEPROM peers, then runs sim/check.py.
# Pass means: telemetry on USART3 at 50 ms, ESC pulses 1000/1300/1600/1900 echoed and measured on PA7,
# ADC2/DMA volts and amps correct, cell 1 calibration written to the EEPROM over I2C, load-cell read as documented.
cd "$(dirname "$0")/.." || exit 1
SIM=${SIM:-sim}; HSE=25000000
OUT=$(mktemp -d sim/.test.XXXXXX); trap 'rm -rf "$OUT"' EXIT
sed "s/hseFrequency: .*/hseFrequency: $HSE/" sim/stand.board > "$OUT/stand.board"
sed "s#elf: .*#elf: ../fw/thrust-v2.elf#" sim/scenario.yaml > "$OUT/scenario.yaml"
"$SIM" run --scenario "$OUT/scenario.yaml" --timeout 2.6 --ascii \
  --expect "1000 15.9" --expect "1300 15.9" --expect "1900 15.9" --expect "1000 15.9" \
  > "$OUT/uart.log" 2> "$OUT/sim.log" || { echo "FAIL sim exit"; exit 1; }
python3 -I sim/check.py "$HSE" thrust-v2.elf "$OUT"
