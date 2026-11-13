// Native Jester adapter: preserve real projectile identities while juggling.
using Byte=unsigned char;using Word=unsigned int;
template<class T>static T&at(Byte*p,Word o){return *reinterpret_cast<T*>(p+o);}
template<class R,class...A>static R call(Word b,Word p,A...a){return reinterpret_cast<R(*)(A...)>(b+p)(a...);}
template<class R,class...A>static R virt(Byte*p,Word o,A...a){return at<R(*)(Byte*,A...)>(at<Byte*>(p,0),o)(p,a...);}
static char*text(Word b,const char*s){char*r,a;call<void>(b,0xb75560,&r,s,&a);return r;}
static void drop(Word b,char*s){char a;if(__atomic_fetch_sub(reinterpret_cast<int*>(s-4),1,__ATOMIC_ACQ_REL)<=0)call<void>(b,0xb76c4c,s-12,&a);}
static void trace(Word b,const char*s,Word n){
#if IRIS_DARK_TRACE
 call<int>(b,0xe8c10,3,"IrisDark","Jester %s value=%x",s,n);
#endif
}
#include "magnet.inc"
static Byte*state(Word b){return reinterpret_cast<Byte*>(b+0xf80500);}
static Word stub(Word b,Word mode){return b+IRIS_JESTER_STUB+mode*40;}
static void schemaParent(Word b,Byte*r,Byte*d,Word kind,const char*parent){
 Byte*m=at<Byte*>(state(b),kind*0x10);at<Byte*>(m,0x24)=d;at<Byte*>(d,0x5c)=m;
 char*n=text(b,parent);Byte*p=virt<Byte*>(r,0x24,&n);drop(b,n);virt<void>(r,0x28,d,virt<Word>(p,0x34),0u);
}
static void metadata(Word b,Byte*parent,Word kind,const char*name,Word factory,Word meta,Word schema,Word size){
 Byte*s=state(b)+kind*0x10;
 if(!at<Word>(s,0)){
  Byte*m=call<Byte*>(b,0xb363dc,40u);call<void>(b,0x894ca0,m);at<Byte*>(s,0)=m;call<void>(b,0x895608,m,name,parent,stub(b,factory));
  if(!kind){Byte*t=call<Byte*>(b,0xb363dc,0x1acu);for(Word o=0;o<0x1ac;o+=4)at<Word>(t,o)=*reinterpret_cast<Word*>(b+0xced208+o);
   at<Word>(t,0)=stub(b,meta);at<Word>(t,0x64)=stub(b,4);at<Word>(t,0x40)=stub(b,5);at<Word>(t,8)=stub(b,6);at<Word>(t,0xc)=stub(b,7);at<Byte*>(s,4)=t;
  }
 }
 Byte*m=call<Byte*>(b,0x851728),*r=m?call<Byte*>(b,0x851920,m):nullptr;
 if(r&&!at<Word>(s,8)){at<Word>(s,8)=1;char*n=text(b,name);virt<void>(r,0xc,&n,stub(b,schema),size,0u);drop(b,n);}
}
// 190 queue of typed weak Projectile handles (native vector layout),
// 19c animation phase,1a0 native state,1a4 spinup/out deadline,1a8 last update.
static void actorSchema(Word b,Byte*r,Byte*d){
 schemaParent(b,r,d,0,"Zombie");char*n=text(b,"Projectile");Word p=virt<Word>(r,0x24,&n);drop(b,n);Word weak=virt<Word>(r,0x20,3u,p,0u,0u);
 // All RtWeakPtr<T> vectors use the same eight-byte storage adapter. The
 // reflected element is explicitly Projectile, never Plant.
 Byte*adapter=call<Byte*>(b,0xb363dc,4u);at<Word>(adapter,0)=b+0xcce168;
 Word vector=virt<Word>(r,0x20,2u,weak,adapter,1u);n=text(b,"iris_juggled_projectiles");virt<void>(r,0x2c,d,&n,0x190u,vector);drop(b,n);
 Word integer=virt<Word>(r,0x14,6u,4u),number=virt<Word>(r,0x14,8u,4u);
 for(Word i=0;i<4;++i){n=text(b,i==0?"iris_jester_phase":i==1?"iris_jester_state":i==2?"iris_jester_deadline":"iris_jester_last_time");virt<void>(r,0x2c,d,&n,0x19c+i*4,i>=2?number:integer);drop(b,n);}
}
static void animation(Word b,Byte*z,const char*label,bool loop){Byte*r=weakObject(b,reinterpret_cast<Word*>(z+0x40));if(!r)return;char*n=text(b,label);Word empty[6]={};call<void>(b,loop?0x44d220:0x44d0b0,r,&n,loop?3u:0u,empty,empty);drop(b,n);}
static Word count(Byte*z){return Word(at<Byte*>(z,0x194)-at<Byte*>(z,0x190))/8;}
static void push(Word b,Byte*z,Byte*p){
 Byte*first=at<Byte*>(z,0x190),*last=at<Byte*>(z,0x194),*cap=at<Byte*>(z,0x198);Word n=count(z);
 if(last==cap){Word room=n?n*2:8;if(room>1000)room=1000;Byte*next=call<Byte*>(b,0xb363dc,room*8);
  for(Word i=0;i<n*8;i+=4)at<Word>(next,i)=at<Word>(first,i);if(first)call<void>(b,0xb36928,first);
  at<Byte*>(z,0x190)=next;last=next+n*8;at<Byte*>(z,0x198)=next+room*8;
 }
 at<Word>(last,0)=at<Word>(last,4)=0;call<void>(b,0x13dea0,last,0u,at<Word>(p,8),at<Word>(p,0xc));at<Byte*>(z,0x194)=last+8;
}
static void release(Word b,Byte*z,bool destroy){
 Byte*first=at<Byte*>(z,0x190),*last=at<Byte*>(z,0x194);
 for(Byte*q=first;q!=last;q+=8){Byte*p=weakObject(b,reinterpret_cast<Word*>(q));if(p&&destroy)call<void>(b,0x2708b4,p);call<void>(b,0x13dea0,q,0u,0u,0u);}
 at<Byte*>(z,0x194)=first;
}
static bool catchable(Word b,Byte*z,Byte*p){
 if(!p||at<Word>(z,0x48)-4u<5u||at<float>(z,0x28)<=0||(at<Word>(z,0x150)&6u)||at<Word>(p,0x84)&0x80000000)return false;
 // Exact whitelist is represented by an empty derived property class: no
 // rank fields or new flags are added to Iris's existing sheet ABI.
 Byte*props=at<Byte*>(p,0x10);if(!props)props=weakObject(b,reinterpret_cast<Word*>(p+0x18));
 if(!props||virt<Byte*>(props,0)!=at<Byte*>(state(b),0x10))return false;
 float vx=at<float>(p,0x38)*at<float>(p,0x50),vy=at<float>(p,0x3c)*at<float>(p,0x54);if(vy<0)vy=-vy;
 return vx>0&&vy<vx*1.7320508f;
}
static Word catchShot(Word b,Byte*z,Byte*p){
 if(!catchable(b,z,p))return 0;
 if(count(z)>=1000){call<void>(b,0x2708b4,p);return 1;}
 // Native property flag bit 0 disables motion/collision; bit 1 hides art.
 at<Word>(p,0x84)|=3;at<float>(p,0x28)=battleTime(b)+2;push(b,z,p);
 if(!at<Word>(z,0x19c)||at<Word>(z,0x19c)==3){at<Word>(z,0x19c)=1;at<float>(z,0x1a4)=battleTime(b)+26.0f/30;animation(b,z,"spinup",false);}
 trace(b,"caught projectile",count(z));return 1;
}
static void launch(Word b,Byte*z,Byte*p){
 at<float>(p,0x2c)=at<float>(z,0x10)-20;at<float>(p,0x30)=at<float>(z,0x14);at<float>(p,0x34)=50;
 at<float>(p,0x38)=-500;at<float>(p,0x3c)=at<float>(p,0x40)=0;
 for(Word o=0x44;o<=0x4c;o+=4)at<float>(p,o)=0;for(Word o=0x50;o<=0x58;o+=4)at<float>(p,o)=1;
 at<float>(p,0x28)=-1;at<float>(p,0x78)=3.14159265f;at<float>(p,0x7c)=0;
 at<Word>(p,0x84)=(at<Word>(p,0x84)&~3u)|0x80000000;
 call<void>(b,0x13dea0,p+0x20,0u,at<Word>(z,8),at<Word>(z,0xc));call<void>(b,0x13dea0,p+0x98,0u,0u,0u);
 trace(b,"launched projectile",reinterpret_cast<Word>(p));
}
static Word update(Word b,Byte*z){
 Byte*board=battleBoard(b);if(!board||at<Word>(board,0xa8)!=5||call<bool>(b,0x1872a8,board))return 0;
 float x=at<float>(z,0x10);bool juggling=count(z)>0;
 call<void>(b,0x5dfc80,z);if(at<Word>(z,0x48)-4u<5u){release(b,z,true);return 0;}
 if(juggling&&at<Word>(z,0x48)==1&&at<float>(z,0x10)!=x){float pos[3]={x+(at<float>(z,0x10)-x)*1.1f,at<float>(z,0x14),at<float>(z,0x18)};virt<void>(z,0x58,pos);}
 float now=battleTime(b);Byte*first=at<Byte*>(z,0x190),*last=at<Byte*>(z,0x194),*out=first;
 float delta=at<float>(z,0x1a8)>0?now-at<float>(z,0x1a8):0;at<float>(z,0x1a8)=now;
 if(at<Word>(z,0x150)&6u){if(delta>0&&delta<=1){at<float>(z,0x1a4)+=delta;for(Byte*q=first;q!=last;q+=8){Byte*p=weakObject(b,reinterpret_cast<Word*>(q));if(p)at<float>(p,0x28)+=delta;}}return 0;}
 for(Byte*q=first;q!=last;q+=8){Byte*p=weakObject(b,reinterpret_cast<Word*>(q));
  if(p&&now<at<float>(p,0x28)){if(out!=q){at<Word>(out,0)=at<Word>(q,0);at<Word>(out,4)=at<Word>(q,4);}out+=8;}
  else{if(p)launch(b,z,p);call<void>(b,0x13dea0,q,0u,0u,0u);}
 }
 at<Byte*>(z,0x194)=out;Word phase=at<Word>(z,0x19c);
 if(phase==1&&now>=at<float>(z,0x1a4)){at<Word>(z,0x19c)=phase=2;animation(b,z,"spin_walk",true);}
 if(phase==2&&!count(z)){at<Word>(z,0x19c)=3;at<float>(z,0x1a4)=now+15.0f/30;animation(b,z,"spindown",false);}
 if(phase==3&&now>=at<float>(z,0x1a4)){at<Word>(z,0x19c)=0;animation(b,z,at<Word>(z,0x48)==3?"eat":"walk",true);}
 if(phase==2&&at<Word>(z,0x48)!=at<Word>(z,0x1a0))animation(b,z,"spin_walk",true);
 at<Word>(z,0x1a0)=at<Word>(z,0x48);
 return 0;
}
extern "C" __attribute__((section(".text.entry")))
Word iris_jester(Word b,Word*args,Word mode){
 if(mode==0){call<void>(b,IRIS_JESTER_REGISTER);metadata(b,call<Byte*>(b,0x5e8c4c),0,"ZombieIrisJester",1,2,3,0x1b0);return 0;}
 if(mode==9){call<void>(b,IRIS_JESTER_PROPS_REGISTER);Byte*parent=**reinterpret_cast<Byte***>(b+0xd0056c);if(parent)metadata(b,parent,1,"IrisJuggleableProjectileProps",10,11,12,0xe8);return 0;}
 if(mode==1){Byte*z=call<Byte*>(b,0xb363dc,0x1b0u);for(Word o=0;o<0x1b0;o+=4)at<Word>(z,o)=0;call<void>(b,0x5de8b8,z);at<Byte*>(z,0)=at<Byte*>(state(b),4);return reinterpret_cast<Word>(z);}
 if(mode==2)return at<Word>(state(b),0);
 if(mode==3){actorSchema(b,reinterpret_cast<Byte*>(args[0]),reinterpret_cast<Byte*>(args[1]));return 0;}
 if(mode==11)return at<Word>(state(b),0x10);
 if(mode==12){schemaParent(b,reinterpret_cast<Byte*>(args[0]),reinterpret_cast<Byte*>(args[1]),1,"ProjectilePropertySheet");return 0;}
 if(mode==10){Byte*parent=at<Byte*>(at<Byte*>(state(b),0x10),8);Byte*p=at<Byte*(*)()>(parent,0xc)();Byte*s=state(b);
  if(!at<Word>(s,0x14)){Byte*t=call<Byte*>(b,0xb363dc,0x80u);for(Word o=0;o<0x80;o+=4)at<Word>(t,o)=at<Word>(at<Byte*>(p,0),o);at<Word>(t,0)=stub(b,11);at<Byte*>(s,0x14)=t;}
  at<Byte*>(p,0)=at<Byte*>(s,0x14);return reinterpret_cast<Word>(p);
 }
 Byte*z=reinterpret_cast<Byte*>(args[0]);
 if(mode==4)return update(b,z);
 if(mode==5)return catchShot(b,z,reinterpret_cast<Byte*>(args[1]));
 if(mode==6||mode==7){release(b,z,true);if(at<Word>(z,0x190))call<void>(b,0xb36928,at<Byte*>(z,0x190));call<void>(b,0x5deafc,z);if(mode==7)call<void>(b,0xb36928,z);return 0;}
 if(mode==8){Byte*props=at<Byte*>(z,0x10);if(!(at<Word>(z,0x84)&0x80000000)||!props)return call<Word>(b,IRIS_JESTER_PROJECTILE_UPDATE,z);
  Word old=at<Word>(props,0x18);at<Word>(props,0x18)=0x10;Word result=call<Word>(b,IRIS_JESTER_PROJECTILE_UPDATE,z);at<Word>(props,0x18)=old;return result;
 }
 return 0;
}
