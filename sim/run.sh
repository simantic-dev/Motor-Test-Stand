#!/bin/sh
# Sim addition. Runs the thrust stand firmware (sim/scenario.yaml) for 2.6 virtual seconds and checks its
# own UART output and the peers' reports. Needs `sim` on PATH (or SIM=...) and sim/build/*.elf from sim/build.sh.
#   sh sim/run.sh                       25 MHz crystal, stock firmware      (configuration A)
#   HSE=24000000 sh sim/run.sh          24 MHz crystal, stock firmware      (configuration B)
#   ELF=thrust-v2-patched.elf sh sim/run.sh   25 MHz, firmware + sim/firmware-cnt-preset.patch (C)
# Output in sim/out/<hse>-<elf>/: uart.log (USART3 both directions, timestamped), sim.log (peer logs).
set -e
cd "$(dirname "$0")/.."
SIM=${SIM:-sim}; HSE=${HSE:-25000000}; ELF=${ELF:-thrust-v2.elf}
[ -f "sim/build/$ELF" ] || { echo "build first: sim/build.sh [patched]"; exit 1; }
OUT=sim/out/$HSE-${ELF%.elf}; mkdir -p "$OUT"
sed "s/hseFrequency: .*/hseFrequency: $HSE/" sim/stand.board > $OUT/stand.board
sed "s#elf: .*#elf: ../../build/$ELF#" sim/scenario.yaml > $OUT/scenario.yaml
"$SIM" run --scenario $OUT/scenario.yaml --timeout 2.6 --ascii \
  --expect "1000 15.9" --expect "1300 15.9" --expect "1900 15.9" --expect "1000 15.9" \
  > "$OUT/uart.log" 2> "$OUT/sim.log"
python3 -I sim/check.py "$HSE" "$ELF" "$OUT"
