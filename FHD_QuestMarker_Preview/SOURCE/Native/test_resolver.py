"""Build/run the C resolver on actual loaded PE bytes and adversarial fixtures.
Usage: python SOURCE/Native/test_resolver.py /path/to/Rangers.exe
No game is executed. Requires a Linux C compiler; test buffers fit PE32.
"""
from pathlib import Path
import copy,json,random,struct,subprocess,sys,tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from verify_release import PE

HERE=Path(__file__).resolve().parent
profile=json.loads((HERE/'game_patterns.json').read_text())
defs=profile['definitions'];count=len(defs)
pe=PE(sys.argv[1]);reference_base=pe.u32(pe.opt+28)
u32=lambda b,o:struct.unpack_from('<I',b,o)[0]
put=lambda b,o,v:struct.pack_into('<I',b,o,v&0xffffffff)

def mapped(base):
    size=pe.u32(pe.opt+56)
    data=bytearray(size)
    header_size=pe.u32(pe.opt+60);data[:header_size]=pe.data[:header_size]
    for rva,_,raw,rawsize,_ in pe.sections:data[rva:rva+rawsize]=pe.data[raw:raw+rawsize]
    rva,length=pe.directory(5);cursor=pe.offset(rva);end=cursor+length
    while cursor+8<=end:
        page,block=struct.unpack_from('<II',pe.data,cursor)
        if not block:break
        for p in range(cursor+8,cursor+block,2):
            entry=struct.unpack_from('<H',pe.data,p)[0]
            if entry>>12==3:
                at=page+(entry&4095);put(data,at,u32(data,at)+base-reference_base)
        cursor+=block
    put(data,pe.opt+28,base)
    expected=[]
    for d in defs:
        at=d['rva']+d['offset']
        if d['kind']=='relative':value=base+at+4+struct.unpack_from('<i',data,at)[0]
        elif d['kind'] in ('writable','indirect_writable'):
            value=u32(data,at)
            if d['kind']=='indirect_writable':value=u32(data,value-base)
        else:value=base+at
        expected.append(value)
    return data,expected

def synthetic(base):
    # Merge overlapping prefix/guard windows before independently shuffling
    # their positions. This preserves shared caller/consumer instruction bytes.
    intervals=[(d['rva'],d['rva']+len(bytes.fromhex(d['data']))) for d in defs]
    intervals += [(d['target_rva'],d['target_rva']+len(bytes.fromhex(d['guard']))) for d in defs if d.get('guard')]
    groups=[]
    for start,end in sorted(intervals):
        if groups and start<=groups[-1][1]:groups[-1][1]=max(end,groups[-1][1])
        else:groups.append([start,end])
    random.Random(312).shuffle(groups)
    cursor=0x2100;mapping=[]
    data=bytearray(0x16000)
    data[:2]=b'MZ';put(data,0x3c,0x80);data[0x80:0x84]=b'PE\0\0'
    struct.pack_into('<HH',data,0x84,0x14c,2);struct.pack_into('<H',data,0x94,224)
    struct.pack_into('<H',data,0x98,0x10b);put(data,0x98+28,base);put(data,0x98+56,len(data))
    for index,(name,start,size,flags) in enumerate([(b'.text',0x2000,0xe000,0x60000020),(b'.data',0x10000,0x6000,0xc0000040)]):
        section=0x178+40*index;data[section:section+len(name)]=name
        put(data,section+8,size);put(data,section+12,start);put(data,section+16,size);put(data,section+36,flags)
    for start,end in groups:
        mapping.append((start,end,cursor));data[cursor:cursor+end-start]=pe.at(start,end-start)
        cursor+=(end-start+127)&~127
    assert cursor<0xe000
    def move(rva):
        for start,end,where in mapping:
            if start<=rva<end:return where+rva-start
        raise ValueError(hex(rva))
    globals_={};data_cursor=0x10100
    def global_location(old_va):
        nonlocal data_cursor
        if old_va not in globals_:
            globals_[old_va]=data_cursor;data_cursor+=16
        return base+globals_[old_va]
    for d in defs:
        if d['kind']=='writable':put(data,move(d['rva'])+d['offset'],global_location(u32(pe.at(d['rva']+d['offset'],4),0)))
        elif d['kind']=='indirect_writable':
            slot=u32(pe.at(d['rva']+d['offset'],4),0)
            target=u32(pe.at(slot-reference_base,4),0)
            new_slot=global_location(slot);put(data,move(d['rva'])+d['offset'],new_slot)
            put(data,new_slot-base,global_location(target))
        elif d['kind']=='relative':
            at=move(d['rva'])+d['offset'];put(data,at,move(d['target_rva'])-(at+4))
    symbols={d['name']:(move(d['target_rva']) if d['kind']=='relative' else move(d['rva'])+d['offset']) for d in defs if d['kind'] in ('code','relative')}
    for edge in profile['edges']:
        source=next(d for d in defs if d['name']==edge['source'])
        at=move(source['rva'])+edge['operand'];put(data,at,symbols[edge['target']]-(at+4))
    put(data,symbols['CallbackStore']+6,base+symbols['MessageRightClick'])
    expected=[]
    for d in defs:
        if d['kind'] in ('code','relative'):expected.append(base+symbols[d['name']])
        else:
            at=move(d['rva'])+d['offset'];value=u32(data,at)
            if d['kind']=='indirect_writable':value=u32(data,value-base)
            expected.append(value)
    return data,expected,move

