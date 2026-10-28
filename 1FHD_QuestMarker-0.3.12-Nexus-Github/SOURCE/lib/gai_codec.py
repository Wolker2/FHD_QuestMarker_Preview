"""Lossless GAI v1 source: sequence records, frame delays and typed GI frames.

This profile stores the sequence table followed by uncompressed GI frames.
Layout reference: local GR_gi/EC_CacheGAI game-structure research.
"""
import struct
from gi_codec import decode as decode_gi,encode as encode_gi

def decode(data):
    assert data[:4]==b'gai\0'
    version,left,top,right,bottom,count,flags,seq_offset,seq_size,*reserved=struct.unpack_from('<11I',data,4)
    result={'format':'srhd-gai1-json-v1','version':version,'bounds':[left,top,right,bottom],'playback_flags':flags,'reserved':reserved,'sequences':[],'frames':[]}
    assert version==1
    if seq_offset:
        table=data[seq_offset:seq_offset+seq_size];n=struct.unpack_from('<I',table)[0]
        for i in range(n):
            name_at,frames_at=struct.unpack_from('<II',table,4+8*i)
            assert frames_at>=name_at and (frames_at-name_at)%2==0
            auxiliary=list(struct.unpack_from('<'+'H'*((frames_at-name_at)//2),table,name_at))
            length=struct.unpack_from('<I',table,frames_at)[0]
            frames=[dict(zip(['frame','delay'],struct.unpack_from('<II',table,frames_at+4+8*j))) for j in range(length)]
            assert all(f['frame']<count for f in frames)
            result['sequences'].append({'auxiliary_u16':auxiliary,'frames':frames})
    for i in range(count):
        offset,length=struct.unpack_from('<II',data,48+8*i)
        result['frames'].append(decode_gi(data[offset:offset+length]))
    assert encode(result)==data,'Noncanonical/unsupported GAI layout'
    return result

def encode(source):
    assert source['format']=='srhd-gai1-json-v1' and source['version']==1
    sequences=source['sequences'];frames=[encode_gi(f) for f in source['frames']]
    table=bytearray(struct.pack('<I',len(sequences))+bytes(8*len(sequences))) if sequences else bytearray()
    for i,seq in enumerate(sequences):
        name_at=len(table);table.extend(struct.pack('<'+'H'*len(seq['auxiliary_u16']),*seq['auxiliary_u16']));frames_at=len(table)
        table.extend(struct.pack('<I',len(seq['frames'])))
        for item in seq['frames']:
            assert 0<=item['frame']<len(frames)
            table.extend(struct.pack('<II',item['frame'],item['delay']))
        struct.pack_into('<II',table,4+8*i,name_at,frames_at)
    offset=48+8*len(frames);seq_offset=offset if table else 0
    header=struct.pack('<4s11I',b'gai\0',source['version'],*source['bounds'],len(frames),source['playback_flags'],seq_offset,len(table),*source['reserved'])
    offset+=len(table);directory=bytearray()
    for frame in frames:directory.extend(struct.pack('<II',offset,len(frame)));offset+=len(frame)
    return header+directory+table+b''.join(frames)
