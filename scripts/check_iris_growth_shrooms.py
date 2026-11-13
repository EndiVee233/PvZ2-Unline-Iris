"""Run the compiled growth adapter through registry, mutation and save timing.

The mutation mock deliberately poisons the old framework, detecting accesses
after the native operation destroys it. It also verifies ARM argument order.
"""
import argparse
from pathlib import Path
import struct
from native_payload import registration_payload
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *


def check(path):
    data = path.read_bytes()
    u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    u.mem_map(0, 0x1000000)
    u.reg_write(UC_ARM_REG_C1_C0_2, 0xf << 20)
    u.reg_write(UC_ARM_REG_FPEXC, 1 << 30)
    ph = struct.unpack_from('<I', data, 28)[0]
    stride, count = struct.unpack_from('<HH', data, 42)
    for q in range(ph, ph + stride * count, stride):
        kind, off, va, _, size, _, _, _ = struct.unpack_from('<8I', data, q)
        if kind == 1:
            u.mem_write(va, data[off:off + size])
    fw, plant, ptype, name, appslot, app, board, clock, tree = [0xf00000+i*0x1000 for i in range(9)]
    textslot, stop, stack = 0xf20000, 0xf30000, 0xfff000
    newer, rig = 0xf10000, 0xf11000
    enemy, emeta, ename, vec = 0xf15000, 0xf16000, 0xf17000, 0xf18000
    def word(p, v): u.mem_write(p, struct.pack('<I', v))
    def read(p): return struct.unpack('<I', u.mem_read(p, 4))[0]
    def floating(p, v): u.mem_write(p, struct.pack('<f', v))
    def number(p): return struct.unpack('<f', u.mem_read(p, 4))[0]
    def text(p): return bytes(u.mem_read(p, 120)).split(b'\0')[0].decode()
    word(fw+4, plant); word(plant+0x30, fw); word(ptype+0x10, name)
    word(plant+0xb8, 7); word(plant+0x58, 2); word(plant+0x5c, 4); word(plant+0x48, 4)
    u.mem_write(plant+0x61,b'\x01')
    floating(plant+0x4c, 173); word(plant+0xb4, 0xffffffff)
    floating(plant+0x44,1)
    word(plant, 0xf40000); word(0xf40070, 0xf50000)
    floating(plant+0x10,500);floating(plant+0x14,250)
    word(enemy,0xf42000);word(0xf42000,0xf50010);word(0xf4203c,0xf50020)
    word(emeta+4,ename);u.mem_write(ename,b'Zombie\0')
    word(enemy+8,55);word(enemy+12,1);floating(enemy+0x10,700);floating(enemy+0x14,250)
    word(0xd00838, appslot); word(appslot, app); word(app+0x6c0, board)
    word(0xd4ed90, clock); word(board+0xa8, 5)
    word(0xd4ec98, tree)
    nodes = []
    for i, label in enumerate(('iris_iceshroom_stage2', 'iris_iceshroom_stage3',
                               'iris_fireshroom_stage2', 'iris_fireshroom_stage3')):
        node = 0xf60000+i*0x100
        word(node+0x10, node+0x80); u.mem_write(node+0x80, label.encode()+b'\0')
        word(node+0x18, 100+i); word(node+0x1c, 1); nodes.append(node)
    # Deliberately nontrivial BST: both left and right branches are exercised.
    word(tree+8, nodes[0]); word(nodes[0]+8, nodes[2]); word(nodes[0]+12, nodes[1]); word(nodes[2]+12, nodes[3])
    entry = registration_payload(data, 0x3b9478, 'PlantIrisDark')
    env = {'pause': False, 'mutations': [], 'labels': [], 'shot': 0, 'actions': [], 'eligible':True, 'traps':[], 'food':[]}
    def ret(v=0): u.reg_write(UC_ARM_REG_R0,v); u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    def hook(cpu, pc, size, _):
        r0,r1,r2,r3 = [u.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
        if pc==0x8821a8: ret(0xf70000)
        elif pc==0x8890c4: word(r0,read(r2)); word(r0+4,read(r2+4)); ret()
        elif pc==0x888b8c: ret(0xf71000)
        elif pc==0x884378: ret(ptype if read(r1)==7 else 0)
        elif pc==0x13dea0: word(r0,r2); word(r0+4,r3); ret()
        elif pc==0x1872a8: ret(int(env['pause']))
        elif pc==0x39df1c:
            assert (r0,r1,r2)==(plant,4,2)
            env['mutations'].append(read(r3))
            old=read(plant+0x30)
            u.mem_write(old, b'\xa5'*0x2c0)
            fresh=newer if old==fw else fw
            u.mem_write(fresh, bytes(0x2c0)); word(fresh+4,plant); word(plant+0x30,fresh)
            floating(plant+0x4c,300);u.mem_write(plant+0x61,b'\0');ret()
        elif pc==0xf50000: ret(rig)
        elif pc==0xf50010:ret(emeta)
        elif pc==0xf50020:assert r1 in (1,3);ret(int(env['eligible']))
        elif pc==0x248120:
            assert r1 in (2,6);word(vec,enemy);word(r0,vec);word(r0+4,vec+4);word(r0+8,vec+4);ret()
        elif pc==0xb75560:
            u.mem_write(textslot,text(r1).encode()+b'\0'); word(textslot-4,100); word(r0,textslot); ret()
        elif pc in (0x44d0b0,0x44d220): env['labels'].append(text(read(r1))); ret()
        elif pc in (0xb76c4c,0xb36928,0xe8c10): ret()
        elif pc==0x3a1b88:
            assert r0==plant and read(plant+0xb4) in (0,1,2); env['shot']+=1;env['actions'].append(read(plant+0xb4));ret(0xf72000)
        elif pc in (0x3ba164,0x3ba2c0):env['food'].append(pc);ret()
        elif pc==0x17a8c4:
            assert r0==board and text(read(r1)) in ('iris_ice_hole','iris_fire_wall')
            env['traps'].append((text(read(r1)),r2,r3));ret(0xf73000)
        elif pc==0x7a3e90:assert r0>0;ret(0)
        elif pc==0x17d518:ret(200+r1*64)
        elif pc==0x1814a4:ret(200+r1*76)
        elif pc==stop: u.emu_stop()
    u.hook_add(UC_HOOK_CODE,hook)
    def run(mode,t,kind):
        floating(clock+0x1c,t); u.mem_write(name,kind.encode()+b'\0')
        u.reg_write(UC_ARM_REG_SP,stack); u.reg_write(UC_ARM_REG_LR,stop)
        u.reg_write(UC_ARM_REG_R0,read(plant+0x30)); u.reg_write(UC_ARM_REG_R4,0x76543210)
        u.emu_start(entry+mode*40,stop,count=200000)
        assert u.reg_read(UC_ARM_REG_PC)==stop and u.reg_read(UC_ARM_REG_SP)==stack
        assert u.reg_read(UC_ARM_REG_R4)==0x76543210
        return u.reg_read(UC_ARM_REG_R0)
    ice='POPANIM_PLANT_ICESHROOM'; fire='POPANIM_PLANT_FIRESHROOM'
    run(8,10,ice); assert number(fw+8)==32.5
    run(8,32.4,ice); assert not env['mutations']
    env['pause']=True; run(8,33,ice); assert not env['mutations']
    env['pause']=False; run(8,33,ice)
    assert env['mutations']==[100] and number(plant+0x4c)==173 and number(newer+8)==55.5
    assert bytes(u.mem_read(plant+0x61,1))==b'\x01'
    assert env['labels']==['growth_stage1'] and number(plant+0x70)>34
    run(8,56,ice+'_IRIS_STAGE2')
    assert env['mutations']==[100,101] and env['labels'][-1]=='growth_stage2'
    run(8,1000,ice+'_IRIS_STAGE3'); assert len(env['mutations'])==2
    u.mem_write(fw+8,bytes(28)); run(8,10,fire); assert number(fw+8)==25
    run(8,25,fire); assert env['mutations'][-1]==102 and number(newer+8)==55
    run(8,55,fire+'_IRIS_STAGE2'); assert env['mutations'][-1]==103
    assert run(4,56,ice+'_IRIS_STAGE3')==0xf72000 and read(plant+0xb4)==0xffffffff
    assert number(0xf7202c)==498 and number(0xf72030)==245 and abs(number(0xf72034)+0.32)<0.0001
    assert run(4,56,fire+'_IRIS_STAGE3')==0xf72000 and env['actions'][-1]==1
    assert read(0xf72098)==55 and number(0xf7202c)==710 and number(0xf72030)==220
    env['eligible']=False;before=env['shot'];assert run(4,56,fire+'_IRIS_STAGE3')==0 and env['shot']==before
    # Food from the juvenile stage destroys the old framework. Every
    # subsequent operation must use its replacement and preserve health.
    env['eligible']=True;word(plant+0x48,4)
    run(5,60,ice);current=read(plant+0x30)
    assert read(plant+0x48)==5 and read(current+0xc)==1 and number(plant+0x4c)==173
    assert env['labels'][-1]=='growth_stage3'
    before=env['shot'];run(4,60.5,ice+'_IRIS_STAGE3');assert env['shot']==before
    run(8,61.2,ice+'_IRIS_STAGE3');assert read(current+0xc)==2 and env['labels'][-1]=='plantfood'
    run(7,65,ice+'_IRIS_STAGE3');assert len(env['traps'])==2 and all(t[0]=='iris_ice_hole' for t in env['traps'])
    assert read(plant+0x48)==4 and read(current+0xc)==0 and env['labels'][-1]=='idle'
    run(7,65,ice+'_IRIS_STAGE3');assert len(env['traps'])==2
    run(5,70,fire+'_IRIS_STAGE3');assert read(current+0xc)==2 and env['labels'][-1]=='plantfood'
    run(7,74,fire+'_IRIS_STAGE3');assert len(env['traps'])==7
    assert {t[2] for t in env['traps'][2:]}==set(range(5)) and len({t[1] for t in env['traps'][2:]})==1
    oak='POPANIM_PLANT_OAKSHOOTER'
    word(plant+0x48,4);before=env['shot'];run(4,80,oak)
    assert env['shot']==before+3 and env['actions'][-3:]==[2,0,2]
    assert abs(number(0xf72038)-288.38645)<0.001 and number(0xf7203c)==166.5
    run(5,90,oak);current=read(plant+0x30);assert read(current+0x18)==0
    before=env['shot'];run(8,91.4,oak);assert env['shot']==before
    run(8,91.42,oak);assert env['shot']==before+1
    env['pause']=True;run(8,92,oak);assert env['shot']==before+1
    env['pause']=False;run(8,92.62,oak);assert env['shot']==before+40 and read(current+0x18)==40
    run(8,92.65,oak);assert env['shot']==before+40
    run(7,93,oak);assert read(plant+0x48)==4
    # Missing registry entry leaves the original plant intact, for saves
    # produced by an incompatible intermediate development package.
    word(tree+8,0); before=len(env['mutations']); floating(fw+8,1)
    run(8,57,fire); assert len(env['mutations'])==before
    print('PASS: tier-two growth timing, stage registry, pause, native mutation ABI, UID-preserving state, HP retention, food growth/ground effects, Oak split arrows and complete 40-shot rain')


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('library',type=Path); check(p.parse_args().library)
