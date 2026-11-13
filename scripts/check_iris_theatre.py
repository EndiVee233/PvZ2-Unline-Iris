"""Run the compiled theatre path, protection and reward code at ARM boundaries."""
import argparse
import math
from pathlib import Path
import struct
from native_payload import registration_payload
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *


def check(path):
    raw=Path(path).read_bytes();u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x1000000)
    u.reg_write(UC_ARM_REG_C1_C0_2,15<<20);u.reg_write(UC_ARM_REG_FPEXC,1<<30)
    ph=struct.unpack_from('<I',raw,28)[0];stride,count=struct.unpack_from('<HH',raw,42)
    for h in range(ph,ph+stride*count,stride):
        kind,off,va,_,size,mem,flags,_=struct.unpack_from('<8I',raw,h)
        if kind==1:
            assert flags!=7;u.mem_write(va,raw[off:off+size])
    entry=registration_payload(raw,0x619fc0,'IrisTheatreProperties');tramp=entry+32*40
    def word(p,v):u.mem_write(p,struct.pack('<I',v&0xffffffff))
    def read(p):return struct.unpack('<I',u.mem_read(p,4))[0]
    def fl(p,v):u.mem_write(p,struct.pack('<f',v))
    def num(p):return struct.unpack('<f',u.mem_read(p,4))[0]
    def txt(p):return bytes(u.mem_read(p,128)).split(b'\0')[0].decode()
    parent,registry,reflect,ptype,desc,strings,stop=[0xf00000+i*0x1000 for i in range(7)]
    app,board,clock,house,vector,ztype,zprops=[0xf10000+i*0x1000 for i in range(7)]
    functions=0xf30000
    word(registry,functions);word(functions+12,functions+0x100)
    word(reflect,functions+0x200);word(ptype,functions+0x300)
    for slot,fn in ((0x24,0x400),(0x28,0x410),(0x14,0x420),(0x2c,0x430),(0x20,0x440)):
        word(functions+0x200+slot,functions+fn)
    word(functions+0x334,functions+0x450)
    word(0xd00838,app+0x800);word(app+0x800,app);word(app+0x6c0,board);word(board+0xa8,5)
    manager=board+0x800;handles=manager+0x100;word(board+0x62c,manager)
    word(manager+4,handles);word(manager+8,handles+16)
    word(handles,999);word(handles+4,1);word(handles+8,100);word(handles+12,1)
    word(0xd4ed90,clock);word(house,functions+0x500);word(functions+0x534,functions+0x550)
    word(house+0xb8,102);word(house+0xbc,1);word(house+8,101);word(house+12,1)
    u.mem_write(strings+0x100,b'POPANIM_TOWERDEFEND_HOUSE_PIG_1\0');word(ztype+0x10,strings+0x100)
    env={'heap':0xf40000,'objects':{101:house,102:ztype},'module':0,'registered':[],
         'fields':{},'paused':False,'steps':0,'house_hits':[],'suns':[],
         'removed':[],'parent_planting':0,'parent_updates':0,'carpet':0,
         'plants':[house],'spent':[],'mutations':[],'force_image':False,'labels':[],'drawn':0,'rects':[],
         'zombies':[],'animations':[],'plant_deaths':[],'sounds':[]}
    def alloc(n):
        p=env['heap'];env['heap']+=(n+31)&~31;assert env['heap']<0xf7f000;u.mem_write(p,bytes(n));return p
    def ret(v=0):u.reg_write(UC_ARM_REG_R0,v);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    def hook(cpu,pc,size,_):
        r0,r1,r2,r3=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
        if pc in (tramp,tramp+36):ret()
        elif pc==tramp+12:env['parent_updates']+=1;ret(99)
        elif pc==tramp+24:env['parent_planting']+=1;ret(77)
        elif pc==tramp+48:ret(98)
        elif pc==0xb363dc:ret(alloc(r0))
        elif pc in (0x894ca0,0x895608,0xb76c4c,0xb36928,0xe8c10,0x5deafc,0x44d220):ret()
        elif pc in (0x134100,0x1341d8,0x12c65c,0x5e8c4c,0x851728):ret(parent)
        elif pc==0x851920:ret(registry)
        elif pc==0x12c770:
            p=alloc(0xd8);word(p,functions+0x800);word(functions+0x80c,functions+0x850)
            fl(p+0x10,123.0);ret(p)
        elif pc==functions+0x850:ret()
        elif pc==0xb75560:
            u.mem_write(strings,txt(r1).encode()+b'\0');word(strings-4,100);word(r0,strings);ret()
        elif pc==functions+0x100:env['registered'].append((txt(read(r1)),r3));ret()
        elif pc==functions+0x400:ret(ptype)
        elif pc==functions+0x410:assert r2==123;ret()
        elif pc==functions+0x420:assert r1 in (6,8);ret(r1)
        elif pc==functions+0x430:env['fields'][txt(read(r2))]=r3;ret()
        elif pc==functions+0x440:ret(456)
        elif pc==functions+0x450:ret(123)
        elif pc==functions+0x470:ret(r0==env['module'])
        elif pc==0x2d8f48:raise AssertionError('unsafe native lookup')
        elif pc==0x13dea0:word(r0,r2);word(r0+4,r3);ret()
        elif pc==0x8821a8:ret(parent)
        elif pc==0x8890c4:word(r0,read(r2));word(r0+4,read(r2+4));ret()
        elif pc==0x888b8c:ret(parent)
        elif pc==0x884378:ret(env['objects'].get(read(r1),0))
        elif pc==0x1872a8:ret(env['paused'])
        elif pc==0x248120:
            entries=env['zombies'] if r1==2 else env['plants']
            storage=alloc(4*len(entries)+4);word(r0,storage);word(r0+4,storage+4*len(entries))
            for i,p in enumerate(entries):word(storage+4*i,p)
            ret()
        elif pc==0x185658:
            env['spent'].append(r1)
            if r1>read(board+0xe0):ret(0)
            else:word(board+0xe0,read(board+0xe0)-r1);ret(1)
        elif pc==0x39df1c:
            env['mutations'].append(read(r3));word(r0+0xb8,read(r3));word(r0+0xbc,read(r3+4));word(r0+0x61,0)
            for off,v in ((0x34,2),(0x38,3),(0x3c,4),(0x40,5),(0x70,10)):fl(r0+off,v)
            ret()
        elif pc==0x17d518:ret(232+64*r1)
        elif pc==0x1814a4:ret(222+76*r1)
        elif pc==0x5de8b8:ret(r0)
        elif pc==0x7a3ee0:ret(0x3f000000)
        elif pc==0x7a3e90:ret(0)
        elif pc==0x62c1e8:ret(0x3f800000)
        elif pc==0x5ee918:ret()
        elif pc in (0x44d0b0,0x44d220):env['animations'].append(txt(read(r1)));ret(1)
        elif pc==0x1a4280:env['sounds'].append(txt(read(r1)));ret()
        elif pc==0x39ece8:env['plant_deaths'].append(r0);word(r0+0x48,3);ret()
        elif pc==0x2708b4:env['removed'].append(r0);ret()
        elif pc==0x6826ec:ret(zprops)
        elif pc==0x5dfc80:
            env['steps']+=1
            if not read(r0+0x150)&6:fl(r0+0x10,num(r0+0x10)-16)
            ret()
        elif pc==functions+0x580:
            for off in (0x10,0x14,0x18):fl(r0+off,num(r1+off-0x10))
            ret()
        elif pc==functions+0x550:
            amount=num(r1+4);env['house_hits'].append(amount);fl(r0+0x4c,num(r0+0x4c)-amount);ret()
        elif pc==0x5e147c:word(r0+0x48,4);fl(r0+0xb0,0);env['removed'].append(r0);ret()
        elif pc==0x5e0b74:fl(r0+0xb0,num(r0+0xb0)-num(r1+4));ret(19)
        elif pc==0x17b6e4:
            env['suns'].append(txt(read(r1)));p=alloc(0xb0);word(p,functions+0x500);word(functions+0x558,functions+0x580);ret(p)
        elif pc in (0x1d2fe0,0x1d2cc4,0x7d2810,0x7d2940):ret()
        elif pc==0x1524d8:assert txt(read(r0+12)).startswith(('IMAGE_BACKGROUNDS_THEATRE_','IMAGE_UI_HUD_INGAME_PLANT_LEVEL_UP'));env['carpet']+=1;ret(int(env['force_image']))
        elif pc==0x7d53cc:
            sp=u.reg_read(UC_ARM_REG_SP);env['rects'].append((r2,r3,read(sp),read(sp+4)));ret()
        elif pc==0xa321fc:
            sp=u.reg_read(UC_ARM_REG_SP);p=alloc(0x44);wide=read(read(sp+4));word(p+8,wide);word(wide-4,100);ret(p)
        elif pc==0x846e0c:
            word(r0,functions+0x900);word(functions+0x98c,functions+0x950);word(functions+0x90c,functions+0x960);word(r0+0x9c,r1);env['labels'].append(r0);ret(r0)
        elif pc==0x847294:word(read(r0+0x9c)+8,read(r1));ret()
        elif pc==functions+0x950:env['drawn']+=1;ret()
        elif pc==functions+0x960:env['removed'].append(r0);ret()
        elif pc==functions+0x970:ret(1)
        elif pc==stop:u.emu_stop()
    u.hook_add(UC_HOOK_CODE,hook)
    def run(mode,*args):
        for reg,value in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),list(args)+[0]*4):u.reg_write(reg,value)
        u.reg_write(UC_ARM_REG_SP,0xfff000);u.reg_write(UC_ARM_REG_LR,stop)
        u.emu_start(entry+40*mode,stop,count=1000000)
        assert u.reg_read(UC_ARM_REG_PC)==stop
        return u.reg_read(UC_ARM_REG_R0)
    run(0);assert len(env['registered'])==4
    props=run(1);module=run(2);private_props=run(3);actor=run(4)
    assert num(private_props+0x10)==123
    env['module']=module;env['objects'][100]=module;env['objects'][103]=props
    word(read(module)+0x10,functions+0x470);word(module+0x10,103);word(module+0x14,1)
    for mode in range(9,13):run(mode,reflect,desc)
    assert env['fields']['IrisTheatreSunDrop']==0xdc
    assert env['fields']['iris_tower44Step']==0x30c
    for i in range(45):word(props+0x60+i*8,-1)
    # A bend from the upper-right entrance to the lower-left house.
    cells=[x*5 for x in range(8,-1,-1)]+[1,2,3,4]
    for i,cell in enumerate(cells):word(props+0x60+cell*8,len(cells)-i-1)
    word(props+0x24,3);fl(props+0x28,.1)
    assert run(17,board)==99 and num(house+0x4c)==3
    word(actor+0x38,104);word(actor+0x3c,1);env['objects'][104]=ztype
    word(read(actor)+0x58,functions+0x580)
    fl(actor+0x10,744);fl(actor+0x14,222);fl(actor+0xb0,1000);fl(actor+0x34,200);fl(actor+0xbc,1000);word(actor+0xc0,2)
    fl(zprops+0xe0,1);word(zprops+0xdc,30)
    run(13,actor);assert math.isclose(num(actor+0xb0),1200) and read(actor+0x194)==35
    env['paused']=True;steps=env['steps'];run(13,actor);assert env['steps']==steps;env['paused']=False
    word(actor+0x150,2);x=num(actor+0x10);run(13,actor);assert num(actor+0x10)==x;word(actor+0x150,0)
    # Road traversal must turn down the left edge, never cut diagonally.
    saw_turn=False
    for _ in range(150):
        run(13,actor)
        if num(actor+0x14)>222:
            saw_turn=True;assert num(actor+0x10)==232,(num(actor+0x10),num(actor+0x14),read(actor+0x194),env['removed'])
        if actor in env['removed']:break
    assert saw_turn and env['house_hits']==[1] and num(house+0x4c)==2
    assert not env['suns']  # Reaching the house does not award kill drops.
    other=run(4);word(other+0x38,104);word(other+0x3c,1);fl(other+0xb0,20)
    hit=alloc(24);fl(hit+4,50);assert run(14,other,hit)==19
    assert env['suns']==['iris_dark_sun','sun_small'];run(14,other,hit);assert len(env['suns'])==2
    cell=alloc(8);word(cell,8);word(cell+4,0);handle=alloc(8)
    assert run(18,board,cell,handle)==10
    word(cell,7);word(cell+4,3);assert run(18,board,cell,handle)==77
    # Two plants share the stock property sheet; only the theatre tower's own
    # launch intervals change. Upgrade debits the real bank before mutation.
    dictionary=alloc(24);word(0xd4ec98,dictionary);previous=0
    for i,name in enumerate(('peashooter','repeater','threepeater')):
        node=alloc(32);label=alloc(32);u.mem_write(label,name.encode()+b'\0');word(node+0x10,label)
        word(node+0x18,200+i);word(node+0x1c,1)
        t=alloc(32);pop=alloc(64);u.mem_write(pop,('POPANIM_PLANT_'+name.upper()).encode()+b'\0');word(t+0x10,pop);env['objects'][200+i]=t
        if previous:word(previous+12,node)
        else:word(dictionary+8,node)
        previous=node
    tower=alloc(0xd8);word(tower+8,105);word(tower+12,1);env['objects'][105]=tower
    word(tower+0xb8,200);word(tower+0xbc,1);word(tower+0x5c,2);word(tower+0x58,2);word(tower+0x48,4)
    fl(tower+0x10,360);fl(tower+0x14,374);word(tower+0x61,1)
    for off,v in ((0x34,2),(0x38,3),(0x3c,4),(0x40,5),(0x70,10)):fl(tower+off,v)
    env['plants'].append(tower);word(props+0x2c,1);word(props+0x1d0,3)
    for i,kind in enumerate((9,11,16)):
        word(props+0x1d4+12*i,kind);word(props+0x1d8+12*i,100+50*i);fl(props+0x1dc+12*i,.5-.1*i)
    run(17,board);assert num(tower+0x3c)==2 and num(tower+0x70)==5
    run(17,board);assert num(tower+0x3c)==2  # Saved tracking prevents double application.
    cursor=alloc(0x20);word(cursor,functions+0xa00);word(functions+0xa2c,functions+0x970);word(board+0x640,cursor)
    assert run(26,board,360,350,0)==0  # Active planting/tool cursor wins.
    word(cursor+0x14,1)
    assert run(26,board,360,350,0)==1  # A completed cursor cannot block selection.
    env['force_image']=True;g=board+0x400;fl(g+0x10,1.25);fl(g+0x14,1.25)
    font=alloc(4);word(0xd00b20,font);word(font,42)
    run(27,board,g);run(27,board,g);assert len(env['labels'])==1 and env['drawn']==2
    wide=read(read(env['labels'][0]+0x9c)+8);assert [read(wide+i*4) for i in range(3)]==list(map(ord,'100'))
    # Carpets must be after the native background and before lawn objects.
    # Test the actual delegate ABI and non-unit app scale plus board zoom.
    items=alloc(72);count=alloc(4);word(items+8,0x12345678);word(count,0)
    run(19,items,count);assert read(count)==1 and read(items+8)==0x12345678
    assert 100001<read(items+4)<300000
    fl(app+0x6a0,1.5);fl(g+0x10,1.25);fl(g+0x14,1.25);fl(g+0x18,10);fl(g+0x1c,20)
    before=len(env['rects']);run(20,items+8,g);rects=env['rects'][before:]
    assert len(rects)==len(cells) and rects[0]==(372,295,120,142),rects[:1]
    assert run(26,board,540,525,0)==1 and read(module+0x28)==105
    word(board+0xe0,30);assert run(26,board,49,0,6)==0 and not env['mutations']
    word(board+0xe0,1000);assert run(26,board,49,0,6)==1
    assert read(board+0xe0)==900 and read(tower+0xb8)==201 and read(tower+0x61)&255==1
    assert math.isclose(num(tower+0x3c),1.6,abs_tol=1e-6)
    run(17,board);assert math.isclose(num(tower+0x3c),1.6,abs_tol=1e-6)
    env['paused']=True;assert run(26,board,49,0,6)==0 and read(board+0xe0)==900;env['paused']=False
    assert run(26,board,49,0,6)==1 and read(board+0xe0)==750 and read(tower+0xb8)==202
    assert run(26,board,49,0,6)==0 and env['mutations']==[201,202]
    assert run(26,board,0,0,4)==1 and read(module+0x28)==0
    # The wolf king stops for authored intro/chui animation markers. Its
    # command grants the whole theatre group a temporary movement boost.
    boss=run(4);follower=run(4);rig=alloc(64);env['objects'][108]=rig
    for z in (boss,follower):
        word(z+0x38,104);word(z+0x3c,1);fl(z+0xb0,16000);word(read(z)+0x58,functions+0x580)
        fl(z+0x10,360);fl(z+0x14,374)
    word(boss+0x40,108);word(boss+0x44,1);env['zombies']=[boss,follower]
    word(zprops+0xd8,9);word(props+0x30,1);word(props+0x34,0);fl(clock+0x1c,0);run(13,boss)
    fl(clock+0x1c,8);x=num(boss+0x10);run(13,boss)
    assert num(boss+0x10)==x and read(boss+0x19c)==1 and env['animations'][-1]=='intro'
    fl(clock+0x1c,10.5);run(13,boss);assert num(follower+0x1b0)==20.5
    word(zprops+0xd8,0);fl(follower+0x10,600);fl(follower+0x14,222);word(follower+0x190,1);word(follower+0x194,25)
    run(13,follower);assert num(follower+0x10)==568
    word(zprops+0xd8,9);fl(clock+0x1c,13.4);run(13,boss);assert read(boss+0x19c)==0
    # Blow retains the real plant for a saved one-second flight. Its ordinary
    # attack update is suppressed during flight and resumes on other plants.
    word(props+0x34,2);fl(boss+0x1a8,13);fl(boss+0x10,360);fl(boss+0x14,374)
    word(tower,functions+0xb00);word(functions+0xb58,functions+0x580)
    fl(tower+0x10,360);fl(tower+0x14,374);fl(tower+0x4c,300);word(tower+0x48,4);u.mem_write(tower+0x61,b'\1')
    run(13,boss);assert env['animations'][-1]=='chui'
    fl(clock+0x1c,16.1);run(13,boss);assert read(module+0x320)==105 and not bytes(u.mem_read(tower+0x61,1))[0],(read(boss+0x19c),num(boss+0x1a0),read(boss+0x1b4),num(boss+0x10),num(boss+0x14),num(tower+0x10),num(tower+0x14),num(tower+0x4c),read(tower+0x48),read(module+0x320),env['animations'])
    assert run(28,tower)==0 and run(28,house)==98
    fl(clock+0x1c,16.6);run(17,board);assert num(tower+0x10)==310 and math.isclose(num(tower+0x18),200,abs_tol=.01)
    fl(clock+0x1c,17.2);run(17,board);assert tower in env['plant_deaths'] and not read(module+0x320)
    # Fire wolves consume a nearby tower through Plant's actual death path.
    word(tower+0x48,4);fl(tower+0x4c,300);fl(tower+0x10,360);fl(tower+0x14,374)
    fire=run(4);word(fire+0x38,104);word(fire+0x3c,1);fl(fire+0xb0,1000);fl(fire+0x10,440);fl(fire+0x14,374)
    word(read(fire)+0x58,functions+0x580);word(zprops+0xd8,7);run(13,fire)
    assert env['plant_deaths'].count(tower)==2 and env['sounds'][-1]=='Play_Zomb_Egypt_Explorer_Mvmt_Burn'
    word(zprops+0xd8,0)
    env['objects'].pop(100);assert run(18,board,cell,handle)==77
    run(22,module)
    assert env['labels'][0] in env['removed']
    print('PASS: theatre ARM registry/schema, ownership, expired weak lookup, paused/frozen adjacent path, wave HP/house damage/sun reward, planting restriction, local intervals, native upgrade cost/mutation, scaled rendering/input, wolf skill markers/group boost, real saved plant flight with attack suppression and fire removal')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('native');check(p.parse_args().native)
