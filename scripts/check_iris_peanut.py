"""Exercise compiled Peanut combat, shell damage, save schema and ARM bridge."""
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
    fw,plant,ptype,name,rig,shot,out,damage,reflection,appslot,app,board,vec,clock=[0xf00000+i*0x1000 for i in range(14)]
    textslot,stop,stack=0xf20000,0xf30000,0xfff000
    def word(p,v):u.mem_write(p,struct.pack('<I',v))
    def read(p):return struct.unpack('<I',u.mem_read(p,4))[0]
    def floats(p,v):u.mem_write(p,struct.pack('<f',v))
    def number(p):return struct.unpack('<f',u.mem_read(p,4))[0]
    def string(p):return bytes(u.mem_read(p,90)).split(b'\0')[0].decode()
    word(fw+4,plant);word(plant,0xf40000);word(0xf40070,0xf50000)
    word(ptype+0x10,name);u.mem_write(name,b'POPANIM_PLANT_PEANUT\0');word(plant+0x60,1)
    word(rig,0xf41000);word(0xf41044,0xf50010)
    word(reflection,0xf42000);word(0xf42014,0xf50020);word(0xf4202c,0xf50030)
    word(0xd00838,appslot);word(appslot,app);word(app+0x6c0,board)
    word(0xd4ed90,clock);floats(clock+0x1c,10)
    word(vec,plant);floats(plant+0x4c,4000);floats(fw+0x24,-1)
    entry=struct.unpack_from('<I',data,0xce529c)[0]
    env={'shots':0,'layers':{},'fallback':0,'reflect':0,'idle':0,'food':0,'labels':[]}
    def ret(value=0):u.reg_write(UC_ARM_REG_R0,value);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    def hook(cpu,pc,size,_):
        r0,r1,r2,r3=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
        if pc==0x8821a8:ret(0xf60000)
        elif pc==0x8890c4:word(r0,1);word(r0+4,2);ret()
        elif pc==0x888b8c:ret(0xf61000)
        elif pc==0x884378:ret(ptype)
        elif pc==0x13dea0:word(r0,0);word(r0+4,0);ret()
        elif pc==0xf50000:assert r0==plant;ret(rig)
        elif pc==0xf50010:assert r0==rig;ret()
        elif pc==0x3a1b88:
            assert r0==plant and read(plant+0xb4)==0;env['shots']+=1;floats(shot+0x2c,200);floats(shot+0x30,100);floats(shot+0x34,0);ret(shot)
        elif pc==0x48a78c:assert r0==shot and number(shot+0x30)==100;ret()
        elif pc==0x3a05f4:assert r0==plant;floats(plant+0x4c,4000);ret()
        elif pc==0x3ba164:env['food']+=1;word(plant+0x48,5);word(plant+0xb4,0xffffffff);ret()
        elif pc in (0x44d0b0,0x44d220):assert r0==rig;ret()
        elif pc==0x3ba2c0:ret()
        elif pc==0x3a50c4:env['idle']+=1;ret()
        elif pc==0x13f310:u.mem_write(r0,bytes(u.mem_read(r2,24)));ret(r0)
        elif pc==0x44cd0c:assert r0==rig;env['layers'][string(read(r1))]=bool(r2);ret()
        elif pc==0xb75560:
            s=string(r1).encode()+b'\0';word(r0,textslot);word(textslot-4,0);u.mem_write(textslot,s);ret()
        elif pc in (0xb76c4c,0xe8c10):ret()
        elif pc==0xb363dc:assert r0==0x28;ret(fw)
        elif pc==entry+440:assert (r0,r1)==(reflection,0x12345678);env['reflect']+=1;ret()
        elif pc==0x3b963c:assert r0==fw;ret()
        elif pc==0xf50020:assert (r0,r1,r2)==(reflection,8,4);ret(567)
        elif pc==0xf50030:
            assert (r0,r1,r3)==(reflection,0x12345678,0x20)
            assert string(read(r2))=='iris_peanut_shell' and read(u.reg_read(UC_ARM_REG_SP))==567;ret()
        elif pc==0x248120:
            assert r1==1 and struct.unpack('<4i',u.mem_read(r2,16))==(0,0,16,6)
            u.mem_write(r0,struct.pack('<3I',vec,vec+4,vec+4));ret()
        elif pc==0xb36928:ret()
        elif pc==0x44d13c:
            assert r0==rig and r2==7 and r3==0xabc and read(u.reg_read(UC_ARM_REG_SP))==0xdef
            env['labels'].append(string(read(r1)));ret(99)
        elif pc==0x3fc8b4:
            assert (r0,r1,r2,r3)==(fw,11,22,33);env['fallback']+=1;ret(101)
        elif pc==stop:u.emu_stop()
    u.hook_add(UC_HOOK_CODE,hook)
    preserved=[UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,UC_ARM_REG_R8,UC_ARM_REG_R9,UC_ARM_REG_R10,UC_ARM_REG_R11]
    def run(mode,args=None):
        u.reg_write(UC_ARM_REG_SP,stack);u.reg_write(UC_ARM_REG_LR,stop);word(stack,0xdef)
        for reg,val in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),args or (fw,11,22,33)):u.reg_write(reg,val)
        for reg in preserved:u.reg_write(reg,0x76540000+reg)
        u.emu_start(entry+mode*40,stop,count=100000)
        assert u.reg_read(UC_ARM_REG_SP)==stack and u.reg_read(UC_ARM_REG_PC)==stop
        assert all(u.reg_read(r)==0x76540000+r for r in preserved)
        return u.reg_read(UC_ARM_REG_R0)
    run(5);assert number(fw+0x20)==0 and number(fw+0x24)==-1
    run(8);assert not any(env['layers'].values())
    run(0);assert env['shots']==2
    floats(plant+0x4c,1800);run(0);assert env['shots']==3
    run(1);assert number(plant+0x4c)==4000 and number(fw+0x20)==4000 and env['food']==1
    assert env['layers']=={'Plantfood_Helmet2':True,'Plantfood_Helmet2_damage1':False,'Plantfood_Helmet2_Damage2':False,'peanut_plantfood_armor':True}
    run(0);assert env['shots']==3  # animation marker during food must not add peas
    floats(clock+0x1c,10.5);run(9);assert read(fw+0x10)==0
    floats(clock+0x1c,11.6);run(9);assert 29<=read(fw+0x10)<=30
    saved=bytes(u.mem_read(fw+8,32));u.mem_write(fw+8,bytes(32));u.mem_write(fw+8,saved)
    floats(clock+0x1c,12.7);run(9);assert read(fw+0x10)==60 and env['shots']==63
    assert read(plant+0xb4)==0xffffffff
    run(10,(out,fw,0,0));assert string(read(out))==''
    run(9);assert env['shots']==63 # serialized counter prevents duplicate fire
    for amount,flag,remaining,passed in ((1500,0,2500,0),(3000,0,0,500),(100,0,0,100),(-100,2,0,-100)):
        floats(damage+4,amount);word(damage+8,flag);run(3,(out,fw,damage,0))
        assert number(fw+0x20)==remaining and number(out+4)==passed
    run(2);assert read(plant+0x48)==4 and env['idle']==1
    run(6,(reflection,0x12345678,0,0));assert env['reflect']==1
    floats(plant+0x4c,1800);word(plant+0x48,4);word(rig+0x180,1);word(rig+0x188,0)
    run(4);assert read(plant+0x84)==3 and read(rig+0x188)==2
    # Preserve the fifth callback argument through the ARM -> Thumb bridge.
    word(textslot,0);u.mem_write(textslot+100,b'attack\0');word(textslot,textslot+100)
    assert run(7,(rig,textslot,7,0xabc))==99 and env['labels']==['attack_damage2']
    u.mem_write(name,b'POPANIM_PLANT_REPEATER\0');assert run(0)==101 and env['fallback']==1
    print('PASS: Peanut two/one heads, full 60-shot food timeline, action restoration, food audio, shell overflow/healing, save schema, damaged callbacks, stock fallback, ARM ABI')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('library',type=Path);check(p.parse_args().library)