with tempfile.TemporaryDirectory(prefix='fhd-resolver-') as temporary:
    temp=Path(temporary);executable=temp/'test_resolver'
    subprocess.run(['cc','-O2','-Wall','-Wextra',str(HERE/'test_resolver.c'),'-o',str(executable)],check=True)
    cases=[]
    actual,expected=mapped(0x04000000)
    cases.append(('provided_exe_rebased',True,actual,expected,0x04000000))
    alternate,alternate_expected=mapped(0x05000000)
    put(alternate,0x80+8 if u32(alternate,0x3c)==0x80 else u32(alternate,0x3c)+8,0x12345678)
    alternate.extend(bytes(0x2000));put(alternate,pe.opt+56,len(alternate))
    cases.append(('different_timestamp_and_image_size',True,alternate,alternate_expected,0x05000000))
    moved,moved_expected,move=synthetic(0x06000000)
    cases.append(('individually_moved_functions_and_globals',True,moved,moved_expected,0x06000000))
    bad=bytearray(moved)
    player=next(d for d in defs if d['name']=='GetPlayer');pos=move(player['rva']);length=len(bytes.fromhex(player['data']))
    bad[0xe800:0xe800+length]=bad[pos:pos+length]
    cases.append(('ambiguous_function_rejected',False,bad,moved_expected,0x06000000))
    bad=bytearray(moved);edge=next(e for e in profile['edges'] if e['target']=='GetPlayer')
    source=next(d for d in defs if d['name']==edge['source']);at=move(source['rva'])+edge['operand'];put(bad,at,u32(bad,at)+4)
    cases.append(('wrong_call_relationship_rejected',False,bad,moved_expected,0x06000000))
    bad=bytearray(moved);d=next(d for d in defs if d['name']=='GovEasy');at=move(d['rva'])+bytes.fromhex(d['data']).index(b'\xf0\x00\x00\x00');bad[at]=0xf1
    cases.append(('changed_object_layout_rejected',False,bad,moved_expected,0x06000000))
    bad=bytearray(moved);d=next(d for d in defs if d['name']=='GalaxyGlobal');put(bad,move(d['rva'])+d['offset'],0x90000000)
    cases.append(('out_of_image_global_rejected',False,bad,moved_expected,0x06000000))
    bad=bytearray(moved);d=next(d for d in defs if d['name']=='GalaxyGlobalCheck');at=move(d['rva'])+d['offset'];put(bad,at,u32(bad,at)+16)
    cases.append(('inconsistent_global_rejected',False,bad,moved_expected,0x06000000))
    bad=bytearray(moved);put(bad,0x98+56,4096)
    cases.append(('invalid_section_bounds_rejected',False,bad,moved_expected,0x06000000))
    for name,success,data,wanted,base in cases:
        fixture=temp/(name+'.bin')
        fixture.write_bytes(struct.pack('<4I',success,len(data),count,base)+struct.pack('<'+str(count)+'I',*wanted)+data)
        subprocess.run([str(executable),str(fixture)],check=True)
    print('PASS:',len(cases),'runtime resolver cases; rejected profiles publish no partial bindings')
