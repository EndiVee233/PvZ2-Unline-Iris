// Hypno-shroom owns a saved allegiance controller, without changing Zombie ABI.
using Byte=unsigned char;using Word=unsigned int;
template<class T>static T&at(Byte*p,Word o){return *reinterpret_cast<T*>(p+o);}
template<class R,class...A>static R call(Word b,Word p,A...a){return reinterpret_cast<R(*)(A...)>(b+p)(a...);}
template<class R,class...A>static R virt(Byte*p,Word o,A...a){return at<R(*)(Byte*,A...)>(at<Byte*>(p,0),o)(p,a...);}
static char*text(Word b,const char*s){char*r,a;call<void>(b,0xb75560,&r,s,&a);return r;}
static void drop(Word b,char*s){char a;if(__atomic_fetch_sub(reinterpret_cast<int*>(s-4),1,__ATOMIC_ACQ_REL)<=0)call<void>(b,0xb76c4c,s-12,&a);}
static void trace(Word b,const char*s,Word n){
#if IRIS_DARK_TRACE
 call<int>(b,0xe8c10,3,"IrisDark","Hypno %s value=%x",s,n);
#endif
}
#include "magnet.inc"
#include "zombie_types.inc"
static Byte*state(Word b){return reinterpret_cast<Byte*>(b+0xf80f40);}
static Word stub(Word b,Word i){return b+IRIS_HYPNO_STUB+i*40;}
// Grid: 50 zombie weak,58 target weak,60 previous time,64 attack timer,
// 68 original wave marker,6c state,70 animation,74 charged,
// 78/7c runtime vtables (deliberately excluded from serialization).
static void field(Word b,Byte*r,Byte*d,const char*n,Word offset,Word type){char*s=text(b,n);virt<void>(r,0x2c,d,&s,offset,type);drop(b,s);}
static void metadata(Word b,bool plant){
 Byte*s=state(b);Word i=plant?1:0;
 if(!at<Word>(s,i*4)){
  Byte*m=call<Byte*>(b,0xb363dc,40u);call<void>(b,0x894ca0,m);at<Byte*>(s,i*4)=m;
  call<void>(b,0x895608,m,plant?"PlantIrisHypno":"IrisHypnoAlly",call<Byte*>(b,plant?0x13b5a0:0x283394),stub(b,plant?16:1));
  Word size=plant?0xf8u:0x7cu;Byte*t=call<Byte*>(b,0xb363dc,size);
  for(Word o=0;o<size;o+=4)at<Word>(t,o)=*reinterpret_cast<Word*>(b+(plant?0xce4398:0xcdbc88)+o);
  at<Word>(t,0)=stub(b,plant?17:2);at<Byte*>(s,8+i*4)=t;
  if(plant){at<Word>(t,0x44)=stub(b,23);at<Word>(t,0x68)=stub(b,21);at<Word>(t,0x90)=stub(b,24);at<Word>(t,0x94)=stub(b,19);at<Word>(t,0x98)=stub(b,20);at<Word>(t,0xb0)=stub(b,22);}
  else{at<Word>(t,0x64)=stub(b,4);at<Word>(t,0x34)=stub(b,5);at<Word>(t,8)=stub(b,6);at<Word>(t,0xc)=stub(b,7);at<Word>(t,0x70)=stub(b,25);}
 }
 Byte*m=call<Byte*>(b,0x851728),*r=m?call<Byte*>(b,0x851920,m):nullptr;
 if(r&&!at<Word>(s,0x10+i*4)){at<Word>(s,0x10+i*4)=1;char*n=text(b,plant?"PlantIrisHypno":"IrisHypnoAlly");virt<void>(r,0xc,&n,stub(b,plant?18:3),plant?0x10u:0x80u,0u);drop(b,n);}
}
static void schema(Word b,Byte*r,Byte*d,bool plant){
 Byte*m=at<Byte*>(state(b),plant?4:0);at<Byte*>(m,0x24)=d;at<Byte*>(d,0x5c)=m;
 char*n=text(b,plant?"PlantFramework":"GridItem");Byte*p=virt<Byte*>(r,0x24,&n);drop(b,n);virt<void>(r,0x28,d,virt<Word>(p,0x34),0u);
 Word integer=virt<Word>(r,0x14,6u,4u),number=virt<Word>(r,0x14,8u,4u);
 if(plant){field(b,r,d,"iris_hypno_charged",8,integer);field(b,r,d,"iris_hypno_food_end",12,number);return;}
 n=text(b,"Zombie");Word z=virt<Word>(r,0x24,&n);drop(b,n);Word weak=virt<Word>(r,0x20,3u,z,0u,0u);
 field(b,r,d,"iris_hypno_zombie",0x50,weak);field(b,r,d,"iris_hypno_target",0x58,weak);
 field(b,r,d,"iris_hypno_previous",0x60,number);field(b,r,d,"iris_hypno_attack",0x64,number);
 field(b,r,d,"iris_hypno_wave_origin",0x68,integer);field(b,r,d,"iris_hypno_state",0x6c,integer);
 field(b,r,d,"iris_hypno_animation",0x70,integer);field(b,r,d,"iris_hypno_charged",0x74,integer);
}
static bool alive(Byte*z){return z&&at<Word>(z,0x48)-4u>=5u&&at<float>(z,0xb0)>0;}
static bool ordinaryGarg(Byte*z){Byte*m=virt<Byte*>(z,0);return m&&equalText(at<const char*>(m,4),"ZombieGargantuar");}
static bool impLanding(Byte*z){
 Word stage=at<Word>(z,0x48);if(stage!=13&&stage!=14)return false;
 Byte*m=virt<Byte*>(z,0);for(Word i=0;m&&i<32;++i,m=at<Byte*>(m,8))if(equalText(at<const char*>(m,4),"ZombieImp"))return true;
 return false;
}
static bool consumer(Byte*z){
 if(!zombieClass(z))return false;Byte*m=virt<Byte*>(z,0);
 for(Word i=0;m&&i<32;++i,m=at<Byte*>(m,8))if(equalText(at<const char*>(m,4),"ZombieGargantuar")||equalText(at<const char*>(m,4),"ZombieZombossMech"))return false;
 return true;
}
static Byte*controller(Word b,Byte*z){
 if(!z)return nullptr;int rect[4]={-8,-1,32,7};MagnetList list={};call<void>(b,0x248120,&list,4u,rect);Byte*result=nullptr;
 for(Byte**q=list.begin;q!=list.end;++q){Byte*p=*q;if(p&&virt<Byte*>(p,0)==at<Byte*>(state(b),0)&&weakObject(b,reinterpret_cast<Word*>(p+0x50))==z){result=p;break;}}
 if(list.begin)call<void>(b,0xb36928,list.begin);return result;
}
static void animation(Word b,Byte*z,const char*label){Byte*r=weakObject(b,reinterpret_cast<Word*>(z+0x40));if(!r)return;char*n=text(b,label);Word empty[6]={};call<void>(b,0x44d220,r,&n,3u,empty,empty);drop(b,n);}
static void bind(Word b,Byte*p,Byte*z){
 if(at<Byte*>(p,0x7c))return;Byte*original=at<Byte*>(z,0),*t=call<Byte*>(b,0xb363dc,0x300u);
 for(Word o=0;o<0x300;o+=4)at<Word>(t,o)=at<Word>(original,o);
 at<Byte*>(p,0x78)=original;at<Byte*>(p,0x7c)=t;at<Word>(t,0x64)=stub(b,8);at<Word>(t,0x3c)=stub(b,9);at<Byte*>(z,0)=t;
 if(ordinaryGarg(z)){at<Word>(t,0x198)=stub(b,28);at<Word>(t,0x19c)=stub(b,29);}
 at<Word>(z,0xac)=1;at<Word>(p,0x70)=0;trace(b,"ally rebound",at<Word>(z,8));
}
static void unbind(Word b,Byte*p){Byte*z=weakObject(b,reinterpret_cast<Word*>(p+0x50));Byte*t=at<Byte*>(p,0x7c);if(z&&t&&at<Byte*>(z,0)==t)at<Byte*>(z,0)=at<Byte*>(p,0x78);if(t)call<void>(b,0xb36928,t);at<Word>(p,0x78)=at<Word>(p,0x7c)=0;}
static void sync(Word b,Byte*p,Byte*z){
 float pos[3]={at<float>(z,0x10),at<float>(z,0x14),0};virt<void>(p,0x58,pos);
 int col=int((pos[0]-200)/64);at<Word>(p,0x44)=Word(col);Word row=0;float distance=100000;
 for(Word i=0;i<5;++i){float d=float(call<int>(b,0x1814a4,battleBoard(b),i))-pos[1];if(d<0)d=-d;if(d<distance){distance=d;row=i;}}at<Word>(p,0x48)=row;
 at<float>(p,0x40)=at<float>(z,0xb0)+(at<float>(z,0x34)>0?at<float>(z,0x34):0);at<Word>(p,0x38)=alive(z)?3u:0u;
}
static void convert(Word b,Byte*z,bool charged){
 if(!alive(z)||controller(b,z))return;
 Byte*m=virt<Byte*>(z,0);for(Word i=0;m&&i<32;++i,m=at<Byte*>(m,8))if(equalText(at<const char*>(m,4),"ZombieZombossMech"))return;
 if(charged&&!ordinaryGarg(z)){
  trace(b,"charged type lookup",0);
  Word type[2]={};if(!findZombieType(b,type,"ZombieGargantuar",true)){trace(b,"charged giant type unavailable",0);return;}
  trace(b,"charged giant type found",type[0]);
  Byte*giant=call<Byte*>(b,0x181a30,battleBoard(b),type,0u);call<void>(b,0x13dea0,type,0u,0u,0u);if(!giant)return;
  trace(b,"charged giant created",at<Word>(giant,8));
  float pos[3]={at<float>(z,0x10),at<float>(z,0x14),0};virt<void>(giant,0x58,pos);call<void>(b,0x2708b4,z);z=giant;
 }
 char*n=text(b,"iris_hypno_ally");Byte*p=call<Byte*>(b,0x17a8c4,battleBoard(b),&n,0u,0u);drop(b,n);if(!p)return;
 call<void>(b,0x13dea0,p+0x50,0u,at<Word>(z,8),at<Word>(z,0xc));at<Word>(p,0x68)=at<Word>(z,0xc0);at<Word>(p,0x74)=charged;at<float>(p,0x60)=battleTime(b);
 at<float>(z,0xb0)=at<float>(z,0xb4);if(at<Word>(z,0x30)&&at<float>(z,0xbc)>0)at<float>(z,0x34)=at<float>(z,0xbc);
 bind(b,p,z);sync(b,p,z);magnetSound(b,z,charged?"Play_Plant_DarkAges_HypnoShroom_Transform_PlantFood":"Play_Plant_DarkAges_HypnoShroom_Transform");trace(b,charged?"charged conversion":"conversion",at<Word>(z,8));
}
static Byte*enemy(Word b,Byte*z){
 int rect[4]={0,0,17,5};MagnetList list={};call<void>(b,0x248120,&list,2u,rect);Byte*best=nullptr;float distance=100000;
 for(Byte**q=list.begin;q!=list.end;++q){Byte*t=*q;if(t==z||!alive(t)||!virt<bool>(t,0x3c,1u))continue;float dy=at<float>(t,0x14)-at<float>(z,0x14);if(dy< -30||dy>30)continue;
  float dx=at<float>(t,0x10)-at<float>(z,0x10);if(dx< -20||dx>distance)continue;best=t;distance=dx;}
 if(list.begin)call<void>(b,0xb36928,list.begin);return best;
}
static void allyUpdate(Word b,Byte*z){
 Byte*p=controller(b,z);if(!p){call<void>(b,0x5dfc80,z);return;}
 if(!alive(z)){Byte*t=at<Byte*>(p,0x78);if(t)at<void(*)(Byte*)>(t,0x64)(z);at<Word>(p,0x38)=0;return;}
 Byte*board=battleBoard(b);if(!board||at<Word>(board,0xa8)!=5||at<Byte>(board,0x671)||call<bool>(b,0x1872a8,board))return;
 if(ordinaryGarg(z)||at<float>(z,0x18)>1.0f||impLanding(z)){
  Byte*v=at<Byte*>(p,0x78);at<void(*)(Byte*)>(v,0x64)(z);sync(b,p,z);if(at<float>(z,0x18)>1.0f)at<Word>(p,0x38)=0;return;
 }
 Byte*t=enemy(b,z);bool eating=t&&at<float>(t,0x10)-at<float>(z,0x10)<=42;Word anim=eating?2u:1u;
 if(at<Word>(p,0x70)!=anim){animation(b,z,eating?"eat":"walk");at<Word>(p,0x70)=anim;}
 // Reuse original locomotion and condition ticks, while the hostile state
 // machine is suspended. AC=1 mirrors the authored walking delta to the right.
 Word a=at<Word>(z,0x68),c=at<Word>(z,0x70);at<Word>(z,0x68)=at<Word>(z,0x70)=0;
 if(eating)at<Word>(z,0xa8)&=~1u;else at<Word>(z,0xa8)|=1u;
 call<void>(b,0x5dfc80,z);at<Word>(z,0x68)=a;at<Word>(z,0x70)=c;
 float now=battleTime(b),dt=now-at<float>(p,0x60);if(dt<0||dt>0.2f)dt=0;at<float>(p,0x60)=now;
 if(eating&&alive(z)&&at<float>(z,0xa0)>0){
  at<float>(p,0x64)+=dt*at<float>(z,0xa0);if(at<float>(p,0x64)>=0.5f){at<float>(p,0x64)-=0.5f;
   Byte*type=weakObject(b,reinterpret_cast<Word*>(z+0x38));Byte*props=type?call<Byte*>(b,0x6826ec,type):nullptr;
   float dps=props?at<float>(props,0x1c):100.0f;
   struct{Byte*source;float amount;Word flags;Word conditions[3];}hit={z,dps*0.5f,0x20000u,{}};virt<void>(t,0x34,&hit);trace(b,"ally bite",Word(dps*0.5f));}
 }else at<float>(p,0x64)=0;
 sync(b,p,z);if(at<float>(z,0x10)>1300){at<Word>(p,0x38)=0;call<void>(b,0x2708b4,z);}
}
static void gridUpdate(Word b,Byte*p){Byte*z=weakObject(b,reinterpret_cast<Word*>(p+0x50));if(!z){call<void>(b,0x2708b4,p);return;}bind(b,p,z);sync(b,p,z);}
static Word remainingEnemies(Word b){int rect[4]={-8,-1,40,7};MagnetList list={};call<void>(b,0x248120,&list,2u,rect);Word n=0;
 for(Byte**q=list.begin;q!=list.end;++q)if(alive(*q)&&!controller(b,*q))++n;if(list.begin)call<void>(b,0xb36928,list.begin);return n;}
