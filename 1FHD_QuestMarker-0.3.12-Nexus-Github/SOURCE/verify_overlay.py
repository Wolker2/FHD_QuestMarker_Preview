from pathlib import Path
import sys
import json
from collections import defaultdict
sys.path.insert(0,str(Path(__file__).resolve().parent/'lib'))
from dat_codec import decode

# TBlockParEC.MergeFrom: blocks match by name and occurrence, strings replace.
def plain(block):
    if 'root' in block:block=block['root']
    return [(e['name'],plain(e['value']) if e['kind']=='block' else e['value']) for e in block['entries']]
def merge(base, overlay):
    out=[(k, merge(v, []) if isinstance(v,list) else v) for k,v in base]
    seen=defaultdict(int)
    for name,value in overlay:
        if isinstance(value,list):
            index=seen[name];seen[name]+=1
            slots=[i for i,(k,v) in enumerate(out) if k==name and isinstance(v,list)]
            if index<len(slots):
                i=slots[index];out[i]=(name,merge(out[i][1],value))
            else:out.append((name,merge(value,[])))
        else:
            out=[(k,v) for k,v in out if not(k==name and isinstance(v,str))]
    out.extend((k,v) for k,v in overlay if isinstance(v,str))
    return out
def children(b,k):return [v for n,v in b if n==k and isinstance(v,list)]
def one(b,k):
    a=[v for n,v in b if n==k];return a[0] if a else None
def find(b,name):
    if one(b,'Name')==name:return b
    for k,v in b:
        if isinstance(v,list):
            hit=find(v,name)
            if hit is not None:return hit
    return None
def path(b,*parts):
    for p in parts:b=children(b,p)[0]
    return b

def read_config(p):
    p=Path(p)
    return json.loads(p.read_text('utf-8')) if p.suffix.lower()=='.json' else decode(p.read_bytes(),'blockpar')

