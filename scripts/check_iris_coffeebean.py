"""Execute Coffee Bean's compiled ARM lifecycle and temporary attack effect."""
import argparse
import math
from pathlib import Path
import struct
from native_payload import registration_payload
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *


def check(path):
    raw=path.read_bytes();u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x1000000)
    u.reg_write(UC_ARM_REG_C1_C0_2,15<<20);u.reg_write(UC_ARM_REG_FPEXC,1<<30)
    ph=struct.unpack_from('<I',raw,28)[0];stride,count=struct.unpack_from('<HH',raw,42)
    for h in range(ph,ph+stride*count,stride):
        kind,off,va,_,size,mem,flags,_=struct.unpack_from('<8I',raw,h)
        if kind==1:
            assert flags!=7;u.mem_write(va,raw[off:off+size])
    entry=registration_payload(raw,0x3b9478,'PlantIrisCoffee');tramp=entry+18*40
    def word(p,v):u.mem_write(p,struct.pack('<I',v&0xffffffff))
    def read(p):return struct.unpack('<I',u.mem_read(p,4))[0]
    def fl(p,v):u.mem_write(p,struct.pack('<f',v))
    def num(p):return struct.unpack('<f',u.mem_read(p,4))[0]
    def txt(p):return bytes(u.mem_read(p,128)).split(b'\0')[0].decode()
    parent,registry,reflect,ptype,desc,strings,stop=[0xf00000+i*0x1000 for i in range(7)]
    app,board,clock,plant,coffee,vec,plant_type=[0xf10000+i*0x1000 for i in range(7)]
    functions=0xf30000;word(registry,functions);word(functions+12,functions+0x100)
    word(reflect,functions+0x200);word(ptype,functions+0x300)
    for off,fn in ((0x24,0x400),(0x28,0x410),(0x14,0x420),(0x2c,0x430),(0x20,0x440)):
        word(functions+0x200+off,functions+fn)
    word(functions+0x334,functions+0x450)
    word(0xd00838,app+0x800);word(app+0x800,app);word(app+0x6c0,board);word(board+0xa8,5);word(0xd4ed90,clock)
    word(plant,functions+0x500);word(functions+0x500,functions+0x550);word(functions+0x570,functions+0x560)
    word(coffee,functions+0x500);word(plant+8,101);word(plant+12,1);word(plant+0x48,4);fl(plant+0x4c,300)
    word(plant+0xb8,102);word(plant+0xbc,1);word(plant_type+4,strings+0x100);u.mem_write(strings+0x100,b'peashooter\0')
    word(coffee+0x48,4);word(coffee+0x5c,3);word(coffee+0x58,2)
    word(parent+4,strings+0x200);u.mem_write(strings+0x200,b'Plant\0')
    env={'heap':0xf40000,'objects':{101:plant,102:plant_type},'grids':[], 'fields':{},'registered':[],
         'paused':False,'removed':[],'damages':[],'queried':[],'sounds':[]}
    def alloc(n):
        p=env['heap'];env['heap']+=(n+31)&~31;assert env['heap']<0xf7f000;u.mem_write(p,bytes(n));return p
    def ret(v=0):u.reg_write(UC_ARM_REG_R0,v);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    def hook(cpu,pc,size,_):
        r0,r1,r2,r3=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
        if pc in (tramp,tramp+12):ret()
        elif pc==tramp+24:env['damages'].append(num(r1+4));ret(77)
        elif pc==0xb363dc:ret(alloc(r0))
        elif pc in (0x894ca0,0x895608,0xb76c4c,0xb36928,0xe8c10,0x282ae4,0x282b78):ret()
        elif pc in (0x13b5a0,0x283394,0x851728):ret(parent)
        elif pc==0x851920:ret(registry)
        elif pc==0xb75560:
            u.mem_write(strings,txt(r1).encode()+b'\0');word(strings-4,100);word(r0,strings);ret()
        elif pc==functions+0x100:env['registered'].append((txt(read(r1)),r3));ret()
        elif pc==functions+0x400:ret(ptype)
        elif pc==functions+0x410:assert r2==123;ret()
        elif pc==functions+0x420:assert r1 in (6,8);ret(r1)
        elif pc==functions+0x430:env['fields'][txt(read(r2))]=r3;ret()
        elif pc==functions+0x440:ret(456)
        elif pc==functions+0x450:ret(123)
        elif pc==functions+0x550:ret(parent)
        elif pc==functions+0x560:ret(0)
        elif pc==0x13dea0:word(r0,r2);word(r0+4,r3);ret()
        elif pc==0x8821a8:ret(parent)
        elif pc==0x8890c4:word(r0,read(r2));word(r0+4,read(r2+4));ret()
        elif pc==0x888b8c:ret(parent)
        elif pc==0x884378:ret(env['objects'].get(read(r1),0))
        elif pc==0x1872a8:ret(env['paused'])
        elif pc==0x248120:
            entries=[plant,coffee] if r1==1 else env['grids']
            if r1==1:env['queried'].append(tuple(read(r2+4*i) for i in range(4)))
            storage=alloc(4*len(entries)+4);word(r0,storage);word(r0+4,storage+4*len(entries))
            for i,p in enumerate(entries):word(storage+4*i,p)
            ret()
        elif pc==0x17a8c4:
            assert txt(read(r1))=='iris_coffee_buff';p=alloc(0x68);word(p,read(0xf81c0c));word(p+8,200+len(env['grids']));word(p+12,1)
            env['grids'].append(p);ret(p)
        elif pc in (0x2708b4,0x39ece8):env['removed'].append(r0);ret()
        elif pc==0x1a4280:env['sounds'].append(txt(read(r1)));ret()
        elif pc==stop:u.emu_stop()
    u.hook_add(UC_HOOK_CODE,hook)
    def run(mode,*args):
        for reg,v in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),list(args)+[0]*4):u.reg_write(reg,v)
        u.reg_write(UC_ARM_REG_SP,0xfff000);u.reg_write(UC_ARM_REG_LR,stop);u.emu_start(entry+mode*40,stop,count=1000000)
        assert u.reg_read(UC_ARM_REG_PC)==stop;return u.reg_read(UC_ARM_REG_R0)
    run(0);run(5);assert env['registered']==[('PlantIrisCoffee',0x14),('IrisCoffeeBuff',0x68)]
    f=run(1);buff=run(6);run(3,reflect,desc);run(8,reflect,desc)
    assert env['fields']['iris_coffee_expiry']==0x60 and env['fields']['iris_coffee_emitted']==16
    word(f+4,coffee);fl(clock+0x1c,10);run(4,f);assert not env['grids']
    env['paused']=True;fl(clock+0x1c,13);run(4,f);assert not env['grids'];env['paused']=False
    run(4,f);assert len(env['grids'])==1 and env['queried'][0]==(2,1,3,3)
    s=env['grids'][0];assert read(s+0x50)==101 and num(s+0x60)==19
    run(4,f);assert len(env['grids'])==1 and env['sounds']==['Play_Plant_DarkAges_CoffeeBean']
    hit=alloc(24);word(hit,plant);fl(hit+4,20);assert run(13,coffee,hit)==77
    assert math.isclose(env['damages'][-1],22) and num(hit+4)==20
    word(hit,0);run(13,coffee,hit);assert env['damages'][-1]==20
    word(hit,plant);fl(clock+0x1c,19);run(13,coffee,hit);assert env['damages'][-1]==20
    run(9,s);assert s in env['removed'] and not read(s+0x64)
    run(4,f);assert coffee in env['removed']
    # Reload reconstructs ownership entirely from the serialized weak/deadline.
    word(s+0x64,1);fl(s+0x60,25);fl(clock+0x1c,20);run(13,coffee,hit);assert math.isclose(env['damages'][-1],22)
    env['objects'].pop(101);run(9,s);assert not read(s+0x64)
    run(10,s);assert not read(s+0x50)
    print('PASS: Coffee ARM registration/saved schema, 3x3 selection, authored emission, pause, once-only buff, 10% damage with restored input, six-second expiry, reload and expired weak cleanup')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('native',type=Path);check(p.parse_args().native)
