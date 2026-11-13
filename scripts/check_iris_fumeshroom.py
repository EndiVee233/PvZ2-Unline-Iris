"""Run the compiled Fume-shroom ARM bridge against controlled board entities."""
import argparse
from pathlib import Path
import struct
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *


def check(path):
    data=path.read_bytes(); u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x1000000)
    u.reg_write(UC_ARM_REG_C1_C0_2,0xf<<20);u.reg_write(UC_ARM_REG_FPEXC,1<<30)
    ph=struct.unpack_from('<I',data,28)[0];step,n=struct.unpack_from('<HH',data,42)
    for p in range(ph,ph+step*n,step):
        kind,off,va,_,size,_,_,_=struct.unpack_from('<8I',data,p)
        if kind==1:u.mem_write(va,data[off:off+size])
    def word(p,v):u.mem_write(p,struct.pack('<I',v))
    def read(p):return struct.unpack('<I',u.mem_read(p,4))[0]
    def floats(p,*v):u.mem_write(p,struct.pack('<'+'f'*len(v),*v))
    fw,plant,ptype,name,clock,appslot,app,board=[0xf00000+i*0x1000 for i in range(8)]
    entities=[0xf10000+i*0x1000 for i in range(6)]
    vtable,ztype,gtype,plain,heavy_name,zname,gname= [0xf20000+i*0x1000 for i in range(7)]
    resultvec,stop,stack=0xf30000,0xf40000,0xfff000
    word(fw+4,plant);word(plant,0xf50000);word(0xf50070,0xf60000)
    word(fw,0xf50100);word(0xf50178,0xf60010)
    word(ptype+0x10,name);u.mem_write(name,b'POPANIM_PLANT_FUMESHROOM\0')
    word(0xd4ed90,clock);word(0xd00838,appslot);word(appslot,app);word(app+0x6c0,board)
    holder,holder_table,resource,effect_manager,effect=[0xf80000+i*0x1000 for i in range(5)]
    word(0xd008bc,appslot+0x100);word(appslot+0x100,holder)
    word(holder,holder_table);word(holder_table+8,0xf60050)
    floats(plant+0x10,200,200);word(plant+0x58,2);word(plant+0x5c,3)
    word(ztype+4,zname);word(ztype+8,0);u.mem_write(zname,b'Zombie\0')
    word(gtype+4,gname);word(gtype+8,ztype);u.mem_write(gname,b'ZombieGargantuar\0')
    word(plain+4,heavy_name);word(plain+8,0);u.mem_write(heavy_name,b'GridItem\0')
    for obj,x,row in zip(entities,[300,800,180,400,350,500],[2,3,2,2,2,1]):
        word(obj,vtable);floats(obj+0x10,x,200);word(obj+0x58,row)
    word(vtable,0xf60020);word(vtable+0x3c,0xf60030);word(vtable+0x34,0xf60040)
    env={'paused':False};hits=[];pushes=[];fallback=[];freed=[];clouds=[]
    def text(p):return bytes(u.mem_read(p,80)).split(b'\0')[0].decode()
    def ret(value=0):u.reg_write(UC_ARM_REG_R0,value);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    def hook(cpu,pc,size,_):
        r0,r1,r2,r3=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
        if pc==0x8821a8:ret(0xf70000)
        elif pc==0x8890c4:word(r0,read(r2) if r2!=plant+0xb8 else 1);word(r0+4,2);ret()
        elif pc==0x888b8c:ret(0xf71000)
        elif pc==0x884378:ret(resource if read(r1)==2 else ptype)
        elif pc==0x13dea0:word(r0,0);word(r0+4,0);ret()
        elif pc==0x248120:
            rect=struct.unpack('<4i',u.mem_read(r2,16));assert r1==6 and rect in ((3,2,15,1),(3,1,15,3))
            selected=[obj for obj in entities if rect[1]<=read(obj+0x58)<rect[1]+rect[3]]
            u.mem_write(resultvec,struct.pack('<'+'I'*len(selected),*selected))
            u.mem_write(r0,struct.pack('<3I',resultvec,resultvec+len(selected)*4,resultvec+len(selected)*4));ret()
        elif pc==0xf60000:ret(0)
        elif pc==0xf60010:ret(0)
        elif pc==0x129ae0:ret(123)
        elif pc==0xf60050:
            assert r1==holder and r2==123 and text(read(r3))=='POPANIM_EFFECTS_FUMESHROOM_BUBBLES'
            assert read(u.reg_read(UC_ARM_REG_SP))==0
            word(r0,2);word(r0+4,2);ret()
        elif pc==0x1809a8:assert r0==board;ret(effect)
        elif pc==0x23a354:assert (r0,r1,r2)==(effect,resource,0);ret(1)
        elif pc==0x23aa6c:
            assert r0==effect and r2==0;clouds.append(text(read(r1)));ret()
        elif pc==0x4e6bb8:
            assert r0==effect and r2==0xffffffff
            assert struct.unpack('<3f',u.mem_read(r1,12))==(145.0,85.0 if clouds[-1]=='plantfood' else 90.0,0.0)
            ret()
        elif pc==0x23a814:assert (r0,r1)==(effect,0);ret()
        elif pc==0xb76c4c:ret()
        elif pc==0xf60020:ret(plain if r0==entities[3] else gtype if r0==entities[5] else ztype)
        elif pc==0xf60030:ret(int(r0!=entities[4]))
        elif pc==0xf60040:
            owner,amount,flags=struct.unpack('<IfI',u.mem_read(r1,12))
            assert owner==plant and flags==0
            hits.append((r0,amount));ret()
        elif pc==0xb36928:freed.append(r0);ret()
        elif pc in (0x3ba164,0x3ba2c0,0xe8c10):ret()
        elif pc==0x1872a8:ret(int(env['paused']))
        elif pc==0x28b850:ret(0xf72000)
        elif pc==0xb75560:
            value=text(r1).encode()+b'\0';word(r0,0xf73000);word(0xf73000-4,0)
            u.mem_write(0xf73000,value);ret()
        elif pc==0x67a3d8:
            point=struct.unpack('<3f',u.mem_read(r2,12));duration=struct.unpack('<f',u.mem_read(u.reg_read(UC_ARM_REG_SP),4))[0]
            assert r1 in entities[:2] and abs(point[0]-struct.unpack('<f',u.mem_read(r1+0x10,4))[0]-120*duration)<1e-3
            pushes.append(r1);ret()
        elif pc==0x3e997c:
            assert (r0,r1,r2,r3)==(fw,0x11223344,0x55667788,0x99aabbcc)
            fallback.append(1);ret(0x1234)
        elif pc==stop:u.emu_stop()
    u.hook_add(UC_HOOK_CODE,hook)
    preserved=[UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,UC_ARM_REG_R8,UC_ARM_REG_R9,UC_ARM_REG_R10,UC_ARM_REG_R11]
    def run(mode):
        entry=struct.unpack_from('<I',data,[0xce45bc,0xce460c,0xce45e4,0xce4610,0xce45e0][mode])[0]
        u.reg_write(UC_ARM_REG_SP,stack);u.reg_write(UC_ARM_REG_LR,stop)
        for reg,v in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),(fw,0x11223344,0x55667788,0x99aabbcc)):u.reg_write(reg,v)
        for reg in preserved:u.reg_write(reg,0x76540000+reg)
        u.emu_start(entry,stop,count=100000)
        assert u.reg_read(UC_ARM_REG_PC)==stop and u.reg_read(UC_ARM_REG_SP)==stack
        assert all(u.reg_read(r)==0x76540000+r for r in preserved)
    run(4);assert not hits and not pushes
    run(0);assert hits==[(entities[0],20),(entities[3],20)] and not pushes
    assert clouds==['special']
    hits.clear();floats(clock+0x1c,10);run(1);assert read(plant+0x48)==5
    env['paused']=True;floats(clock+0x1c,11);run(2);assert not hits
    env['paused']=False
    floats(clock+0x1c,11.2);run(2);assert not hits  # still charging
    floats(clock+0x1c,11.3);run(0);assert not hits  # authored use_action starts gas
    assert clouds==['special','plantfood']
    for t in (11.4,11.7,12,13,14.99,15):floats(clock+0x1c,t);run(2)
    for obj in (entities[0],entities[1],entities[3],entities[5]):
        assert abs(sum(amount for who,amount in hits if who==obj)-1500)<.01
    assert not any(who in (entities[2],entities[4]) for who,_ in hits)
    assert pushes and entities[5] not in pushes
    run(3);assert read(plant+0x48)==4
    u.mem_write(name,b'POPANIM_PLANT_LASERBEAN\0');run(0)
    assert fallback==[1] and u.reg_read(UC_ARM_REG_R0)==0x1234
    print('PASS: fume 20 line/grave damage; three-row PF total 1500; flying/range/heavy filters; pause; stock fallback; ARM ABI')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('library',type=Path);check(p.parse_args().library)
