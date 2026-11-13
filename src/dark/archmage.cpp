// Aster's Archmage sleeps plants; it does not use the Wizard's sheep list.
// A separate saved GridItem owns each sleep, without changing Plant's ABI.
using Byte=unsigned char;using Word=unsigned int;
template<class T>static T&at(Byte*p,Word o){return *reinterpret_cast<T*>(p+o);}
template<class R,class...A>static R call(Word b,Word p,A...a){return reinterpret_cast<R(*)(A...)>(b+p)(a...);}
template<class R,class...A>static R virt(Byte*p,Word o,A...a){return at<R(*)(Byte*,A...)>(at<Byte*>(p,0),o)(p,a...);}
static char*text(Word b,const char*s){char*r,a;call<void>(b,0xb75560,&r,s,&a);return r;}
static void drop(Word b,char*s){char a;if(__atomic_fetch_sub(reinterpret_cast<int*>(s-4),1,__ATOMIC_ACQ_REL)<=0)call<void>(b,0xb76c4c,s-12,&a);}
static void trace(Word b,const char*s,Word n){
#if IRIS_DARK_TRACE
 call<int>(b,0xe8c10,3,"IrisDark","Archmage %s value=%x",s,n);
#endif
}
#include "magnet.inc"
static Byte*state(Word b){return reinterpret_cast<Byte*>(b+0xf80600);}
static Word stub(Word b,Word mode){return b+IRIS_ARCHMAGE_STUB+mode*40;}
// Runtime lookup is not a saved owner. Both keys are weak handles; the
// serialized controller rebuilds this acceleration table after a load.
static Byte*cache(Word b,Word i){return state(b)+0x40+i*16;}
static void clear(Word b,Byte*w){call<void>(b,0x13dea0,w,0u,0u,0u);}
static Byte*sleeping(Word b,Byte*p){
 for(Word i=0;i<128;++i){Byte*c=cache(b,i);if(at<Word>(c,0)==at<Word>(p,8)&&at<Word>(c,4)==at<Word>(p,0xc)){
  Byte*s=weakObject(b,reinterpret_cast<Word*>(c+8));if(s)return s;clear(b,c);clear(b,c+8);
 }}return nullptr;
}
static void remember(Word b,Byte*s,Byte*p){
 if(sleeping(b,p))return;
 for(Word i=0;i<128;++i){Byte*c=cache(b,i);if(!(at<Word>(c,0)|at<Word>(c,4))||!weakObject(b,reinterpret_cast<Word*>(c+8))){
  call<void>(b,0x13dea0,c,0u,at<Word>(p,8),at<Word>(p,0xc));call<void>(b,0x13dea0,c+8,0u,at<Word>(s,8),at<Word>(s,0xc));return;
 }}
}
static void forget(Word b,Byte*s){for(Word i=0;i<128;++i){Byte*c=cache(b,i);if(at<Word>(c,8)==at<Word>(s,8)&&at<Word>(c,12)==at<Word>(s,0xc)){clear(b,c);clear(b,c+8);}}}
static void pauseRig(Word b,Byte*p,bool pause){Byte*r=virt<Byte*>(p,0x70);if(r)call<void>(b,0x45255c,r,Word(pause));}
static void field(Word b,Byte*r,Byte*d,const char*name,Word offset,Word type){char*n=text(b,name);virt<void>(r,0x2c,d,&n,offset,type);drop(b,n);}
static Word weakType(Word b,Byte*r,const char*name){char*n=text(b,name);Word t=virt<Word>(r,0x24,&n);drop(b,n);return virt<Word>(r,0x20,3u,t,0u,0u);}
static void schema(Word b,Byte*r,Byte*d,bool sleep){
 Byte*m=at<Byte*>(state(b),sleep?0x10:0);at<Byte*>(m,0x24)=d;at<Byte*>(d,0x5c)=m;
 char*n=text(b,sleep?"GridItem":"Zombie");Byte*p=virt<Byte*>(r,0x24,&n);drop(b,n);virt<void>(r,0x28,d,virt<Word>(p,0x34),0u);
 Word number=virt<Word>(r,0x14,8u,4u),integer=virt<Word>(r,0x14,6u,4u);
 if(sleep){field(b,r,d,"iris_sleep_plant",0x50,weakType(b,r,"Plant"));field(b,r,d,"iris_sleep_effect",0x58,weakType(b,r,"Effect_PopAnim"));field(b,r,d,"iris_sleep_last_time",0x60,number);field(b,r,d,"iris_sleep_active",0x64,integer);
  field(b,r,d,"iris_sleep_orb",0x68,weakType(b,r,"Effect_PopAnim"));field(b,r,d,"iris_sleep_orb_start",0x70,number);field(b,r,d,"iris_sleep_orb_x",0x74,number);field(b,r,d,"iris_sleep_orb_y",0x78,number);field(b,r,d,"iris_sleep_orb_z",0x7c,number);field(b,r,d,"iris_sleep_orb_phase",0x80,integer);}
 else{field(b,r,d,"iris_archmage_phase",0x190,integer);field(b,r,d,"iris_archmage_next_spell",0x194,number);field(b,r,d,"iris_archmage_last_time",0x198,number);field(b,r,d,"iris_archmage_cast_start",0x19c,number);field(b,r,d,"iris_archmage_fired",0x1a0,integer);}
}
static void metadata(Word b,bool sleep){
 Byte*s=state(b)+(sleep?0x10:0);const char*name=sleep?"IrisSleepSpell":"ZombieIrisArchmage";
 if(!at<Word>(s,0)){
  Byte*m=call<Byte*>(b,0xb363dc,40u);call<void>(b,0x894ca0,m);at<Byte*>(s,0)=m;
  call<void>(b,0x895608,m,name,call<Byte*>(b,sleep?0x283394:0x5e8c4c),stub(b,sleep?6:1));
  Word length=sleep?0x7cu:0x1acu;Byte*t=call<Byte*>(b,0xb363dc,length);
  for(Word o=0;o<length;o+=4)at<Word>(t,o)=*reinterpret_cast<Word*>(b+(sleep?0xcdbc88:0xced208)+o);
  at<Word>(t,0)=stub(b,sleep?7:2);at<Word>(t,0x64)=stub(b,sleep?9:4);
  if(sleep){at<Word>(t,8)=stub(b,10);at<Word>(t,0xc)=stub(b,11);at<Word>(t,0x70)=stub(b,12);at<Word>(t,0x3c)=stub(b,13);}
  at<Byte*>(s,4)=t;
 }
 Byte*m=call<Byte*>(b,0x851728),*r=m?call<Byte*>(b,0x851920,m):nullptr;
 if(r&&!at<Word>(s,8)){at<Word>(s,8)=1;char*n=text(b,name);virt<void>(r,0xc,&n,stub(b,sleep?8:3),sleep?0x84u:0x1a4u,0u);drop(b,n);}
}
static Byte*makeEffect(Word b,const char*id,const char*label){
 Byte*h=**reinterpret_cast<Byte***>(b+0xd008bc);if(!h)return nullptr;char*n=text(b,id);Word w[2]={};
 at<void(*)(Word*,Byte*,Word,char**,Word)>(at<Byte*>(h,0),8)(w,h,call<Word>(b,0x129ae0),&n,0u);drop(b,n);Byte*res=weakObject(b,w);clear(b,reinterpret_cast<Byte*>(w));if(!res)return nullptr;
 Byte*e=call<Byte*>(b,0x1809a8,battleBoard(b));if(!e)return nullptr;call<void>(b,0x23a354,e,res,0u);call<void>(b,0x23a814,e,0u);n=text(b,label);call<void>(b,0x23aa6c,e,&n,0u);drop(b,n);return e;
}
static Byte*effect(Word b,Byte*s,Byte*p){
 Byte*e=weakObject(b,reinterpret_cast<Word*>(s+0x58));
 if(!e){e=makeEffect(b,"POPANIM_EFFECTS_SLEEPPING_PLANT_EFFECT","animation");if(!e)return nullptr;
  call<void>(b,0x13dea0,s+0x58,0u,at<Word>(e,8),at<Word>(e,0xc));
 }
 // This PAM was authored in a large attachment canvas. Actor-attached
 // Aster effects inherit that canvas origin; standalone Iris effects do not.
 float pos[3]={at<float>(p,0x10)-150,at<float>(p,0x14)-120,at<float>(p,0x18)};call<void>(b,0x4e6bb8,e,pos,0xffffffffu);return e;
}
static void orb(Word b,Byte*s,Byte*p){
 if(!at<Word>(s,0x80))return;float age=battleTime(b)-at<float>(s,0x70);Byte*e=weakObject(b,reinterpret_cast<Word*>(s+0x68));
 if(age>=0.5f+35.0f/30){if(e)call<void>(b,0x2708b4,e);clear(b,s+0x68);at<Word>(s,0x80)=0;return;}
 if(!e){e=makeEffect(b,"POPANIM_EFFECTS_ZOMBIE_ARCHMAGE_PROJECTILE",age<0.5f?"idle":"boom");if(!e)return;call<void>(b,0x13dea0,s+0x68,0u,at<Word>(e,8),at<Word>(e,0xc));}
 float t=age*2;if(t<0)t=0;if(t>1)t=1;
 if(t>=1&&at<Word>(s,0x80)==1){at<Word>(s,0x80)=2;char*n=text(b,"boom");call<void>(b,0x23aa6c,e,&n,0u);drop(b,n);}
 // The donor's projectile sheet places the authored PAM at (-141,-220).
 float pos[3]={at<float>(s,0x74)*(1-t)+(at<float>(p,0x10)-20)*t-141,
               at<float>(s,0x78)*(1-t)+(at<float>(p,0x14)+40)*t-220,
               at<float>(s,0x7c)*(1-t)+150*t*(1-t)};
 call<void>(b,0x4e6bb8,e,pos,0xffffffffu);
}
static void wake(Word b,Byte*s){
 Byte*p=weakObject(b,reinterpret_cast<Word*>(s+0x50));if(p)pauseRig(b,p,false);
 Byte*e=weakObject(b,reinterpret_cast<Word*>(s+0x58));if(e)call<void>(b,0x2708b4,e);clear(b,s+0x58);forget(b,s);at<Word>(s,0x64)=0;
 e=weakObject(b,reinterpret_cast<Word*>(s+0x68));if(e)call<void>(b,0x2708b4,e);clear(b,s+0x68);at<Word>(s,0x80)=0;
 if(p)trace(b,"plant awake",at<Word>(p,8));
}
static bool eligible(Word b,Byte*z,Byte*p){
 if(!p||at<Word>(p,0x48)==3||at<float>(p,0x4c)<=0||!at<Byte>(p,0x60)||at<Byte>(p,0xd0)||at<Byte>(p,0xd1)||sleeping(b,p))return false;
 if(at<float>(p,0x10)>at<float>(z,0x10)+32)return false;
 Byte*t=weakObject(b,reinterpret_cast<Word*>(p+0xb8));const char*n=t?at<const char*>(t,0x10):nullptr;
 return !equalText(n,"POPANIM_PLANT_CARROTMISSILE")&&!equalText(n,"POPANIM_PLANT_SMALLCHESTNUT");
}
static Byte*target(Word b,Byte*z){
 int rect[4]={0,0,16,5};MagnetList list={};call<void>(b,0x248120,&list,1u,rect);Byte*chosen=nullptr;Word count=0;
 for(Byte**q=list.begin;q!=list.end;++q)if(eligible(b,z,*q)&&call<Word>(b,0x7a3e90,++count)==0)chosen=*q;
 if(list.begin)call<void>(b,0xb36928,list.begin);return chosen;
}
static void putToSleep(Word b,Byte*p,Byte*caster){
 if(sleeping(b,p))return;char*n=text(b,"iris_sleep_spell");Byte*s=call<Byte*>(b,0x17a8c4,battleBoard(b),&n,at<Word>(p,0x5c),at<Word>(p,0x58));drop(b,n);if(!s)return;
 call<void>(b,0x13dea0,s+0x50,0u,at<Word>(p,8),at<Word>(p,0xc));at<Word>(s,0x64)=1;at<float>(s,0x60)=battleTime(b);remember(b,s,p);pauseRig(b,p,true);effect(b,s,p);trace(b,"plant asleep",at<Word>(p,8));
 if(caster){at<float>(s,0x70)=battleTime(b);at<float>(s,0x74)=at<float>(caster,0x10);at<float>(s,0x78)=at<float>(caster,0x14);at<float>(s,0x7c)=100;at<Word>(s,0x80)=1;orb(b,s,p);}
}
static void cast(Word b,Byte*z){
 Byte*p=target(b,z);if(!p)return;float x=at<float>(p,0x10),y=at<float>(p,0x14)-30;int row=int(at<Word>(p,0x58));putToSleep(b,p,z);
 int rect[4]={0,row-1,16,3};MagnetList list={};call<void>(b,0x248120,&list,1u,rect);
 for(Byte**q=list.begin;q!=list.end;++q){Byte*other=*q;if(!eligible(b,z,other))continue;float dx=at<float>(other,0x10)-x,dy=at<float>(other,0x14)-y;if(dx*dx+dy*dy<=92.16f*92.16f)putToSleep(b,other,nullptr);}
 if(list.begin)call<void>(b,0xb36928,list.begin);
}
static void animate(Word b,Byte*z,const char*label,bool loop){Byte*r=weakObject(b,reinterpret_cast<Word*>(z+0x40));if(!r)return;char*n=text(b,label);Word empty[6]={};call<void>(b,loop?0x44d220:0x44d0b0,r,&n,loop?3u:0u,empty,empty);drop(b,n);}
static Word actorUpdate(Word b,Byte*z){
 Byte*board=battleBoard(b);if(!board||at<Word>(board,0xa8)!=5||call<bool>(b,0x1872a8,board))return 0;
 float now=battleTime(b),delta=now-at<float>(z,0x198);if(delta<0||delta>1)delta=0;at<float>(z,0x198)=now;
 float point[3]={at<float>(z,0x10),at<float>(z,0x14),at<float>(z,0x18)};call<void>(b,0x5dfc80,z);
 if(at<Word>(z,0x48)-4u<5u)return 0;
 if(!at<float>(z,0x194))at<float>(z,0x194)=now+11+float(call<Word>(b,0x7a3e90,3001u))/1000;
 if(at<Word>(z,0x150)&6u){if(at<Word>(z,0x190))at<float>(z,0x19c)+=delta;return 0;}
 if(!at<Word>(z,0x190)&&now>=at<float>(z,0x194)&&target(b,z)){
  at<Word>(z,0x190)=1;at<Word>(z,0x1a0)=0;at<float>(z,0x19c)=now;at<float>(z,0x194)=now+15+float(call<Word>(b,0x7a3e90,3001u))/1000;animate(b,z,"sheep",false);trace(b,"cast started",1);
 }
 if(at<Word>(z,0x190)){
  virt<void>(z,0x58,point);float age=now-at<float>(z,0x19c);
  if(!at<Word>(z,0x1a0)&&age>=32.0f/30){at<Word>(z,0x1a0)=1;cast(b,z);}
  if(age>=60.0f/30){at<Word>(z,0x190)=0;animate(b,z,"walk",true);}
 }return 0;
}
static void sleepUpdate(Word b,Byte*s){
 Byte*p=weakObject(b,reinterpret_cast<Word*>(s+0x50));
 if(!at<Word>(s,0x64)||!p||at<Word>(p,0x48)==3||at<float>(p,0x4c)<=0||!at<Byte>(p,0x60)||at<Byte>(p,0xd0)){
  wake(b,s);call<void>(b,0x2708b4,s);return;
 }
 remember(b,s,p);pauseRig(b,p,true);effect(b,s,p);
 Byte*board=battleBoard(b);if(board&&!call<bool>(b,0x1872a8,board))orb(b,s,p);
}
extern "C" __attribute__((section(".text.entry")))
Word iris_archmage(Word b,Word*args,Word mode){
 if(mode==0){call<void>(b,IRIS_ARCHMAGE_REGISTER);metadata(b,false);return 0;}
 if(mode==5){call<void>(b,IRIS_SLEEP_REGISTER);metadata(b,true);return 0;}
 if(mode==1||mode==6){bool sleep=mode==6;Word size=sleep?0x84u:0x1a4u;Byte*p=call<Byte*>(b,0xb363dc,size);for(Word o=0;o<size;o+=4)at<Word>(p,o)=0;call<void>(b,sleep?0x282ae4:0x5de8b8,p);at<Byte*>(p,0)=at<Byte*>(state(b),sleep?0x14:4);return reinterpret_cast<Word>(p);}
 if(mode==2||mode==7)return at<Word>(state(b),mode==7?0x10:0);
 if(mode==3||mode==8){schema(b,reinterpret_cast<Byte*>(args[0]),reinterpret_cast<Byte*>(args[1]),mode==8);return 0;}
 Byte*p=reinterpret_cast<Byte*>(args[0]);if(mode==4)return actorUpdate(b,p);
 if(mode==9){sleepUpdate(b,p);return 0;}
 if(mode==10||mode==11){wake(b,p);clear(b,p+0x50);call<void>(b,0x282b78,p);if(mode==11)call<void>(b,0xb36928,p);return 0;}
 if(mode==12){at<Word>(p,0x38)=1;at<float>(p,0x3c)=1000;at<float>(p,0x40)=1000;return 0;}
 if(mode==13)return 0;
 if(mode==14){Byte*s=sleeping(b,p);if(s){if(at<Byte>(p,0xd0)){wake(b,s);call<void>(b,0x2708b4,s);}else{pauseRig(b,p,true);return 0;}}return call<Word>(b,IRIS_SLEEP_PLANT_UPDATE,p);}
 return 0;
}
