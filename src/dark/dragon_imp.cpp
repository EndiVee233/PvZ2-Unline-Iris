// Dragon imps retain Iris's native FutureImp actor, rig, flying and save state.
// Aster's fire multiplier is absent from the old property schema, so scope its
// zero multiplier by the exact authored PopAnim, leaving every other hit alone.
using Byte=unsigned char;using Word=unsigned int;
template<class T>static T&at(Byte*p,Word o){return *reinterpret_cast<T*>(p+o);}
template<class R,class...A>static R call(Word b,Word p,A...a){return reinterpret_cast<R(*)(A...)>(b+p)(a...);}
template<class R,class...A>static R virt(Byte*p,Word o,A...a){return at<R(*)(Byte*,A...)>(at<Byte*>(p,0),o)(p,a...);}
static char*text(Word b,const char*s){char*r,a;call<void>(b,0xb75560,&r,s,&a);return r;}
static void drop(Word b,char*s){char a;if(__atomic_fetch_sub(reinterpret_cast<int*>(s-4),1,__ATOMIC_ACQ_REL)<=0)call<void>(b,0xb76c4c,s-12,&a);}
static void trace(Word,const char*,Word){}
#include "magnet.inc"
extern "C" __attribute__((section(".text.entry")))
Word iris_dragon_imp(Word b,Word*args,Word){Byte*z=reinterpret_cast<Byte*>(args[0]),*hit=reinterpret_cast<Byte*>(args[1]);
 if(z&&hit&&(at<Word>(hit,8)&0x80u)){Byte*t=weakObject(b,reinterpret_cast<Word*>(z+0x38));
  if(t&&equalText(at<const char*>(t,0x10),"POPANIM_ZOMBIE_ZOMBIE_DARK_IMP_DRAGON"))return 0;}
 return call<Word>(b,IRIS_DRAGON_IMP_DAMAGE,z,hit);
}
