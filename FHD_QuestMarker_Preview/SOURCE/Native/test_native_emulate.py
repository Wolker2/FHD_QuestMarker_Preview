"""Run the freestanding i386 ABI fixture on hosts without Linux IA32 support.
Requires unicorn==2.1.4. This emulates synthetic objects, not the Windows game.
"""
import struct
import sys
from pathlib import Path
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_INTR
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX, UC_X86_REG_EDX, UC_X86_REG_ESP, UC_X86_REG_FPCW

data=Path(sys.argv[1]).read_bytes()
assert data[:6]==b'\x7fELF\x01\x01'
entry,phoff=struct.unpack_from('<II',data,24)
phsize,phcount=struct.unpack_from('<HH',data,42)
segments=[]
for i in range(phcount):
    kind,offset,address,_,filesize,memsize,_,_=struct.unpack_from('<IIIIIIII',data,phoff+i*phsize)
    if kind==1:segments.append((offset,address,filesize,memsize))
start=min(s[1] for s in segments)&~4095
end=(max(s[1]+s[3] for s in segments)+4095)&~4095
cpu=Uc(UC_ARCH_X86,UC_MODE_32)
cpu.mem_map(start,end-start)
for offset,address,size,_ in segments:cpu.mem_write(address,data[offset:offset+size])
cpu.mem_map(0x70000000,0x200000)
cpu.reg_write(UC_X86_REG_ESP,0x701ffff0)
cpu.reg_write(UC_X86_REG_FPCW,0x37f)
result=[]
def interrupt(uc,number,_):
    assert number==0x80
    syscall=uc.reg_read(UC_X86_REG_EAX)
    if syscall==1:
        result.append(uc.reg_read(UC_X86_REG_EBX));uc.emu_stop()
    elif syscall==4:
        text=uc.mem_read(uc.reg_read(UC_X86_REG_ECX),uc.reg_read(UC_X86_REG_EDX))
        sys.stdout.write(text.decode());uc.reg_write(UC_X86_REG_EAX,len(text))
    elif syscall==125:uc.reg_write(UC_X86_REG_EAX,0)
    else:raise RuntimeError(f'Unexpected syscall: {syscall}')
cpu.hook_add(UC_HOOK_INTR,interrupt)
cpu.emu_start(entry,0,count=100_000_000)
assert result==[0],f'i386 fixture failed, exit code {result}; inspect CHECK line modulo 250'
