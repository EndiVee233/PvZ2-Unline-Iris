// Iris-owned Dark Dragon actors. The stock ZombossBattleModule retains its
// spawn, health notification and completion lifecycle; actor state is saved.
using Byte=unsigned char;using Word=unsigned int;
template<class T>static T&at(Byte*p,Word o){return *reinterpret_cast<T*>(p+o);}
template<class R,class...A>static R call(Word b,Word p,A...a){return reinterpret_cast<R(*)(A...)>(b+p)(a...);}
template<class R,class...A>static R virt(Byte*p,Word o,A...a){return at<R(*)(Byte*,A...)>(at<Byte*>(p,0),o)(p,a...);}
static char*text(Word b,const char*s){char*r,a;call<void>(b,0xb75560,&r,s,&a);return r;}
static void drop(Word b,char*s){char a;if(__atomic_fetch_sub(reinterpret_cast<int*>(s-4),1,__ATOMIC_ACQ_REL)<=0)call<void>(b,0xb76c4c,s-12,&a);}
static void trace(Word b,const char*s,Word n){
#if IRIS_DARK_TRACE
 call<int>(b,0xe8c10,3,"IrisDark","Dragon %s value=%x",s,n);
#endif
}
#include "magnet.inc"
#include "dragon_fields.inc"
static Byte*state(Word b){return reinterpret_cast<Byte*>(b+0xf81d00);}
static Word stub(Word b,Word i){return b+IRIS_DRAGON_STUB+i*40;}
static const char*name(Word k){return k==0?"IrisDragonProperties":k==1?"ZombieIrisDragon":"ZombieIrisDragonImp";}
static Word bytes(Word k){return k==0?0x400:k==1?0x240:0x1d0;}
static void metadata(Word b){Byte*s=state(b);
 for(Word k=0;k<3;++k){if(!at<Word>(s,k*4)){Byte*m=call<Byte*>(b,0xb363dc,40u);call<void>(b,0x894ca0,m);at<Byte*>(s,k*4)=m;
  call<void>(b,0x895608,m,name(k),call<Byte*>(b,k==0?0x12c65c:0x5e8c4c),stub(b,1+k));
  Byte*prototype=k==0?call<Byte*>(b,0x12c770):nullptr;Byte*source=prototype?at<Byte*>(prototype,0):reinterpret_cast<Byte*>(b+0xced208);
  Word count=k==0?0x44:0x1ac;Byte*v=call<Byte*>(b,0xb363dc,count);for(Word o=0;o<count;o+=4)at<Word>(v,o)=at<Word>(source,o);
  if(prototype){at<Word>(s,0x48)=at<Word>(source,8);virt<void>(prototype,0xc);at<Word>(v,8)=stub(b,15);at<Word>(v,0xc)=stub(b,16);}at<Word>(v,0)=stub(b,4+k);at<Byte*>(s,0x20+k*4)=v;
  if(k){at<Word>(v,0x64)=stub(b,k==1?10:11);at<Word>(v,0x34)=stub(b,12);at<Word>(v,8)=stub(b,13);at<Word>(v,0xc)=stub(b,14);}
 }
 Byte*manager=call<Byte*>(b,0x851728),*r=manager?call<Byte*>(b,0x851920,manager):nullptr;
 if(r&&!(at<Word>(s,0x40)&(1u<<k))){at<Word>(s,0x40)|=1u<<k;char*n=text(b,name(k));virt<void>(r,0xc,&n,stub(b,7+k),bytes(k),0u);drop(b,n);}}
}
static void field(Word b,Byte*r,Byte*d,const char*n,Word off,Word type){char*s=text(b,n);virt<void>(r,0x2c,d,&s,off,type);drop(b,s);}
static void schema(Word b,Byte*r,Byte*d,Word k){Byte*m=at<Byte*>(state(b),k*4);at<Byte*>(m,0x24)=d;at<Byte*>(d,0x5c)=m;
 char*n=text(b,k==0?"ZombiePropertySheet":"Zombie");Byte*parent=virt<Byte*>(r,0x24,&n);drop(b,n);virt<void>(r,0x28,d,virt<Word>(parent,0x34),0u);
 Word number=virt<Word>(r,0x14,8u,4u),integer=virt<Word>(r,0x14,6u,4u);
 if(!k){for(Word i=0;i<DRAGON_FIELD_COUNT;++i)field(b,r,d,dragonFields[i].name,dragonFields[i].offset,number);
  n=text(b,"ZombieType");Word type=virt<Word>(r,0x24,&n);drop(b,n);type=virt<Word>(r,0x20,3u,type,0u,0u);
  for(Word i=0;i<9;++i){char label[]="SummonType0";label[10]=char('0'+i);field(b,r,d,label,DRAGON_SUMMON_OFFSET+8*i,type);}
 }else{
  for(Word i=0;i<16;++i){char label[]="iris_dragon_saved00";label[17]=char('0'+i/10);label[18]=char('0'+i%10);field(b,r,d,label,0x190+4*i,i<4?integer:number);}
 }
}
static Byte*properties(Word b,Byte*z){Byte*t=weakObject(b,reinterpret_cast<Word*>(z+0x38));return t?call<Byte*>(b,0x6826ec,t):nullptr;}
static float parameter(Byte*p,const char*name){if(!p)return 0;for(Word i=0;i<DRAGON_FIELD_COUNT;++i)if(equalText(name,dragonFields[i].name))return at<float>(p,dragonFields[i].offset);return 0;}
static float phaseParameter(Byte*p,Word phase,const char*tail){char key[64]="Phase0";key[5]=char('0'+phase);Word i=6;while(*tail&&i<63)key[i++]=*tail++;key[i]=0;return parameter(p,key);}
static void animation(Word b,Byte*z,const char*label,bool loop){Byte*r=weakObject(b,reinterpret_cast<Word*>(z+0x40));if(!r)return;char*n=text(b,label);Word empty[6]={};call<void>(b,loop?0x44d220:0x44d0b0,r,&n,loop?3u:0u,empty,empty);drop(b,n);}
static bool active(Word b){Byte*board=battleBoard(b);return board&&at<Word>(board,0xa8)==5&&!call<bool>(b,0x1872a8,board);}
static void bossUpdate(Word b,Byte*z){if(!active(b))return;
 if(at<float>(z,0xb0)<=0||at<Word>(z,0x48)-4u<5u){call<void>(b,0x5dfc80,z);return;}
 Byte*p=properties(b,z);if(!p)return;float now=battleTime(b);
 if(!at<Word>(z,0x190)){at<Word>(z,0x190)=1;at<Word>(z,0x198)=1;at<float>(z,0x1a0)=now+310.0f/30;
  animation(b,z,"intro",false);trace(b,"intro started",at<Word>(z,8));}
 // Let Iris update collision, status conditions and attachments while the
 // authored action controller owns displacement and animations.
 float pos[3]={at<float>(z,0x10),at<float>(z,0x14),at<float>(z,0x18)};Word fsm=at<Word>(z,0x68),state70=at<Word>(z,0x70);
 at<Word>(z,0x68)=at<Word>(z,0x70)=0;call<void>(b,0x5dfc80,z);at<Word>(z,0x68)=fsm;at<Word>(z,0x70)=state70;virt<void>(z,0x58,pos);
 if(at<Word>(z,0x198)==1&&now>=at<float>(z,0x1a0)){at<Word>(z,0x198)=0;animation(b,z,"idle",true);trace(b,"intro completed",0);}
 // Further action handlers are added only after this actor/asset bridge is
 // exercised in the isolated package; campaign boss entry remains locked.
}
static void impUpdate(Word b,Byte*z){if(active(b))call<void>(b,0x5dfc80,z);}
extern "C" __attribute__((section(".text.entry")))
Word iris_dragon(Word b,Word*args,Word mode){
 if(mode==0){call<void>(b,IRIS_DRAGON_REGISTER);metadata(b);return 0;}
 if(mode>=1&&mode<=3){Word k=mode-1,n=bytes(k);Byte*p=call<Byte*>(b,0xb363dc,n);for(Word i=0;i<n;i+=4)at<Word>(p,i)=0;
  if(!k){Byte*q=call<Byte*>(b,0x12c770);for(Word i=0;i<0xd8;i+=4)at<Word>(p,i)=at<Word>(q,i);call<void>(b,0xb36928,q);}else call<void>(b,0x5de8b8,p);
  at<Byte*>(p,0)=at<Byte*>(state(b),0x20+4*k);return reinterpret_cast<Word>(p);}
 if(mode>=4&&mode<=6)return at<Word>(state(b),4*(mode-4));
 if(mode>=7&&mode<=9){schema(b,reinterpret_cast<Byte*>(args[0]),reinterpret_cast<Byte*>(args[1]),mode-7);return 0;}
 Byte*p=reinterpret_cast<Byte*>(args[0]);if(mode==10){bossUpdate(b,p);return 0;}if(mode==11){impUpdate(b,p);return 0;}
 if(mode==12)return call<Word>(b,0x5e0b74,p,reinterpret_cast<Byte*>(args[1]));
 if(mode==13||mode==14){call<void>(b,0x5deafc,p);if(mode==14)call<void>(b,0xb36928,p);return 0;}
 if(mode==15||mode==16){for(Word i=0;i<9;++i)call<void>(b,0x13dea0,p+DRAGON_SUMMON_OFFSET+8*i,0u,0u,0u);reinterpret_cast<void(*)(Byte*)>(at<Word>(state(b),0x48))(p);if(mode==16)call<void>(b,0xb36928,p);return 0;}
 return 0;
}
