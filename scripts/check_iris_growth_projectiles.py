"""Exercise native Ice-shot probability, bounded splitting and stock fallback."""
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
    entry=struct.unpack_from('<I',data,0xce754c)[0]
    assert struct.unpack_from('<I',data,0xce7564)[0]==entry+40
    projectile,props,source,sheet,actions,hit,near1,near2,far,vec,clock,appslot,app,board=[0xf00000+i*0x1000 for i in range(14)]
    pmeta,zmeta,pname,zname,name,stop,stack=0xf20000,0xf21000,0xf22000,0xf23000,0xf24000,0xf30000,0xfff000
    def word(a,v):u.mem_write(a,struct.pack('<I',v))
    def read(a):return struct.unpack('<I',u.mem_read(a,4))[0]
    def floating(a,v):u.mem_write(a,struct.pack('<f',v))
    def number(a):return struct.unpack('<f',u.mem_read(a,4))[0]
    def text(a):return bytes(u.mem_read(a,120)).split(b'\0')[0].decode()
    word(projectile+0x10,props);word(props+0x70,name);u.mem_write(name,b'POPANIM_EFFECTS_ICESHROOM_BULLET\0')
    word(projectile+0x20,1);word(projectile+0x5c,2);floating(projectile+0x2c,600);floating(projectile+0x30,250)
    word(projectile,0xf43000);word(0xf4304c,entry+40)
    word(source,0xf40000);word(0xf40000,0xf50000);word(pmeta+4,pname);u.mem_write(pname,b'Plant\0')
    for i,z in enumerate((hit,near1,near2,far)):
        word(z,0xf41000);word(0xf41000,0xf50010);word(0xf4103c,0xf50020)
        word(0xf41040,0xf50030);word(0xf41034,0xf50040)
        word(z+8,20+i);word(z+0xc,1);floating(z+0x10,600+(20*i if i<3 else 400));floating(z+0x14,250)
    word(zmeta+4,zname);u.mem_write(zname,b'Zombie\0')
    word(sheet+0x30,actions);word(sheet+0x34,actions+3*0x60)
    for i in range(3):word(actions+i*0x60+8,100+i);word(actions+i*0x60+12,1)
    word(0xd00838,appslot);word(appslot,app);word(app+0x6c0,board);word(0xd4ed90,clock)
    env={'random':0,'freeze':[],'spawn':[],'impact':0,'collision':0,'source':True,'damage':[],'splash':[],'blocked':False}
    def ret(v=0):u.reg_write(UC_ARM_REG_R0,v);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    def hook(cpu,pc,size,_):
        r0,r1,r2,r3=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
        sp=u.reg_read(UC_ARM_REG_SP)
        if pc==0x8821a8:ret(0xf60000)
        elif pc==0x8890c4:word(r0,read(r2));word(r0+4,read(r2+4));ret()
        elif pc==0x888b8c:ret(0xf61000)
        elif pc==0x884378:ret(source if read(r1)==1 and env['source'] else sheet if read(r1)==2 else 0)
        elif pc==0x13dea0:word(r0,r2);word(r0+4,r3);ret()
        elif pc==0xf50000:ret(pmeta)
        elif pc==0xf50010:ret(zmeta)
        elif pc==0xf50020:assert r1==3;ret(1)
        elif pc==0xf50030:ret(int(env['blocked']))
        elif pc==0xf50040:env['damage'].append(number(r1+4));ret()
        elif pc==0x39e838:assert r1==source;word(r0,2);word(r0+4,1);ret()
        elif pc==0x7a3e90:assert r0==1000;ret(env['random'])
        elif pc==0x5e0ed8:
            assert r1==1 and struct.unpack('<f',struct.pack('<I',r2))[0]==5
            env['freeze'].append(r0);ret()
        elif pc==0x248120:
            assert r1==6;u.mem_write(vec,struct.pack('<5I',hit,near1,near2,far,0))
            word(r0,vec);word(r0+4,vec+20);word(r0+8,vec+20);ret()
        elif pc==0x180cd0:
            assert r0==board and struct.unpack('<f',struct.pack('<I',r1))[0]==600
            weak=read(sp);assert read(weak) in (101,102) and read(sp+4)==source
            child=0xf70000+len(env['spawn'])*0x100
            u.mem_write(child,bytes(0x100));floating(child+0x2c,600);floating(child+0x30,250)
            env['spawn'].append((child,read(weak)));ret(child)
        elif pc==0x489930:env['impact']+=1;env['splash'].append(number(props+0x20));ret(91)
        elif pc==0x4896d8:u.mem_write(r1,bytes(24));floating(r1+4,number(props+0x14));ret()
        elif pc==0x48958c:env['collision']+=1;ret(71)
        elif pc in (0xb36928,0xe8c10):ret()
        elif pc==stop:u.emu_stop()
    u.hook_add(UC_HOOK_CODE,hook)
    def run(mode,target=hit):
        u.reg_write(UC_ARM_REG_R0,projectile);u.reg_write(UC_ARM_REG_R1,target)
        u.reg_write(UC_ARM_REG_SP,stack);u.reg_write(UC_ARM_REG_LR,stop);u.reg_write(UC_ARM_REG_R4,0x12345678)
        u.emu_start(entry+mode*40,stop,count=200000)
        assert u.reg_read(UC_ARM_REG_PC)==stop and u.reg_read(UC_ARM_REG_SP)==stack
        assert u.reg_read(UC_ARM_REG_R4)==0x12345678
        return u.reg_read(UC_ARM_REG_R0)
    floating(props+0x14,36);assert run(1)==91 and env['freeze']==[hit] and not env['spawn']
    env['random']=75;run(1);assert len(env['freeze'])==1
    env['random']=74;floating(props+0x14,60);run(1)
    assert len(env['freeze'])==2 and len(env['spawn'])==2
    for child,kind in env['spawn']:
        assert kind==101 and read(child+0x98)==20 and read(child+0x9c)==1
        assert number(child+0x38)>0 and number(child+0x3c)==0
    floating(props+0x14,30);run(1);assert len(env['spawn'])==4 and all(k==102 for _,k in env['spawn'][2:])
    assert len(env['freeze'])==2
    floating(props+0x14,15);run(1);assert len(env['spawn'])==4
    word(projectile+0x98,20);word(projectile+0x9c,1)
    assert run(0)==0 and env['collision']==0
    assert run(0,near1)==71 and env['collision']==1
    env['source']=False;floating(props+0x14,60);run(1);assert len(env['spawn'])==4
    u.mem_write(name,b'POPANIM_STOCK_UNRELATED\0');assert run(0)==71 and run(1)==91
    assert len(env['freeze'])==2 and len(env['spawn'])==4
    u.mem_write(name,b'POPANIM_EFFECTS_FIRESHROOM_BULLET\0');floating(props+0x14,45);floating(props+0x20,37)
    assert run(0)==91 and abs(env['damage'][-1]-51.75)<0.001
    assert abs(env['splash'][-1]-42.55)<0.001 and number(props+0x14)==45 and number(props+0x20)==37
    env['blocked']=True;before=len(env['damage']);assert run(0)==0 and len(env['damage'])==before
    print('PASS: scoped freeze probability, two bounded split generations, native spawn ABI, saved exclusion handle, vanished source and stock fallback')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('library',type=Path);check(p.parse_args().library)
