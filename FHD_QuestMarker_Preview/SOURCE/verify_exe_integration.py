"""Exercise the packaged DLL on the real target PE bytes with synthetic Windows loader APIs.
Requires pefile and unicorn. This does not launch or simulate the complete game.
"""
import struct,sys
from pathlib import Path
import pefile
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import *
ROOT=Path(__file__).resolve().parent.parent
TARGET=Path(sys.argv[1])
DLL=ROOT/'Native/FHDQuestMarker.dll'
GAME_BASE=0x400000;DLL_BASE=0x13000000;STOP=0x7000f000;STACK=0x700ef000
HOOKS={'clear':(0x1276ec,6),'offer':(0x129e34,5),'easy':(0x12b518,8),'hard':(0x12b810,8),
       'routeOpen':(0x2a0160,8),'routePath':(0x2a339c,9),'routeMouse':(0x2a300c,6)}
def u32(cpu,p):return struct.unpack('<I',cpu.mem_read(p,4))[0]
def put(cpu,p,n):cpu.mem_write(p,struct.pack('<I',n&0xffffffff))
def symbols(pe):
    out={};data=DLL.read_bytes();offset=pe.FILE_HEADER.PointerToSymbolTable;count=pe.FILE_HEADER.NumberOfSymbols
    strings=offset+18*count;i=0
    while i<count:
        raw=data[offset+i*18:offset+(i+1)*18];name,value,section,_,_,aux=struct.unpack('<8sIhHBB',raw)
        if name[:4]==b'\0'*4:
            p=strings+struct.unpack('<I',name[4:])[0];name=data[p:data.index(b'\0',p)]
        else:name=name.rstrip(b'\0')
        if section>0:out[name.decode()]=DLL_BASE+pe.sections[section-1].VirtualAddress+value
        i+=1+aux
    return out

def fresh():
    cpu=Uc(UC_ARCH_X86,UC_MODE_32);pe=pefile.PE(str(DLL));exe=pefile.PE(str(TARGET));syms=symbols(pe)
    for p,base in [(exe,GAME_BASE),(pe,DLL_BASE)]:
        size=(p.OPTIONAL_HEADER.SizeOfImage+4095)&~4095;cpu.mem_map(base,size)
        cpu.mem_write(base,p.get_memory_mapped_image())
    cpu.mem_map(0,4096);cpu.mem_map(0x70000000,0x200000);cpu.mem_map(0x71000000,0x30000)
    put(cpu,0x30,0x70001000);put(cpu,0x70001008,GAME_BASE);put(cpu,0x7000100c,0x70002000)
    head=0x70002014;entries=[0x70003000,0x70003100];put(cpu,head,entries[0]+8)
    apis={};pos=0x70004000
    for idx,(name,exports) in enumerate([('ntdll.dll',['NtProtectVirtualMemory','NtFlushInstructionCache']),('kernelbase.dll',['GetModuleHandleExW'])]):
        entry=entries[idx];base=0x71000000+idx*0x10000;put(cpu,entry+8,entries[idx+1]+8 if idx+1<len(entries) else head)
        put(cpu,entry+0x18,base);put(cpu,entry+0x30,pos);cpu.mem_write(pos,(name+'\0').encode('utf-16le'));pos+=100
        cpu.mem_write(base,b'MZ');put(cpu,base+0x3c,0x80);cpu.mem_write(base+0x80,b'PE\0\0')
        cpu.mem_write(base+0x98,struct.pack('<H',0x10b));put(cpu,base+0x98+96,0x200);put(cpu,base+0x98+100,0x100)
        put(cpu,base+0x200+20,len(exports));put(cpu,base+0x200+24,len(exports))
        put(cpu,base+0x200+28,0x400);put(cpu,base+0x200+32,0x440);put(cpu,base+0x200+36,0x480)
        for i,name in enumerate(exports):
            put(cpu,base+0x400+4*i,0x1000+i*0x10);put(cpu,base+0x440+4*i,0x500+i*64)
            cpu.mem_write(base+0x480+2*i,struct.pack('<H',i));cpu.mem_write(base+0x500+i*64,(name+'\0').encode())
            api=base+0x1000+i*0x10;argc={'NtProtectVirtualMemory':5,'NtFlushInstructionCache':3,'GetModuleHandleExW':3}[name]
            cpu.mem_write(api,b'\xc2'+struct.pack('<H',argc*4));apis[api]=name
    def intercept(uc,address,size,_):
        if address in apis:
            sp=uc.reg_read(UC_X86_REG_ESP);name=apis[address]
            if name=='NtProtectVirtualMemory':put(uc,u32(uc,sp+20),0x20)
            if name=='GetModuleHandleExW':put(uc,u32(uc,sp+12),DLL_BASE)
            uc.reg_write(UC_X86_REG_EAX,1 if name=='GetModuleHandleExW' else 0)
    cpu.hook_add(UC_HOOK_CODE,intercept);cpu.reg_write(UC_X86_REG_FPCW,0x37f)
    return cpu,syms,exe

