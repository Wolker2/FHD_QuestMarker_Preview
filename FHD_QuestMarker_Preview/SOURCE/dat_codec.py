"""Standalone SRHD BlockPar DAT (new-format) codec, fitted to rangers-utils format."""
from dataclasses import dataclass, field
import io,re,struct,zlib

@dataclass
class Node:
    sorted:bool=True
    entries:list=field(default_factory=list)  # [(key, string-or-Node)]

def parse_txt(s):
    root=Node();parents=[];cur=root
    for original in s.splitlines():
        line=original.strip()
        if not line or line.startswith('//'):continue
        if line=='}':
            if not parents: raise ValueError('extra closing')
            cur=parents.pop();continue
        if '{' in line and line.endswith('{'):
            head=line[:-1].rstrip()
            if head.endswith(('^','~')):
                cur.sorted=head[-1]=='^';head=head[:-1].rstrip()
            else:cur.sorted=True
            child=Node();cur.entries.append((head,child));parents.append(cur);cur=child
        elif '=' in line:
            name,value=line.split('=',1);cur.entries.append((name.rstrip(),value.lstrip()))
        else:raise ValueError('Unexpected '+line)
    if parents:raise ValueError('Unclosed blocks')
    return root

def packuint(x):return struct.pack('<I',x)
def wide(x):return x.encode('utf-16le')+b'\x00\x00'

def encode_tree(node):
    def gen(n):
        seq=list(n.entries)
        if n.sorted:
            seq.sort(key=lambda x:x[0].casefold())
        out=bytearray();out.extend(bytes((int(n.sorted),)));out.extend(packuint(len(seq)))
        total={}
        for key,val in seq:total[key.casefold()]=total.get(key.casefold(),0)+1
        idx={}
        for key,val in seq:
            if n.sorted:
                ind=idx.get(key.casefold(),0); idx[key.casefold()]=ind+1
                out.extend(packuint(ind));out.extend(packuint(total[key.casefold()] if ind==0 else 0))
            if isinstance(val,Node):
                out.extend(b'\x02');out.extend(wide(key));out.extend(gen(val))
            else:
                out.extend(b'\x01');out.extend(wide(key));out.extend(wide(val))
        return out
    return bytes(gen(node))

def _keystream(seed,n):
    for i in range(n):
        hi,lo=divmod(seed,0x1f31d)
        seed=lo*0x41a7-hi*0xb14
        if seed<1:seed+=0x7fffffff
        yield (seed-1)&255

def dat_build(node,seed=0x51A2C3D4,key=0xB1E8C689):
    raw=encode_tree(node)
    comp=b'ZL01'+packuint(len(raw))+zlib.compress(raw,9)
    digest=zlib.crc32(comp)
    encrypted=bytes(a^b for a,b in zip(comp,_keystream(seed,len(comp))))
    return packuint(digest)+packuint(seed^key)+encrypted

def dat_unwrap(data,key=0xB1E8C689):
    hash,encrypted_seed=struct.unpack_from('<II',data)
    seed=encrypted_seed^key
    comp=bytes(a^b for a,b in zip(data[8:],_keystream(seed,len(data)-8)))
    assert zlib.crc32(comp)==hash,'CRC failure'
    assert comp[:4]==b'ZL01'
    sz=struct.unpack_from('<I',comp,4)[0]
    raw=zlib.decompress(comp[8:]);assert len(raw)==sz
    return raw

def decode_tree(raw):
    f=io.BytesIO(raw)
    def uint():return struct.unpack('<I',f.read(4))[0]
    def getwide():
        v=bytearray()
        while True:
            c=f.read(2)
            if not c:raise ValueError('early EOF')
            if c==b'\x00\x00':break
            v.extend(c)
        return v.decode('utf-16le')
    def node():
        sort=f.read(1)==b'\x01';count=uint();n=Node(sort)
        for _ in range(count):
            if sort:
                i,total=uint(),uint()
            k=f.read(1)[0];name=getwide()
            if k==1:val=getwide()
            elif k==2:val=node()
            else:raise ValueError('unknown kind '+str(k))
            n.entries.append((name,val))
        return n
    result=node()
    assert f.tell()==len(raw),f'leftover {len(raw)-f.tell()}'
    return result

def find(n,*path):
    for p in path:
        n=next(val for key,val in n.entries if key==p)
    return n

if __name__=='__main__':
    from pathlib import Path
    p=Path('/mnt/data/questmarker_research/new312/Mods/FHD_MODS/FHD_QuestMarker_Preview')
    for name in ('Main','Lang'):
        d=(p/'CFG'/ ('Rus/' if name=='Lang' else '')/(name+'.dat')).read_bytes()
        dec=decode_tree(dat_unwrap(d))
        txt=parse_txt((p/'SOURCE'/'CFG'/(name+'.txt')).read_text('utf-8'))
        # Check binary recreation from decoded vs original: same decoded semantic
        remade=decode_tree(dat_unwrap(dat_build(dec)))
        assert repr(dec)==repr(remade)
        print(name,'original',len(d),'rebuilt from original',len(dat_build(dec)),'text nodes',len(txt.entries),'decoded nodes',len(dec.entries),'matches original bytes?',dat_build(dec)==d)
