#!/usr/bin/env python3
"""Compile the small BlockPar overlay using rangers-utils.

Usage: PYTHONPATH=/path/to/rangers-utils python SOURCE/build_dat.py
"""
from pathlib import Path
import struct
import zlib

from rangers.blockpar import BlockPar
from rangers.cachedata import CacheData
from rangers.io import Buffer

ROOT = Path(__file__).resolve().parent.parent
SEED = 0x51A2C3D4
KEY = 0xB1E8C689
CACHE_KEY = 0xEA8F3F37


def build(source: Path, output: Path) -> None:
    tree = BlockPar.from_txt(str(source), encoding="utf-8")
    content = Buffer.from_bytes(b"")
    tree.save(content, new_format=True)
    raw = content._io.getvalue()
    compressed = b"ZL01" + struct.pack("<I", len(raw)) + zlib.compress(raw, 9)
    digest = zlib.crc32(compressed)
    buffer = Buffer.from_bytes(struct.pack("<II", digest, SEED ^ KEY) + compressed)
    buffer.seek(8)
    buffer.cipher(SEED)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(buffer._io.getvalue())
    check = BlockPar.from_dat(str(output))
    assert check.getone("ML").getone("Gov").getone("Panel").getall("Panel")[1].getone("QuestReturnControl")
    galaxy = check.getone("ML").getone("Galaxy").getone("Panel")
    assert "QuestClearControl" not in galaxy
    frame = galaxy.getall("Panel")[1]
    assert len(frame.getall("GraphButton")) == 4
    clear = frame.getall("GraphButton")[3]
    assert clear.getone("ImageNormal") == "GI,Bm.FHDQuestMarker.ClearN"
    assert "Caption" not in clear  # Empty caption creates a label with no font.
    map_panel = galaxy.getall("Panel")[1].getone("Panel")
    assert "GAI" not in map_panel and "Image" not in map_panel
    marker = map_panel.getone("FHDQuestMarkerOverlay").getone("Image")
    assert marker.getone("Image") == "GAI,Bm.FHDQuestMarker.GNPoQ"
    assert marker.getone("Pos") == "0,0,-10"  # InterfacePos adds a delta.
    assert marker.getone("Active") == "False"


if __name__ == "__main__":
    build(ROOT / "SOURCE/CFG/Main.txt", ROOT / "CFG/Main.dat")
    build_lang = BlockPar.from_txt(str(ROOT / "SOURCE/CFG/Lang.txt"), encoding="utf-8")
    content = Buffer.from_bytes(b"")
    build_lang.save(content, new_format=True)
    raw = content._io.getvalue()
    compressed = b"ZL01" + struct.pack("<I", len(raw)) + zlib.compress(raw, 9)
    buffer = Buffer.from_bytes(struct.pack("<II", zlib.crc32(compressed), SEED ^ KEY) + compressed)
    buffer.seek(8)
    buffer.cipher(SEED)
    destination = ROOT / "CFG/Rus/Lang.dat"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(buffer._io.getvalue())
    assert BlockPar.from_dat(str(destination)).getone("Script").getone("QuestMarker")
    cache = CacheData.from_txt(str(ROOT / "SOURCE/CFG/CacheData.txt"), encoding="utf-8")
    cache_bytes = Buffer.from_bytes(b"")
    cache.save(cache_bytes)
    raw = cache_bytes._io.getvalue()
    compressed = b"ZL01" + struct.pack("<I", len(raw)) + zlib.compress(raw, 9)
    buffer = Buffer.from_bytes(struct.pack("<II", zlib.crc32(compressed), SEED ^ CACHE_KEY) + compressed)
    buffer.seek(8)
    buffer.cipher(SEED)
    destination = ROOT / "CFG/CacheData.dat"
    destination.write_bytes(buffer._io.getvalue())
    assert CacheData.from_dat(str(destination)).getone("Bm").getone("FHDQuestMarker").getone("GNPoQ").endswith("GNPoQ.gai")
    print("BlockPar and CacheData DAT round trip: OK")
