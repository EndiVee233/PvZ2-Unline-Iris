"""Verify the compiled casting adapter and its native walking fallback ABI."""
import argparse
from pathlib import Path
import struct
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *


def check(path):
    data=path.read_bytes();u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x1000000)
    u.reg_write(UC_ARM_REG_C1_C0_2,0xf<<20);u.reg_write(UC_ARM_REG_FPEXC,1<<30)
    ph=struct.unpack_from('<I',data,28)[0];stride,n=struct.unpack_from('<HH',data,42)
    for h in range(ph,ph+stride*n,stride):
        kind,off,va,_,size,_,_,_=struct.unpack_from('<8I',data,h)
        if kind==1:u.mem_write(va,data[off:off+size])
    op=struct.unpack_from('<I',data,0x6336f8)[0];delta=(op&0xffffff)<<2
    if delta&0x2000000:delta-=0x4000000
    entry=0x6336f8+8+delta;zombie,stop,stack=0xf00000,0xf10000,0xfff000
    env={'random':[],'max':False,'cast':False,'calls':0,'deadlines':[]}
    def word(p,v):u.mem_write(p,struct.pack('<I',v))
    def read(p):return struct.unpack('<I',u.mem_read(p,4))[0]
    def fl(p,v):u.mem_write(p,struct.pack('<f',v))
    def number(p):return struct.unpack('<f',u.mem_read(p,4))[0]
    def ret(v=0):u.reg_write(UC_ARM_REG_R0,v);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    def hook(cpu,pc,size,_):
        r0=u.reg_read(UC_ARM_REG_R0)
        if pc==0xe8c10:ret()
        elif pc==0x7a3e90:
            assert r0 in (2001,3001);env['random'].append(r0);ret(r0-1 if env['max'] else 0)
        elif pc==entry+40:
            assert r0==zombie;env['calls']+=1;env['deadlines'].append(number(zombie+0x184))
            if env['cast']:word(zombie+0x48,13);fl(zombie+0x184,12.5)
            ret(123)
        elif pc==stop:u.emu_stop()
    u.hook_add(UC_HOOK_CODE,hook)
    def run():
        u.reg_write(UC_ARM_REG_R0,zombie);u.reg_write(UC_ARM_REG_SP,stack);u.reg_write(UC_ARM_REG_LR,stop)
        u.reg_write(UC_ARM_REG_R4,0x12345678);u.emu_start(entry,stop,count=10000)
        assert u.reg_read(UC_ARM_REG_PC)==stop and u.reg_read(UC_ARM_REG_SP)==stack
        assert u.reg_read(UC_ARM_REG_R4)==0x12345678 and u.reg_read(UC_ARM_REG_R0)==123
    fl(zombie+0x184,-1);word(zombie+0x48,0);run();assert number(zombie+0x184)==7
    run();assert len(env['random'])==1
    env['cast']=True;run();assert number(zombie+0x184)==11 and env['random'][-1]==3001
    env['cast']=False;env['max']=True;word(zombie+0x48,0);fl(zombie+0x184,-1);run();assert number(zombie+0x184)==9
    env['cast']=True;run();assert number(zombie+0x184)==14
    # A restored in-progress deadline survives without another random draw.
    env['cast']=False;fl(zombie+0x184,12.345);before=len(env['random']);run()
    assert len(env['random'])==before and abs(number(zombie+0x184)-12.345)<0.0001
    print('PASS: native wizard ABI/fallback, first 7-9s and repeat 11-14s ranges, transition-only randomization and restored deadlines')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('library',type=Path);check(p.parse_args().library)
