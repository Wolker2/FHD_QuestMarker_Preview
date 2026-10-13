from pathlib import Path
import sys
from collections import defaultdict
from rangers.blockpar import BlockPar

# TBlockParEC.MergeFrom: blocks match by name and occurrence, strings replace.
def plain(block):
    return [(n.content.name, plain(n.content.content) if isinstance(n.content.content, BlockPar) else n.content.content) for n in block._order_map]
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
    return BlockPar.from_txt(str(p),encoding='utf-8') if p.suffix.lower()=='.txt' else BlockPar.from_dat(str(p))

def run(folder, vanilla, trading):
    base=plain(read_config(vanilla))
    mod=plain(BlockPar.from_dat(str(folder/'CFG/Main.dat')))
    trade=plain(read_config(trading))
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
    for label, overlays in [('vanilla',[mod]),('quest + trade',[mod,trade]),('trade + quest',[trade,mod])]:
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
        if trade in overlays:
            for i in range(10):
                for kind in ['Buy','Sell']:
                    assert find(map_panel,f'MGF{kind}Mark{i}') is not None,label+': trading marker overwritten'
        print('PASS:',label)
    lang=plain(BlockPar.from_dat(str(folder/'CFG/Rus/Lang.dat')))
    place=path(lang,'Script','QuestMarker','Place')
    assert "InterfaceState('Galaxy','FHDQuestMarkV035',1)" in one(place,'08')
    assert "RunChildForm('Galaxy',2)" in one(place,'09'), 'Quest map must open in the playable jump mode used by M'
    print('PASS: marker script compiled and caption cannot load an empty font path')

if __name__=='__main__':
    if len(sys.argv)!=4:raise SystemExit('Usage: verify_overlay.py MOD_DIR VANILLA_MAIN TRADE_MAIN')
    run(Path(sys.argv[1]),sys.argv[2],sys.argv[3])
