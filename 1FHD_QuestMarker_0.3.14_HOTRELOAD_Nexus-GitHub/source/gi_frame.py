#!/usr/bin/env python3
"""Resize a native RGB565/6-bit-alpha GI frame to measured screenshot bounds.
Uses GI format 2 (three RLE planes) for input and output. Pillow and numpy required.
"""
from pathlib import Path
import struct
import numpy as np
from PIL import Image

def decode(path):
    b=Path(path).read_bytes();h=struct.unpack_from('<16I',b)
    assert h[:2]==(26983,1) and h[10:12]==(2,3)
    out=np.zeros((h[5]-h[3],h[4]-h[2],4),dtype=np.uint8)
    for plane in (2,1,0):
        off,size,l,t,r,bottom,_,_=struct.unpack_from('<8I',b,64+32*plane)
        if not size: continue
        data=b[off:off+size];_,w,height,_=struct.unpack_from('<4I',data)
        assert (w,height)==(r-l,bottom-t)
        values=np.full((height,w),63 if plane==2 else 0,dtype=np.uint16)
        written=np.zeros((height,w),bool);p=16;x=y=0;step=1 if plane==2 else 2
        while p<len(data):
            code=data[p];p+=1;n=code&127
            if not n:
                y+=1;x=0;continue
            assert y<height and x+n<=w
            if code&128:
                assert p+n*step<=len(data)
                values[y,x:x+n]=np.frombuffer(data[p:p+n*step],dtype='u1' if step==1 else '<u2')
                written[y,x:x+n]=True;p+=n*step
            x+=n
        assert y==height and p==len(data)
        dst=out[t-h[3]:bottom-h[3],l-h[2]:r-h[2]]
        if plane==2:
            dst[:,:,3]=((63-values.astype(np.int16))*255//63).astype(np.uint8)
        else:
            rgb=np.stack(((values>>11)*255//31,((values>>5)&63)*255//63,(values&31)*255//31),axis=2).astype(np.uint8)
            if plane==1:dst[:,:,:3]=rgb
            else:dst[written,:3]=rgb[written];dst[written,3]=255
    return Image.fromarray(out)

def encode(image,path):
    rgba=np.asarray(image.convert('RGBA'));height,width=rgba.shape[:2]
    rgb=rgba[:,:,:3].astype(np.uint16)
    packed=((rgb[:,:,0]*31+127)//255<<11)|((rgb[:,:,1]*63+127)//255<<5)|((rgb[:,:,2]*31+127)//255)
    # Quantize alpha once; alpha=0 remains transparent and alpha=255 opaque.
    a=((rgba[:,:,3].astype(np.uint16)*63+127)//255).astype(np.uint8)
    planes=[]
    for plane in range(3):
        valid=(a==63) if plane==0 else ((a>0)&(a<63))
        values=(63-a) if plane==2 else packed
        body=bytearray()
        for y in range(height):
            row=valid[y];last=np.flatnonzero(row)
            stop=int(last[-1])+1 if len(last) else 0;x=0
            while x<stop:
                opaque=bool(row[x]);end=x+1
                while end<stop and end-x<127 and bool(row[end])==opaque:end+=1
                body.append((end-x)|(128 if opaque else 0))
                if opaque:
                    body.extend(values[y,x:end].astype('u1' if plane==2 else '<u2').tobytes())
                x=end
            body.append(0)
        planes.append(struct.pack('<4I',len(body),width,height,0)+body)
    header=struct.pack('<16I',26983,1,0,0,width,height,0xf800,0x7e0,0x1f,0,2,3,0,0,0,0)
    directory=bytearray();offset=160
    for payload in planes:
        directory.extend(struct.pack('<8I',offset,len(payload),0,0,width,height,0,0));offset+=len(payload)
    Path(path).write_bytes(header+directory+b''.join(planes))

if __name__=='__main__':
    import sys
    if len(sys.argv)!=5:raise SystemExit('Usage: gi_frame.py INPUT.gi OUTPUT.gi WIDTH HEIGHT')
    image=decode(sys.argv[1]);image=image.crop(image.getbbox()).resize((int(sys.argv[3]),int(sys.argv[4])),Image.Resampling.LANCZOS)
    encode(image,sys.argv[2])
