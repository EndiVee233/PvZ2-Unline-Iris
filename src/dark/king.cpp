// Dark Ages King's stationary intro/knighting behavior, without ranks.
using Byte=unsigned char;using Word=unsigned int;
template<class T>static T&at(Byte*p,Word o){return *reinterpret_cast<T*>(p+o);}
template<class R,class...A>static R call(Word b,Word p,A...a){return reinterpret_cast<R(*)(A...)>(b+p)(a...);}
template<class R,class...A>static R virt(Byte*p,Word o,A...a){return at<R(*)(Byte*,A...)>(at<Byte*>(p,0),o)(p,a...);}
static char*text(Word b,const char*s){char*r,a;call<void>(b,0xb75560,&r,s,&a);return r;}
static void drop(Word b,char*s){char a;if(__atomic_fetch_sub(reinterpret_cast<int*>(s-4),1,__ATOMIC_ACQ_REL)<=0)call<void>(b,0xb76c4c,s-12,&a);}
static void trace(Word b,const char*s,Word n){
#if IRIS_DARK_TRACE
 call<int>(b,0xe8c10,3,"IrisDark","King %s value=%x",s,n);
#endif
}
#include "magnet.inc"
static Byte*state(Word b){return reinterpret_cast<Byte*>(b+0xf80e40);}
static Word stub(Word b,Word mode){return b+IRIS_KING_STUB+mode*40;}
// 190 phase,194 phase start,198 next knighting,19c target weak,
// 1a4 previous time,1a8/1ac stationary board position,1b0 landed.
static void metadata(Word b){
 Byte*s=state(b),*parent=call<Byte*>(b,0x5e8c4c);
 if(!at<Word>(s,0)){
  Byte*m=call<Byte*>(b,0xb363dc,40u);call<void>(b,0x894ca0,m);at<Byte*>(s,0)=m;
  call<void>(b,0x895608,m,"ZombieIrisKing",parent,stub(b,1));Byte*t=call<Byte*>(b,0xb363dc,0x1acu);
  for(Word o=0;o<0x1ac;o+=4)at<Word>(t,o)=*reinterpret_cast<Word*>(b+0xced208+o);
  at<Word>(t,0)=stub(b,2);at<Word>(t,0x64)=stub(b,4);at<Word>(t,0x34)=stub(b,8);at<Word>(t,8)=stub(b,6);at<Word>(t,0xc)=stub(b,7);at<Byte*>(s,4)=t;
  // Aster's King has a whole-body death. Iris's generic rig has no detached
  // head/arm pieces for this model, so skip the normal 2/3 and 1/3 stages.
  at<Word>(t,0x190)=stub(b,9);at<Word>(t,0x194)=stub(b,9);at<Word>(t,0xb8)=stub(b,9);
 }
 Byte*m=call<Byte*>(b,0x851728),*r=m?call<Byte*>(b,0x851920,m):nullptr;
 if(r&&!at<Word>(s,8)){at<Word>(s,8)=1;char*n=text(b,"ZombieIrisKing");virt<void>(r,0xc,&n,stub(b,3),0x1b4u,0u);drop(b,n);}
}
static void field(Word b,Byte*r,Byte*d,const char*name,Word offset,Word type){char*n=text(b,name);virt<void>(r,0x2c,d,&n,offset,type);drop(b,n);}
static void schema(Word b,Byte*r,Byte*d){
 Byte*m=at<Byte*>(state(b),0);at<Byte*>(m,0x24)=d;at<Byte*>(d,0x5c)=m;
 char*n=text(b,"Zombie");Byte*p=virt<Byte*>(r,0x24,&n);drop(b,n);virt<void>(r,0x28,d,virt<Word>(p,0x34),0u);
 Word number=virt<Word>(r,0x14,8u,4u),integer=virt<Word>(r,0x14,6u,4u);
 field(b,r,d,"iris_king_phase",0x190,integer);field(b,r,d,"iris_king_phase_start",0x194,number);field(b,r,d,"iris_king_next_knighting",0x198,number);
 n=text(b,"Zombie");Word type=virt<Word>(r,0x24,&n);drop(b,n);field(b,r,d,"iris_king_target",0x19c,virt<Word>(r,0x20,3u,type,0u,0u));
 field(b,r,d,"iris_king_last_time",0x1a4,number);field(b,r,d,"iris_king_anchor_x",0x1a8,number);field(b,r,d,"iris_king_anchor_y",0x1ac,number);
 field(b,r,d,"iris_king_landed",0x1b0,integer);
}
static void animation(Word b,Byte*z,const char*label,bool loop){Byte*r=weakObject(b,reinterpret_cast<Word*>(z+0x40));if(!r)return;char*n=text(b,label);Word empty[6]={};call<void>(b,loop?0x44d220:0x44d0b0,r,&n,loop?3u:0u,empty,empty);drop(b,n);}
static int rowOf(Word b,float y){int row=0;float best=100000;Byte*board=battleBoard(b);for(int i=0;i<5;++i){float d=float(call<int>(b,0x1814a4,board,i))-y;if(d<0)d=-d;if(d<best){best=d;row=i;}}return row;}
static bool begin(Word b,Byte*z){
 bool taken[5]={};int rect[4]={0,0,16,5};MagnetList list={};call<void>(b,0x248120,&list,2u,rect);
 for(Byte**q=list.begin;q!=list.end;++q){Byte*p=*q;if(!p||p==z||at<Word>(p,0x48)-4u<5u)continue;if(virt<Byte*>(p,0)==at<Byte*>(state(b),0))taken[rowOf(b,at<float>(p,0x14))]=true;}
 if(list.begin)call<void>(b,0xb36928,list.begin);int row=rowOf(b,at<float>(z,0x14));
 if(taken[row]){row=-1;Word n=0;for(int i=0;i<5;++i)if(!taken[i]&&call<Word>(b,0x7a3e90,++n)==0)row=i;}
 if(row<0){call<void>(b,0x5e147c,z,0u);return false;}
 Byte*board=battleBoard(b);at<float>(z,0x1a8)=float(call<int>(b,0x17d518,board,8));at<float>(z,0x1ac)=float(call<int>(b,0x1814a4,board,row));
 float point[3]={at<float>(z,0x1a8),at<float>(z,0x1ac),at<float>(z,0x18)};virt<void>(z,0x58,point);animation(b,z,"intro",false);return true;
}
static bool isClass(Byte*p,const char*name){Byte*t=p?virt<Byte*>(p,0):nullptr;for(Word i=0;t&&i<32;++i,t=at<Byte*>(t,8))if(equalText(at<const char*>(t,4),name))return true;return false;}
static void land(Word b,Byte*z){
 at<Word>(z,0x1b0)=1;int rect[4]={8,rowOf(b,at<float>(z,0x14)),1,1};MagnetList list={};call<void>(b,0x248120,&list,5u,rect);
 for(Byte**q=list.begin;q!=list.end;++q){Byte*p=*q;
  if(isClass(p,"Plant")){if(at<Word>(p,0x48)!=3)call<void>(b,0x39ece8,p,0u);}
  else if(isClass(p,"GridItem")){struct{Byte*source;float amount;Word flags;Word conditions[3];}damage={z,1000000000.0f,0,{}};virt<void>(p,0x34,&damage);}
 }
 if(list.begin)call<void>(b,0xb36928,list.begin);trace(b,"landed in column eight",Word(rect[1]));
}
static bool eligible(Word b,Byte*z){
 if(!zombieClass(z)||!virt<bool>(z,0x3c,1u)||at<Word>(z,0x30)==9)return false;
 Byte*t=weakObject(b,reinterpret_cast<Word*>(z+0x38));const char*n=t?at<const char*>(t,4):nullptr;
 return equalText(n,"dark")||equalText(n,"dark_armor1")||equalText(n,"dark_armor2")||equalText(n,"dark_armor3");
}
static Byte*target(Word b,Byte*z){
 Byte*board=battleBoard(b);int col=8,row=0;float best=100000;
 for(int i=0;i<16;++i){float d=float(call<int>(b,0x17d518,board,i))-at<float>(z,0x10);if(d<0)d=-d;if(d<best){best=d;col=i;}}
 best=100000;for(int i=0;i<5;++i){float d=float(call<int>(b,0x1814a4,board,i))-at<float>(z,0x14);if(d<0)d=-d;if(d<best){best=d;row=i;}}
 int rect[4]={col-3,row-1,4,3};MagnetList list={};call<void>(b,0x248120,&list,2u,rect);Byte*chosen=nullptr;best=100000;
 for(Byte**q=list.begin;q!=list.end;++q)if(eligible(b,*q)&&at<float>(*q,0x10)<best){best=at<float>(*q,0x10);chosen=*q;}
 if(list.begin)call<void>(b,0xb36928,list.begin);return chosen;
}
static void crown(Word b,Byte*z){
 trace(b,"crown callback enter",at<Word>(z,8));
 Byte*t=weakObject(b,reinterpret_cast<Word*>(z+0x19c));if(!eligible(b,t))t=target(b,z);
 trace(b,"crown candidate",reinterpret_cast<Word>(t));
 if(t){at<Word>(t,0x30)=9;at<float>(t,0x34)=at<float>(t,0xbc)=1600;
  Byte*r=weakObject(b,reinterpret_cast<Word*>(t+0x40));if(r){trace(b,"crown rig before",at<Word>(r,0));virt<void>(r,0xe4,9u);trace(b,"crown rig helmet set",9);virt<void>(r,0xf4);trace(b,"crown rig refreshed",9);}
  trace(b,"crowned zombie",at<Word>(t,8));
 }call<void>(b,0x13dea0,z+0x19c,0u,0u,0u);
}
static bool surrender(Word b,Byte*z){
 Byte*board=battleBoard(b),*waves=call<Byte*>(b,0x179f5c,board);
 // Both versions use state 4 for a completed native WaveManager. Do not
 // surrender between waves merely because there are no current targets.
 if(!waves||!call<bool>(b,0x555e7c,waves))return false;
 int rect[4]={0,0,16,5};MagnetList list={};call<void>(b,0x248120,&list,2u,rect);bool other=false;
 for(Byte**q=list.begin;q!=list.end;++q){Byte*p=*q;if(!zombieClass(p)||at<Word>(p,0x48)-4u<5u||at<Word>(p,0x48)-9u<2u)continue;
  if(virt<Byte*>(p,0)!=at<Byte*>(state(b),0)){other=true;break;}
 }
 if(list.begin)call<void>(b,0xb36928,list.begin);if(other)return false;
 trace(b,"surrender after final wave",at<Word>(z,8));call<void>(b,0x5e147c,z,0u);return true;
}
static Word planting(Word b,Byte*board,int*cell,Word*type){
 if(cell&&cell[0]==8&&cell[1]>=0&&cell[1]<5){
  Byte*t=weakObject(b,type);const char*n=t?at<const char*>(t,4):nullptr;
  bool instant=equalText(n,"cherry_bomb")||equalText(n,"jalapeno")||equalText(n,"powerlily")||equalText(n,"iceburg")||equalText(n,"empea")||equalText(n,"powerplant")||equalText(n,"goldleaf")||equalText(n,"grapeshot");
  if(!instant){int rect[4]={8,cell[1],1,1};MagnetList list={};call<void>(b,0x248120,&list,2u,rect);bool blocked=false;
   for(Byte**q=list.begin;q!=list.end;++q){Byte*p=*q;if(p&&at<Word>(p,0x48)-4u>=5u&&virt<Byte*>(p,0)==at<Byte*>(state(b),0)){blocked=true;break;}}
   if(list.begin)call<void>(b,0xb36928,list.begin);
   if(blocked)return 10; // Iris's existing invalid-tile reason and UI.
  }
 }
 return call<Word>(b,IRIS_KING_PLANTING_ORIGINAL,board,cell,type);
}
static Word update(Word b,Byte*z){
 Byte*board=battleBoard(b);if(!board||at<Word>(board,0xa8)!=5||call<bool>(b,0x1872a8,board))return 0;
 float now=battleTime(b),delta=now-at<float>(z,0x1a4);if(delta<0||delta>1)delta=0;at<float>(z,0x1a4)=now;
 if(!at<Word>(z,0x190)){at<Word>(z,0x190)=1;at<float>(z,0x194)=now;if(!begin(b,z))return 0;}
 call<void>(b,0x5dfc80,z);if(at<Word>(z,0x48)-4u<5u)return 0;
 float point[3]={at<float>(z,0x1a8),at<float>(z,0x1ac),at<float>(z,0x18)};virt<void>(z,0x58,point);
 if(at<Word>(z,0x150)&6u){at<float>(z,0x194)+=delta;at<float>(z,0x198)+=delta;return 0;}
 Word phase=at<Word>(z,0x190);float age=now-at<float>(z,0x194);
 if(phase==1&&age>=50.0f/30&&!at<Word>(z,0x1b0))land(b,z);
 if(phase==3&&age>=57.0f/30&&(at<Word>(z,0x19c)|at<Word>(z,0x1a0)))crown(b,z);
 if((phase==1&&age>=97.0f/30)||(phase==3&&age>=120.0f/30)){
  trace(b,"return to idle before",phase);at<Word>(z,0x190)=phase=2;at<float>(z,0x198)=now+2.5f;at<float>(z,0x194)=now;animation(b,z,"idle",true);trace(b,"return to idle after",phase);
 }
 if(phase==2&&now>=at<float>(z,0x198)){
  if(surrender(b,z))return 0;
  Byte*t=target(b,z);if(t){call<void>(b,0x13dea0,z+0x19c,0u,at<Word>(t,8),at<Word>(t,0xc));at<Word>(z,0x190)=3;at<float>(z,0x194)=now;animation(b,z,"special",false);trace(b,"knighting started",1);}
 }
 return 0;
}
extern "C" __attribute__((section(".text.entry")))
Word iris_king(Word b,Word*args,Word mode){
 if(mode==0){call<void>(b,IRIS_KING_REGISTER);metadata(b);return 0;}
 if(mode==1){Byte*z=call<Byte*>(b,0xb363dc,0x1b4u);for(Word o=0;o<0x1b4;o+=4)at<Word>(z,o)=0;call<void>(b,0x5de8b8,z);at<Byte*>(z,0)=at<Byte*>(state(b),4);return reinterpret_cast<Word>(z);}
 if(mode==2)return at<Word>(state(b),0);
 if(mode==3){schema(b,reinterpret_cast<Byte*>(args[0]),reinterpret_cast<Byte*>(args[1]));return 0;}
 if(mode==9)return 0;
 if(mode==5)return planting(b,reinterpret_cast<Byte*>(args[0]),reinterpret_cast<int*>(args[1]),reinterpret_cast<Word*>(args[2]));
 Byte*z=reinterpret_cast<Byte*>(args[0]);if(mode==4)return update(b,z);
 if(mode==8){trace(b,"damage before HP bits",at<Word>(z,0xb0));trace(b,"damage amount bits",at<Word>(reinterpret_cast<Byte*>(args[1]),4));call<void>(b,0x5e0b74,z,args[1]);trace(b,"damage after state",at<Word>(z,0x48));return 0;}
 if(mode==6||mode==7){call<void>(b,0x13dea0,z+0x19c,0u,0u,0u);call<void>(b,0x5deafc,z);if(mode==7)call<void>(b,0xb36928,z);return 0;}
 return 0;
}
