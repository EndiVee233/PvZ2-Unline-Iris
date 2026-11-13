"""Exercise compiled ground effects, including pause, reload and destruction."""
import argparse
from pathlib import Path
import struct
from native_payload import registration_payload
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *


def check(path):
    data=path.read_bytes();u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x1000000)
    u.reg_write(UC_ARM_REG_C1_C0_2,0xf<<20);u.reg_write(UC_ARM_REG_FPEXC,1<<30)
    ph=struct.unpack_from('<I',data,28)[0];stride,n=struct.unpack_from('<HH',data,42)
    for h in range(ph,ph+stride*n,stride):
        kind,off,va,_,size,_,_,_=struct.unpack_from('<8I',data,h)
        if kind==1:u.mem_write(va,data[off:off+size])
    entry=registration_payload(data,0x282388,'IrisIceHole')
    parent,registry,reflect,ptype,desc,textslot,stop=[0xf00000+i*0x1000 for i in range(7)]
    appslot,app,board,clock,holder_slot,holder=[0xf10000+i*0x1000 for i in range(6)]
    effect,resource,vec,meta_name=[0xf20000+i*0x1000 for i in range(4)]
    zombie=0xf24000;stack=0xfff000
    def word(p,v):u.mem_write(p,struct.pack('<I',v))
    def read(p):return struct.unpack('<I',u.mem_read(p,4))[0]
    def fl(p,v):u.mem_write(p,struct.pack('<f',v))
    def number(p):return struct.unpack('<f',u.mem_read(p,4))[0]
    def text(p):return bytes(u.mem_read(p,100)).split(b'\0')[0].decode()
    word(registry,0xf30000);word(0xf3000c,0xf40000);word(reflect,0xf31000)
    for o,fn in ((0x24,0xf40010),(0x28,0xf40020),(0x14,0xf40030),(0x2c,0xf40040),(0x20,0xf40050)):word(0xf31000+o,fn)
    word(ptype,0xf32000);word(0xf32034,0xf40060)
    word(0xd00838,appslot);word(appslot,app);word(app+0x6c0,board);word(board+0xa8,5)
    word(0xd4ed90,clock);word(0xd008bc,holder_slot);word(holder_slot,holder)
    word(holder,0xf33000);word(0xf33008,0xf40070)
    word(zombie,0xf34000);word(0xf34000,0xf40080);word(0xf3403c,0xf40090)
    word(0xf34034,0xf400a0);word(0xf34058,0xf400b0)
    word(meta_name+4,meta_name+0x100);u.mem_write(meta_name+0x100,b'Zombie\0')
    word(zombie+8,88);word(zombie+12,1);fl(zombie+0x10,500);fl(zombie+0x14,300)
    env={'alloc':[],'registered':[],'fields':[],'base':0,'pause':False,'effect':False,'labels':[],
         'damage':[],'kills':0,'removed':[],'zombie':False,'stun':0,'destruct':0,'delete':[]}
    def ret(v=0):u.reg_write(UC_ARM_REG_R0,v);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    def hook(cpu,pc,size,_):
        r0,r1,r2,r3=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
        if pc==entry+480:env['base']+=1;ret()
        elif pc==0xb363dc:
            p=0xf50000+len(env['alloc'])*0x200;env['alloc'].append((p,r0));u.mem_write(p,b'\xcd'*r0);ret(p)
        elif pc in (0x894ca0,0xb76c4c,0xe8c10):ret()
        elif pc==0x283394:ret(parent)
        elif pc==0x895608:assert r2==parent and text(r1) in ('IrisIceHole','IrisFireWall');ret()
        elif pc==0x851728:ret(0xf35000)
        elif pc==0x851920:ret(registry)
        elif pc==0xb75560:u.mem_write(textslot,text(r1).encode()+b'\0');word(textslot-4,100);word(r0,textslot);ret()
        elif pc==0xf40000:env['registered'].append((text(read(r1)),r2,r3));ret()
        elif pc==0xf40010:assert text(read(r1)) in ('GridItem','Plant','Zombie','Effect_PopAnim');ret(ptype)
        elif pc==0xf40060:ret(123)
        elif pc==0xf40020:assert (r0,r1,r2,r3)==(reflect,desc,123,0);ret()
        elif pc==0xf40030:assert r1 in (6,8) and r2==4;ret(r1)
        elif pc==0xf40050:assert (r1,r2,r3)==(3,ptype,0);ret(99)
        elif pc==0xf40040:env['fields'].append((text(read(r2)),r3));ret()
        elif pc==0x282ae4:u.mem_write(r0,bytes(0x50));ret(r0)
        elif pc==0x282b78:env['destruct']+=1;ret()
        elif pc==0xb36928:env['delete'].append(r0);ret()
        elif pc==0x1872a8:ret(int(env['pause']))
        elif pc==0x8821a8:ret(0xf36000)
        elif pc==0x8890c4:word(r0,read(r2));word(r0+4,read(r2+4));ret()
        elif pc==0x888b8c:ret(0xf37000)
        elif pc==0x884378:
            ident=read(r1);ret(resource if ident==77 else effect if ident==66 and env['effect'] else zombie if ident==88 and env['zombie'] else 0)
        elif pc==0x13dea0:word(r0,r2);word(r0+4,r3);ret()
        elif pc==0x129ae0:ret(999)
        elif pc==0xf40070:word(r0,77);ret()
        elif pc==0x1809a8:env['effect']=True;word(effect+8,66);word(effect+12,1);ret(effect)
        elif pc==0x23a354:assert (r0,r1,r2)==(effect,resource,0);ret()
        elif pc==0x23a814:assert r0==effect and r1==0;ret()
        elif pc==0x23aa6c:env['labels'].append(text(read(r1)));ret()
        elif pc==0x4e6bb8:assert r0==effect;ret()
        elif pc==0x2708b4:
            env['removed'].append(r0)
            if r0==effect:env['effect']=False
            ret()
        elif pc==0x248120:
            assert r1==2;word(vec,zombie);word(r0,vec);word(r0+4,vec+4 if env['zombie'] else vec);word(r0+8,vec+4);ret()
        elif pc==0xf40080:ret(meta_name)
        elif pc==0xf40090:assert r1==1;ret(1)
        elif pc==0xf400a0:assert read(r1+8)==0x80;env['damage'].append(number(r1+4));ret()
        elif pc==0xf400b0:fl(zombie+0x18,number(r1+8));ret()
        elif pc==0x5e0ed8:assert r0==zombie and r1==2;env['stun']+=1;ret()
        elif pc==0x5e147c:assert r0==zombie;env['kills']+=1;env['zombie']=False;ret()
        elif pc==stop:u.emu_stop()
    u.hook_add(UC_HOOK_CODE,hook)
    def run(mode,args=(0,0,0,0)):
        u.reg_write(UC_ARM_REG_SP,stack);u.reg_write(UC_ARM_REG_LR,stop)
        for r,v in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),args):u.reg_write(r,v)
        u.reg_write(UC_ARM_REG_R4,0x12345678);u.emu_start(entry+mode*40,stop,count=200000)
        assert u.reg_read(UC_ARM_REG_PC)==stop and u.reg_read(UC_ARM_REG_SP)==stack
        assert u.reg_read(UC_ARM_REG_R4)==0x12345678
        return u.reg_read(UC_ARM_REG_R0)
    run(0);run(0)
    assert env['base']==2 and [n for n,_,_ in env['registered']]==['IrisIceHole','IrisFireWall']
    assert len(env['alloc'])==4
    run(5,(reflect,desc,0,0));fields=dict(env['fields'])
    assert fields['iris_effect']==0x64 and fields['iris_sink4z']==0xcc and fields['iris_source']==0x74
    assert len(fields)==24
    ice=run(1);fire=run(2)
    assert read(ice+0x50)==0 and read(fire+0x50)==1
    for p in (ice,fire):fl(p+0x10,500);fl(p+0x14,300);run(11,(p,0,0,0))
    assert read(fire+0x38)==1 and number(fire+0x3c)==1000
    def tick(p,t):fl(clock+0x1c,t);run(10,(p,0,0,0))
    tick(fire,10);assert env['labels'][-1]=='plantfood_in'
    env['zombie']=True;tick(fire,11);assert not env['damage']
    tick(fire,11.34);assert env['damage']==[300] and env['labels'][-1]=='plantfood'
    tick(fire,12);assert env['damage']==[300]
    env['pause']=True;tick(fire,14);assert len(env['damage'])==1
    env['pause']=False;tick(fire,14);assert env['damage']==[300,300]
    # Existing saved visual is reused, rather than duplicated after reload.
    before=len(env['labels']);tick(fire,14.1);assert len(env['labels'])==before
    tick(fire,18.1);assert env['labels'][-1]=='plantfood_out'
    tick(fire,19);assert fire in env['removed'] and effect in env['removed']
    tick(ice,20);tick(ice,21.21);assert env['stun']==1 and read(ice+0x60)==1
    tick(ice,21.3);assert env['stun']==1 and number(zombie+0x18)<0
    tick(ice,22);assert env['kills']==1 and read(ice+0x80)==0
    tick(ice,25);assert ice in env['removed']
    run(8,(ice,0,0,0));assert env['destruct']==1 and ice in env['delete']
    print('PASS: independent trap classes, factories/schema/weak ownership, pause, fire 300/2s/8s, intro/out, saved visual reuse, ice single capture/sink/kill and cleanup')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('library',type=Path);check(p.parse_args().library)