def run(folder, vanilla, trading=None):
    base=plain(read_config(vanilla))
    mod=plain(read_config(folder/'CFG/Main.dat'))
    trade=plain(read_config(trading)) if trading else None
    overlay=path(mod,'ML','Galaxy','Panel')
    assert find(overlay,'FHDQuestClearButton') is None, 'Old free-floating reset button is still present'
    map_overlay=children(overlay,'Panel')[1]
    button_overlay=children(map_overlay,'GraphButton')
    assert len(button_overlay)==4, 'Expected three untouched buttons and the native ButDel patch'
    clear=button_overlay[3]
    assert one(clear,'ImageNormal')=='GI,Bm.FHDQuestMarker.ClearN'
    assert 'FHDQuestMarkV035' in one(children(clear,'OnPressCode')[0],'00')
    assert one(clear,'Caption') is None or one(clear,'Font'), 'Reset button creates a caption with an empty font cache key'
    # Verify the actual merged config, including the FHD_Trade used in the crash log.
    original=path(base,'ML','Galaxy','Panel')
    original_map=children(children(original,'Panel')[1],'Panel')[0]
    original_bg=children(original_map,'Image')[0]
    cases=[('vanilla',[mod])]
    if trade is not None:cases += [('quest + trade',[mod,trade]),('trade + quest',[trade,mod])]
    for label, overlays in cases:
        cfg=base
        for o in overlays:cfg=merge(cfg,o)
        galaxy=path(cfg,'ML','Galaxy','Panel')
        map_panel=children(children(galaxy,'Panel')[1],'Panel')[0]
        assert children(map_panel,'Image')[0]==original_bg, label+': background changed'
        frame=children(galaxy,'Panel')[1]
        button=find(frame,'ButDel')
        assert button is not None,label+': native map reset button missing'
        assert one(button,'Pos')=='369,567,-2' and one(button,'Size')=='37,37'
        assert one(button,'ImageNormal')=='GI,Bm.FHDQuestMarker.ClearN'
        assert 'FHDQuestMarkV035' in one(children(button,'OnPressCode')[0],'00')
        assert one(frame,'Pos')=='107,22,-2'
        if label=='vanilla':
            # TfGalaxy2.InitializeLayout adds half the extra screen width/height to frame position.
            x=107+(1920-1024)//2+369
            y=22+(1080-768)//2+567
            assert abs(x+18.5-943)<2 and abs(y+18.5-762)<3
        assert children(map_panel,'GAI')==children(original_map,'GAI'), label+': vanilla player/route icons changed'
        marker=find(map_panel,'FHDQuestMarkV035')
        assert marker is not None,label+': marker overwritten'
        assert one(marker,'Pos')=='0,0,-10',label+': InterfacePos origin is nonzero'
        assert one(marker,'Active')=='False'
        assert one(marker,'Image')=='GAI,Bm.FHDQuestMarker.GNPoQ'
        route_label=find(frame,'FHDQuestRouteInfo')
        details=find(frame,'FHDQuestRouteDeadline')
        assert route_label is not None and details is not None
        assert one(route_label,'Font')=='Font.2SmallBold'
        assert one(details,'Font')=='Font.2SmallBold'
        layout=json.loads((folder/'SOURCE/layout.json').read_text())
        lx,ly,lw,lh=layout['label_bounds'];dx,dy,dw,dh=layout['deadline_bounds']
        fx,fy,fw,fh=layout['frame_bounds'];ox,oy=layout['reference_frame_origin']
        assert one(route_label,'Pos')==f'{lx-ox},{ly-oy},-3'
        assert one(route_label,'Size')==f'{lw},{lh}'
        assert one(details,'Pos')==f'{dx-ox},{dy-oy},-3'
        assert one(details,'Size')==f'{dw},{dh}'
        assert one(route_label,'TextColor')=='0,255,0' and one(details,'TextColor')=='0,255,0'
        route_frame=find(frame,'FHDQuestRouteFrame')
        native_frame=find(frame,'ImagePanel')
        assert route_frame is not None and native_frame is not None
        assert one(route_frame,'Pos')==f'{fx-ox},{fy-oy},0'
        assert one(route_frame,'Size')==f'{fw},{fh}'
        assert one(route_frame,'MouseBlocking')=='False' and one(route_frame,'Active')=='True'
        assert native_frame==find(original,'ImagePanel'), 'Native frame image changed'
        assert float(one(route_frame,'Pos').split(',')[2]) > float(one(native_frame,'Pos').split(',')[2])
        assert one(frame,'Size')=='810,704'
        for width,height in [(1024,768),(1920,1080),(2560,1440),(3440,1440)]:
            origin=(107+(width-1024)//2,22+(height-768)//2)
            for x,y,w,h in [layout['frame_bounds'],layout['label_bounds'],layout['deadline_bounds']]:
                absolute=(origin[0]+x-ox,origin[1]+y-oy)
                assert absolute[0]-origin[0]==x-ox and absolute[1]-origin[1]==y-oy
                assert 0<=x-ox and x-ox+w<=810 and 0<=y-oy and y-oy+h<=704
                assert absolute[0]>=0 and absolute[1]>=0 and absolute[0]+w<=width and absolute[1]+h<=height
        print('PASS: measured frame bounds, green text, native frame in front, anchors at four resolutions')
        assert one(route_label,'Active')=='False' and one(details,'Active')=='False'
        assert 'FHD_RouteClear' in one(children(button,'OnPressCode')[0],'01')
        if trade in overlays:
            for i in range(10):
                for kind in ['Buy','Sell']:
                    assert find(map_panel,f'MGF{kind}Mark{i}') is not None,label+': trading marker overwritten'
        print('PASS:',label)
    lang=plain(read_config(folder/'CFG/Rus/Lang.dat'))
    mark=path(lang,'Script','QuestMarker','Mark')
    assert "InterfaceState('Galaxy','FHDQuestMarkV035',1)" in one(mark,'08')
    assert "InterfacePos('Galaxy','FHDQuestMarkV035',-25+x+CoordX(star)/5,-25+y,0)" in one(mark,'07')
    assert 'FHD_RouteClear' not in str(mark), 'Mark must preserve the pending route'
    place=path(lang,'Script','QuestMarker','Place')
    assert 'FHD_RouteClear' in one(place,'00')
    assert 'QuestMarker.Mark' in one(place,'01')
    assert "RunChildForm('Galaxy',2)" in one(place,'02'), 'Quest map must open in the playable jump mode used by M'
    offer=path(lang,'Script','QuestMarker','Return')
    assert 'FHD_RoutePrepare' in one(offer,'00')
    assert "RunChildForm('Galaxy',2)" in one(offer,'10')
    assert 'FHD_RouteTarget' in one(offer,'06') and 'QuestMarker.Mark' in one(offer,'06')
    assert 'FHD_RouteDeadlineText' in one(offer,'09')
    assert "InterfaceState('Galaxy','FHDQuestMarkV035',-1)" in one(offer,'13')
    assert one(details,'MouseBlocking')=='False'
    assert one(details,'Caption') is None
    assert find(overlay,'FHDQuestRouteDetailsButton') is None
    assert "QuestMarker.Place" not in str(offer)
    print('PASS: animated endpoint and deadline scripts compiled; reset and close clean the endpoint')

if __name__=='__main__':
    if len(sys.argv) not in (3,4):raise SystemExit('Usage: verify_overlay.py MOD_DIR VANILLA_MAIN [TRADE_MAIN]')
    run(Path(sys.argv[1]),sys.argv[2],sys.argv[3] if len(sys.argv)==4 else None)
