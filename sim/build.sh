#!/bin/sh
# Sim addition. Builds firmware/v2 (STM32G431CBUx, the CubeIDE project) into sim/build/thrust-v2.elf
# with arm-none-eabi-gcc directly; no CubeIDE needed, no source file is modified.
# `sh sim/build.sh patched` builds a scratch copy with sim/firmware-cnt-preset.patch applied instead
# (-> sim/build/thrust-v2-patched.elf); `FIX=1 sh sim/build.sh` does the same with sim/proposed-firmware-fix.patch (-> thrust-v2-fixed.elf); the tracked sources are never touched.
# Float printf/scanf are linked because the firmware formats and parses floats on its UART.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NAME=thrust-v2
if [ "$1" = patched ] || [ -n "$FIX" ]; then
  P=firmware-cnt-preset; NAME=thrust-v2-patched
  [ -n "$FIX" ] && { P=proposed-firmware-fix; NAME=thrust-v2-fixed; }   # FIX=1: the PROPOSED stale-CC3IF fix
  rm -rf "$ROOT/sim/build/v2-patched"; mkdir -p "$ROOT/sim/build"
  cp -R "$ROOT/firmware/v2" "$ROOT/sim/build/v2-patched"
  (cd "$ROOT/sim/build/v2-patched" && patch -p3 < "$ROOT/sim/$P.patch")
  cd "$ROOT/sim/build/v2-patched"
else
  cd "$ROOT/firmware/v2"
fi
OUT="$ROOT/sim/build"; mkdir -p "$OUT"
SRC="Core/Src/main.c Core/Src/stm32g4xx_it.c Core/Src/stm32g4xx_hal_msp.c Core/Src/syscalls.c Core/Src/sysmem.c Core/Src/system_stm32g4xx.c Core/Startup/startup_stm32g431cbux.s"
for f in Drivers/STM32G4xx_HAL_Driver/Src/*.c; do
  case "$f" in *_template.c) ;; *) SRC="$SRC $f" ;; esac
done
arm-none-eabi-gcc -mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard -Os -g -std=gnu11 \
  -ffunction-sections -fdata-sections -DUSE_HAL_DRIVER -DSTM32G431xx \
  -ICore/Inc -IDrivers/STM32G4xx_HAL_Driver/Inc -IDrivers/STM32G4xx_HAL_Driver/Inc/Legacy \
  -IDrivers/CMSIS/Device/ST/STM32G4xx/Include -IDrivers/CMSIS/Include \
  -TSTM32G431CBUX_FLASH.ld --specs=nano.specs -u _printf_float -u _scanf_float -Wl,--gc-sections \
  $SRC -o "$OUT/$NAME.elf" -lc -lm
arm-none-eabi-size "$OUT/$NAME.elf"
