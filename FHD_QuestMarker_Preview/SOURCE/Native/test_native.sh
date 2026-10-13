#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
out="$(mktemp)"
trap 'rm -f "$out"' EXIT
gcc -m32 -std=c11 -O2 -ffreestanding -fno-builtin -fno-stack-protector \
    -fno-asynchronous-unwind-tables -fno-pic -fno-pie -nostdlib -no-pie \
    -Wl,-e,_start test_native.c -o "$out"
if [[ "${FHD_TEST_EMULATE:-0}" == 1 ]]; then
    python3 test_native_emulate.py "$out"
else
    "$out"
fi
