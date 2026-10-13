#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
gcc -m32 -std=c11 -O2 -ffreestanding -fno-builtin -fno-stack-protector -fno-asynchronous-unwind-tables -fno-pic -fno-pie -c quest_marker.c -o quest_marker.o
python3 elf_to_coff.py quest_marker.o quest_marker.coff
ld -m i386pe --no-leading-underscore --shared --entry DllMain --subsystem console --image-base 0x13000000 --disable-auto-import --no-insert-timestamp quest_marker.coff quest_marker.def -o ../../Native/FHDQuestMarker.dll
