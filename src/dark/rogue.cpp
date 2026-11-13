// Aster Rogue state machine adapted to Iris's actor ABI.
// Uses Iris's existing dark_thief type identity for persistent bookkeeping.
using Byte=unsigned char;using Word=unsigned int;
template<class T>static T&at(Byte*p,Word o){return *reinterpret_cast<T*>(p+o);}
template<class R,class...A>static R call(Word b,Word p,A...a){return reinterpret_cast<R(*)(A...)>(b+p)(a...);}
template<class R,class...A>static R virt(Byte*p,Word o,A...a){return at<R(*)(Byte*,A...)>(at<Byte*>(p,0),o)(p,a...);}
static char*text(Word b,const char*s){char*r,a;call<void>(b,0xb75560,&r,s,&a);return r;}
static void drop(Word b,char*s){char a;if(__atomic_fetch_sub(reinterpret_cast<int*>(s-4),1,__ATOMIC_ACQ_REL)<=0)call<void>(b,0xb76c4c,s-12,&a);}
static void trace(Word b,const char*s,Word n){
#if IRIS_DARK_TRACE
 call<int>(b,0xe8c10,3,"IrisDark","Rogue %s value=%x",s,n);
#endif
}
#include "magnet.inc"
// 190 phase (0 entered,1 cloaking,2 cloaked),194 transition deadline,
// 198 lamp reveal,19c injury flash deadline,1a0 previous native state,
// 1a4 previous update time (freeze/stun must suspend cloak animation).
static Byte*state(Word b){return reinterpret_cast<Byte*>(b+0xf80400);}
static Word stub(Word b,Word mode){return b+IRIS_ROGUE_STUB+mode*40;}
static void registerRogue(Word b){
 Byte*s=state(b),*parent=call<Byte*>(b,0x5e8c4c);
 if(!at<Word>(s,0)){
  Byte*m=call<Byte*>(b,0xb363dc,40u);call<void>(b,0x894ca0,m);at<Byte*>(s,0)=m;
  call<void>(b,0x895608,m,"ZombieIrisRogue",parent,stub(b,1));
  // Aster Rogue derives directly from Zombie. ZombieBasic's initialization
  // assumes a Basic-specific rig and cannot be paired with the generic rig.
  Byte*t=call<Byte*>(b,0xb363dc,0x1acu);
  for(Word o=0;o<0x1ac;o+=4)at<Word>(t,o)=*reinterpret_cast<Word*>(b+0xced208+o);
  at<Word>(t,0)=stub(b,2);at<Word>(t,0x64)=stub(b,4);at<Word>(t,0x68)=stub(b,5);
  at<Word>(t,0x3c)=stub(b,6);at<Word>(t,0x34)=stub(b,7);at<Byte*>(s,4)=t;
 }
 Byte*m=call<Byte*>(b,0x851728),*r=m?call<Byte*>(b,0x851920,m):nullptr;
 if(r&&!at<Word>(s,8)){at<Word>(s,8)=1;char*n=text(b,"ZombieIrisRogue");virt<void>(r,0xc,&n,stub(b,3),0x1b0u,0u);drop(b,n);}
}
static void schema(Word b,Byte*r,Byte*d){
 Byte*m=at<Byte*>(state(b),0);at<Byte*>(m,0x24)=d;at<Byte*>(d,0x5c)=m;
 char*n=text(b,"Zombie");Byte*p=virt<Byte*>(r,0x24,&n);drop(b,n);virt<void>(r,0x28,d,virt<Word>(p,0x34),0u);
 Word integer=virt<Word>(r,0x14,6u,4u),number=virt<Word>(r,0x14,8u,4u);
 for(Word i=0;i<6;++i){n=text(b,i==0?"iris_rogue_phase":i==1?"iris_rogue_deadline":i==2?"iris_rogue_reveal":i==3?"iris_rogue_flash":i==4?"iris_rogue_native_state":"iris_rogue_last_time");virt<void>(r,0x2c,d,&n,0x190+i*4,(i==1||i==3||i==5)?number:integer);drop(b,n);}
}
static void animation(Word b,Byte*z,const char*label,bool loop){
 Byte*r=weakObject(b,reinterpret_cast<Word*>(z+0x40));if(!r)return;char*n=text(b,label);Word empty[6]={};call<void>(b,loop?0x44d220:0x44d0b0,r,&n,loop?3u:0u,empty,empty);drop(b,n);
}
static bool lit(Word b,Byte*z){
 int rect[4]={0,0,16,5};MagnetList list={};call<void>(b,0x248120,&list,1u,rect);bool found=false;
 for(Byte**q=list.begin;q!=list.end;++q){Byte*p=*q;if(!p||at<Word>(p,0x48)==3)continue;
  Byte*t=weakObject(b,reinterpret_cast<Word*>(p+0xb8));if(!t||!equalText(at<const char*>(t,0x10),"POPANIM_PLANT_STREETLAMP"))continue;
  Byte*f=at<Byte*>(p,0x30);if(f&&battleTime(b)<at<float>(f,0x10)){found=true;break;}
  float dx=(at<float>(z,0x10)-at<float>(p,0x10))/64,dy=(at<float>(z,0x14)-at<float>(p,0x14))/76;
  if(dx<0)dx=-dx;if(dy<0)dy=-dy;int ax=int(dx+0.5f),ay=int(dy+0.5f);
  if(ay<=2&&ax<=3&&(ay==2?ax==0:ax+ay!=4)){found=true;break;}
 }
 if(list.begin)call<void>(b,0xb36928,list.begin);return found;
}
static Word update(Word b,Byte*z){
 Byte*board=battleBoard(b);if(!board||at<Word>(board,0xa8)!=5||call<bool>(b,0x1872a8,board))return 0;
 Word phase=at<Word>(z,0x190);float point[3]={at<float>(z,0x10),at<float>(z,0x14),at<float>(z,0x18)};
 call<void>(b,0x5dfc80,z);if(at<Word>(z,0x48)-4u<5u)return 0;float now=battleTime(b);
 float delta=now-at<float>(z,0x1a4);if(delta<0||delta>1)delta=0;at<float>(z,0x1a4)=now;
 if((at<Word>(z,0x150)&6u)&&phase==1){at<float>(z,0x194)+=delta;virt<void>(z,0x58,point);return 0;}
 if(!phase&&point[0]<=747){at<Word>(z,0x190)=phase=1;at<float>(z,0x194)=now+130.0f/30;animation(b,z,"invisible",false);trace(b,"cloak started",1);}
 if(phase==1){virt<void>(z,0x58,point);if(now>=at<float>(z,0x194)){at<Word>(z,0x190)=phase=2;at<float>(z,0x194)=now;animation(b,z,"invisible_walk",true);trace(b,"cloaked",2);}}
 if(phase==2){Word reveal=lit(b,z);if(reveal!=at<Word>(z,0x198))trace(b,"lamp reveal",reveal);at<Word>(z,0x198)=reveal;
  Word current=at<Word>(z,0x48);if(current==1&&at<Word>(z,0x1a0)!=1)animation(b,z,"invisible_walk",true);
 }
 at<Word>(z,0x1a0)=at<Word>(z,0x48);return 0;
}
static Word draw(Word b,Byte*z,Word graphics){
 Word phase=at<Word>(z,0x190);float now=battleTime(b);int alpha=255;
 if(phase==2&&at<Word>(z,0x48)-4u>=5u){
  if(at<Word>(z,0x198))alpha=127;
  else if(now<at<float>(z,0x19c))alpha=178;
  else{float f=(now-at<float>(z,0x194))*2;if(f>=1)return 0;alpha=int(255*(1-f));}
 }
 Word flags=at<Word>(z,0xa8),color[4];for(Word i=0;i<4;++i){color[i]=at<Word>(z,0x174+i*4);at<Word>(z,0x174+i*4)=i==3?Word(alpha):255u;}
 at<Word>(z,0xa8)=flags|0x2000;Word result=call<Word>(b,0x5e3428,z,graphics);
 at<Word>(z,0xa8)=flags;for(Word i=0;i<4;++i)at<Word>(z,0x174+i*4)=color[i];return result;
}
extern "C" __attribute__((section(".text.entry")))
Word iris_rogue(Word b,Word*args,Word mode){
 if(mode==0){call<void>(b,IRIS_ROGUE_REGISTER);registerRogue(b);return 0;}
 if(mode==1){Byte*z=call<Byte*>(b,0xb363dc,0x1b0u);for(Word o=0;o<0x1b0;o+=4)at<Word>(z,o)=0;call<void>(b,0x5de8b8,z);at<Byte*>(z,0)=at<Byte*>(state(b),4);trace(b,"instance created",reinterpret_cast<Word>(z));return reinterpret_cast<Word>(z);}
 if(mode==2)return at<Word>(state(b),0);
 if(mode==3){schema(b,reinterpret_cast<Byte*>(args[0]),reinterpret_cast<Byte*>(args[1]));return 0;}
 Byte*z=reinterpret_cast<Byte*>(args[0]);
 if(mode==4)return update(b,z);
 if(mode==5)return draw(b,z,args[1]);
 if(mode==6){if(at<Word>(z,0x190)==2&&!at<Word>(z,0x198))return 0;return call<Word>(b,0x5e2e18,z,args[1]);}
 if(mode==7){at<float>(z,0x19c)=battleTime(b)+0.15f;return call<Word>(b,0x5e0b74,z,args[1]);}
 return 0;
}
