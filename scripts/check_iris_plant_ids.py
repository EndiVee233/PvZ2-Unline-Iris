"""Run the original enum constructor and real forward/reverse ARM lookups."""
import argparse
import json
from pathlib import Path
import struct
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
from iris_plant_ids_native import PLANT_IDS

STOCK=('sunflower peashooter wallnut tallnut bonkchoy cabbagepult melonpult cherry_bomb '
       'coconutcannon gravebuster iceburg laser_bean potatomine repeater snapdragon spikeweed '
       'threepeater torchwood kernelpult springbean snowpea chilibean splitpea lightningreed '
       'peapod magnifyinggrass bloomerang holonut empea blover starfruit imitater jalapeno '
       'wintermelon twinsunflower marigold spikerock powerlily squash citron powerplant '
       'sunshroom pultshroom puffshroom scaredyshroom rotoshroom').split()

def check(path):
    raw=path.read_bytes();u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x1000000)
    ph=struct.unpack_from('<I',raw,28)[0];stride,count=struct.unpack_from('<HH',raw,42)
    for h in range(ph,ph+stride*count,stride):
        kind,off,va,_,n,_,_,_=struct.unpack_from('<8I',raw,h)
        if kind==1:u.mem_write(va,raw[off:off+n])
    def read(p):return struct.unpack('<I',u.mem_read(p,4))[0]
    def word(p,v):u.mem_write(p,struct.pack('<I',v&0xffffffff))
    def txt(p):return bytes(u.mem_read(p,160)).split(b'\0')[0].decode()
    heap=0xf40000
    empty=0xf7e00c
    def alloc(n):
        nonlocal heap
        p=heap;heap+=(n+31)&~31;assert heap<0xf7f000;u.mem_write(p,bytes(n));return p
    def string(s):
        data=s.encode()+b'\0';p=alloc(len(data)+12)
        for o,v in ((0,len(data)-1),(4,len(data)-1),(8,2)):word(p+o,v)
        u.mem_write(p+12,data);return p+12
    def ret(v=0):u.reg_write(UC_ARM_REG_R0,v&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    def hook(cpu,pc,n,_):
        r0,r1,r2=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2)]
        if pc==0xb75560:word(r0,string(txt(r1)));ret()
        elif pc==0xb74b98:word(r0,read(r1));ret()
        elif pc==0x163f6c:
            key=txt(read(r1));root=read(r0+8);node=root;parent=r0+4;left=False
            while node:
                name=txt(read(node+16))
                if key==name:ret(node+20);return
                parent=node;left=key<name;node=read(node+(8 if left else 12))
            node=alloc(24);word(node,1);word(node+4,parent);word(node+16,read(r1))
            if parent==r0+4:word(r0+8,node)
            else:word(parent+(8 if left else 12),node)
            root=read(r0+8);lo=root;hi=root
            while read(lo+8):lo=read(lo+8)
            while read(hi+12):hi=read(hi+12)
            word(r0+12,lo);word(r0+16,hi);word(r0+20,read(r0+20)+1)
            word(r1,empty)  # Actual native rvalue-key insertion moves the string.
            ret(node+20)
        elif pc==0x1640b8:word(r1+4,r2);ret(r1)
        elif pc in (0x162844,0xb739d8,0xb76c4c,0xe8c10):ret()
        elif pc==0xb39a54:
            previous=read(r0);word(r0,previous+r1);ret(previous)
        elif pc==0xe86ac:
            a=bytes(u.mem_read(r0,r2));b=bytes(u.mem_read(r1,r2));ret((a>b)-(a<b))
        elif pc==0xb759b4:raise ValueError('unknown enum key')
        elif pc==0xfff000:u.emu_stop()
    u.hook_add(UC_HOOK_CODE,hook)
    def run(pc,*args):
        for r,v in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),list(args)+[0]*4):u.reg_write(r,v)
        u.reg_write(UC_ARM_REG_SP,0xff0000);u.reg_write(UC_ARM_REG_LR,0xfff000)
        u.emu_start(pc,0xfff000,count=2000000);assert u.reg_read(UC_ARM_REG_PC)==0xfff000
        assert u.reg_read(UC_ARM_REG_SP)==0xff0000
        return u.reg_read(UC_ARM_REG_R0)
    aliases={'sunshroom_grown':42,'sunshroom_stage3':42,
             'iris_iceshroom_stage2':52,'iris_iceshroom_stage3':52,
             'iris_fireshroom_stage2':53,'iris_fireshroom_stage3':53}
    expected={name:i for i,name in enumerate(STOCK,1)}|PLANT_IDS
    for obj in (0xf10000,0xf11000):
        assert run(0x1628dc,obj)==obj
        for name,value in (expected|aliases).items():
            key=alloc(4);word(key,string(name));assert run(0x32cdf8,obj,key)==value,(name,value)
        for name,value in expected.items():
            output=alloc(4);run(0x32ceec,output,obj,value);assert txt(read(output))==name,(name,value)
    key=alloc(4);word(key,string('unregistered_plant'))
    try:run(0x32cdf8,obj,key)
    except ValueError:pass
    else:raise AssertionError('Unknown keys must retain native rejection')
    print('PASS: real ARM constructor, all 46 stock IDs unchanged, ten stable new IDs, '
          'growth aliases, native forward/reverse lookups, independent instances and unknown-key rejection')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('library',type=Path);check(p.parse_args().library)
