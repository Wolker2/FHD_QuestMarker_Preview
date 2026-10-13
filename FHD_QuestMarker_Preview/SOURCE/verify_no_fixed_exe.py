"""Verify production DLL source has no hard-coded RVAs and no version gate."""
from pathlib import Path
import re
root=Path(__file__).resolve().parent
marker=(root/'Native/quest_marker.c').read_text()
route=(root/'Native/quest_route.h').read_text()
resolver=(root/'Native/game_resolver.h').read_text()
for text in (marker,route):
    assert not re.search(r'\bgame\s*\+\s*0x[0-9a-fA-F]+',text), 'Fixed EXE RVA found'
    assert not re.search(r'route_call\(0x[0-9a-fA-F]+',text), 'Fixed route-call RVA found'
    assert not re.search(r'0x461000|0x6ac53b97|EXE_SHA',text,re.I), 'Build-specific gate found'
assert 'game_find_pattern' in resolver and 'if(found)return 0' in resolver
assert 'game_resolve(game,gameSymbols)' in marker
assert 'GS_GetPlayer' in route and 'GS_GalaxyOpen' in route
print('PASS: no fixed EXE offsets, build timestamp/size gate, or fixed route-call RVA')
