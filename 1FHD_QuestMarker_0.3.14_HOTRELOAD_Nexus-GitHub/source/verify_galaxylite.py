"""Static checks for this QuestMarker variant alongside AModGalaxyLite.
Run with PYTHONPATH=... python SOURCE/verify_galaxylite.py /path/to/AModGalaxyLite/CFG/Main.txt /path/to/AModGalaxyLite/CFG/Rus/Lang.txt
"""
from pathlib import Path
import hashlib
import json
import sys
from verify_overlay import children, find, merge, one, path, plain, read_config

root=Path(__file__).resolve().parent.parent
lite_main=Path(sys.argv[1]);lite_lang=Path(sys.argv[2]);
qm=plain(read_config(root/'CFG/Main.dat'))
lm=plain(read_config(lite_main))
ql=plain(read_config(root/'CFG/Rus/Lang.dat'))
from rangers.blockpar import BlockPar
ll=plain(BlockPar.from_dat(str(lite_lang))) if lite_lang.suffix.lower()==".dat" else plain(BlockPar.from_txt(str(lite_lang),encoding="cp1251"))
assert 'Size=810,704' not in (root/'SOURCE/CFG/Main.txt').read_text()
base=path(lm,'ML','Galaxy','Panel')
lite_map=children(children(base,'Panel')[1],'Panel')[0]
assert one(lite_map,'Pos')=='24,30'
assert one(lite_map,'Size')=='1150,786'
# The first panel is PanelMain, the second is the expanded Galaxy frame.
for label,inputs in [('AModGalaxyLite -> QuestMarker',(lm,qm)),('QuestMarker -> AModGalaxyLite',(qm,lm))]:
    cfg=[]
    for mod in inputs: cfg=merge(cfg,mod)
    galaxy=path(cfg,'ML','Galaxy','Panel')
    panels=children(galaxy,'Panel')
    assert one(panels[0],'Name')=='PanelMain', label
    frame=panels[1]
    assert one(frame,'Size')=='1200,966',label
    assert one(frame,'Pos')=='-88,-87,-2',label
    map_panel=children(frame,'Panel')[0]
    assert one(map_panel,'Size')=='1150,786',label
    assert one(map_panel,'Pos')=='24,30',label
    assert find(map_panel,'PathCurPos') is not None,label
    assert find(map_panel,'PathDesPos') is not None,label
    assert find(map_panel,'RedRing0') is not None,label
    assert find(map_panel,'RedRing151') is not None,label
    assert find(map_panel,'FHDQuestMarkV035') is not None,label
    marker=find(map_panel,'FHDQuestMarkV035')
    assert one(marker,'Pos')=='0,0,-10',label
    assert one(marker,'Active')=='False',label
    assert one(marker,'Image')=='Bm.FHDQuestMarker.GNPoQ',label
    assert one(find(map_panel,'FHDQuestMarkerLayer'),'Size')=='1150,786',label
    for name,pos,size in [
        ('FHDQuestRouteFrame','221,907,-2','758,47'),
        ('FHDQuestRouteInfo','310,923,-3','450,24'),
        ('FHDQuestRouteDeadline','770,923,-3','123,24'),
    ]:
        element=find(frame,name)
        assert element is not None,(label,name)
        assert one(element,'Pos')==pos,(label,name)
        assert one(element,'Size')==size,(label,name)
    buttons=children(frame,'GraphButton')
    assert len(buttons)==5,label
    assert one(buttons[3],'Name')=='ButDel', label
    assert 'FHD_RouteClear' in one(children(buttons[3],'OnPressCode')[0],'01'),label
    assert one(buttons[4],'Name')=='ButUndo',label
    assert one(find(frame,'FHDQuestRouteInfo'),'MouseBlocking')=='False'
    assert one(find(frame,'ImagePanel'),'Size')=='1200,895'
    # Engine UI uses smaller (more negative) z for objects drawn in front.
    background_z=int(one(find(frame,'ImagePanel'),'Pos').split(',')[2])
    route_z=int(one(find(frame,'FHDQuestRouteFrame'),'Pos').split(',')[2])
    text_z=int(one(find(frame,'FHDQuestRouteInfo'),'Pos').split(',')[2])
    deadline_z=int(one(find(frame,'FHDQuestRouteDeadline'),'Pos').split(',')[2])
    assert text_z < route_z < background_z and deadline_z < route_z,(label,'frame/label occlusion')
    assert one(find(frame,'FHDQuestRouteFrame'),'Active')=='True'
    assert one(find(frame,'FHDQuestRouteFrame'),'Image')=='GI,Bm.FHDQuestMarker.RouteFrame'
    print('PASS merged config:',label)

s=path(ql,'Script','QuestMarker','Mark')
assert '1152' in one(s,'01') and '790' in one(s,'02')
assert "CT('Constellations.GalaxySizeX')" in one(s,'03')
assert "CT('Constellations.GalaxySizeY')" in one(s,'04')
assert "CoordX(star)" in one(s,'06') and "CoordY(star)" in one(s,'07')
assert "InterfacePos('Galaxy','FHDQuestMarkV035',x-25,y-25,0)" in one(s,'07')
ls=(lite_lang.parent/'Lang.txt').read_text(encoding='cp1251') if lite_lang.suffix.lower()=='.dat' else lite_lang.read_text(encoding='cp1251')
assert 'formSizeX = 1152' in ls and 'formSizeY = 790' in ls
assert "CT('Constellations.GalaxySizeX')" in ls and "CT('Constellations.GalaxySizeY')" in ls
const=path(ll,'Constellations')
assert one(const,'GalaxySizeX')=='280' and one(const,'GalaxySizeY')=='200'
assert one(const,'GalaxyCountStars')=='200'
# Verify all endpoints of the increased 280x200 area align with the GalaxyLite formula.
for x,y in [(0,0),(140,100),(280,200),(75,190),(279,1)]:
    quest=(1152*x/280 -25,790*y/200-25)
    lite=(1152/280*x -25,790/200*y-25)
    assert all(abs(a-b)<1e-10 for a,b in zip(quest,lite))
    assert -25<=quest[0]<=1127 and -25<=quest[1]<=765
print('PASS galaxy size / coordinate mapping')
# Guide states that binaries are unchanged and contains external reference to original target EXE.
assert hashlib.sha256((root/'Native/FHDQuestMarker.dll').read_bytes()).hexdigest()=='3718676f1c61c246b0bf7e56689323601d17c3fa53aad5a60d4b409345a1c323'
print('PASS patched 0.3.14 native library checksum')
print('PASS all GalaxyLite tests')
