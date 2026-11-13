// Scoped Dark Gargantuar attack/imp callbacks on Iris's retained native class.
using Byte=unsigned char;using Word=unsigned int;
template<class T>static T&at(Byte*p,Word o){return *reinterpret_cast<T*>(p+o);}
template<class R,class...A>static R call(Word b,Word p,A...a){return reinterpret_cast<R(*)(A...)>(b+p)(a...);}
template<class R,class...A>static R virt(Byte*p,Word o,A...a){return at<R(*)(Byte*,A...)>(at<Byte*>(p,0),o)(p,a...);}
static char*text(Word b,const char*s){char*r,a;call<void>(b,0xb75560,&r,s,&a);return r;}
static void drop(Word b,char*s){char a;if(__atomic_fetch_sub(reinterpret_cast<int*>(s-4),1,__ATOMIC_ACQ_REL)<=0)call<void>(b,0xb76c4c,s-12,&a);}
static void trace(Word b,const char*s,Word n){
#if IRIS_DARK_TRACE
 call<int>(b,0xe8c10,3,"IrisDark","DarkGarg %s value=%x",s,n);
#endif
}
#include "magnet.inc"
#include "zombie_types.inc"
static bool darkGarg(Word b,Byte*z){Byte*t=weakObject(b,reinterpret_cast<Word*>(z+0x38));return t&&equalText(at<const char*>(t,8),"ZombieGargantuar");}
static bool friendly(Word b,Byte*z){Word fn=*reinterpret_cast<Word*>(b+0xf80f58);return fn&&reinterpret_cast<Word(*)(Byte*)>(fn)(z);}
static void throwImp(Word b,Byte*z){
 if(at<Byte>(z,0x184))return;Word type[2]={};if(!findZombieType(b,type,"dark_imp")){trace(b,"missing dark imp",0);return;}
 Byte*board=battleBoard(b),*imp=call<Byte*>(b,0x181a30,board,type,0u);call<void>(b,0x13dea0,type,0u,0u,0u);if(!imp)return;
 bool ally=friendly(b,z);float sign=ally?1.0f:-1.0f;
 float pos[3]={at<float>(z,0x10)+sign*100.0f,at<float>(z,0x14)+2.0f,at<float>(z,0x18)+115.0f};virt<void>(imp,0x58,pos);
 float target=float(call<int>(b,0x17d518,board,ally?6u:2u));
 call<void>(b,0x64529c,imp,target,at<float>(z,0x14),0.0f,1.5f,250.0f,1u);
 Byte*rig=weakObject(b,reinterpret_cast<Word*>(z+0x40));if(rig){char*n=text(b,"pod");call<void>(b,0x44cd0c,rig,&n,0u);drop(b,n);}
 at<Byte>(z,0x184)=1;
 if(ally){Word fn=*reinterpret_cast<Word*>(b+0xf80f5c);if(fn)reinterpret_cast<void(*)(Byte*)>(fn)(imp);}
 trace(b,ally?"allied imp launched":"imp launched",at<Word>(imp,8));
}
extern "C" __attribute__((section(".text.entry")))
Word iris_dark_garg(Word b,Word*args,Word mode){
 Byte*z=reinterpret_cast<Byte*>(args[0]);
 if(mode==1){throwImp(b,z);return 0;}
 if(!darkGarg(b,z))return call<Word>(b,IRIS_GARG_EVENT,z,args[1],args[2],args[3]);
 // The callback receives a std::string reference, not a character buffer.
 const char*event=args[3]?*reinterpret_cast<const char**>(args[3]):nullptr;
 if(equalText(event,"smash_left")||equalText(event,"smash_righ")){
  Byte*t=virt<Byte*>(z,0x198);if(!t)t=virt<Byte*>(z,0x19c);
  if(t){struct{Byte*source;float amount;Word flags;Word conditions[3];}hit={z,1500.0f,0x100000u,{}};virt<void>(t,0x34,&hit);trace(b,friendly(b,z)?"allied smash":"smash",1500);}
  return 0;
 }
 if(equalText(event,"cannon_fire")){throwImp(b,z);return 0;}
 return call<Word>(b,IRIS_GARG_EVENT,z,args[1],args[2],args[3]);
}
