from pathlib import Path
import shutil, subprocess, re, struct, json, sys

# Offline generator for the documented reference layout only. Runtime lookup
# does not use this address table; extending to changed layouts requires review.
ROOT=Path(__file__).resolve().parents[2]
EXE=Path(sys.argv[1])
sys.path.insert(0,str(ROOT/'SOURCE'))
from verify_release import PE
pe=PE(EXE)
imagebase=pe.u32(pe.opt+28)
text_sec=next((x for x in pe.sections if x[0]==0x1000),None)
assert text_sec
text=pe.at(text_sec[0],text_sec[3])
# Operand relocation positions, not arbitrary-looking four-byte constants.
relocations=set()
rva,size=pe.directory(5);cursor=pe.offset(rva);end=cursor+size
while cursor+8<=end:
    page,block=struct.unpack_from('<II',pe.data,cursor)
    if not block:break
    for p in range(cursor+8,cursor+block,2):
        v=struct.unpack_from('<H',pe.data,p)[0]
        if v>>12==3:relocations.add(page+(v&4095))
    cursor+=block
disassembly=subprocess.check_output(['objdump','-d','-Mintel','--insn-width=15',str(EXE)],text=True)
instructions={}
def parse_instructions(text):
    for line in text.splitlines():
        m=re.match(r'^\s*([0-9a-f]+):\s*\t([0-9a-f ]+)\t(.*)$',line)
        if m:
            at=int(m[1],16)-imagebase
            b=bytes.fromhex(m[2]);instructions[at]=(b,m[3].strip())
parse_instructions(disassembly)

def disassemble_at(at):
    # Delphi stores data between routines; linear whole-image disassembly can
    # lose alignment. Each known reference routine starts a fresh decode.
    parse_instructions(subprocess.check_output(['objdump','-d','-Mintel','--insn-width=15',
        '--start-address='+hex(imagebase+at),'--stop-address='+hex(imagebase+at+1024),
        str(EXE)],text=True))

functions=[
 ('GetPlayer',0x347300),('PlanetRelation',0x339988),('PlanetPoint',0x33684c),
 ('JumpArrival',0x2e2694),('JumpDeparture',0x2e25c0),('ArtefactBoost',0x2ead84),
 ('ArtefactCount',0x2eab98),('JumpDays',0x2e2734),('SetText',0x9e0d0),
 ('ListAdd',0x161c0),('ShowStarInfo',0x2793ac),('GetByName',0xc5940),
 ('ShipSpeed',0x2f10e8),('GetTank',0x2d6558),('GetEngine',0x2d6560),
 ('EquipmentUsable',0x2d6604),('ShipRange',0x2d6e6c),('ShipBonus',0x2f1ec8),
 ('StarVisible',0x3f3a84),('SetDisabled',0xad12c),('SetActive',0xc11bc),
 ('GalaxyOpen',0x274bb8),('RebuildPath',0x277ac4),('GalaxyMouseUp',0x2777b0),
 ('GovClear',0x11ee30),('GovOffer',0x1211b8),('GovEasy',0x122760),('GovHard',0x122a18),
 ('AddChoice',0x11ee88),('ExecutePress',0xad910),('MessageRightClick',0x35cdb4),
]

definitions=[]

def pattern(at,limit=192,stop_ret=True):
    cursor=at
    decoded=[]
    while cursor in instructions and cursor-at<limit:
        b,asm=instructions[cursor]
        decoded.append((cursor,b,asm))
        cursor+=len(b)
        if stop_ret and asm.split(' ',1)[0] in ('ret','retf'):break
    if cursor==at:raise ValueError(hex(at))
    data=bytearray(pe.at(at,cursor-at));mask=bytearray([255]*len(data))
    for loc in relocations:
        if at<=loc and loc+4<=cursor:mask[loc-at:loc-at+4]=bytes(4)
    calls=[]
    for loc,b,asm in decoded:
        # Address-sensitive relative calls/jumps. Local short branches stay exact.
        if len(b)==5 and b[0] in (0xe8,0xe9):
            mask[loc-at+1:loc-at+5]=bytes(4)
            dest=loc+5+struct.unpack_from('<i',b,1)[0]
            calls.append((loc-at+1,dest))
    for i,v in enumerate(mask):
        if not v:data[i]=0
    return bytes(data),bytes(mask),calls

