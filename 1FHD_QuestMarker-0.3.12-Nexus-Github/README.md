# FHD Quest Marker Preview 0.3.12 — review sources

Пакет исходников для GitHub и проверки модераторами. Все 14 рабочих файлов мода, включая DLL, пересобираются побайтово точно. C-исходники предоставлены в исходном архиве; ручное восстановление проекта на вашем ПК не требуется. Пакет содержит меньше 100 файлов.

## Content and build inputs

This package preserves the runtime behavior of `FHD_QuestMarker_Preview_0.3.12(new exe).rar`. Original metadata credits **Prolog_D**. It includes the supplied C/header sources, recovered editable configuration/graphics sources, automated build and verification. No specific Nexus moderator checklist was attached; the checks below establish reconstruction and test results, not moderation approval.

| Source | Rebuilt runtime files |
| --- | --- |
| `SOURCE/Native/` | `Native/FHDQuestMarker.dll` from supplied C/headers and DEF |
| `SOURCE/CFG/*.json` | Main.dat, CacheData.dat, Rus/Lang.dat |
| `SOURCE/Assets/graphics.json` | Eight GI images and one GAI animation containing twenty GI frames |
| `SOURCE/ModuleInfo.txt` | Original CP1251 metadata |

No SCR was supplied, so an RSON project is unnecessary. Script text is visible in the configuration JSON. Native C/header/DEF files are preserved from the upload, not decompiled substitutes. The ELF-to-COFF conversion tool is also supplied source. All object files and DLL output are created in temporary directories.

The original CFG text contained the same leaf values as the packed configs, but compiling it did not reproduce all original block-order/sort metadata. The lossless JSON is therefore the authoritative configuration source. It preserves repeated blocks, ordering, flags and original encryption seeds. Runtime config bytes remain unchanged.

GI/GAI JSON describes geometry, RGB565 pixel values, transparency/RLE commands, animation frames and sequence records. No prebuilt GI/GAI or opaque encoded payload is required. The animation's auxiliary sequence values are preserved as typed integers without assigning them an unverified meaning. `SOURCE/layout.json` retains the supplied UI measurements; its 0.3.11 label reflects the unchanged layout inherited by 0.3.12.

## Automatic build and checks

Verified tools: **GCC 13.3.0**, **GNU binutils 2.42**, **Python 3.12.14**, **zlib 1.3.2**. The build uses Python's standard library plus GNU gcc/ld. It emits PE32/i386 through a freestanding ELF32 object and the supplied COFF converter; no Windows runtime or MinGW library is linked.

```sh
python3 -m pip install -r requirements-tests.txt
python3 tests/verify.py --report dist/ci-verification.json
python3 build.py --verify-original
```

GitHub Actions performs these steps and publishes an install ZIP and fresh report as a downloadable artifact. Output: `dist/FHD_QuestMarker-0.3.12-install.zip`, under `Mods/FHD_MODS/FHD_QuestMarker_Preview/`. This contains the 14 rebuilt mod files only. For intentional edits, omit `--verify-original`, which enforces the uploaded runtime hashes. Different compiler, linker or zlib versions may change binary bytes.

Unicorn 2.1.4 runs the supplied freestanding i386 ABI/object fixture. PeFile 2024.8.26 is used by the optional actual-EXE integration test. Neither is a runtime dependency of the mod. A game EXE is unnecessary for building or the synthetic/overlay/planner tests.

## Target EXE and external dependency

The mod requires **UtilityFunctionsPack**, declared by the original ModuleInfo. It was not supplied and is not bundled here. Native loading uses the game's `Data.ScriptLibs` mechanism; the supplied source states that XenoNativeLoader is unnecessary.

The uploaded `Rangers.exe` was used as a **compatibility reference**, not edited or rebuilt. It is not included in the source package or generated install ZIP. Exact target:

- SHA-256: `e43a4b15503c705eebe2d8ce5778c2a2fb090db515a3fd86d319e5c5aa692ebf`.
- Size: 4,533,760 bytes; PE SizeOfImage `0x461000`; TimeDateStamp `0x6AC53B97`.
- Reported version: 2.1.2500. That version string alone does not establish binary compatibility.

`SOURCE/EXE_COMPATIBILITY.md` preserves the supplied address-migration and hook notes. The DLL checks image metadata and guarded instruction bytes; the Python compatibility check additionally requires the full target SHA-256.

When that exact EXE is available, the optional verification command is:

```sh
python3 tests/verify.py --exe /path/to/Rangers.exe --report dist/exe-verification.json
```

This check was already run here using the attached EXE. It is not a prerequisite for reconstructing the mod. GitHub CI runs the checks available without distributing that EXE and explicitly reports that actual target-EXE bytes were not tested there.

## Verification performed

`build-verification.json` records **29 source/serialization/reference checks** and **six successful test stages** (one stage compiles the route fixture):

- Isolated source-only rebuild: all 14 runtime SHA-256 hashes match the upload, including the C-built DLL, three configs, all GI images and the complete GAI sequence/frames.
- Local resource paths and all 16 configured native export bindings resolve.
- The supplied overlay checks pass against the Galaxy UI from the user's vanilla snapshot, and with the previously supplied FHD_Trade overlay in both merge orders. They cover reset controls, background/frame preservation, animated marker, green text, deadline fields and anchors at four resolutions. Minimal JSON fixtures and provenance are included.
- The supplied route-planner fixture passes **5000 comparisons with an independent fuel-state BFS oracle**, plus reachability, refueling, geometry and hyperspace timing cases.
- The supplied freestanding i386 fixture passes Delphi ABI, route preparation/application/reset, ETA ledger, same-system/moving-planet/ship objectives, deadlines, animated marker cleanup and panel-click tests using synthetic game objects.
- The rebuilt DLL passes PE32/i386/export/relocation checks, has no static imports, and matches **21 function guards** plus three map-hook prologues in the exact supplied EXE.
- Actual EXE/DLL bytes pass emulated initialization, repeated initialization, quest capture and callback fallback, all **seven hooks**, and trampoline register/stack/object effects. Unsupported metadata or damaged signatures are rejected before code mutation in the tested cases. Windows APIs are synthetic fixtures.

No Windows game session or interactive UI was launched. These tests do not establish real save compatibility, live loader behavior, real travel-time accuracy or the suggested ±5–7-day estimate. `VERIFICATION.md` preserves the supplied in-game checklist. Metadata advertises Russian/English, while only the Russian language config was supplied; no translation or extra language DAT was invented.

## Exclusions and provenance

The source ZIP stays below the requested 100-file limit. It excludes the game EXE, original archive, generated DLL/DAT/GI/GAI/install ZIP, object files, caches and git history. It also excludes the unused 1.2 MB `RouteFrame_original.gi` design baseline, superseded text CFG copies, old output hashes and redundant helper scripts. The actual supplied runtime frame and every runtime image are retained as typed source and rebuild exactly; no resizing or layout change was applied.

Input archive SHA-256: `1bb50d7668cef516c328c2530a51c8fa5b534682355ada0e46d1cae44ca03378` (2,367,541 bytes). `original-file-sha256.json` contains all fourteen runtime hashes; `recovery-notes.json` records the source/exclusion decisions. The source upload remains unchanged.

The DAT codec reimplements the format used by Sergei Osminin's MIT-licensed rangers-utils. GI/GAI layout was cross-checked with the existing local game-structure research. This packaging does not claim authorship of the original mod or assign it a new license; no original mod license file was supplied.
