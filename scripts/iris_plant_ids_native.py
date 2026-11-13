"""Extend the native plant enum, not the unrelated resource UID ordering."""
import json
from pathlib import Path
import struct
import subprocess
from native_payload import require_position_independent

PLANT_IDS=json.loads((Path(__file__).resolve().parents[1]/'src/dark/plant-ids.json').read_text())

def patch_plant_ids_native(path,source,ndk,out,*,trace=False):
    data=bytearray(path.read_bytes());hook=0x1628dc
    if struct.unpack_from('<2I',data,hook)!=(0xe92d47f0,0xe24ddc03):
        raise ValueError('Unexpected Iris PlantType enum constructor')
    ph=struct.unpack_from('<I',data,28)[0];stride,count=struct.unpack_from('<HH',data,42)
    h,=[h for h in range(ph,ph+stride*count,stride) if struct.unpack_from('<I',data,h)[0]==1
        and struct.unpack_from('<I',data,h+24)[0]==5
        and sum(struct.unpack_from('<I',data,h+o)[0] for o in (4,16))==len(data)]
    va=struct.unpack_from('<I',data,h+8)[0];size=struct.unpack_from('<I',data,h+16)[0]
    data.extend(bytes(-(va+size)%4));size=len(data)-struct.unpack_from('<I',data,h+4)[0]
    start=va+size;tramp=start+40;entry=tramp+12
    def branch(pc,target,thumb=False):
        d=target-pc-8
        if d%2 or not -0x2000000<=d<0x2000000:raise ValueError('Plant enum branch out of range')
        return ((0xfa000000|((d&2)<<23)) if thumb else 0xea000000)|((d>>2)&0xffffff)
    (out/'iris_plant_ids.inc').write_text(''.join(f' add(b,object,"{name}",{value});\n' for name,value in PLANT_IDS.items()))
    tools=ndk/'toolchains/llvm/prebuilt/windows-x86_64/bin'
    obj,blob,linker=[out/('iris-plant-ids'+e) for e in ('.o','.bin','.ld')]
    linker.write_text(f'SECTIONS {{ . = {entry}; .text : {{ *(.text.entry) *(.text*) *(.rodata*) }} /DISCARD/ : {{ *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) }} }}')
    subprocess.run([tools/'clang++.exe','--target=armv7a-linux-androideabi21','-mthumb','-Oz','-fPIC',
                    '-ffreestanding','-fno-exceptions','-fno-rtti','-fno-unwind-tables','-fno-asynchronous-unwind-tables',
                    f'-DIRIS_PLANT_IDS_ORIGINAL={tramp}',f'-DIRIS_PLANT_IDS_TRACE={int(trace)}',
                    '-I',out,'-c',source,'-o',obj],check=True)
    require_position_independent(obj)
    subprocess.run([tools/'ld.lld.exe','-T',linker,'--oformat=binary','-o',blob,obj],check=True)
    code=bytearray(struct.pack('<10I',0xe92d401f,0xe1a0100d,0xe3a02000,0xe59f0010,0xe08f0000,
        branch(start+20,entry,True),0xe28dd010,0xe8bd8010,0xe320f000,(-(start+24))&0xffffffff))
    code+=data[hook:hook+8]+struct.pack('<I',branch(tramp+8,hook+8))+blob.read_bytes()
    code+=bytes(-len(code)%4)
    if start+len(code)>=0xf7f000:raise ValueError('Plant enum payload overlaps writable metadata')
    struct.pack_into('<I',data,hook,branch(hook,start));data.extend(code)
    struct.pack_into('<II',data,h+16,size+len(code),size+len(code));path.write_bytes(data)