def matches(data,mask):
    # Search with the longest fully fixed run as an exact anchor.
    runs=list(re.finditer(b'\xff+',mask));run=max(runs,key=lambda m:m.end()-m.start())
    anchor=data[run.start():run.end()];found=[];p=0
    while True:
        p=text.find(anchor,p)
        if p<0:break
        at=p-run.start();p+=1
        if at>=0 and at+len(data)<=len(text) and all(not m or text[at+i]==v for i,(v,m) in enumerate(zip(data,mask))):found.append(at+0x1000)
    return found

for name,at in functions:
    disassemble_at(at)
    data,mask,calls=pattern(at)
    found=matches(data,mask)
    for limit in (384,768):
        if found==[at]:break
        data,mask,calls=pattern(at,limit)
        found=matches(data,mask)
    if name=='AddChoice':
        # TfGov and another dialog contain byte-identical AddChoice routines.
        # Select the callee of the uniquely identified government offer, then
        # validate that callee's body, rather than guessing one duplicate.
        guard,guard_mask,_=pattern(at)
        data,mask,calls=pattern(0x1211b8)
        assert matches(data,mask)==[0x1211b8]
        definitions.append(dict(name=name,rva=0x1211b8,target_rva=at,data=data.hex(),mask=mask.hex(),offset=0x3e,
            kind='relative',guard=guard.hex(),guard_mask=guard_mask.hex(),calls=calls))
        continue
    assert found==[at],(name,len(data),[hex(v) for v in found])
    definitions.append(dict(name=name,rva=at,data=data.hex(),mask=mask.hex(),offset=0,kind='code',calls=calls))

data,mask,calls=pattern(0x35c399,64,False)
assert matches(data,mask)==[0x35c399]
definitions.append(dict(name='CallbackStore',rva=0x35c399,data=data.hex(),mask=mask.hex(),offset=9,kind='code',calls=calls))

data,mask,calls=pattern(0x122d52,64,False)
assert matches(data,mask)==[0x122d52]
definitions.append(dict(name='QuestLayout',rva=0x122d52,data=data.hex(),mask=mask.hex(),offset=0,kind='code',calls=calls))

# Global locations are read from uniquely identified instructions, rather than
# inferred from the executable image base or a shared shift of code addresses.
for name,target in [('GalaxyGlobal',0x41d2a0),('GalaxyScreenGlobal',0x41cbb4),('FuelBaseGlobal',0x41ba28),('FuelBoostGlobal',0x41ba98)]:
    candidates=[]
    for loc in sorted(relocations):
        if not 0x1000<=loc<text_sec[0]+text_sec[3]:continue
        if struct.unpack('<I',pe.at(loc,4))[0] != imagebase+target:continue
        # Find the actual instruction boundary containing the relocated operand.
        starts=[p for p in range(loc-6,loc+1) if p in instructions and p+len(instructions[p][0])>=loc+4]
        if not starts:continue
        start=max(starts)
        try:data,mask,calls=pattern(start,80,False)
        except ValueError:continue
        if matches(data,mask)==[start]:
            candidates.append((start,loc-start,data,mask,calls))
        if len(candidates)==2:break
    for index,(at,operand,data,mask,calls) in enumerate(candidates):
        definitions.append(dict(name=name+('Check' if index else ''),rva=at,data=data.hex(),mask=mask.hex(),offset=operand,kind='writable',calls=calls))
    if len(candidates)==1 and name.startswith('Fuel'):
        # The unit's exported data pointer is also referenced indirectly by
        # ship code. Verify the setter and a separate consumer agree.
        slot=0x4131c8 if name=='FuelBaseGlobal' else 0x413534
        assert pe.at(slot,4)==struct.pack('<I',imagebase+target)
        indirect=[]
        for loc in sorted(relocations):
            if not 0x1000<=loc<text_sec[0]+text_sec[3]:continue
            if pe.at(loc,4)!=struct.pack('<I',imagebase+slot):continue
            starts=[p for p in range(loc-6,loc+1) if p in instructions and p+len(instructions[p][0])>=loc+4]
            if not starts:continue
            at=max(starts);data,mask,calls=pattern(at,80,False)
            if matches(data,mask)==[at]:
                indirect.append(dict(name=name+'Check',rva=at,data=data.hex(),mask=mask.hex(),offset=loc-at,kind='indirect_writable',calls=calls));break
        assert len(indirect)==1,name
        definitions.extend(indirect)
    else:assert len(candidates)==2,name

