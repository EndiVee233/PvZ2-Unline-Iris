"""Execute compiled King registration, timers and native crown mutation."""
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
 entry=registration_payload(raw,0x619fc0,'ZombieIrisKing')
 def word(p,v):u.mem_write(p,struct.pack('<I',v))
 def read(p):return struct.unpack('<I',u.mem_read(p,4))[0]
 def fl(p,v):u.mem_write(p,struct.pack('<f',v))
 def num(p):return struct.unpack('<f',u.mem_read(p,4))[0]
 def txt(p):return bytes(u.mem_read(p,120)).split(b'\0')[0].decode()
 parent,registry,reflect,ptype,desc,textslot,stop=[0xf00000+i*0x1000 for i in range(7)]
 appslot,app,board,clock=[0xf10000+i*0x1000 for i in range(4)]
 target,type_,rig,vec=[0xf20000+i*0x1000 for i in range(4)]
 word(registry,0xf30000);word(0xf3000c,0xf40000);word(reflect,0xf31000)
 for o,f in ((0x24,0xf40010),(0x28,0xf40020),(0x14,0xf40030),(0x2c,0xf40040),(0x20,0xf40050)):word(0xf31000+o,f)
 word(ptype,0xf32000);word(0xf32034,0xf40060);word(parent+4,parent+0x100);u.mem_write(parent+0x100,b'Zombie\0')
 word(0xd00838,appslot);word(appslot,app);word(app+0x6c0,board);word(board+0xa8,5);word(0xd4ed90,clock)
 word(target,0xced208);word(target+8,78);word(target+12,1);word(target+0x48,1);word(target+0x38,77);word(target+0x3c,1);word(target+0x40,79);word(target+0x44,1)
 fl(target+0x10,600);fl(target+0x14,332);word(type_+4,type_+0x100);u.mem_write(type_+0x100,b'dark_armor2\0')
 word(rig,0xf33000);word(0xf330e4,0xf40070);word(0xf330f4,0xf40080)
 objects={77:type_,78:target,79:rig};env={'heap':0xf50000,'registered':[],'fields':[],'pause':False,'labels':[],'helms':[],'dtor':0,'finished':False,'surrendered':0,'placement':False}
 def ret(v=0):u.reg_write(UC_ARM_REG_R0,v);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def hook(cpu,pc,size,_):
  r0,r1,r2,r3=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
  if pc==entry+400:ret()
  elif pc==entry+412:ret(0)
  elif pc==0xb363dc:p=env['heap'];env['heap']+=0x1000;u.mem_write(p,bytes(r0));ret(p)
  elif pc in (0x894ca0,0xb76c4c,0xb36928,0xe8c10):ret()
  elif pc==0x5e8c4c:ret(parent)
  elif pc==0x895608:assert txt(r1)=='ZombieIrisKing';ret()
  elif pc==0x851728:ret(0xf35000)
  elif pc==0x851920:ret(registry)
  elif pc==0xb75560:u.mem_write(textslot,txt(r1).encode()+b'\0');word(textslot-4,100);word(r0,textslot);ret()
  elif pc==0xf40000:env['registered'].append((txt(read(r1)),r3));ret()
  elif pc==0xf40010:assert txt(read(r1))=='Zombie';ret(ptype)
  elif pc==0xf40060:ret(123)
  elif pc==0xf40020:assert r2==123;ret()
  elif pc==0xf40030:assert r1 in (6,8);ret(r1)
  elif pc==0xf40040:env['fields'].append((txt(read(r2)),r3));ret()
  elif pc==0xf40050:assert r1==3;ret(500)
  elif pc==0x5de8b8:word(r0+8,90);word(r0+12,1);word(r0+0x40,79);word(r0+0x44,1);ret(r0)
  elif pc==0x1872a8:ret(env['pause'])
  elif pc==0x5dfc80:fl(r0+0x10,num(r0+0x10)-1);ret()
  elif pc==0x1a3dcc:u.mem_write(r0+0x10,bytes(u.mem_read(r1,12)));ret()
  elif pc==0x17d518:ret(160+64*r1)
  elif pc==0x1814a4:ret(180+76*r1)
  elif pc==0x248120:
   if r1==5:word(r0,0);word(r0+4,0);ret();return
   if env['placement']:word(r0,vec);word(r0+4,vec+4);word(vec,env['king']);ret();return
   assert r1==2;assert tuple(struct.unpack('<4i',u.mem_read(r2,16))) in ((5,1,4,3),(0,0,16,5))
   word(r0,vec);word(r0+4,vec+4);word(vec,target);ret()
  elif pc==0x5e2e18:ret(1)
  elif pc==0x179f5c:ret(0xf14000)
  elif pc==0x555e7c:ret(env['finished'])
  elif pc==0x5e147c:env['surrendered']+=1;word(r0+0x48,4);ret()
  elif pc==0x8821a8:ret(0xf36000)
  elif pc==0x8890c4:word(r0,read(r2));word(r0+4,read(r2+4));ret()
  elif pc==0x888b8c:ret(0xf37000)
  elif pc==0x884378:ret(objects.get(read(r1),0))
  elif pc==0x13dea0:word(r0,r2);word(r0+4,r3);ret()
  elif pc==0xf40070:env['helms'].append(r1);ret()
  elif pc==0xf40080:ret()
  elif pc in (0x44d220,0x44d0b0):env['labels'].append(txt(read(r1)));ret()
  elif pc==0x5deafc:env['dtor']+=1;ret()
  elif pc==stop:u.emu_stop()
 u.hook_add(UC_HOOK_CODE,hook)
 def run(mode,*args):
  for reg,v in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),list(args)+[0]*4):u.reg_write(reg,v)
  u.reg_write(UC_ARM_REG_SP,0xfff000);u.reg_write(UC_ARM_REG_LR,stop);u.reg_write(UC_ARM_REG_R4,0x12345678)
  u.emu_start(entry+mode*40,stop,count=150000)
  assert u.reg_read(UC_ARM_REG_PC)==stop and u.reg_read(UC_ARM_REG_SP)==0xfff000 and u.reg_read(UC_ARM_REG_R4)==0x12345678
  return u.reg_read(UC_ARM_REG_R0)
 run(0);run(0);assert env['registered']==[('ZombieIrisKing',0x1b4)];run(3,reflect,desc);assert len(env['fields'])==8
 z=run(1);word(z+0x48,1);fl(z+0x10,672);fl(z+0x14,332);fl(clock+0x1c,1);run(4,z)
 assert all(read(read(z)+offset)==entry+9*40 for offset in (0xb8,0x190,0x194)) and run(9,z)==0
 assert read(z+0x190)==1 and num(z+0x10)==672 and env['labels']==['intro']
 fl(clock+0x1c,4.3);run(4,z);assert read(z+0x190)==2
 fl(clock+0x1c,6.9);run(4,z);assert read(z+0x190)==3 and read(z+0x19c)==78
 fl(clock+0x1c,8);word(z+0x150,6);run(4,z);assert not env['helms'];word(z+0x150,0)
 env['pause']=True;fl(clock+0x1c,8.2);run(4,z);assert not env['helms'];env['pause']=False
 fl(clock+0x1c,9.95);run(4,z);assert read(target+0x30)==9 and num(target+0x34)==num(target+0xbc)==1600 and env['helms']==[9]
 run(4,z);assert env['helms']==[9]
 fl(clock+0x1c,12.1);run(4,z);assert read(z+0x190)==2
 fl(clock+0x1c,15);run(4,z);assert read(z+0x190)==2 # Already-crowned targets excluded.
 word(target+0x30,0);run(4,z);assert read(z+0x190)==3
 # A king remains between waves; it surrenders only after the final wave
 # and only after all non-king enemies have gone.
 fl(clock+0x1c,20);run(4,z);env['finished']=True;fl(clock+0x1c,23);run(4,z);assert not env['surrendered']
 word(target+0x48,4);run(4,z);assert env['surrendered']==1
 # The same board predicate services the hover preview and final placement;
 # ordinary packets are blocked while the donor's instant-plant list works.
 env['king']=z;env['placement']=True;word(z+0x48,1);cell,weak=0xf24000,0xf25000
 word(cell,8);word(cell+4,2);word(weak,77);word(weak+4,1);assert run(5,board,cell,weak)==10
 word(cell,7);assert run(5,board,cell,weak)==0
 word(cell,8);u.mem_write(type_+0x100,b'cherry_bomb\0');assert run(5,board,cell,weak)==0
 env['placement']=False
 run(6,z);assert not read(z+0x19c) and env['dtor']==1
 print('PASS: King saved schema/native ABI, stationary intro, 2.5s idle, authored knighting frame, pause/freeze, real crown/1600 HP/max HP, exclusion/re-knighting and weak cleanup')


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('library',type=Path);check(p.parse_args().library)
