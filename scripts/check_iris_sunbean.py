"""Run compiled Sun Bean callbacks through consumption, carry and PF expiry."""
import argparse
from pathlib import Path
import struct
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *


def check(path):
    data=path.read_bytes();u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x1000000)
    u.reg_write(UC_ARM_REG_C1_C0_2,0xf<<20);u.reg_write(UC_ARM_REG_FPEXC,1<<30)
    ph=struct.unpack_from('<I',data,28)[0];step,n=struct.unpack_from('<HH',data,42)
    for q in range(ph,ph+step*n,step):
        kind,off,va,_,size,_,_,_=struct.unpack_from('<8I',data,q)
        if kind==1:u.mem_write(va,data[off:off+size])
    fw,plant,ptype,name,zombie,zmeta,zname,manager,vec,damage,out,appslot,app,board,clock,collect,rig=[0xf00000+i*0x1000 for i in range(17)]
    textslot,stop,stack=0xf20000,0xf30000,0xfff000
    def word(p,v):u.mem_write(p,struct.pack('<I',v))
    def read(p):return struct.unpack('<I',u.mem_read(p,4))[0]
    def floating(p,v):u.mem_write(p,struct.pack('<f',v))
    def number(p):return struct.unpack('<f',u.mem_read(p,4))[0]
    def text(p):return bytes(u.mem_read(p,110)).split(b'\0')[0].decode()
    word(fw+4,plant);word(ptype+0x10,name);u.mem_write(name,b'POPANIM_PLANT_SUNBEAN\0')
    word(plant+0xb8,7);word(zombie+8,77);word(zombie+12,1)
    word(zombie,0xf40000);word(0xf40000,0xf50000);word(zmeta+4,zname);u.mem_write(zname,b'Zombie\0')
    word(plant,0xf41000);word(0xf41070,0xf50010)
    word(collect,0xf42000);word(0xf42058,0xf50020)
    word(0xd00838,appslot);word(appslot,app);word(app+0x6c0,board)
    word(0xd4ed90,clock);word(board+0xa8,5)
    word(manager+0x10,vec);word(manager+0x14,vec);word(manager+0x18,vec+4096)
    floating(plant+0x4c,50);word(damage,zombie);floating(damage+4,100)
    floating(zombie+0x10,650);floating(zombie+0x14,250);floating(zombie+0xb0,200);floating(zombie+0x34,100)
    entry=struct.unpack_from('<I',data,0xce3ad8)[0]
    env={'sun':0,'spawn':0,'dead':False,'kill':0,'pause':False,'stock':0,'labels':[],'stun':0}
    def ret(v=0):u.reg_write(UC_ARM_REG_R0,v);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    def hook(cpu,pc,size,_):
        r0,r1,r2,r3=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
        if pc==0x8821a8:ret(0xf60000)
        elif pc==0x8890c4:word(r0,read(r2));word(r0+4,read(r2+4));ret()
        elif pc==0x888b8c:ret(0xf61000)
        elif pc==0x884378:ret(ptype if read(r1)==7 else 0 if env['dead'] else zombie)
        elif pc==0x13dea0:word(r0,r2);word(r0+4,r3);ret()
        elif pc==0xf50000:ret(zmeta)
        elif pc==0xf50010:ret(rig)
        elif pc==0x3d6f04:assert r0==board;ret(manager)
        elif pc==0x3d9578:assert (r0,r1)==(manager,zombie);ret(1)
        elif pc==0x3d9ac4:
            assert r0==manager+0x10
            end=read(manager+0x14);u.mem_write(end,bytes(u.mem_read(r1,32)));word(manager+0x14,end+32);ret()
        elif pc==0x13f310:u.mem_write(r0,bytes(u.mem_read(r2,24)));ret(r0)
        elif pc==0x1872a8:ret(int(env['pause']))
        elif pc==entry+200:
            # The original subsystem erases state 2 and leaves reserved states.
            rows=[bytes(u.mem_read(p,32)) for p in range(vec,read(manager+0x14),32) if read(p+0x18)!=2]
            for i,row in enumerate(rows):u.mem_write(vec+i*32,row)
            word(manager+0x14,vec+len(rows)*32);ret()
        elif pc==0xb75560:
            u.mem_write(textslot,text(r1).encode()+b'\0');word(textslot-4,0);word(r0,textslot);ret()
        elif pc in (0xb76c4c,0xe8c10):ret()
        elif pc==0x17b6e4:
            label=text(read(r1));assert label in ('iris_dark_sun','sun_small')
            env['sun']+=25 if label=='iris_dark_sun' else 5;env['spawn']+=1;ret(collect)
        elif pc==0xf50020:assert r0==collect;ret()
        elif pc in (0x1d2fe0,0x1d2cc4):assert r0==collect;ret()
        elif pc==0x5e0ed8:assert (r0,r1)==(zombie,2);env['stun']+=1;ret()
        elif pc==0x5e0b54:assert r0==zombie and not read(zombie+0xa8)&0x1000;ret()
        elif pc==0x5e147c:assert (r0,r1)==(zombie,0);env['kill']+=1;ret()
        elif pc in (0x3ba164,0x3ba2c0):ret()
        elif pc in (0x44d220,0x44d0b0):assert r0==rig;env['labels'].append(text(read(r1)));ret()
        elif pc==0x3d6d54:env['stock']+=1;ret(55)
        elif pc==stop:u.emu_stop()
    u.hook_add(UC_HOOK_CODE,hook)
    preserved=[UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,UC_ARM_REG_R8,UC_ARM_REG_R9,UC_ARM_REG_R10,UC_ARM_REG_R11]
    def run(mode,args=None):
        u.reg_write(UC_ARM_REG_SP,stack);u.reg_write(UC_ARM_REG_LR,stop)
        for reg,val in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),args or (fw,0,0,0)):u.reg_write(reg,val)
        for reg in preserved:u.reg_write(reg,0x76540000+reg)
        u.emu_start(entry+mode*40,stop,count=150000)
        assert u.reg_read(UC_ARM_REG_PC)==stop and u.reg_read(UC_ARM_REG_SP)==stack
        assert all(u.reg_read(reg)==0x76540000+reg for reg in preserved)
        return u.reg_read(UC_ARM_REG_R0)
    def eat():return run(0,(out,fw,damage,0))
    def tick():run(3,(manager,0,0,0))
    eat();assert read(manager+0x14)==vec+32 and number(vec+0x10)==300
    eat();assert read(manager+0x14)==vec+32 # no stacking the same damage
    floating(zombie+0x34,80);tick();assert env['sun']==0 # four points carried
    floating(zombie+0x34,75);tick();assert env['sun']==5
    saved=bytes(u.mem_read(vec,32));u.mem_write(vec,bytes(32));u.mem_write(vec,saved)
    floating(zombie+0xb0,100);tick();assert env['sun']==25
    env['pause']=True;floating(zombie+0xb0,0);tick();assert env['sun']==25
    env['pause']=False;env['dead']=True;tick();assert env['sun']==60 and read(manager+0x14)==vec
    # The 300 sunlight cap includes helmet health and survives serialized state.
    env['dead']=False;floating(zombie+0xb0,2000);floating(zombie+0x34,100);eat()
    floating(zombie+0xb0,0);tick();assert env['sun']==360 and read(manager+0x14)==vec
    # Charged form: full activation, persisted plant state, 1+2 second fuse,
    # double conversion with a 600-point cap, and exactly one native kill.
    floating(zombie+0xb0,2000);floating(zombie+0x34,100);floating(clock+0x1c,10)
    run(1);assert read(plant+0x88)==1;run(2);assert env['labels']==['plantfood_on','plantfood']
    eat();assert env['stun']==1 and read(zombie+0xa8)&0x1000
    floating(clock+0x1c,12.9);tick();assert env['sun']==360 and env['kill']==0
    floating(clock+0x1c,13);tick();assert env['sun']==960 and env['kill']==1
    tick();assert env['sun']==960 and env['kill']==1
    u.mem_write(name,b'POPANIM_PLANT_CHILIBEAN\0');assert eat()==55 and env['stock']==1
    print('PASS: Sun Bean fatal consumption, nonstacking, 5-sun carry, body/helm cap, pause, weak death, serialized state, charged 1+2s burst, stock fallback and ARM ABI')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('library',type=Path);check(p.parse_args().library)
