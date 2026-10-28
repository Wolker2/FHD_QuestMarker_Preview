#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
output="${1:-../../Native/FHDQuestMarker.dll}"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
mkdir -p "$(dirname "$output")"
gcc -m32 -std=c11 -O2 -ffreestanding -fno-builtin -fno-stack-protector -fno-asynchronous-unwind-tables -fno-pic -fno-pie -c quest_marker.c -o "$work/quest_marker.o"
python3 elf_to_coff.py "$work/quest_marker.o" "$work/quest_marker.coff"
ld -m i386pe --no-leading-underscore --shared --entry DllMain --subsystem console --image-base 0x13000000 --disable-auto-import --no-insert-timestamp "$work/quest_marker.coff" quest_marker.def -o "$output"
