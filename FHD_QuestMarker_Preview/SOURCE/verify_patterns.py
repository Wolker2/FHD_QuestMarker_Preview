"""Validate ABI/code relationships by instruction signatures, without an EXE hash.
Usage: python SOURCE/verify_patterns.py /path/to/Rangers.exe
"""
from pathlib import Path
import json,re,struct,sys
from verify_release import PE

def resolve(path):
    pe=PE(path)
    assert pe.machine==0x14c,'Only i386 PE32 games are supported'
    base=pe.u32(pe.opt+28)
    definitions=json.loads((Path(__file__).parent/'Native/game_patterns.json').read_text())
    positions={};resolved={}
    for d in definitions['definitions']:
        data=bytes.fromhex(d['data']);mask=bytes.fromhex(d['mask'])
        run=max(re.finditer(b'\xff+',mask),key=lambda m:m.end()-m.start());anchor=data[run.start():run.end()]
        found=[]
        for rva,size,raw,rawsize,flags in pe.sections:
            if flags&0x60000000!=0x60000000:continue
            section=pe.data[raw:raw+rawsize];cursor=0
            while True:
                cursor=section.find(anchor,cursor)
                if cursor<0:break
                at=cursor-run.start();cursor+=1
                if at<0 or at+len(data)>len(section):continue
                if all(not flag or section[at+i]==value for i,(value,flag) in enumerate(zip(data,mask))):found.append(rva+at)
        assert len(found)==1,f'{d["name"]}: signature has {len(found)} matches'
        at=positions[d['name']]=found[0];operand=at+d['offset']
        if d['kind']=='relative':
            target=operand+4+struct.unpack('<i',pe.at(operand,4))[0]
            body=pe.at(target,len(bytes.fromhex(d['guard'])))
            assert all(not f or body[i]==v for i,(v,f) in enumerate(zip(bytes.fromhex(d['guard']),bytes.fromhex(d['guard_mask'])))), 'Derived AddChoice body mismatch'
        elif d['kind'] in ('writable','indirect_writable'):
            target=struct.unpack('<I',pe.at(operand,4))[0]-base
            if d['kind']=='indirect_writable':target=struct.unpack('<I',pe.at(target,4))[0]-base
            assert any(rva<=target and target+4<=rva+size and flags&0xc0000000==0xc0000000 for rva,size,_,_,flags in pe.sections), 'Global is outside writable image data'
        else:target=operand
        resolved[d['name']]=target
    for edge in definitions['edges']:
        at=positions[edge['source']]+edge['operand']
        target=at+4+struct.unpack('<i',pe.at(at,4))[0]
        assert target==resolved[edge['target']],f'Wrong call: {edge["source"]} -> {edge["target"]}'
    target=struct.unpack('<I',pe.at(resolved['CallbackStore']+6,4))[0]-base
    assert target==resolved['MessageRightClick'],'Wrong message callback'
    for name in ['GalaxyGlobal','GalaxyScreenGlobal','FuelBaseGlobal','FuelBoostGlobal']:
        assert resolved[name]==resolved[name+'Check'],name+': consumers disagree'
    return resolved

if __name__=='__main__':
    symbols=resolve(sys.argv[1]);print('PASS:',len(symbols),'uniquely resolved code/data signatures and their call relationships; no version/hash selection')