extern "C" __attribute__((section(".text.entry")))
Word iris_hypno(Word b,Word*args,Word mode){
 if(mode==0||mode==15){call<void>(b,mode==0?IRIS_HYPNO_REGISTER:IRIS_HYPNO_REGISTER_PLANT);metadata(b,mode==15);at<Word>(state(b),0x18)=stub(b,27);at<Word>(state(b),0x1c)=stub(b,10);return 0;}
 if(mode==1||mode==16){bool plant=mode==16;Word size=plant?0x10u:0x80u;Byte*p=call<Byte*>(b,0xb363dc,size);for(Word o=0;o<size;o+=4)at<Word>(p,o)=0;if(!plant)call<void>(b,0x282ae4,p);at<Byte*>(p,0)=at<Byte*>(state(b),plant?12:8);return reinterpret_cast<Word>(p);}
 if(mode==2||mode==17)return at<Word>(state(b),mode==2?0:4);
 if(mode==3||mode==18){schema(b,reinterpret_cast<Byte*>(args[0]),reinterpret_cast<Byte*>(args[1]),mode==18);return 0;}
 Byte*p=reinterpret_cast<Byte*>(args[0]);
 if(mode==4){gridUpdate(b,p);return 0;}
 if(mode==5){Byte*z=weakObject(b,reinterpret_cast<Word*>(p+0x50)),*hit=reinterpret_cast<Byte*>(args[1]);Byte*source=at<Byte*>(hit,0);if(z&&zombieClass(source)&&!controller(b,source)){virt<void>(z,0x34,hit);sync(b,p,z);}return 0;}
 if(mode==6||mode==7){unbind(b,p);call<void>(b,0x13dea0,p+0x50,0u,0u,0u);call<void>(b,0x13dea0,p+0x58,0u,0u,0u);call<void>(b,0x282b78,p);if(mode==7)call<void>(b,0xb36928,p);return 0;}
 if(mode==8){allyUpdate(b,p);return 0;}
 if(mode==9||mode==23)return 0;
 if(mode==10){convert(b,p,false);return 0;}
 if(mode==27)return controller(b,p)!=nullptr;
 if(mode==28){Byte*t=enemy(b,p);return t&&at<float>(t,0x10)-at<float>(p,0x10)<=42?reinterpret_cast<Word>(t):0;}
 if(mode==29)return 0;
 if(mode==24)return 1;
 if(mode==11){if(call<bool>(b,IRIS_HYPNO_WINCON))return 1;return remainingEnemies(b)==0;}
 if(mode==12){Byte*hit=reinterpret_cast<Byte*>(args[1]),*source=at<Byte*>(hit,0);bool friendly=controller(b,p)!=nullptr;
  if(friendly&&source&&(!zombieClass(source)||controller(b,source)))return 0;
  return call<Word>(b,IRIS_HYPNO_DAMAGE,p,hit);
 }
 if(mode==13){int rect[4]={-8,-1,32,7};MagnetList list={};if(p==battleBoard(b)){call<void>(b,0x248120,&list,4u,rect);for(Byte**q=list.begin;q!=list.end;++q)if(*q&&virt<Byte*>(*q,0)==at<Byte*>(state(b),0))gridUpdate(b,*q);if(list.begin)call<void>(b,0xb36928,list.begin);}return call<Word>(b,IRIS_HYPNO_UPDATE,p);}
 if(mode==19){call<void>(b,0x3ba164,p);at<Word>(p,8)=1;Byte*plant=at<Byte*>(p,4);at<Word>(plant,0x48)=5;at<float>(p,12)=battleTime(b)+0.15f;magnetAnimation(b,p,"plantfood_on",false);return 0;}
 if(mode==20){call<void>(b,0x3ba2c0,p);at<Word>(at<Byte*>(p,4),0x48)=4;magnetAnimation(b,p,"plantfood",true);return 0;}
 if(mode==21)return 0;
 if(mode==22){Byte*f=reinterpret_cast<Byte*>(args[1]),*plant=at<Byte*>(f,4),*hit=reinterpret_cast<Byte*>(args[2]),*z=at<Byte*>(hit,0);
  trace(b,"plant damage HP bits",plant?at<Word>(plant,0x4c):0);trace(b,"plant damage amount bits",at<Word>(hit,4));trace(b,"plant damage flags",at<Word>(hit,8));
  if(plant&&at<float>(hit,4)>0&&at<float>(plant,0x4c)>=0&&at<float>(plant,0x4c)<=at<float>(hit,4)&&consumer(z))convert(b,z,at<Word>(f,8)!=0);
  return call<Word>(b,0x13f310,p,f,hit);
 }
 if(mode==25){at<Word>(p,0x38)=0;return 0;}
 if(mode==26){Word count=call<Word>(b,IRIS_HYPNO_COUNT);int rect[4]={-8,-1,40,7};MagnetList list={};call<void>(b,0x248120,&list,2u,rect);
  for(Byte**q=list.begin;q!=list.end;++q)if(count&&alive(*q)&&controller(b,*q))--count;if(list.begin)call<void>(b,0xb36928,list.begin);return count;}
 return 0;
}
