"""Exercise the compiled Rogue class, including native ABI and saved state."""
import argparse,struct
from pathlib import Path
from native_payload import registration_payload
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *


def check(path):
    raw=path.read_bytes();u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x1000000)
    u.reg_write(UC_ARM_REG_C1_C0_2,0xf<<20);u.reg_write(UC_ARM_REG_FPEXC,1<<30)
    ph=struct.unpack_from('<I',raw,28)[0];stride,n=struct.unpack_from('<HH',raw,42)
    for h in range(ph,ph+stride*n,stride):
        kind,off,va,_,size,_,_,_=struct.unpack_from('<8I',raw,h)
        if kind==1:u.mem_write(va,raw[off:off+size])
    entry=registration_payload(raw,0x619fc0,'ZombieIrisRogue')
    parent,registry,reflect,ptype,desc,textslot,stop=[0xf00000+i*0x1000 for i in range(7)]
    appslot,app,board,clock=[0xf10000+i*0x1000 for i in range(4)]
    plant,planttype,framework,vec=[0xf20000+i*0x1000 for i in range(4)]
    stack=0xfff000
    def word(p,v):u.mem_write(p,struct.pack('<I',v))
    def read(p):return struct.unpack('<I',u.mem_read(p,4))[0]
    def fl(p,v):u.mem_write(p,struct.pack('<f',v))
    def number(p):return struct.unpack('<f',u.mem_read(p,4))[0]
    def text(p):return bytes(u.mem_read(p,100)).split(b'\0')[0].decode()
    word(registry,0xf30000);word(0xf3000c,0xf40000);word(reflect,0xf31000)
    for o,fn in ((0x24,0xf40010),(0x28,0xf40020),(0x14,0xf40030),(0x2c,0xf40040)):word(0xf31000+o,fn)
    word(ptype,0xf32000);word(0xf32034,0xf40060)
    word(0xd00838,appslot);word(appslot,app);word(app+0x6c0,board);word(board+0xa8,5);word(0xd4ed90,clock)
    word(plant+0x30,framework);word(plant+0xb8,77);word(plant+0xbc,1)
    word(planttype+0x10,planttype+0x100);u.mem_write(planttype+0x100,b'POPANIM_PLANT_STREETLAMP\0')
    fl(plant+0x10,500);fl(plant+0x14,300)
    env={'alloc':[],'registered':[],'fields':[],'pause':False,'lamps':False,'native_updates':0,'draws':[],'damage':0,'labels':[]}
    def ret(v=0):u.reg_write(UC_ARM_REG_R0,v);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    def hook(cpu,pc,size,_):
        r0,r1,r2,r3=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
        if pc==entry+320:ret()
        elif pc==0xb363dc:
            p=0xf50000+len(env['alloc'])*0x1000;env['alloc'].append((p,r0));u.mem_write(p,b'\xcd'*r0);ret(p)
        elif pc in (0x894ca0,0xb76c4c,0xe8c10,0xb36928):ret()
        elif pc==0x5e8c4c:ret(parent)
        elif pc==0x895608:assert r2==parent and text(r1)=='ZombieIrisRogue';ret()
        elif pc==0x851728:ret(0xf35000)
        elif pc==0x851920:ret(registry)
        elif pc==0xb75560:u.mem_write(textslot,text(r1).encode()+b'\0');word(textslot-4,100);word(r0,textslot);ret()
        elif pc==0xf40000:env['registered'].append((text(read(r1)),r2,r3));ret()
        elif pc==0xf40010:assert text(read(r1))=='Zombie';ret(ptype)
        elif pc==0xf40060:ret(123)
        elif pc==0xf40020:assert (r0,r1,r2,r3)==(reflect,desc,123,0);ret()
        elif pc==0xf40030:assert r1 in (6,8) and r2==4;ret(r1)
        elif pc==0xf40040:env['fields'].append((text(read(r2)),r3));ret()
        elif pc==0x5de8b8:ret(r0)
        elif pc==0x1872a8:ret(int(env['pause']))
        elif pc==0x5dfc80:env['native_updates']+=1;fl(r0+0x10,number(r0+0x10)-1);ret()
        elif pc==0x1a3dcc:
            u.mem_write(r0+0x10,bytes(u.mem_read(r1,12)));ret()
        elif pc==0x248120:
            assert r1==1;word(r0,vec if env['lamps'] else 0);word(r0+4,vec+4 if env['lamps'] else 0);word(vec,plant);ret()
        elif pc==0x8821a8:ret(0xf36000)
        elif pc==0x8890c4:word(r0,read(r2));word(r0+4,read(r2+4));ret()
        elif pc==0x888b8c:ret(0xf37000)
        elif pc==0x884378:ret(planttype if read(r1)==77 else 0)
        elif pc==0x13dea0:word(r0,r2);word(r0+4,r3);ret()
        elif pc==0x5e3428:env['draws'].append((read(r0+0xa8),[read(r0+0x174+i*4) for i in range(4)]));ret(45)
        elif pc==0x5e2e18:ret(1)
        elif pc==0x5e0b74:env['damage']+=1;ret(22)
        elif pc==stop:u.emu_stop()
    u.hook_add(UC_HOOK_CODE,hook)
    def run(mode,*args):
        for reg,v in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),list(args)+[0]*4):u.reg_write(reg,v)
        u.reg_write(UC_ARM_REG_SP,stack);u.reg_write(UC_ARM_REG_LR,stop);u.reg_write(UC_ARM_REG_R4,0x12345678)
        u.emu_start(entry+mode*40,stop,count=100000)
        assert u.reg_read(UC_ARM_REG_PC)==stop and u.reg_read(UC_ARM_REG_SP)==stack and u.reg_read(UC_ARM_REG_R4)==0x12345678
        return u.reg_read(UC_ARM_REG_R0)
    run(0);run(0);assert len(env['registered'])==1 and env['registered'][0][2]==0x1b0
    run(3,reflect,desc);assert [o for _,o in env['fields']]==list(range(0x190,0x1a8,4))
    z=run(1);assert env['alloc'][-1][1]==0x1b0 and read(z)==read(0xf80404)
    assert read(read(z)+0x64)==entry+4*40
    assert read(read(z)+0x7c)==0x5e2a94
    word(z+0x48,1);fl(z+0x10,740);fl(z+0x14,300);fl(clock+0x1c,1)
    run(4,z);assert read(z+0x190)==1 and number(z+0x10)==740
    # Pause preserves the saved transition deadline and suppresses movement.
    env['pause']=True;fl(clock+0x1c,20);before=env['native_updates'];run(4,z)
    assert read(z+0x190)==1 and env['native_updates']==before
    env['pause']=False;run(4,z);assert read(z+0x190)==2
    fl(clock+0x1c,21);run(4,z);assert run(6,z,1)==0
    before=len(env['draws']);run(5,z,123);assert len(env['draws'])==before
    # Original Aster footprint: lamp reveals the hidden actor at half opacity.
    env['lamps']=True;fl(z+0x10,500);run(4,z);assert read(z+0x198)==1 and run(6,z,1)==1
    before=read(z+0xa8);run(5,z,123);assert env['draws'][-1][1]==[255,255,255,127] and read(z+0xa8)==before
    # Outside the footprint it becomes untargetable again; a direct hit flashes.
    fl(z+0x10,900);run(4,z);assert read(z+0x198)==0
    run(7,z,456);assert env['damage']==1;run(5,z,123);assert env['draws'][-1][1][3]==178
    # Plant food illuminates the whole board for its saved 30-second timer.
    fl(framework+0x10,40);run(4,z);assert read(z+0x198)==1
    word(z+0x48,4);run(5,z,123);assert env['draws'][-1][1][3]==255
    print('PASS: Rogue native constructor/vtable/schema, cloak hold/pause, untargetable invisibility, original lamp footprint/PF, half-alpha reveal, injury flash and death draw')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('library',type=Path);check(p.parse_args().library)
