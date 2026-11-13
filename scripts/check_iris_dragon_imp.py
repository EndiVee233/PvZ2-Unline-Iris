"""Execute the scoped ARM fire filter without bypassing the saved hook chain."""
import argparse
from pathlib import Path
import struct
from native_payload import registration_payload
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *


def check(path):
    raw=path.read_bytes();u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x1000000)
    ph=struct.unpack_from('<I',raw,28)[0];stride,count=struct.unpack_from('<HH',raw,42)
    for h in range(ph,ph+stride*count,stride):
        kind,off,va,_,size,_,flags,_=struct.unpack_from('<8I',raw,h)
        if kind==1:assert flags!=7;u.mem_write(va,raw[off:off+size])
    entry=registration_payload(raw,0x5e0b74,'POPANIM_ZOMBIE_ZOMBIE_DARK_IMP_DRAGON');tramp=entry+40
    z,t,hit,text,stop=[0xf00000+i*0x1000 for i in range(5)]
    def word(p,v):u.mem_write(p,struct.pack('<I',v))
    def read(p):return struct.unpack('<I',u.mem_read(p,4))[0]
    word(z+0x38,100);word(z+0x3c,1);word(t+0x10,text)
    u.mem_write(hit,struct.pack('<IfIIII',z,50,0x80,0,0,0));called=[];resolved=[True]
    def ret(v=0):u.reg_write(UC_ARM_REG_R0,v);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    def hook(cpu,pc,size,data):
        a,b,c,d=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
        if pc==tramp:called.append((a,b,bytes(u.mem_read(hit,24))));ret(77)
        elif pc==0x8821a8:ret(1)
        elif pc==0x8890c4:word(a,read(c));word(a+4,read(c+4));ret()
        elif pc==0x888b8c:ret(1)
        elif pc==0x884378:ret(t if resolved[0] else 0)
        elif pc==0x13dea0:word(a,c);word(a+4,d);ret()
        elif pc==stop:u.emu_stop()
    u.hook_add(UC_HOOK_CODE,hook)
    def run(flags,popanim):
        word(hit+8,flags);u.mem_write(text,popanim.encode()+b'\0')
        for r,v in ((UC_ARM_REG_R0,z),(UC_ARM_REG_R1,hit),(UC_ARM_REG_SP,0xfff000),(UC_ARM_REG_LR,stop)):u.reg_write(r,v)
        u.emu_start(entry,stop,count=100000);assert u.reg_read(UC_ARM_REG_PC)==stop
        return u.reg_read(UC_ARM_REG_R0)
    dragon='POPANIM_ZOMBIE_ZOMBIE_DARK_IMP_DRAGON'
    assert run(0x80,dragon)==0 and not called
    assert run(0x81,dragon)==0 and not called
    assert run(0,dragon)==77 and len(called)==1
    assert run(0x80,'POPANIM_ZOMBIE_GARGANTUAR_IMP')==77 and len(called)==2
    resolved[0]=False;assert run(0x80,dragon)==77 and len(called)==3
    assert all(a==z and b==hit and struct.unpack_from('<f',record,4)[0]==50 for a,b,record in called)
    print('PASS: dragon imp ARM fire immunity, ordinary hit, unrelated FutureImp, expired type and unmodified parent damage chain')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('native',type=Path);check(p.parse_args().native)
