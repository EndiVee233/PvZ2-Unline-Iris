"""Run real ARM hypno callbacks with native boundaries mocked explicitly."""
import argparse
from pathlib import Path
import struct
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *
from native_payload import registration_payload


def check(path):
    raw=path.read_bytes(); u=Uc(UC_ARCH_ARM,UC_MODE_ARM); u.mem_map(0,0x1000000)
    u.reg_write(UC_ARM_REG_C1_C0_2,0xf<<20);u.reg_write(UC_ARM_REG_FPEXC,1<<30)
    ph=struct.unpack_from('<I',raw,28)[0];stride,count=struct.unpack_from('<HH',raw,42)
    for h in range(ph,ph+stride*count,stride):
        kind,off,va,_,size,_,_,_=struct.unpack_from('<8I',raw,h)
        if kind==1:u.mem_write(va,raw[off:off+size])
    entry=registration_payload(raw,0x282388,'IrisHypnoAlly');tramp=entry+30*40
    def w(p,v):u.mem_write(p,struct.pack('<I',v))
    def read(p):return struct.unpack('<I',u.mem_read(p,4))[0]
    def fl(p,v):u.mem_write(p,struct.pack('<f',v))
    def num(p):return struct.unpack('<f',u.mem_read(p,4))[0]
    def txt(p):return bytes(u.mem_read(p,160)).split(b'\0')[0].decode()
    stop=0xff1000;registry=0xf30000;reflect=0xf31000;descriptor=0xf32000;parent=0xf33000
    appslot=0xf34000;app=0xf35000;board=0xf36000;clock=0xf37000
    zombie=0xf38000;enemy=0xf39000;plant=0xf3a000;hit=0xf3b000
    w(0xd00838,appslot);w(appslot,app);w(app+0x6c0,board);w(board+0xa8,5);w(0xd4ed90,clock)
    w(registry,0xf40000);w(0xf4000c,0xff1010);w(reflect,0xf41000)
    for o,fn in ((0x24,0xff1020),(0x28,0xff1030),(0x14,0xff1040),(0x2c,0xff1050),(0x20,0xff1060)):w(0xf41000+o,fn)
    w(parent,0xf42000);w(0xf42034,0xff1070)
    zmeta=0xf43000;w(zmeta+4,zmeta+0x100);u.mem_write(zmeta+0x100,b'Zombie\0')
    zvt=0xf44000;w(zvt,0xff1080);w(zvt+0x34,0xff1090);w(zvt+0x3c,0xff10a0);w(zvt+0x58,0xff10b0);w(zvt+0x64,0xff10c0)
    w(plant,0xf46000);w(0xf46000,0xff10d0);w(0xf46070,0xff1100);w(0xf45004,0xf45100);u.mem_write(0xf45100,b'Plant\0')
    for i,z in enumerate((zombie,enemy),1):
        w(z,zvt);w(z+8,i);w(z+12,1);fl(z+0xb0,100);fl(z+0xb4,200);fl(z+0x10,400+i*30);fl(z+0x14,222)
        fl(z+0xa0,1);w(z+0x68,123);w(z+0x70,456)
    env={'heap':0xf90000,'grids':[],'objects':{1:zombie,2:enemy},'registered':[], 'fields':[],
         'sounds':[],'root_ticks':[],'death_ticks':0,'body_hits':[],'native_count':2,'native_win':False,'original_updates':0}
    giant=0xf47000;gvt=0xf48000;gmeta=0xf49000;gtype=0xf4a000
    u.mem_write(gvt,bytes(u.mem_read(zvt,0x300)));w(gvt,0xff10e0);w(gvt+0x64,0xff10f0)
    w(gmeta+4,gmeta+0x100);u.mem_write(gmeta+0x100,b'ZombieGargantuar\0');w(gmeta+8,zmeta)
    w(gtype+8,gtype+0x100);u.mem_write(gtype+0x100,b'ZombieGargantuar\0')
    w(giant,gvt);w(giant+8,4);w(giant+12,1);w(giant+0x38,3);w(giant+0x3c,1);fl(giant+0xb0,3600);fl(giant+0xb4,3600);fl(giant+0xa0,1)
    env['objects'].update({3:gtype,4:giant});env['removed']=[];env['garg_ticks']=0;w(0xd4e964,123)
    def alloc(size):
        p=env['heap'];env['heap']+=(size+31)//32*32;u.mem_write(p,bytes(size));return p
    def ret(v=0):u.reg_write(UC_ARM_REG_R0,v);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    def hook(cpu,pc,size,data):
        r0,r1,r2,r3=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
        if pc in (tramp,tramp+12):ret()
        elif pc==tramp+24:env['body_hits'].append((r0,num(r1+4)));ret(123)
        elif pc==tramp+36:env['original_updates']+=1;ret()
        elif pc==tramp+48:ret(env['native_win'])
        elif pc==tramp+68:ret(env['native_count'])
        elif pc==0xb363dc:ret(alloc(r0))
        elif pc in (0x894ca0,0xb36928,0xb76c4c,0xe8c10,0x282b78,0x3ba164,0x3ba2c0,0x44d220,0x44d0b0):ret()
        elif pc in (0x13b5a0,0x283394):ret(parent)
        elif pc==0x895608:ret()
        elif pc==0x851728:ret(123)
        elif pc==0x851920:ret(registry)
        elif pc==0xb75560:
            p=alloc(192)+12;u.mem_write(p,txt(r1).encode()+b'\0');w(p-4,100);w(r0,p);ret()
        elif pc==0xff1010:env['registered'].append((txt(read(r1)),r3));ret()
        elif pc==0xff1020:ret(parent)
        elif pc in (0xff1030,):ret()
        elif pc==0xff1040:ret(r1)
        elif pc==0xff1050:env['fields'].append((txt(read(r2)),r3));ret()
        elif pc==0xff1060:ret(789)
        elif pc==0xff1070:ret(456)
        elif pc==0xff1080:ret(zmeta)
        elif pc==0xff1090:env['body_hits'].append((r0,num(r1+4)));fl(r0+0xb0,num(r0+0xb0)-num(r1+4));ret()
        elif pc==0xff10a0:ret(1)
        elif pc==0xff10b0:u.mem_write(r0+0x10,bytes(u.mem_read(r1,12)));ret()
        elif pc==0xff10c0:env['death_ticks']+=1;ret()
        elif pc==0xff10d0:ret(0xf45000)
        elif pc==0xff10e0:ret(gmeta)
        elif pc==0xff10f0:env['garg_ticks']+=1;ret()
        elif pc==0xff1100:ret()
        elif pc==0x365ec4:
            assert r2==8;v=alloc(8);w(v,3);w(v+4,1);w(r0+8,v);w(r0+12,v+8);ret()
        elif pc==0x881b84:ret()
        elif pc==0x181a30:assert r0==board and read(r1)==3;ret(giant)
        elif pc==0x282ae4:w(r0+8,r0);w(r0+12,1);ret(r0)
        elif pc==0x248120:
            items=env['grids'] if r1==4 else [zombie,enemy];v=alloc(8+len(items)*4)
            for i,p in enumerate(items):w(v+i*4,p)
            w(r0,v);w(r0+4,v+4*len(items));ret()
        elif pc==0x17a8c4:
            assert txt(read(r1))=='iris_hypno_ally';p=alloc(0x80);w(p,read(0xf80f48));w(p+8,p);w(p+12,1)
            env['grids'].append(p);env['objects'][p]=p;ret(p)
        elif pc==0x8821a8:ret(123)
        elif pc==0x8890c4:w(r0,read(r2));w(r0+4,read(r2+4));ret()
        elif pc==0x888b8c:ret(456)
        elif pc==0x884378:ret(env['objects'].get(read(r1),0))
        elif pc==0x13dea0:w(r0,r2);w(r0+4,r3);ret()
        elif pc==0x1814a4:ret(222+76*r1)
        elif pc==0x1872a8:ret(0)
        elif pc==0x1a4280:env['sounds'].append(txt(read(r1)));ret()
        elif pc==0x13f310:ret(r0)
        elif pc==0x5dfc80:env['root_ticks'].append((read(r0+0x68),read(r0+0x70),read(r0+0xa8)&1));ret()
        elif pc==0x2708b4:env['removed'].append(r0);ret()
        elif pc==stop:u.emu_stop()
    u.hook_add(UC_HOOK_CODE,hook)
    def run(mode,*args):
        for reg,value in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),list(args)+[0]*4):u.reg_write(reg,value)
        u.reg_write(UC_ARM_REG_SP,0xfff000);u.reg_write(UC_ARM_REG_LR,stop);u.reg_write(UC_ARM_REG_R4,0x12345678)
        u.emu_start(entry+mode*40,stop,count=300000)
        assert u.reg_read(UC_ARM_REG_PC)==stop and u.reg_read(UC_ARM_REG_SP)==0xfff000 and u.reg_read(UC_ARM_REG_R4)==0x12345678
        return u.reg_read(UC_ARM_REG_R0)
    run(0);run(15);run(0);run(15)
    assert env['registered']==[('IrisHypnoAlly',0x80),('PlantIrisHypno',0x10)]
    run(3,reflect,descriptor);run(18,reflect,descriptor);assert len(env['fields'])==10
    fw=run(16);w(fw+4,plant);fl(plant+0x4c,50);w(hit,zombie);fl(hit+4,50);w(hit+8,0x20000)
    out=alloc(32);run(22,out,fw,hit);assert len(env['grids'])==1
    proxy=env['grids'][0];assert num(zombie+0xb0)==200 and read(zombie+0xac)==1
    assert read(zombie)!=zvt and read(proxy+0x78)==zvt and read(proxy+0x50)==1
    assert run(9,zombie,1)==0
    run(22,out,fw,hit);assert len(env['grids'])==1
    fl(clock+0x1c,.1);run(8,zombie);fl(clock+0x1c,.2);run(8,zombie)
    fl(clock+0x1c,.3);run(8,zombie);fl(clock+0x1c,.4);run(8,zombie);fl(clock+0x1c,.5);run(8,zombie)
    assert env['body_hits'][-1]==(enemy,50)
    assert all(a==c==0 for a,c,_ in env['root_ticks']) and read(zombie+0x68)==123 and read(zombie+0x70)==456
    assert run(26)==1 and not run(11)
    w(enemy+0x48,4);assert run(11)==1
    w(hit,plant);run(12,zombie,hit);assert env['body_hits'][-1][0]==enemy
    w(hit,enemy);assert run(12,zombie,hit)==123
    w(zombie+0x48,4);run(8,zombie);assert env['death_ticks']==1
    run(6,proxy);assert read(zombie)==zvt and read(proxy+0x7c)==0
    env['grids'].clear();w(enemy+0x48,0);w(zombie+0x48,0)
    # Charging must replace the consumer with a real native Gargantuar,
    # retaining its state machine and attack-target callbacks.
    run(19,fw);w(hit,enemy);run(22,out,fw,hit)
    assert env['removed']==[enemy] and len(env['grids'])==1
    assert read(giant+0xac)==1 and num(giant+0xb0)==3600
    assert read(read(giant)+0x198)==entry+28*40 and read(read(giant)+0x19c)==entry+29*40
    run(8,giant);assert env['garg_ticks']==1
    assert read(0xf80f58)==entry+27*40 and read(0xf80f5c)==entry+10*40
    # A giant's smash is not a bite and cannot consume another Hypno-shroom.
    count=len(env['grids']);w(hit,giant);run(22,out,fw,hit);assert len(env['grids'])==count
    print('PASS: hypno actual ARM registration/schema, fatal-consumption conversion, healed/reversed ally, hostile FSM suspension, real enemy damage, friendly shot filtering, proxy/death cleanup, scoped win/wave counts and ABI')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('library',type=Path);check(parser.parse_args().library)
