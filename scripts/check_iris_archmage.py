"""Execute the actual ARM sleep controller and Archmage in a mocked Iris ABI."""
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
 entry=registration_payload(raw,0x619fc0,'ZombieIrisArchmage')
 def word(p,v):u.mem_write(p,struct.pack('<I',v))
 def read(p):return struct.unpack('<I',u.mem_read(p,4))[0]
 def fl(p,v):u.mem_write(p,struct.pack('<f',v))
 def num(p):return struct.unpack('<f',u.mem_read(p,4))[0]
 def txt(p):return bytes(u.mem_read(p,150)).split(b'\0')[0].decode()
 parent,registry,reflect,ptype,desc,textslot,stop=[0xf00000+i*0x1000 for i in range(7)]
 appslot,app,board,clock,holder_slot,holder=[0xf10000+i*0x1000 for i in range(6)]
 plant,near,far,resource,effect,rig,vec=[0xf20000+i*0x1000 for i in range(7)]
 word(registry,0xf30000);word(0xf3000c,0xf40000);word(reflect,0xf31000)
 for o,f in ((0x24,0xf40010),(0x28,0xf40020),(0x14,0xf40030),(0x2c,0xf40040),(0x20,0xf40050)):word(0xf31000+o,f)
 word(ptype,0xf32000);word(0xf32034,0xf40060)
 word(0xd00838,appslot);word(appslot,app);word(app+0x6c0,board);word(board+0xa8,5);word(0xd4ed90,clock)
 word(0xd008bc,holder_slot);word(holder_slot,holder);word(holder,0xf33000);word(0xf33008,0xf40070)
 objects={77:plant,78:near,79:far,80:resource,81:effect};env={'heap':0xf50000,'alloc':[],'fields':[],'registered':[],
  'pause':False,'paused':False,'native':0,'removed':[],'labels':[],'spawns':[]}
 for i,p in enumerate((plant,near,far)):
  word(p,0xf34000);word(p+8,77+i);word(p+12,1);word(p+0x48,4);fl(p+0x4c,300);u.mem_write(p+0x60,b'\1');fl(p+0x10,400+64*i);fl(p+0x14,300 if i<2 else 500)
 word(0xf34070,0xf40080)
 word(effect+8,81);word(effect+12,1)
 def ret(v=0):u.reg_write(UC_ARM_REG_R0,v);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def alloc(size):
  p=env['heap'];env['heap']+=0x1000;env['alloc'].append((p,size));u.mem_write(p,bytes(size));return p
 def hook(cpu,pc,size,_):
  r0,r1,r2,r3=[u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
  if pc in (entry+600,entry+612):ret()
  elif pc==entry+624:env['native']+=1;ret(42)
  elif pc==0xb363dc:ret(alloc(r0))
  elif pc in (0x894ca0,0xb76c4c,0xb36928,0xe8c10):ret()
  elif pc in (0x5e8c4c,0x283394):ret(parent)
  elif pc==0x895608:assert txt(r1) in ('ZombieIrisArchmage','IrisSleepSpell');ret()
  elif pc==0x851728:ret(0xf35000)
  elif pc==0x851920:ret(registry)
  elif pc==0xb75560:u.mem_write(textslot,txt(r1).encode()+b'\0');word(textslot-4,100);word(r0,textslot);ret()
  elif pc==0xf40000:env['registered'].append((txt(read(r1)),r3));ret()
  elif pc==0xf40010:assert txt(read(r1)) in ('Zombie','GridItem','Plant','Effect_PopAnim');ret(ptype)
  elif pc==0xf40060:ret(123)
  elif pc==0xf40020:assert r2==123;ret()
  elif pc==0xf40030:assert r1 in (6,8);ret(r1)
  elif pc==0xf40040:env['fields'].append((txt(read(r2)),r3));ret()
  elif pc==0xf40050:assert r1==3;ret(500)
  elif pc in (0x5de8b8,0x282ae4):
   ident=100+len(objects);word(r0+8,ident);word(r0+12,1);objects[ident]=r0;ret(r0)
  elif pc==0x1872a8:ret(env['pause'])
  elif pc==0x5dfc80:fl(r0+0x10,num(r0+0x10)-1);ret()
  elif pc==0x1a3dcc:u.mem_write(r0+0x10,bytes(u.mem_read(r1,12)));ret()
  elif pc==0x248120:
   assert r1==1;word(r0,vec);word(r0+4,vec+12)
   for i,p in enumerate((plant,near,far)):word(vec+i*4,p)
   ret()
  elif pc==0x7a3e90:ret(r0-1 if 1<r0<=128 else 0)
  elif pc==0x17a8c4:
   assert txt(read(r1))=='iris_sleep_spell';s=alloc(0x84);word(s,read(0xf80614));ident=100+len(objects);word(s+8,ident);word(s+12,1);objects[ident]=s;env['spawns'].append(s);ret(s)
  elif pc==0x8821a8:ret(0xf36000)
  elif pc==0x8890c4:word(r0,read(r2));word(r0+4,read(r2+4));ret()
  elif pc==0x888b8c:ret(0xf37000)
  elif pc==0x884378:ret(objects.get(read(r1),0))
  elif pc==0x13dea0:word(r0,r2);word(r0+4,r3);ret()
  elif pc==0xf40070:assert txt(read(r3)) in ('POPANIM_EFFECTS_SLEEPPING_PLANT_EFFECT','POPANIM_EFFECTS_ZOMBIE_ARCHMAGE_PROJECTILE');word(r0,80);word(r0+4,1);ret()
  elif pc==0xf40080:ret(rig)
  elif pc==0x45255c:assert r0==rig;env['paused']=bool(r1);ret()
  elif pc==0x129ae0:ret(1)
  elif pc==0x1809a8:ret(effect)
  elif pc in (0x23a354,0x23a814,0x4e6bb8,0x282b78):ret()
  elif pc==0x23aa6c:assert txt(read(r1)) in ('animation','idle','boom');ret()
  elif pc==0x2708b4:env['removed'].append(r0);ret()
  elif pc in (0x44d220,0x44d0b0):env['labels'].append(txt(read(r1)));ret()
  elif pc==stop:u.emu_stop()
 u.hook_add(UC_HOOK_CODE,hook)
 def run(mode,*args):
  for reg,v in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),list(args)+[0]*4):u.reg_write(reg,v)
  u.reg_write(UC_ARM_REG_SP,0xfff000);u.reg_write(UC_ARM_REG_LR,stop);u.reg_write(UC_ARM_REG_R4,0x12345678)
  u.emu_start(entry+mode*40,stop,count=200000)
  assert u.reg_read(UC_ARM_REG_PC)==stop and u.reg_read(UC_ARM_REG_SP)==0xfff000 and u.reg_read(UC_ARM_REG_R4)==0x12345678
  return u.reg_read(UC_ARM_REG_R0)
 run(0);run(5);run(0);run(5);assert env['registered']==[('ZombieIrisArchmage',0x1a4),('IrisSleepSpell',0x84)]
 run(3,reflect,desc);run(8,reflect,desc);assert {o for _,o in env['fields']}=={0x190,0x194,0x198,0x19c,0x1a0,0x50,0x58,0x60,0x64,0x68,0x70,0x74,0x78,0x7c,0x80}
 z=run(1);assert read(read(z)+0x64)==entry+160;word(z+0x48,1);fl(z+0x28,600);fl(z+0x10,740)
 s=run(6);word(s+0x50,77);word(s+0x54,1);word(s+0x64,1);run(12,s);run(9,s)
 assert env['paused'];before=env['native'];run(14,plant);assert env['native']==before
 # Cache is transient; loading the saved controller reconstructs it.
 u.mem_write(0xf80640,bytes(128*16));run(9,s);run(14,plant);assert env['native']==before
 # Native food state wakes the plant and leaves its real object on board.
 u.mem_write(plant+0xd0,b'\1');run(14,plant);assert not env['paused'] and env['native']==before+1 and s in env['removed'];u.mem_write(plant+0xd0,b'\0')
 # A removed weak target cleans its effect, with no pointer reuse.
 run(10,s);assert effect in env['removed'];assert run(14,plant)==42
 # Walking starts an independently saved first-spell timer.
 fl(clock+0x1c,1);run(4,z);assert num(z+0x194)==12
 fl(clock+0x1c,12.1);run(4,z);assert read(z+0x190)==1
 pos=num(z+0x10);fl(clock+0x1c,12.6);word(z+0x150,6);run(4,z);assert abs(num(z+0x19c)-12.6)<0.001
 word(z+0x150,0);fl(clock+0x1c,13);env['pause']=True;run(4,z);assert read(z+0x1a0)==0;env['pause']=False
 fl(clock+0x1c,13.8);run(4,z);assert read(z+0x1a0)==1 and env['spawns']
 ids={read(p+0x50) for p in env['spawns']};assert ids=={77,78}
 for p in env['spawns']:assert read(p+0x64)==1
 fl(clock+0x1c,15);run(4,z);assert read(z+0x190)==0
 print('PASS: Archmage/sleep native ABI and saved schemas, persistent sleep/cache reload, real plant retention, food wake, weak cleanup, first/repeat spell timers, freeze and pause')


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('library',type=Path);check(p.parse_args().library)
