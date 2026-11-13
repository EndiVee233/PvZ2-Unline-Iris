"""Reject linker fixups that an appended freestanding payload cannot load."""
import struct
from elftools.elf.elffile import ELFFile
from elftools.elf.relocation import RelocationSection


def require_position_independent(path):
    with path.open('rb') as stream:
        elf = ELFFile(stream)
        bad = [(section.name, relocation['r_offset'])
               for section in elf.iter_sections() if isinstance(section, RelocationSection)
               for relocation in section.iter_relocations()
               if relocation['r_info_type'] == 2]  # R_ARM_ABS32 needs a loader fixup
    if bad:
        raise ValueError(f'{path.name}: absolute pointers in native payload: {bad}')


def registration_payload(data, hook, class_name):
    """Locate one adapter through the explicitly chained registration stubs.

    Tests must follow each real chain instead of assuming their adapter is
    always the last one to hook the shared native class registration.
    """
    ph=struct.unpack_from('<I',data,28)[0];stride,count=struct.unpack_from('<HH',data,42)
    segments=[struct.unpack_from('<8I',data,h) for h in range(ph,ph+stride*count,stride)
              if struct.unpack_from('<I',data,h)[0]==1]
    def offset(address):
        for _,off,va,_,size,_,_,_ in segments:
            if va<=address<va+size:return off+address-va
        raise ValueError(f'Unmapped adapter address {address:x}')
    def read(address):return struct.unpack_from('<I',data,offset(address))[0]
    def target(address):
        op=read(address)
        if op&0xff000000!=0xea000000:raise ValueError(f'Expected registration chain at {address:x}')
        delta=(op&0xffffff)<<2
        if delta&0x2000000:delta-=0x4000000
        return address+8+delta
    address=target(hook);end=len(data)
    for _ in range(32):
        mode=read(address+8)&0xff;start=address-mode*40
        n=0
        while n<64 and read(start+n*40)==0xe92d401f and read(start+n*40+8)==0xe3a02000|n:n+=1
        if not n:break
        if class_name.encode()+b'\0' in data[offset(start):end]:return start
        # Archmage registers its actor at mode 0 and its ground controller
        # at mode 5; the latter has the second saved registration chain.
        # Hypno's plant registration is mode 15 and also uses its second
        # trampoline; mode 0 owns the independent GridItem registration.
        chain=start+n*40+(12 if mode in (5,15) else 0)
        end=offset(start);address=target(chain)
    raise ValueError(f'Native registration payload not found: {class_name}')
