"""Exercise the actual ARM Dark Gargantuar event callback, with explicit native boundaries."""
from pathlib import Path
import struct,argparse
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
def check(path):
 raw=path.read_bytes();u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x1000000);u.reg_write(UC_ARM_REG_C1_C0_2,0xf<<20);u.reg_write(UC_ARM_REG_FPEXC,1<<30)
 ph=struct.unpack_from('<I',raw,28)[0];stride,n=struct.unpack_from('<HH',raw,42)
 for h in range(ph,ph+stride*n,stride):
  kind,off,va,_,size,_,_,_=struct.unpack_from('<8I',raw,h)
  if kind==1:u.mem_write(va,raw[off:off+size])
 def w(p,v):u.mem_write(p,struct.pack('<I',v))
 def read(p):return struct.unpack('<I',u.mem_read(p,4))[0]
 def fl(p,v):u.mem_write(p,struct.pack('<f',v))
 def num(p):return struct.unpack('<f',u.mem_read(p,4))[0]
 def txt(p):return bytes(u.mem_read(p,120)).split(b'\0')[0].decode()
 v=read(0x63c7ac);d=(v&0xffffff)<<2
 if d&0x2000000:d-=0x4000000
 entry=0x63c7b4+d;stop=0xff1000
 z,typ,target,imp,rig,board=[0xf30000+i*0x1000 for i in range(6)];vt=0xf37000
 for p in (z,target,imp,rig):w(p,vt)
 for offset,fn in ((0x198,0xff1010),(0x19c,0xff1020),(0x34,0xff1030),(0x58,0xff1040)):w(vt+offset,fn)
 w(z+0x38,1);w(z+0x3c,1);w(z+0x40,3);w(typ+8,typ+0x100);u.mem_write(typ+0x100,b'ZombieGargantuar\0');w(typ+4,typ+0x200);u.mem_write(typ+0x200,b'dark_imp\0')
 fl(z+0x10,600);fl(z+0x14,222);fl(z+0x18,0);w(0xd4e964,123)
 w(0xd00838,0xf39000);w(0xf39000,0xf3a000);w(0xf3a6c0,board)
 state={'hits':[],'spawns':0,'land':[],'hidden':[],'fallback':0,'friendly':False,'converted':[],'target':target,'grid':0,'heap':0xf90000}
 def alloc(n):p=state['heap'];state['heap']+=(n+31)//32*32;return p
 def ret(v=0):u.reg_write(UC_ARM_REG_R0,v);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def hook(cpu,pc,size,data):
  r0,r1,r2,r3=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
  if pc==0x8821a8:ret(123)
  elif pc==0x8890c4:w(r0,read(r2));w(r0+4,read(r2+4));ret()
  elif pc==0x888b8c:ret(456)
  elif pc==0x884378:ret({1:typ,2:typ,3:rig}.get(read(r1),0))
  elif pc==0x13dea0:w(r0,r2);w(r0+4,r3);ret()
  elif pc==0xff1010:ret(state['target'])
  elif pc==0xff1020:ret(state['grid'])
  elif pc==0xff1030:state['hits'].append((r0,read(r1),num(r1+4),read(r1+8)));ret()
  elif pc==0xff1040:u.mem_write(r0+0x10,bytes(u.mem_read(r1,12)));ret()
  elif pc==0x365ec4:
   assert r2==8;v=alloc(8);w(v,2);w(v+4,1);w(r0+8,v);w(r0+12,v+8);ret()
  elif pc in (0x881b84,0xb36928,0xb76c4c,0xe8c10):ret()
  elif pc==0x181a30:assert r0==board and read(r1)==2;state['spawns']+=1;ret(imp)
  elif pc==0x17d518:ret(200+64*r1)
  elif pc==0x64529c:
   sp=u.reg_read(UC_ARM_REG_SP);state['land'].append((r0,r1,r2,r3,read(sp),read(sp+4),read(sp+8)));ret()
  elif pc==0x44cd0c:state['hidden'].append((r0,txt(read(r1)),r2));ret()
  elif pc==0xb75560:p=alloc(180)+12;u.mem_write(p,txt(r1).encode()+b'\0');w(p-4,100);w(r0,p);ret()
  elif pc==0xff1050:ret(state['friendly'])
  elif pc==0xff1060:state['converted'].append(r0);ret()
  elif pc==entry+80:state['fallback']+=1;ret(99)
  elif pc==stop:u.emu_stop()
 u.hook_add(UC_HOOK_CODE,hook);w(0xf80f58,0xff1050);w(0xf80f5c,0xff1060)
 def run(event):
  ev=0xf3b000;w(ev,ev+0x100);u.mem_write(ev+0x100,event.encode()+b'\0')
  for r,v in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),(z,0,0,ev)):u.reg_write(r,v)
  u.reg_write(UC_ARM_REG_SP,0xfff000);u.reg_write(UC_ARM_REG_LR,stop);u.emu_start(entry,stop,count=100000);assert u.reg_read(UC_ARM_REG_PC)==stop and u.reg_read(UC_ARM_REG_SP)==0xfff000
 run('smash_left');assert state['hits']==[(target,z,1500.0,0x100000)]
 state['target']=0;state['grid']=target;run('smash_righ');assert len(state['hits'])==2
 run('cannon_fire');assert state['spawns']==1 and num(imp+0x10)==500 and num(imp+0x18)==115 and state['hidden']==[(rig,'pod',0)] and u.mem_read(z+0x184,1)==b'\1'
 run('cannon_fire');assert state['spawns']==1
 u.mem_write(z+0x184,b'\0');state['friendly']=True;run('cannon_fire');assert num(imp+0x10)==700 and state['converted']==[imp]
 assert state['land'][0][1]==struct.unpack('<I',struct.pack('<f',328.0))[0] and state['land'][0][4:]==(0x3fc00000,0x437a0000,1)
 run('walk');assert state['fallback']==1
 u.mem_write(typ+0x100,b'ZombieGargantuarMech\0');run('smash_left');assert state['fallback']==2
 print('PASS: actual ARM std::string event ABI, 1500 smash/ground target, single dark imp trajectory, allied direction/conversion and Mech fallback')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('library',type=Path);check(p.parse_args().library)