def call(cpu,address):
    put(cpu,STACK,STOP);cpu.reg_write(UC_X86_REG_ESP,STACK)
    cpu.emu_start(address,STOP,count=1000000)
    assert cpu.reg_read(UC_X86_REG_EIP)==STOP,'Execution did not return'
    return cpu.reg_read(UC_X86_REG_EAX)

cpu,s,exe=fresh()
assert call(cpu,s['FHDQuest_Init'])==0,'DLL rejected the supplied EXE'
for name,(rva,length) in list(HOOKS.items())[:4]:
    assert cpu.mem_read(GAME_BASE+rva,1)==b'\xe9',f'{name} hook missing'
assert u32(cpu,GAME_BASE+0x3a3ce4)==s['questRightClick']
assert call(cpu,s['FHDQuest_Init'])==0,'Repeated init failed'
# Capture an accepted quest through the installed callback, using the real EXE GetPlayer.
player=0x70010000;sender=0x70011000;message=0x70011200;quest=0x70011400
items=0x70011600;quest_list=0x70011700;description=0x70011800;message_text=0x70011a00
put(cpu,GAME_BASE+0x47c19c,player^0xb1cd15d3)
put(cpu,player+0x520,quest_list);put(cpu,quest_list+4,items);put(cpu,quest_list+8,1)
put(cpu,items,quest);put(cpu,quest+0x10,0x70013000);put(cpu,quest+0x18,description)
cpu.mem_write(description,('mission objective'+'\0').encode('utf-16le'))
cpu.mem_write(message_text,('details: mission objective, accepted'+'\0').encode('utf-16le'))
put(cpu,sender+0x8c,message);cpu.mem_write(message+0x10,b'\x03');put(cpu,message+0x20,message_text)
cpu.reg_write(UC_X86_REG_EAX,0x70012000);cpu.reg_write(UC_X86_REG_EDX,sender)
cpu.reg_write(UC_X86_REG_ECX,0x123);put(cpu,STACK+4,0x70011c00)
call(cpu,s['questRightClick'])
assert cpu.reg_read(UC_X86_REG_ESP)==STACK+8,'Quest callback must pop its point argument'
assert call(cpu,s['FHD_GetKind'])==0 and call(cpu,s['FHD_GetTarget'])==0x70013000
# Unmatched messages must preserve the original callback arguments.
cpu.mem_write(message+0x10,b'\x01');fallback=[]
def capture_fallback(uc,address,size,_):
    if address==GAME_BASE+0x3a4810:
        sp=uc.reg_read(UC_X86_REG_ESP)
        fallback.append((uc.reg_read(UC_X86_REG_EAX),uc.reg_read(UC_X86_REG_EDX),uc.reg_read(UC_X86_REG_ECX),u32(uc,sp+4)))
        uc.reg_write(UC_X86_REG_EIP,u32(uc,sp));uc.reg_write(UC_X86_REG_ESP,sp+8)
cpu.hook_add(UC_HOOK_CODE,capture_fallback)
cpu.reg_write(UC_X86_REG_EAX,0x70012000);cpu.reg_write(UC_X86_REG_EDX,sender)
cpu.reg_write(UC_X86_REG_ECX,0x123);put(cpu,STACK+4,0x70011c00)
call(cpu,s['questRightClick'])
assert fallback==[(0x70012000,sender,0x123,0x70011c00)]
assert call(cpu,s['FHD_GetKind'])==0xffffffff and call(cpu,s['FHD_GetTarget'])==0
# Enter route preparation far enough to install map hooks, then use a zero-speed stub.
player=0x70010000;gov=0x70012000;planet=0x70013000;star=0x70014000
put(cpu,s['government'],gov);put(cpu,s['offerVisible'],1);put(cpu,gov+0x100,planet)
put(cpu,planet+0x18,star);put(cpu,player+0x24,star);put(cpu,GAME_BASE+0x47c19c,player^0xb1cd15d3)
cpu.mem_write(GAME_BASE+0x32c8dc,b'\x33\xc0\xc3')
# Keep the actual guarded entry intact until route_install has checked it.
real_speed=exe.get_data(0x32c8dc,8);cpu.mem_write(GAME_BASE+0x32c8dc,real_speed)
def zero_speed(uc,address,size,_):
    if address==GAME_BASE+0x32c8dc:
        sp=uc.reg_read(UC_X86_REG_ESP);uc.reg_write(UC_X86_REG_EAX,0)
        uc.reg_write(UC_X86_REG_EIP,u32(uc,sp));uc.reg_write(UC_X86_REG_ESP,sp+4)
