"""Keep native Gargantuar FSM/save handling; scope only its two dark attacks."""
import struct
import subprocess
from native_payload import require_position_independent


def patch_dark_gargantuar_native(path,source,ndk,out,*,trace=False):
    data=bytearray(path.read_bytes());address=0x63c7ac
    if struct.unpack_from('<2I',data,address)!=(0xe92d4830,0xe1a04000):raise ValueError('Unexpected Gargantuar event prologue')
    ph=struct.unpack_from('<I',data,28)[0];stride,count=struct.unpack_from('<HH',data,42)
    h,=[h for h in range(ph,ph+stride*count,stride) if struct.unpack_from('<I',data,h)[0]==1
         and struct.unpack_from('<I',data,h+24)[0]==5 and sum(struct.unpack_from('<I',data,h+o)[0] for o in (4,16))==len(data)]
    _,off,va,_,size,mem,_,_=struct.unpack_from('<8I',data,h);assert size==mem
    pad=-(va+size)%4;data.extend(bytes(pad));size+=pad;start=va+size;tramp=start+80;entry=tramp+12
    def branch(pc,target,thumb=False):
        d=target-pc-8
        if d%(2 if thumb else 4) or not -0x2000000<=d<0x2000000:raise ValueError('Gargantuar branch out of range')
        return ((0xfa000000|((d&2)<<23)) if thumb else 0xea000000)|((d>>2)&0xffffff)
    tools=ndk/'toolchains/llvm/prebuilt/windows-x86_64/bin'
    obj,blob,linker=[out/('iris-dark-garg'+s) for s in ('.o','.bin','.ld')]
    linker.write_text(f'SECTIONS {{ . = {entry:#x}; .text : {{ *(.text.entry) *(.text*) *(.rodata*) }} /DISCARD/ : {{ *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) }} }}')
    subprocess.run([tools/'clang++.exe','--target=armv7a-linux-androideabi21','-mthumb','-Oz','-fPIC','-ffreestanding','-fno-exceptions','-fno-rtti','-fno-math-errno','-fno-jump-tables','-fno-unwind-tables','-fno-asynchronous-unwind-tables',
                    f'-DIRIS_DARK_TRACE={int(trace)}',f'-DIRIS_GARG_EVENT={tramp}','-c',source,'-o',obj],check=True)
    require_position_independent(obj);subprocess.run([tools/'ld.lld.exe','-T',linker,'--oformat=binary','-o',blob,obj],check=True)
    code=bytearray()
    for mode in range(2):
        pc=start+len(code);code.extend(struct.pack('<10I',0xe92d401f,0xe1a0100d,0xe3a02000|mode,0xe59f0010,0xe08f0000,branch(pc+20,entry,True),0xe28dd010,0xe8bd8010,0xe320f000,(-(pc+24))&0xffffffff))
    code.extend(data[address:address+8]);code.extend(struct.pack('<I',branch(tramp+8,address+8)))
    code.extend(blob.read_bytes());code.extend(bytes(-len(code)%4))
    if va+size+len(code)>0xf7f000:raise ValueError('Gargantuar overlaps writable state')
    data.extend(code);struct.pack_into('<I',data,address,branch(address,start));struct.pack_into('<II',data,h+16,size+len(code),size+len(code));path.write_bytes(data)
