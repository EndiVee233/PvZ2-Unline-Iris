"""Verify the independent fire-stone class, save schema and impact timeline."""
import argparse
from pathlib import Path
import struct
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *


def check(path):
    data=path.read_bytes();u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x1000000)
    u.reg_write(UC_ARM_REG_C1_C0_2,0xf<<20);u.reg_write(UC_ARM_REG_FPEXC,1<<30)
    ph=struct.unpack_from('<I',data,28)[0];stride,n=struct.unpack_from('<HH',data,42)
    for h in range(ph,ph+stride*n,stride):
        kind,off,va,_,size,_,_,_=struct.unpack_from('<8I',data,h)
        if kind==1:u.mem_write(va,data[off:off+size])
    op=struct.unpack_from('<I',data,0x486d74)[0];d=(op&0xffffff)<<2
    if d&0x2000000:d-=0x4000000
    entry=0x486d74+8+d-80
    meta,table,instance,parent,registry,reflect,ptype,desc,textslot,stop=[0xf00000+i*0x1000 for i in range(10)]
    appslot,app,board,target=0xf10000,0xf11000,0xf12000,0xf13000;stack=0xfff000
    def word(p,v):u.mem_write(p,struct.pack('<I',v))
    def read(p):return struct.unpack('<I',u.mem_read(p,4))[0]
    def number(p):return struct.unpack('<f',u.mem_read(p,4))[0]
    def text(p):return bytes(u.mem_read(p,80)).split(b'\0')[0].decode()
    word(registry,0xf20000);word(0xf2000c,0xf30000)
    word(reflect,0xf21000)
    for slot,fn in ((0x24,0xf30010),(0x28,0xf30020),(0x14,0xf30030),(0x2c,0xf30040)):word(0xf21000+slot,fn)
    word(ptype,0xf22000);word(0xf22034,0xf30050)
    word(0xd00838,appslot);word(appslot,app);word(app+0x6c0,board)
    env={'alloc':[],'base':0,'registered':0,'fields':[],'pause':False,'hit':0,'removed':0}
    def ret(v=0):u.reg_write(UC_ARM_REG_R0,v);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    def hook(cpu,pc,size,_):
        r0,r1,r2,r3=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
        if pc==entry+280:env['base']+=1;ret()
        elif pc==0xb363dc:
            assert r0 in (40,0x58,0xa8);allocation={40:meta,0x58:table,0xa8:instance}[r0]
            env['alloc'].append(r0);u.mem_write(allocation,b'\xcd'*r0);ret(allocation)
        elif pc==0x894ca0:assert r0==meta;ret()
        elif pc==0x16a72c:ret(parent)
        elif pc==0x895608:assert (r0,r2,r3)==(meta,parent,entry+120) and text(r1)=='IrisFireStone';ret()
        elif pc==0x851728:ret(0xf23000)
        elif pc==0x851920:ret(registry)
        elif pc==0xb75560:u.mem_write(textslot,text(r1).encode()+b'\0');word(textslot-4,100);word(r0,textslot);ret()
        elif pc in (0xb76c4c,0xe8c10):ret()
        elif pc==0xf30000:assert (r0,r2,r3)==(registry,entry+200,0xa8);env['registered']+=1;ret()
        elif pc==0xf30010:assert r0==reflect and text(read(r1))=='Projectile';ret(ptype)
        elif pc==0xf30050:ret(123)
        elif pc==0xf30020:assert (r0,r1,r2,r3)==(reflect,desc,123,0);ret()
        elif pc==0xf30030:assert r1 in (6,8) and r2==4;ret(r1)
        elif pc==0xf30040:env['fields'].append((text(read(r2)),r3,read(u.reg_read(UC_ARM_REG_SP))));ret()
        elif pc==0x488238:assert r0==instance;u.mem_write(instance,bytes(0xa0));ret()
        elif pc==0x1872a8:ret(int(env['pause']))
        elif pc==0x8821a8:ret(0xf60000)
        elif pc==0x8890c4:word(r0,read(r2));word(r0+4,read(r2+4));ret()
        elif pc==0x888b8c:ret(0xf61000)
        elif pc==0x884378:ret(target if read(r1)==7 else 0)
        elif pc==0x13dea0:word(r0,r2);word(r0+4,r3);ret()
        elif pc==0xf30060:assert r0==instance and r1==target;env['hit']+=1;ret()
        elif pc==0xf30070:assert r0==instance and r1==0;env['hit']+=1;ret()
        elif pc==0x2708b4:assert r0==instance;env['removed']+=1;ret()
        elif pc==stop:u.emu_stop()
    u.hook_add(UC_HOOK_CODE,hook)
    def run(mode,args=(0,0,0,0)):
        u.reg_write(UC_ARM_REG_SP,stack);u.reg_write(UC_ARM_REG_LR,stop)
        for r,v in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),args):u.reg_write(r,v)
        u.reg_write(UC_ARM_REG_R4,0x12345678);u.emu_start(entry+mode*40,stop,count=100000)
        assert u.reg_read(UC_ARM_REG_PC)==stop and u.reg_read(UC_ARM_REG_SP)==stack
        assert u.reg_read(UC_ARM_REG_R4)==0x12345678
        return u.reg_read(UC_ARM_REG_R0)
    run(2);run(2);assert env['alloc']==[40,0x58] and env['registered']==1 and env['base']==2
    assert run(4)==meta and read(table)==entry+160 and read(table+0x48)==entry+240
    assert run(3)==instance and read(instance)==table and number(instance+0xa0)==0 and read(instance+0xa4)==0
    run(5,(reflect,desc,0,0));assert env['fields']==[('iris_age',0xa0,8),('iris_impacted',0xa4,6)]
    assert read(meta+0x24)==desc and read(desc+0x5c)==meta
    word(table+0x34,0xf30060);word(table+0x4c,0xf30070);word(instance+0x98,7)
    def tick(dt):run(6,(instance,struct.unpack('<I',struct.pack('<f',dt))[0],0,0))
    env['pause']=True;tick(0.1);assert number(instance+0xa0)==0
    env['pause']=False;tick(1);assert number(instance+0xa0)==0
    for _ in range(3):tick(0.1)
    assert env['hit']==0;tick(0.04);assert env['hit']==1 and read(instance+0xa4)==1 and not env['removed']
    for _ in range(8):tick(0.1)
    assert env['hit']==1 and not env['removed'];tick(0.1);assert env['removed']==1
    # Mid-animation restore has a saved impact marker and cannot hit twice.
    u.mem_write(instance+0xa0,struct.pack('<f',0.7));tick(0.1);assert env['hit']==1
    word(instance+0xa4,0);word(instance+0x98,0);tick(0.1);assert env['hit']==2
    print('PASS: own fire-stone RTClass, parent constructor/vtable/schema, ten-frame impact, 37-frame lifetime, pause, missing target and saved impact marker')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('library',type=Path);check(p.parse_args().library)
