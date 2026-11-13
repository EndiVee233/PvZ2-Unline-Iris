"""Check own runtime class registration, factory and inherited save schema."""
import argparse
from pathlib import Path
import struct
from native_payload import registration_payload
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *


def check(path):
    data=path.read_bytes();u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x1000000)
    u.reg_write(UC_ARM_REG_C1_C0_2,0xf<<20);u.reg_write(UC_ARM_REG_FPEXC,1<<30)
    ph=struct.unpack_from('<I',data,28)[0];step,n=struct.unpack_from('<HH',data,42)
    segments=[]
    for q in range(ph,ph+step*n,step):
        kind,off,va,_,size,mem,flags,_=struct.unpack_from('<8I',data,q)
        if kind==1:
            assert flags!=7;u.mem_write(va,data[off:off+size]);segments.append((va,size,mem,flags))
    assert (0xf80000,0,8192,6) in segments
    entry=registration_payload(data,0x3b9478,'PlantIrisDark')
    meta,table,instance,parent,registry,reflect,ptype,desc,textslot,stop,stack=[0xf00000+i*0x1000 for i in range(11)]
    stack=0xfff000
    def word(p,v):u.mem_write(p,struct.pack('<I',v))
    def read(p):return struct.unpack('<I',u.mem_read(p,4))[0]
    def string(p):return bytes(u.mem_read(p,60)).split(b'\0')[0].decode()
    word(registry,0xf10000);word(0xf1000c,0xf20000)
    word(reflect,0xf11000)
    for slot,fn in ((0x24,0xf20010),(0x28,0xf20020),(0x14,0xf20030),(0x2c,0xf20040),(0x20,0xf20060)):word(0xf11000+slot,fn)
    word(ptype,0xf12000);word(0xf12034,0xf20050)
    env={'allocated':[],'registered':0,'base':0,'fields':[]}
    def ret(v=0):u.reg_write(UC_ARM_REG_R0,v);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    def hook(cpu,pc,size,_):
        r0,r1,r2,r3=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
        if pc==entry+560:env['base']+=1;ret()
        elif pc==0xb363dc:
            allocation=meta if r0==40 else table if r0==0xf8 else instance
            assert r0 in (40,0xf8,0x2c0);env['allocated'].append(r0);u.mem_write(allocation,b'\xcd'*r0);ret(allocation)
        elif pc==0x894ca0:assert r0==meta;ret()
        elif pc==0x13b5a0:ret(parent)
        elif pc==0x895608:
            assert (r0,r2,r3)==(meta,parent,entry+40) and string(r1)=='PlantIrisDark';ret()
        elif pc==0x851728:ret(0xf13000)
        elif pc==0x851920:assert r0==0xf13000;ret(registry)
        elif pc==0xb75560:u.mem_write(textslot,string(r1).encode()+b'\0');word(textslot-4,0);word(r0,textslot);ret()
        elif pc in (0xb76c4c,0xe8c10):ret()
        elif pc==0xf20000:
            assert (r0,r2,r3)==(registry,entry+120,0x2c0) and string(read(r1))=='PlantIrisDark'
            env['registered']+=1;ret()
        elif pc==0xf20010:assert r0==reflect and string(read(r1)) in ('PlantFramework','ZombieParticle','Zombie');ret(ptype)
        elif pc==0xf20050:ret(123)
        elif pc==0xf20020:assert (r0,r1,r2,r3)==(reflect,desc,123,0);ret()
        elif pc==0xf20030:assert r0==reflect and r1 in (6,8) and r2==4;ret(r1)
        elif pc==0xf20060:assert (r0,r1,r2,r3)==(reflect,3,ptype,0);ret(100)
        elif pc==0xf20070:assert r0==0xf13000;ret(1)
        elif pc==0xf20040:
            assert (r0,r1)==(reflect,desc);env['fields'].append((string(read(r2)),r3,read(u.reg_read(UC_ARM_REG_SP))));ret()
        elif pc==stop:u.emu_stop()
    u.hook_add(UC_HOOK_CODE,hook)
    def run(mode,args=(0,0,0,0)):
        u.reg_write(UC_ARM_REG_SP,stack);u.reg_write(UC_ARM_REG_LR,stop)
        for reg,v in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),args):u.reg_write(reg,v)
        u.reg_write(UC_ARM_REG_R4,0x98765432);u.emu_start(entry+mode*40,stop,count=100000)
        assert u.reg_read(UC_ARM_REG_SP)==stack and u.reg_read(UC_ARM_REG_R4)==0x98765432
        assert u.reg_read(UC_ARM_REG_PC)==stop;return u.reg_read(UC_ARM_REG_R0)
    run(0);run(0);assert env['allocated']==[40,0xf8] and env['registered']==1 and env['base']==2
    assert run(2)==meta and read(table)==entry+80
    assert read(table+0xe8)==0x13f3b4 and read(table+0xf4)==0x3b9dc8
    assert read(table+0x90)==0x3e91f8
    assert run(1)==instance and read(instance)==table and bytes(u.mem_read(instance+4,0x2bc))==bytes(0x2bc)
    run(3,(reflect,desc,0,0))
    assert read(meta+0x24)==desc and read(desc+0x5c)==meta
    expected=[(f'iris_state{i}',8+i*4,6 if i in (1,4) else 8) for i in range(7)]
    for i in range(20):
        expected.append((f'iris_metal{i:02}w',0x40+i*32,100))
        expected.extend((f'iris_metal{i:02}{chr(97+j)}',0x48+i*32+j*4,6 if j==0 else 8) for j in range(4))
        expected.append((f'iris_metal{i:02}t',0x58+i*32,100))
    assert env['fields']==expected
    # ARM aggregate return storage is uninitialized on entry. The manual
    # aiming branch must construct an empty handle, never release garbage.
    word(0xf8108c,0xf20070);word(instance+4,0xf13000)
    output=0xf14000;word(output,0xfeedface);word(output+4,0xbaadf00d)
    assert run(9,(output,instance,0,0))==output
    assert read(output)==read(output+4)==0
    print('PASS: separate RX/RW segments, idempotent runtime class registration, relocated vtable, zeroed factory, inherited and explicit save fields, ARM ABI')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('library',type=Path);check(p.parse_args().library)
