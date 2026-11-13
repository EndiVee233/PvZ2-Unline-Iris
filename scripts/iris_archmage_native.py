"""Own Archmage actor and saved sleep controller, using Iris's ABI."""
import struct
import subprocess
from native_payload import require_position_independent


def patch_archmage_native(path, source, ndk, out, *, trace=False):
    data=bytearray(path.read_bytes())
    for address in (0x619fc0,0x282388):
        if struct.unpack_from('<I',data,address)[0]&0xff000000!=0xea000000:
            raise ValueError('Archmage requires the previous actor/ground adapters')
    if struct.unpack_from('<2I',data,0x39f964)!=(0xe92d4830,0xe1a04000):
        raise ValueError('Unexpected Plant::Update prologue')
    phoff=struct.unpack_from('<I',data,28)[0];stride,count=struct.unpack_from('<HH',data,42)
    h,=[h for h in range(phoff,phoff+stride*count,stride)
         if struct.unpack_from('<I',data,h)[0]==1 and struct.unpack_from('<I',data,h+24)[0]==5
         and sum(struct.unpack_from('<I',data,h+o)[0] for o in (4,16))==len(data)]
    _,off,va,_,size,mem,_,_=struct.unpack_from('<8I',data,h);assert size==mem
    pad=-(va+size)%4;data.extend(bytes(pad));size+=pad;start=va+size
    actor,ground,plant,entry=start+600,start+612,start+624,start+636
    def branch(pc,target,thumb=False):
        d=target-pc-8
        if d%(2 if thumb else 4) or not -0x2000000<=d<0x2000000:raise ValueError('Archmage branch out of range')
        return ((0xfa000000|((d&2)<<23)) if thumb else 0xea000000)|((d>>2)&0xffffff)
    tools=ndk/'toolchains/llvm/prebuilt/windows-x86_64/bin'
    obj,blob,linker=[out/('iris-archmage'+s) for s in ('.o','.bin','.ld')]
    linker.write_text(f'SECTIONS {{ . = {entry:#x}; .text : {{ *(.text.entry) *(.text*) *(.rodata*) }} /DISCARD/ : {{ *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) }} }}')
    subprocess.run([tools/'clang++.exe','--target=armv7a-linux-androideabi21','-mthumb','-Oz','-fPIC','-ffreestanding','-fno-exceptions','-fno-rtti','-fno-math-errno','-fno-jump-tables','-fno-unwind-tables','-fno-asynchronous-unwind-tables',
        f'-DIRIS_DARK_TRACE={int(trace)}',f'-DIRIS_ARCHMAGE_STUB={start}',f'-DIRIS_ARCHMAGE_REGISTER={actor}',f'-DIRIS_SLEEP_REGISTER={ground}',f'-DIRIS_SLEEP_PLANT_UPDATE={plant}','-c',source,'-o',obj],check=True)
    require_position_independent(obj)
    subprocess.run([tools/'ld.lld.exe','-T',linker,'--oformat=binary','-o',blob,obj],check=True)
    code=bytearray()
    for mode in range(15):
        pc=start+len(code);code.extend(struct.pack('<10I',0xe92d401f,0xe1a0100d,0xe3a02000|mode,0xe59f0010,0xe08f0000,branch(pc+20,entry,True),0xe28dd010,0xe8bd8010,0xe320f000,(-(pc+24))&0xffffffff))
    for address,where,mode in ((0x619fc0,actor,0),(0x282388,ground,5)):
        old=struct.unpack_from('<I',data,address)[0];d=(old&0xffffff)<<2
        if d&0x2000000:d-=0x4000000
        code.extend(struct.pack('<3I',branch(where,address+8+d),0xe320f000,0xe320f000))
        struct.pack_into('<I',data,address,branch(address,start+40*mode))
    code.extend(data[0x39f964:0x39f96c]);code.extend(struct.pack('<I',branch(plant+8,0x39f96c)))
    struct.pack_into('<I',data,0x39f964,branch(0x39f964,start+560))
    code.extend(blob.read_bytes());code.extend(bytes(-len(code)%4))
    # RX has a large reserved gap before the separately mapped RW page.
    if va+size+len(code)>0xf7f000:raise ValueError('Archmage code would overlap the RW state page')
    data.extend(code);struct.pack_into('<II',data,h+16,size+len(code),size+len(code));path.write_bytes(data)