cpu.hook_add(UC_HOOK_CODE,zero_speed)
assert call(cpu,s['FHD_RoutePrepare'])==0xfffffffe,'Route guards or map installation failed'
for name,(rva,length) in HOOKS.items():
    assert cpu.mem_read(GAME_BASE+rva,1)==b'\xe9',f'{name} hook missing'
    assert u32(cpu,s[name+'Continue'])==GAME_BASE+rva+length
    original=exe.get_data(rva,length)
    assert cpu.mem_read(s[name+'Trampoline'],length)==original,f'{name} trampoline bytes differ'
# Execute each actual trampoline to its continuation; these prologs contain no relocations.
for name,(rva,length) in HOOKS.items():
    cpu2,syms2,_=fresh();put(cpu2,syms2[name+'Continue'],GAME_BASE+rva+length)
    for reg,value in [(UC_X86_REG_EAX,player),(UC_X86_REG_EDX,0x11223344),(UC_X86_REG_ECX,0x55667788),
                      (UC_X86_REG_EBX,0x111),(UC_X86_REG_ESI,0x222),(UC_X86_REG_EDI,0x333),(UC_X86_REG_EBP,0x444),
                      (UC_X86_REG_ESP,STACK),(UC_X86_REG_EFLAGS,0x202)]:cpu2.reg_write(reg,value)
    cpu2.emu_start(syms2[name+'Trampoline'],GAME_BASE+rva+length,count=100)
    actual=[cpu2.reg_read(x) for x in [UC_X86_REG_EAX,UC_X86_REG_EDX,UC_X86_REG_ECX,UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP,UC_X86_REG_ESP,UC_X86_REG_EFLAGS]]
    stack_actual=bytes(cpu2.mem_read(STACK-256,256));object_actual=bytes(cpu2.mem_read(player,0x100))
    cpu3,_,_=fresh()
    for reg,value in [(UC_X86_REG_EAX,player),(UC_X86_REG_EDX,0x11223344),(UC_X86_REG_ECX,0x55667788),
                      (UC_X86_REG_EBX,0x111),(UC_X86_REG_ESI,0x222),(UC_X86_REG_EDI,0x333),(UC_X86_REG_EBP,0x444),
                      (UC_X86_REG_ESP,STACK),(UC_X86_REG_EFLAGS,0x202)]:cpu3.reg_write(reg,value)
    cpu3.emu_start(GAME_BASE+rva,GAME_BASE+rva+length,count=100)
    expected=[cpu3.reg_read(x) for x in [UC_X86_REG_EAX,UC_X86_REG_EDX,UC_X86_REG_ECX,UC_X86_REG_EBX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP,UC_X86_REG_ESP,UC_X86_REG_EFLAGS]]
    assert actual==expected and stack_actual==bytes(cpu3.mem_read(STACK-256,256)) and object_actual==bytes(cpu3.mem_read(player,0x100)),name+' changes prolog effects'
# Unsupported timestamp and damaged hook must fail before any code mutation.
for corruption,expected in [(lambda c:put(c,GAME_BASE+u32(c,GAME_BASE+0x3c)+8,0),3),
                            (lambda c:c.mem_write(GAME_BASE+0x1276ec,b'\x90'),4)]:
    cpu4,syms4,_=fresh();corruption(cpu4);snapshot=bytes(cpu4.mem_read(GAME_BASE+0x1000,0x474000))
    assert call(cpu4,syms4['FHDQuest_Init'])==expected
    assert bytes(cpu4.mem_read(GAME_BASE+0x1000,0x474000))==snapshot,'Rejected init mutated EXE code'
print('PASS: real target PE + packaged DLL initialization, repeated init, callback, seven hooks,')
print('      accepted-quest capture/fallback, trampoline effects, unsupported/damaged EXE rejection without writes')
