"""Execute the compiled ARM aiming module against mocked engine boundaries."""
import argparse
import json
import math
from pathlib import Path
import struct
from native_payload import registration_payload
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *


def check(path):
    raw=Path(path).read_bytes();u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x1000000)
    u.reg_write(UC_ARM_REG_C1_C0_2,0xf<<20);u.reg_write(UC_ARM_REG_FPEXC,1<<30)
    ph=struct.unpack_from('<I',raw,28)[0];stride,count=struct.unpack_from('<HH',raw,42)
    for h in range(ph,ph+stride*count,stride):
        kind,off,va,_,size,mem,flags,_=struct.unpack_from('<8I',raw,h)
        if kind==1:
            assert flags!=7;u.mem_write(va,raw[off:off+size])
            if va==0xf80000:assert mem==8192
    def read(p):return struct.unpack('<I',u.mem_read(p,4))[0]
    def word(p,v):u.mem_write(p,struct.pack('<I',v&0xffffffff))
    def fl(p,v):u.mem_write(p,struct.pack('<f',v))
    def num(p):return struct.unpack('<f',u.mem_read(p,4))[0]
    def txt(p):return bytes(u.mem_read(p,128)).split(b'\0')[0].decode()
    def branch(pc):
        op=read(pc);assert op&0xff000000==0xea000000;d=(op&0xffffff)<<2
        return pc+8+(d-0x4000000 if d&0x2000000 else d)
    entry=registration_payload(raw,0x619fc0,'IrisOakTrainProperties');tramp=entry+45*40
    reflect,ptype,registry,parent,desc,strings,stop=[0xf00000+i*0x1000 for i in range(7)]
    app,board,clock,plant,vector,pool,types=[0xf10000+i*0x1000 for i in range(7)]
    functions=0xf30000
    word(registry,functions);word(functions+0xc,functions+0x100)
    word(reflect,functions+0x200);word(ptype,functions+0x300)
    for slot,fn in ((0x24,0x400),(0x28,0x410),(0x14,0x420),(0x2c,0x430),(0x20,0x440)):
        word(functions+0x200+slot,functions+fn)
    word(functions+0x334,functions+0x450)
    word(0xd00838,app+0x800);word(app+0x800,app);word(app+0x6c0,board);word(board+0xa8,5)
    word(board+0x62c,board+0x800);word(0xd4ed90,clock)
    word(plant,functions+0x500);word(functions+0x534,functions+0x550);word(functions+0x570,functions+0x560)
    word(plant+8,111);word(plant+12,1);fl(plant+0x4c,1000);fl(plant+0x10,180);fl(plant+0x14,400)
    env={'heap':0xf40000,'objects':{111:plant},'registered':[],'fields':{},'module':0,'props':0,
         'updates':0,'shots':[],'zombies':[],'removed':[],'paused':False,'parent_wins':0,'hp_hits':[],
         'hud_draws':0,'push':0,'widgets':[],'module_destroyed':0}
    def alloc(n):
        p=env['heap'];env['heap']+=(n+31)&~31;assert env['heap']<0xf7f000;u.mem_write(p,bytes(n));return p
    def ret(v=0):u.reg_write(UC_ARM_REG_R0,v);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    def ret_float(v):ret(struct.unpack('<I',struct.pack('<f',v))[0])
    def hook(cpu,pc,size,_):
        r0,r1,r2,r3=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
        if pc==tramp:ret()
        elif pc==tramp+12:env['parent_wins']+=1;ret(77)
        elif pc==tramp+24:env['updates']+=1;ret(99)
        elif pc==0xb363dc:ret(alloc(r0))
        elif pc in (0x894ca0,0x895608,0xb76c4c,0xb36928,0xe8c10,0x5deafc,0x881b84):ret()
        elif pc in (0x134100,0x1341d8,0x5e8c4c):ret(parent)
        elif pc==0x851728:ret(parent)
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
        elif pc==0x2d8f48:raise AssertionError('unsafe native module lookup')
        elif pc==functions+0x470:ret(r0==env['module'])
        elif pc==0x13dea0:word(r0,r2);word(r0+4,r3);ret()
        elif pc==0x8821a8:ret(parent)
        elif pc==0x8890c4:word(r0,read(r2));word(r0+4,read(r2+4));ret()
        elif pc==0x888b8c:ret(pool)
        elif pc==0x884378:ret(env['objects'].get(read(r1),0))
        elif pc==0x1872a8:ret(env['paused'])
        elif pc==0x536398:ret(0)
        elif pc==0x248120:
            items=([plant] if r1==1 else env['zombies']);word(r0,vector);word(r0+4,vector+4*len(items))
            for i,z in enumerate(items):word(vector+4*i,z)
            ret()
        elif pc==0x365ec4:word(r0+8,types);word(r0+12,types+56);ret()
        elif pc==0x181a30:
            z=alloc(0x1c0);word(z,read(0xf81048));word(z+8,z);word(z+12,1);fl(z+0xb0,390)
            env['objects'][z]=z;env['zombies'].append(z);ret(z)
        elif pc==0x5de8b8:ret(r0)
        elif pc==0x1524d8:
            assert txt(read(r0+0xc)).startswith('IMAGE_UI_HUD_INGAME_OAK_')
            assert read(r0)==read(r0+4)==read(r0+8)==0
            ret(0)
        elif pc==0x7d2810:env['push']+=1;ret()
        elif pc==0x7d2940:env['push']-=1;ret()
        elif pc==0xa321fc:
            sp=u.reg_read(UC_ARM_REG_SP);p=alloc(0x44);wide=read(read(sp+4));word(p+8,wide);word(wide-4,read(wide-4)+1);ret(p)
        elif pc==0x846e0c:
            word(r0,functions+0x600);word(functions+0x68c,functions+0x650);word(functions+0x60c,functions+0x660)
            word(r0+0x9c,r1);env['widgets'].append(r0);ret(r0)
        elif pc==0x847294:
            config=read(r0+0x9c);wide=read(r1);word(config+8,wide);word(wide-4,read(wide-4)+1);ret()
        elif pc==functions+0x650:env['hud_draws']+=1;ret()
        elif pc==functions+0x660:env['removed'].append(r0);ret()
        elif pc==read(0xcd37c0):env['module_destroyed']+=1;ret()
        elif pc==0x17d518:ret(180+64*r1)
        elif pc==0x1814a4:ret(200+100*r1)
        elif pc==0x7a3e90:assert r0>0;ret(0)
        elif pc==0x2708b4:env['removed'].append(r0);fl(r0+0xb0,0);ret()
        elif pc==0x5e0b74:
            fl(r0+0xb0,num(r0+0xb0)-num(r1+4))
            if num(r0+0xb0)<=0:word(r0+0x48,4)
            ret(19)
        elif pc==0x5dfc80:ret()
        elif pc==functions+0x550:
            amount=num(r1+4);env['hp_hits'].append(amount);fl(r0+0x4c,num(r0+0x4c)-amount);ret()
        elif pc==functions+0x560:ret(0)
        elif pc==0x3a1b88:
            p=alloc(0xb0);fl(p+0x2c,200);fl(p+0x30,400);fl(p+0x34,32);env['shots'].append((p,read(r0+0xb4)));ret(p)
        elif pc in (0xe88a4,0xe87cc,0xe87d8):
            a=struct.unpack('<f',struct.pack('<I',r0))[0];c=struct.unpack('<f',struct.pack('<I',r1))[0]
            ret_float(math.atan2(a,c) if pc==0xe88a4 else math.sin(a) if pc==0xe87cc else math.cos(a))
        elif pc==stop:u.emu_stop()
    u.hook_add(UC_HOOK_CODE,hook)
    def run(mode,*args):
        for reg,value in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),list(args)+[0]*4):u.reg_write(reg,value)
        u.reg_write(UC_ARM_REG_SP,0xfff000);u.reg_write(UC_ARM_REG_LR,stop);u.emu_start(entry+40*mode,stop,count=2000000);return u.reg_read(UC_ARM_REG_R0)
    run(0);assert len(env['registered'])==9
    props=run(1);module=run(2);env['props']=props;env['module']=module
    # Expired entry before a live module is expected during restart cleanup.
    manager=board+0x800;entries=manager+0x100
    word(manager+4,entries);word(manager+8,entries+16)
    word(entries,999);word(entries+4,1);word(entries+8,112);word(entries+12,1)
    env['objects'][112]=module;word(read(module)+0x10,functions+0x470)
    word(module+0x10,100);word(module+0x14,1);env['objects'][100]=props
    word(module+0x30,111);word(module+0x34,1)
    run(21,reflect,desc);fields=env['fields'];assert fields['Target255Wave']==0x185c and fields['Target000Time']==0x60
    assert len(fields)==15+256*6
    run(22,reflect,desc);assert fields['iris_oak_plant']==0x30 and fields['iris_oak_ammo3']==0x5c
    for i,v in enumerate((1000,100,300,500,2000,300,6,4,3,12,10,5,0,40,2)):word(props+0x20+i*4,v)
    # Both scheduled events have explicit coords; second expires after 10s.
    for i,(time,kind,x,y,life,wave) in enumerate(((3,0,5,1,0,1),(6,5,7,4,10,2))):
        p=props+0x60+24*i;fl(p,time);word(p+4,kind);word(p+8,x);word(p+12,y);fl(p+16,life);word(p+20,wave)
    for i,kind in enumerate(('Wizard','Archmage','Gargantuar','Bottle','ArrowYellow','ArrowBlue','ArrowPurple')):
        ztype=alloc(32);name=alloc(64);u.mem_write(name,('ZombieIrisTarget'+kind).encode()+b'\0');word(ztype+8,name);word(types+8*i,200+i);word(types+8*i+4,1);env['objects'][200+i]=ztype
    fl(clock+0x1c,20);assert run(37,board)==99;assert read(module+0x18)==1 and read(module+0x50)==12 and num(module+0x1c)==20
    font=alloc(4);word(0xd00b20,font);word(font,42)
    run(40,board,board+0x400);assert env['hud_draws']==6 and len(env['widgets'])==6 and env['push']==0
    run(40,board,board+0x400);assert env['hud_draws']==12 and len(env['widgets'])==6 and env['push']==0
    assert run(36)==0;assert not env['zombies']
    fl(clock+0x1c,23);run(37,board);assert len(env['zombies'])==1 and read(module+0x20)==1
    z=env['zombies'][0];assert num(z+0x10)==500 and num(z+0x14)==300
    # Pausing cannot consume targets or arrows, and native updates still chain.
    env['paused']=True;fl(clock+0x1c,26);run(37,board);assert read(module+0x20)==1
    assert run(39,board,700,400,0)==0;env['paused']=False
    run(37,board);assert len(env['zombies'])==2 and read(module+0x20)==2
    assert math.isclose(num(env['zombies'][1]+0x198),36)
    # Main-keyboard 1/2/3/4 choose normal/power/multiple/tracking in this game.
    assert run(38,plant)==1;assert run(39,board,9,0,6)==1 and read(module+0x28)==1
    assert run(39,board,700,400,0)==1 and len(env['shots'])==1 and env['shots'][0][1]==5
    assert read(module+0x54)==9 and math.isclose(num(env['shots'][0][0]+0x38),664.64,abs_tol=1)
    run(39,board,700,400,0);assert len(env['shots'])==1
    fl(clock+0x1c,27);run(39,board,10,0,6);run(39,board,700,400,0);assert len(env['shots'])==6 and read(module+0x58)==4
    # Manual refill/automatic empty-magazine refill both take three game seconds.
    word(module+0x50,4);run(39,board,46,0,6);assert num(module+0x60)==30
    run(39,board,8,0,6);fl(clock+0x1c,29);run(39,board,700,400,0);assert len(env['shots'])==6
    run(37,board);assert read(module+0x50)==4
    fl(clock+0x1c,30);run(37,board);assert read(module+0x50)==12 and num(module+0x60)==0
    word(module+0x50,1);run(39,board,700,400,0);assert num(module+0x60)==33 and read(module+0x50)==0
    env['paused']=True;fl(clock+0x1c,33);run(37,board);assert read(module+0x50)==0;env['paused']=False
    run(37,board);assert read(module+0x50)==12
    # Fatal hit awards exactly once; the still-live bonus target gates victory.
    hit=alloc(24);fl(hit+4,400);assert run(31,z,hit)==19;assert read(module+0x24)==300
    run(31,z,hit);assert read(module+0x24)==300 and run(36)==0
    bonus=env['zombies'][1];word(bonus+0x190,5);run(31,bonus,hit);assert read(module+0x24)==400 and read(module+0x58)==8
    run(37,board);assert run(36)==1
    fl(app+0x6a0,2)
    run(39,board,1400,800,5)
    assert num(module+0x40)==700 and num(module+0x44)==400
    fl(app+0x6a0,1)
    # The adapter does not own results or input on ordinary battle boards.
    env['module']=0;assert run(36)==77 and run(38,plant)==0 and env['parent_wins']==1
    env['objects'].pop(112);assert run(38,plant)==0
    word(manager+8,entries-8);assert run(38,plant)==0
    run(43,module);assert env['module_destroyed']==1 and not read(module+0x48) and all(w in env['removed'] for w in env['widgets'])
    print('PASS: ARM registration/schema, authored timing/coords/lifetime, pause, real shot actions/inventory, five-arrow spread, single score/ammo reward, win gating and ordinary fallback')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('native');check(p.parse_args().native)
