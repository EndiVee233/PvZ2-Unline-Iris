// The stock object registry's group 8 contains every loaded ZombieType.
// Avoid hard-coded UID handles and preserve ownership of the returned weak.
// Native RtWeak snapshot: pool, scratch, begin/end, count, owns-scratch flag.
// 881a44 writes byte 14; it is NOT a three-pointer std::vector.
struct ZombieTypeList{Word prefix[2];Word*begin,*end;Word count,ownership;};
static_assert(sizeof(ZombieTypeList)==0x18,"RtWeak snapshot ABI");
static bool findZombieType(Word b,Word*out,const char*name,bool className=false){
 // Ghidra FUN_00375ec4 is VA 365ec4 in the ELF. Its r1 argument is unused;
 // it gets the authoritative RtRegistry itself and snapshots type pool 8.
 ZombieTypeList list={};call<void>(b,0x365ec4,&list,0u,8u);bool found=false;
 for(Word*q=list.begin;q!=list.end;q+=2){Byte*t=weakObject(b,q);if(t&&equalText(at<const char*>(t,className?8:4),name)){
  call<void>(b,0x13dea0,out,0u,q[0],q[1]);found=true;break;}}
 call<void>(b,0x881b84,&list);return found;
}
