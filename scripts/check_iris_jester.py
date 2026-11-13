"""Compiled ARM Jester: whitelist class, real queue, return flight and saves."""
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
 entry=registration_payload(raw,0x619fc0,'ZombieIrisJester')
 parent,registry,reflect,ptype,desc,textslot,stop=[0xf00000+i*0x1000 for i in range(7)]
 appslot,app,board,clock,props_parent_slot,props_parent=[0xf10000+i*0x1000 for i in range(6)]
 parent_sheet,shot,second,vec,stack=0xf20000,0xf21000,0xf22000,0xf23000,0xfff000
 def word(p,v):u.mem_write(p,struct.pack('<I',v))
 def read(p):return struct.unpack('<I',u.mem_read(p,4))[0]
 def fl(p,v):u.mem_write(p,struct.pack('<f',v))
 def num(p):return struct.unpack('<f',u.mem_read(p,4))[0]
 def text(p):return bytes(u.mem_read(p,100)).split(b'\0')[0].decode()
 word(registry,0xf30000);word(0xf3000c,0xf40000);word(reflect,0xf31000)
 for o,fn in ((0x24,0xf40010),(0x28,0xf40020),(0x14,0xf40030),(0x2c,0xf40040),(0x20,0xf40050)):word(0xf31000+o,fn)
 word(ptype,0xf32000);word(0xf32034,0xf40060)
 word(0xd00838,appslot);word(appslot,app);word(app+0x6c0,board);word(board+0xa8,5);word(0xd4ed90,clock)
 word(0xd0056c,props_parent_slot);word(props_parent_slot,props_parent);word(props_parent+0xc,0xf40100)
 word(parent_sheet,0xf33000);word(shot+8,88);word(shot+12,1);word(second+8,89);word(second+12,1)
 env={'heap':0xf50000,'alloc':[],'registered':[],'fields':[],'pause':False,'animations':[],
      'updates':0,'mask':[],'removed':[],'deletes':[],'native_dtor':0,'schema_kind':0}
 objects={88:shot,89:second}
 def ret(v=0):u.reg_write(UC_ARM_REG_R0,v);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def hook(cpu,pc,size,_):
  r0,r1,r2,r3=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
  if pc in (entry+520,entry+544):ret()
  elif pc==0xb363dc:
   p=env['heap'];env['heap']+=(r0+15)&~15;env['alloc'].append((p,r0));u.mem_write(p,b'\0'*r0);ret(p)
  elif pc==0x895608:word(r0+8,r2);word(r0+0xc,r3);ret()
  elif pc in (0x894ca0,0xb76c4c,0xe8c10):ret()
  elif pc==0x5e8c4c:ret(parent)
  elif pc==0x851728:ret(0xf35000)
  elif pc==0x851920:ret(registry)
  elif pc==0xb75560:u.mem_write(textslot,text(r1).encode()+b'\0');word(textslot-4,100);word(r0,textslot);ret()
  elif pc==0xf40000:env['registered'].append((text(read(r1)),r2,r3));ret()
  elif pc==0xf40010:assert text(read(r1)) in ('Zombie','Projectile','ProjectilePropertySheet');ret(ptype)
  elif pc==0xf40060:ret(123)
  elif pc==0xf40020:assert (r0,r1,r2,r3)==(reflect,desc,123,0);ret()
  elif pc==0xf40030:ret(r1)
  elif pc==0xf40050:
   if r1==2:assert r2==99 and read(r3)==0xcce168;ret(111)
   else:assert r1==3;ret(99)
  elif pc==0xf40040:env['fields'].append((text(read(r2)),r3));ret()
  elif pc==0xf40100:ret(parent_sheet)
  elif pc==0x5de8b8:ret(r0)
  elif pc==0x1872a8:ret(int(env['pause']))
  elif pc==0x5dfc80:env['updates']+=1;ret()
  elif pc==0x8821a8:ret(0xf36000)
  elif pc==0x8890c4:word(r0,read(r2));word(r0+4,read(r2+4));ret()
  elif pc==0x888b8c:ret(0xf37000)
  elif pc==0x884378:ret(objects.get(read(r1),0))
  elif pc==0x13dea0:word(r0,r2);word(r0+4,r3);ret()
  elif pc==entry+532:env['mask'].append(read(parent_sheet+0x18));ret(456)
  elif pc==0x2708b4:env['removed'].append(r0);ret()
  elif pc==0x5deafc:env['native_dtor']+=1;ret()
  elif pc==0xb36928:env['deletes'].append(r0);ret()
  elif pc==stop:u.emu_stop()
 u.hook_add(UC_HOOK_CODE,hook)
 def run(mode,*args):
  for reg,v in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),list(args)+[0]*4):u.reg_write(reg,v)
  u.reg_write(UC_ARM_REG_SP,stack);u.reg_write(UC_ARM_REG_LR,stop);u.reg_write(UC_ARM_REG_R4,0x12345678)
  u.emu_start(entry+mode*40,stop,count=100000)
  assert u.reg_read(UC_ARM_REG_PC)==stop and u.reg_read(UC_ARM_REG_SP)==stack and u.reg_read(UC_ARM_REG_R4)==0x12345678
  return u.reg_read(UC_ARM_REG_R0)
 run(0);run(9);run(0);run(9);assert [x[0] for x in env['registered']]==['ZombieIrisJester','IrisJuggleableProjectileProps']
 run(3,reflect,desc);assert [o for _,o in env['fields']]==[0x190,0x19c,0x1a0,0x1a4,0x1a8]
 run(12,reflect,desc);sheet=run(10);assert sheet==parent_sheet and read(read(sheet))==entry+11*40
 z=run(1);assert read(read(z)+0x7c)==0x5e2a94;word(z+0x48,1);fl(z+0x28,600);fl(z+0x10,600);fl(z+0x14,300)
 for p in (shot,second):
  word(p+0x10,sheet);fl(p+0x38,333);fl(p+0x50,1);fl(p+0x54,1);word(p+0x84,0x10)
 fl(clock+0x1c,1);assert run(5,z,shot)==1 and read(shot+0x84)==0x13 and num(shot+0x28)==3
 assert read(z+0x194)-read(z+0x190)==8
 word(z+0x150,2);assert run(5,z,second)==0
 run(4,z);fl(clock+0x1c,1.5);run(4,z);assert num(shot+0x28)==3.5
 word(z+0x150,0)
 fl(shot+0x38,-333);assert run(5,z,shot)==0;fl(shot+0x38,333)
 env['pause']=True;fl(clock+0x1c,4);before=env['updates'];run(4,z);assert env['updates']==before and read(z+0x194)-read(z+0x190)==8
 env['pause']=False;run(4,z);assert read(z+0x194)==read(z+0x190) and num(shot+0x38)==-500
 assert num(shot+0x34)==50 and read(shot+0x84)==0x80000010 and read(shot+0x98)==0
 assert run(5,z,shot)==0
 word(sheet+0x18,15);assert run(8,shot)==456 and env['mask']==[0x10] and read(sheet+0x18)==15
 word(shot+0x84,0);run(8,shot);assert env['mask'][-1]==15
 # A saved queued object remains the same native projectile after reload.
 fl(clock+0x1c,8);assert run(5,z,second)==1;run(7,z);assert env['native_dtor']==1 and second in env['removed']
 print('PASS: Jester typed whitelist/weak-vector schema, native objects, delayed queue/pause, returned velocity/plant collision mask, scoped property restoration and owned-shot cleanup')


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('library',type=Path);check(p.parse_args().library)
