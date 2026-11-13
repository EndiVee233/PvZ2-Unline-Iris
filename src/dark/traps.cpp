// Iris-owned, serializable ground effects for the two Chinese mushrooms.
// Never instantiate Aster objects: its GridItem/Actor layouts differ.
using Byte=unsigned char;using Word=unsigned int;
template<class T>static T&at(Byte*p,Word o){return *reinterpret_cast<T*>(p+o);}
template<class R,class...A>static R call(Word b,Word p,A...a){return reinterpret_cast<R(*)(A...)>(b+p)(a...);}
template<class R,class...A>static R virt(Byte*p,Word o,A...a){return at<R(*)(Byte*,A...)>(at<Byte*>(p,0),o)(p,a...);}
static char*text(Word b,const char*s){char*r,a;call<void>(b,0xb75560,&r,s,&a);return r;}
static void drop(Word b,char*s){char a;if(__atomic_fetch_sub(reinterpret_cast<int*>(s-4),1,__ATOMIC_ACQ_REL)<=0)call<void>(b,0xb76c4c,s-12,&a);}
static void trace(Word b,const char*s,Word n){
#if IRIS_DARK_TRACE
 call<int>(b,0xe8c10,3,"IrisDark","Trap %s value=%x",s,n);
#endif
}
#include "magnet.inc"
// 50 kind,54 phase,58 start,5c previous,60 consumed,64 effect weak,
// 6c next attack,70 phase-start,74 source weak,80 five sinking records.
static Byte*state(Word b){return reinterpret_cast<Byte*>(b+0xf80300);}
static Word stub(Word b,Word mode){return b+IRIS_TRAP_STUB+mode*40;}
static void registerTraps(Word b){
 Byte*s=state(b);Byte*parent=call<Byte*>(b,0x283394);
 if(!at<Word>(s,0))for(Word i=0;i<2;++i){
  Byte*m=call<Byte*>(b,0xb363dc,40u);call<void>(b,0x894ca0,m);at<Byte*>(s,i*4)=m;
  call<void>(b,0x895608,m,i?"IrisFireWall":"IrisIceHole",parent,stub(b,1+i));
  Byte*t=call<Byte*>(b,0xb363dc,0x7cu);
  for(Word o=0;o<0x7c;o+=4)at<Word>(t,o)=*reinterpret_cast<Word*>(b+0xcdbc88+o);
  at<Word>(t,0)=stub(b,3+i);at<Word>(t,8)=stub(b,7);at<Word>(t,0xc)=stub(b,8);
  at<Word>(t,0x3c)=stub(b,9);at<Word>(t,0x64)=stub(b,10);at<Word>(t,0x70)=stub(b,11);
  at<Byte*>(s,8+i*4)=t;
 }
 Byte*m=call<Byte*>(b,0x851728);Byte*r=m?call<Byte*>(b,0x851920,m):nullptr;
 if(!r||at<Word>(s,0x10))return;at<Word>(s,0x10)=1;
 for(Word i=0;i<2;++i){char*n=text(b,i?"IrisFireWall":"IrisIceHole");virt<void>(r,0xc,&n,stub(b,5+i),0xd0u,0u);drop(b,n);}
}
static void field(Word b,Byte*r,Byte*d,const char*name,Word offset,Word type){char*n=text(b,name);virt<void>(r,0x2c,d,&n,offset,type);drop(b,n);}
static Word weakType(Word b,Byte*r,const char*name){char*n=text(b,name);Word t=virt<Word>(r,0x24,&n);drop(b,n);return virt<Word>(r,0x20,3u,t,0u,0u);}
static void schema(Word b,Byte*r,Byte*d,Word kind){
 Byte*m=at<Byte*>(state(b),kind*4);at<Byte*>(m,0x24)=d;at<Byte*>(d,0x5c)=m;
 char*n=text(b,"GridItem");Byte*p=virt<Byte*>(r,0x24,&n);drop(b,n);virt<void>(r,0x28,d,virt<Word>(p,0x34),0u);
 Word integer=virt<Word>(r,0x14,6u,4u),number=virt<Word>(r,0x14,8u,4u);
 for(Word i=0;i<5;++i)field(b,r,d,i==0?"iris_kind":i==1?"iris_phase":i==2?"iris_start":i==3?"iris_previous":"iris_consumed",0x50+i*4,(i==2||i==3)?number:integer);
 field(b,r,d,"iris_next_attack",0x6c,number);field(b,r,d,"iris_phase_start",0x70,number);
 field(b,r,d,"iris_source",0x74,weakType(b,r,"Plant"));Word zombie=weakType(b,r,"Zombie");
 field(b,r,d,"iris_effect",0x64,weakType(b,r,"Effect_PopAnim"));
 // Combat timers, hit count and in-progress sinks survive battle saves.
 for(Word i=0;i<5;++i){char label[]="iris_sink0w";label[9]=char('0'+i);
  field(b,r,d,label,0x80+i*16,zombie);label[10]='t';field(b,r,d,label,0x88+i*16,number);
  label[10]='z';field(b,r,d,label,0x8c+i*16,number);}
}
static Byte*visual(Word b,Byte*p,const char*label){
 Byte*e=weakObject(b,reinterpret_cast<Word*>(p+0x64));
 if(!e){Byte*holder=**reinterpret_cast<Byte***>(b+0xd008bc);if(!holder)return nullptr;
  char*n=text(b,at<Word>(p,0x50)?"POPANIM_EFFECTS_FIRESHROOM_SKILL":"POPANIM_EFFECTS_ICE_HOLE");Word w[2]={};
  at<void(*)(Word*,Byte*,Word,char**,Word)>(at<Byte*>(holder,0),8)(w,holder,call<Word>(b,0x129ae0),&n,0u);drop(b,n);
  Byte*res=weakObject(b,w);call<void>(b,0x13dea0,w,0u,0u,0u);if(!res)return nullptr;
  e=call<Byte*>(b,0x1809a8,battleBoard(b));if(!e)return nullptr;
  call<void>(b,0x23a354,e,res,0u);call<void>(b,0x23a814,e,0u);
  call<void>(b,0x13dea0,p+0x64,0u,at<Word>(e,8),at<Word>(e,0xc));
 }
 char*n=text(b,label);call<void>(b,0x23aa6c,e,&n,0u);drop(b,n);
 float pos[3]={at<float>(p,0x10)-(at<Word>(p,0x50)?100.0f:110.0f),at<float>(p,0x14)-(at<Word>(p,0x50)?120.0f:130.0f),0};
 call<void>(b,0x4e6bb8,e,pos,0xffffffffu);return e;
}
static void removeVisual(Word b,Byte*p){Byte*e=weakObject(b,reinterpret_cast<Word*>(p+0x64));if(e)call<void>(b,0x2708b4,e);call<void>(b,0x13dea0,p+0x64,0u,0u,0u);}
static bool heavy(Byte*z){
 Byte*t=virt<Byte*>(z,0);for(Word i=0;t&&i<32;++i,t=at<Byte*>(t,8)){const char*n=at<const char*>(t,4);
  if(equalText(n,"ZombieGargantuar")||equalText(n,"ZombieGargantuarMech")||equalText(n,"ZombieZombossMech")||equalText(n,"ZombieDarkKing")||equalText(n,"ZombieIrisKing")||equalText(n,"ZombieBull"))return true;
 }return false;
}
static void sinks(Word b,Byte*p,float time,bool finish){
 Byte*source=weakObject(b,reinterpret_cast<Word*>(p+0x74));
 for(Word i=0;i<5;++i){Byte*s=p+0x80+i*16;Byte*z=weakObject(b,reinterpret_cast<Word*>(s));if(!z)continue;
  float age=time-at<float>(s,8);if(finish||age>=0.75f){
   // Native kill preserves rewards, kill statistics and wave bookkeeping.
   at<float>(z,0x18)=at<float>(s,0xc);call<void>(b,0x5e147c,z,source);
   call<void>(b,0x13dea0,s,0u,0u,0u);continue;
  }
  float point[3]={at<float>(p,0x10),at<float>(p,0x14)-10,at<float>(s,0xc)-age*100};virt<void>(z,0x58,point);
 }
}
static void attack(Word b,Byte*p,float time){
 bool fire=at<Word>(p,0x50);int row=int(at<Word>(p,0x48)),col=int(at<Word>(p,0x44));
 int rect[4]={col-2,row-1,5,3};MagnetList list={};call<void>(b,0x248120,&list,2u,rect);
 Byte*source=weakObject(b,reinterpret_cast<Word*>(p+0x74));
 for(Byte**q=list.begin;q!=list.end;++q){Byte*z=*q;
  if(!zombieClass(z)||!virt<bool>(z,0x3c,1u))continue;
  float dx=at<float>(z,0x10)-at<float>(p,0x10),dy=at<float>(z,0x14)-at<float>(p,0x14);
  if(fire){if(dx< -32||dx>32||dy< -38||dy>38)continue;
   // Iris's reflected fire flag is 0x80 (Aster uses 0x200).
   struct{Byte*source;float amount;Word flags;Word conditions[3];}damage={source,300,0x80,{}};virt<void>(z,0x34,&damage);
   trace(b,"fire wall hit",300);
  }else{
   if(dx*dx+dy*dy>92.16f*92.16f||heavy(z)||at<Word>(p,0x60)>=5)continue;
   bool taken=false;for(Word i=0;i<5;++i){Byte*s=p+0x80+i*16;if(at<Word>(s,0)==at<Word>(z,8)&&at<Word>(s,4)==at<Word>(z,0xc))taken=true;}
   if(taken)continue;
   for(Word i=0;i<5;++i){Byte*s=p+0x80+i*16;if(at<Word>(s,0)||at<Word>(s,4))continue;
    call<void>(b,0x13dea0,s,0u,at<Word>(z,8),at<Word>(z,0xc));at<float>(s,8)=time;at<float>(s,0xc)=at<float>(z,0x18);
    call<void>(b,0x5e0ed8,z,2u,0.8f);++at<Word>(p,0x60);trace(b,"ice hole consumed",at<Word>(p,0x60));break;
   }
  }
 }
 if(list.begin)call<void>(b,0xb36928,list.begin);
}
static void update(Word b,Byte*p){
 Byte*board=battleBoard(b);if(!board||at<Word>(board,0xa8)!=5||call<bool>(b,0x1872a8,board))return;
 float time=battleTime(b),age=time-at<float>(p,0x58);bool fire=at<Word>(p,0x50);Word phase=at<Word>(p,0x54);
 if(!phase){trace(b,"first update",at<Word>(p,0x50));at<Word>(p,0x54)=1;at<float>(p,0x58)=time;age=0;visual(b,p,"plantfood_in");phase=1;}
 float intro=fire?40.0f/30:36.0f/30;
 if(phase==1&&age>=intro){at<Word>(p,0x54)=phase=2;visual(b,p,"plantfood");at<float>(p,0x6c)=time;}
 if(!weakObject(b,reinterpret_cast<Word*>(p+0x64)))visual(b,p,phase==1?"plantfood_in":phase==2?"plantfood":"plantfood_out");
 if(!fire)sinks(b,p,time,false);
 if(phase==2&&time>=at<float>(p,0x6c)){attack(b,p,time);at<float>(p,0x6c)=time+(fire?2.0f:0.05f);}
 if(phase==2&&age>=(fire?8.0f:142.0f/30)){
  if(fire){at<Word>(p,0x54)=3;at<float>(p,0x70)=time;visual(b,p,"plantfood_out");}
  else{sinks(b,p,time,true);removeVisual(b,p);call<void>(b,0x2708b4,p);}
 }
 if(fire&&phase==3&&time-at<float>(p,0x70)>=25.0f/30){removeVisual(b,p);call<void>(b,0x2708b4,p);}
 at<float>(p,0x5c)=time;
}
extern "C" __attribute__((section(".text.entry")))
Word iris_traps(Word b,Word*args,Word mode){
 if(mode==0){call<void>(b,IRIS_TRAP_REGISTER);registerTraps(b);return 0;}
 if(mode==1||mode==2){Byte*p=call<Byte*>(b,0xb363dc,0xd0u);for(Word o=0;o<0xd0;o+=4)at<Word>(p,o)=0;call<void>(b,0x282ae4,p);at<Byte*>(p,0)=at<Byte*>(state(b),8+(mode-1)*4);at<Word>(p,0x50)=mode-1;trace(b,"instance created",mode-1);return reinterpret_cast<Word>(p);}
 if(mode==3||mode==4)return at<Word>(state(b),(mode-3)*4);
 if(mode==5||mode==6){schema(b,reinterpret_cast<Byte*>(args[0]),reinterpret_cast<Byte*>(args[1]),mode-5);return 0;}
 Byte*p=reinterpret_cast<Byte*>(args[0]);
 if(mode==7||mode==8){removeVisual(b,p);call<void>(b,0x13dea0,p+0x74,0u,0u,0u);for(Word i=0;i<5;++i)call<void>(b,0x13dea0,p+0x80+i*16,0u,0u,0u);call<void>(b,0x282b78,p);if(mode==8)call<void>(b,0xb36928,p);return 0;}
 if(mode==9)return 0;
 if(mode==10){update(b,p);return 0;}
 if(mode==11){at<Word>(p,0x38)=1;at<float>(p,0x3c)=1000;at<float>(p,0x40)=1000;at<float>(p,0x58)=battleTime(b);trace(b,"initialized",at<Word>(p,0x50));return 0;}
 return 0;
}