names={f['rva']:f['name'] for f in definitions if f['kind']=='code' and not f['offset']}
names.update({f['target_rva']:f['name'] for f in definitions if f['kind']=='relative'})
edges=[]
for d in definitions:
    for operand,target in d.pop('calls'):
        if target in names:edges.append(dict(source=d['name'],operand=operand,target=names[target]))

manifest={'reference_exe_sha256':'e43a4b15503c705eebe2d8ce5778c2a2fb090db515a3fd86d319e5c5aa692ebf',
          'definitions':definitions,'edges':edges,'note':'Reference RVAs are generator provenance only. Runtime resolves signatures in executable sections.'}
(ROOT/'SOURCE/Native/game_patterns.json').write_text(json.dumps(manifest,indent=2)+'\n')
lines=['/* Generated masked instruction signatures. No build timestamp, image size',
       '   or fixed RVA lookup is used to select the running executable. */',
       'enum GameSymbol {']
lines += ['    GS_'+d['name']+',' for d in definitions]
lines += ['    GS_Count','};','static u8 *gameSymbols[GS_Count];',
          'typedef struct {const u8 *bytes,*mask;u16 length,anchor,anchorLength,offset;u8 kind;const u8 *guard,*guardMask;u16 guardLength;} GamePattern;']
for d in definitions:
    data=bytes.fromhex(d['data']);mask=bytes.fromhex(d['mask'])
    for kind,payload in [('Bytes',data),('Mask',mask)]:
        lines.append('static const u8 gp'+d['name']+kind+'[]={'+','.join(f'0x{v:02x}' for v in payload)+'};')
    if d.get('guard'):
        for kind,key in [('Guard','guard'),('GuardMask','guard_mask')]:
            lines.append('static const u8 gp'+d['name']+kind+'[]={'+','.join(f'0x{v:02x}' for v in bytes.fromhex(d[key]))+'};')
lines.append('static const GamePattern gamePatterns[GS_Count]={')
for d in definitions:
    mask=bytes.fromhex(d['mask']);run=max(re.finditer(b'\xff+',mask),key=lambda m:m.end()-m.start())
    extra=f'gp{d["name"]}Guard,gp{d["name"]}GuardMask,{len(d["guard"])//2}' if d.get('guard') else '0,0,0'
    lines.append(f'    {{gp{d["name"]}Bytes,gp{d["name"]}Mask,{len(mask)},{run.start()},{run.end()-run.start()},{d["offset"]},{ {"code":0,"writable":1,"relative":2,"indirect_writable":3}[d["kind"]]},{extra}}},')
lines+=['};','static const struct {u16 source,operand,target;} gameEdges[]={']
lines += [f'    {{GS_{e["source"]},{e["operand"]},GS_{e["target"]}}},' for e in edges]
lines+=['};']
(ROOT/'SOURCE/Native/game_patterns.h').write_text('\n'.join(lines)+'\n')
print('Generated',len(definitions),'unique patterns and',len(edges),'call relationships')
print('Pattern lengths:',min(len(d['mask'])//2 for d in definitions),max(len(d['mask'])//2 for d in definitions))
print(ROOT)
