// Authored OakTrain schedule, real targets and mouse aiming in Iris's ABI.
using Byte=unsigned char;using Word=unsigned int;
template<class T>static T&at(Byte*p,Word o){return *reinterpret_cast<T*>(p+o);}
template<class R,class...A>static R call(Word b,Word p,A...a){return reinterpret_cast<R(*)(A...)>(b+p)(a...);}
template<class R,class...A>static R virt(Byte*p,Word o,A...a){return at<R(*)(Byte*,A...)>(at<Byte*>(p,0),o)(p,a...);}
static char*text(Word b,const char*s){char*r,a;call<void>(b,0xb75560,&r,s,&a);return r;}
static void drop(Word b,char*s){char a;if(__atomic_fetch_sub(reinterpret_cast<int*>(s-4),1,__ATOMIC_ACQ_REL)<=0)call<void>(b,0xb76c4c,s-12,&a);}
static void trace(Word b,const char*s,Word n){
#if IRIS_DARK_TRACE
 call<int>(b,0xe8c10,3,"IrisDark","OakTrain %s value=%x",s,n);
#endif
}
#include "magnet.inc"
#include "zombie_types.inc"
static Byte*state(Word b){return reinterpret_cast<Byte*>(b+0xf81000);}
static Word stub(Word b,Word mode){return b+IRIS_OAK_TRAIN_STUB+mode*40;}
static const char*className(Word k){switch(k){case 0:return "IrisOakTrainProperties";case 1:return "IrisOakTrain";
 case 2:return "ZombieIrisTargetWizard";case 3:return "ZombieIrisTargetArchmage";case 4:return "ZombieIrisTargetGargantuar";
 case 5:return "ZombieIrisTargetBottle";case 6:return "ZombieIrisTargetArrowYellow";case 7:return "ZombieIrisTargetArrowBlue";
 default:return "ZombieIrisTargetArrowPurple";}}
static const char*setting(Word i){switch(i){case 0:return "TotalLife";case 1:return "ArrowScore";case 2:return "WizardScore";
 case 3:return "ArchmageScore";case 4:return "BossScore";case 5:return "HealNum";case 6:return "ArrowPowerNum";
 case 7:return "ArrowMultipleNum";case 8:return "ArrowTrackNum";case 9:return "Arrow0";case 10:return "Arrow1";
 case 11:return "Arrow2";case 12:return "Arrow3";case 13:return "IrisWaveCount";default:return "IrisTargetCount";}}
static void metadata(Word b){Byte*s=state(b);
 for(Word k=0;k<9;++k){if(!at<Word>(s,k*4)){
  Byte*m=call<Byte*>(b,0xb363dc,40u);call<void>(b,0x894ca0,m);at<Byte*>(s,k*4)=m;
  call<void>(b,0x895608,m,className(k),call<Byte*>(b,k==0?0x134100:k==1?0x1341d8:0x5e8c4c),stub(b,1+k));
  Word bytes=k<2?0x44u:0x1acu;Byte*t=call<Byte*>(b,0xb363dc,bytes);
  for(Word o=0;o<bytes;o+=4)at<Word>(t,o)=*reinterpret_cast<Word*>(b+(k==0?0xcdd658:k==1?0xcd37b8:0xced208)+o);
  at<Word>(t,0)=stub(b,11+k);if(!k)at<Word>(t,0x38)=stub(b,12);
  if(k==1){at<Word>(t,8)=stub(b,43);at<Word>(t,0xc)=stub(b,44);}
  if(k>=2){at<Word>(t,0x64)=stub(b,30);at<Word>(t,0x34)=stub(b,31);at<Word>(t,8)=stub(b,33);at<Word>(t,0xc)=stub(b,34);
   at<Word>(t,0x190)=at<Word>(t,0x194)=stub(b,35);at<Word>(t,0xb8)=stub(b,42);}
  at<Byte*>(s,0x40+k*4)=t;
 }
 Byte*m=call<Byte*>(b,0x851728),*r=m?call<Byte*>(b,0x851920,m):nullptr;
 if(r&&!(at<Word>(s,0x80)&(1u<<k))){at<Word>(s,0x80)|=1u<<k;char*n=text(b,className(k));virt<void>(r,0xc,&n,stub(b,21+k),k==0?0x1860u:k==1?0x64u:0x1c0u,0u);drop(b,n);}}
 // Explicit bridges used only by Dark-enabled desktop input/framework builds.
 at<Word>(s,0x84)=stub(b,39);at<Word>(s,0x88)=stub(b,40);at<Word>(s,0x8c)=stub(b,38);
}
static void field(Word b,Byte*r,Byte*d,const char*name,Word offset,Word type){char*n=text(b,name);virt<void>(r,0x2c,d,&n,offset,type);drop(b,n);}
static void schema(Word b,Byte*r,Byte*d,Word kind){Byte*m=at<Byte*>(state(b),kind*4);at<Byte*>(m,0x24)=d;at<Byte*>(d,0x5c)=m;
 char*n=text(b,kind==0?"LevelModuleProperties":kind==1?"LevelModule":"Zombie");Byte*p=virt<Byte*>(r,0x24,&n);drop(b,n);virt<void>(r,0x28,d,virt<Word>(p,0x34),0u);
 Word integer=virt<Word>(r,0x14,6u,4u),number=virt<Word>(r,0x14,8u,4u);
 if(!kind){for(Word i=0;i<15;++i)field(b,r,d,setting(i),0x20+i*4,integer);
  for(Word i=0;i<256;++i)for(Word f=0;f<6;++f){char name[32]="Target000";Word h=i>=200?2:i>=100?1:0,u=i-h*100,t=Word((static_cast<unsigned long long>(u)*0xcccccccdULL)>>35);u-=10*t;name[6]=char('0'+h);name[7]=char('0'+t);name[8]=char('0'+u);
   const char*tail=f==0?"Time":f==1?"Kind":f==2?"X":f==3?"Y":f==4?"Life":"Wave";Word j=9;while(*tail)name[j++]=*tail++;name[j]=0;
   field(b,r,d,name,0x60+i*24+f*4,f==0||f==4?number:integer);}
 }else if(kind==1){
  for(Word i=0;i<6;++i)field(b,r,d,i==0?"iris_oak_initialized":i==1?"iris_oak_start":i==2?"iris_oak_next_target":i==3?"iris_oak_score":i==4?"iris_oak_arrow":"iris_oak_last_shot",0x18+i*4,i==1||i==5?number:integer);
  n=text(b,"Plant");Word type=virt<Word>(r,0x24,&n);drop(b,n);field(b,r,d,"iris_oak_plant",0x30,virt<Word>(r,0x20,3u,type,0u,0u));
  field(b,r,d,"iris_oak_wave",0x38,integer);field(b,r,d,"iris_oak_finished",0x3c,integer);
  field(b,r,d,"iris_oak_aim_x",0x40,number);field(b,r,d,"iris_oak_aim_y",0x44,number);
  for(Word i=0;i<4;++i)field(b,r,d,i==0?"iris_oak_ammo0":i==1?"iris_oak_ammo1":i==2?"iris_oak_ammo2":"iris_oak_ammo3",0x50+i*4,integer);
  field(b,r,d,"iris_oak_reload_end",0x60,number);
 }else{
  for(Word i=0;i<9;++i)field(b,r,d,i==0?"iris_target_kind":i==1?"iris_target_spawn":i==2?"iris_target_expires":i==3?"iris_target_next_attack":i==4?"iris_target_phase":i==5?"iris_target_phase_end":i==6?"iris_target_accounted":i==7?"iris_target_last_time":"iris_target_direction",0x190+i*4,i==1||i==2||i==3||i==5||i==7?number:integer);
 }
}
static Byte*module(Word b){return ownedLevelModule(b,battleBoard(b),at<Byte*>(state(b),4));}
static Byte*properties(Word b,Byte*m){return m?weakObject(b,reinterpret_cast<Word*>(m+0x10)):nullptr;}
static bool alive(Byte*z){return z&&at<float>(z,0xb0)>0&&at<Word>(z,0x48)-4u>=5u;}
static void animation(Word b,Byte*z,const char*label,bool loop){Byte*r=weakObject(b,reinterpret_cast<Word*>(z+0x40));if(!r)return;char*n=text(b,label);Word empty[6]={};call<void>(b,loop?0x44d220:0x44d0b0,r,&n,loop?3u:0u,empty,empty);drop(b,n);}
static void plantAnimation(Word b,Byte*p,const char*label){Byte*r=virt<Byte*>(p,0x70);if(!r)return;char*n=text(b,label);Word empty[6]={};call<void>(b,0x44d0b0,r,&n,0u,empty,empty);drop(b,n);}
static bool target(Byte*z,Word b){if(!z)return false;Byte*m=virt<Byte*>(z,0);for(Word k=2;k<9;++k)if(m==at<Byte*>(state(b),k*4))return true;return false;}
static float randomDelay(Word b,float lo,float hi){return lo+float(call<Word>(b,0x7a3e90,Word((hi-lo)*1000)+1))/1000;}
static Byte*oakPlant(Word b,Byte*m){Byte*p=weakObject(b,reinterpret_cast<Word*>(m+0x30));if(p)return p;
 int rect[4]={0,0,9,5};MagnetList list={};call<void>(b,0x248120,&list,1u,rect);
 for(Byte**q=list.begin;q!=list.end;++q){Byte*t=*q,*type=t?weakObject(b,reinterpret_cast<Word*>(t+0xb8)):nullptr;if(type&&equalText(at<const char*>(type,0x10),"POPANIM_PLANT_OAKSHOOTER")){p=t;call<void>(b,0x13dea0,m+0x30,0u,at<Word>(p,8),at<Word>(p,0xc));break;}}
 if(list.begin)call<void>(b,0xb36928,list.begin);return p;
}
static void award(Word b,Byte*m,Byte*z){if(at<Word>(z,0x1a8))return;at<Word>(z,0x1a8)=1;Byte*p=properties(b,m);if(!p)return;Word kind=at<Word>(z,0x190),score=at<Word>(p,kind==0?0x28:kind==1?0x2c:kind==2?0x30:0x24);
 at<Word>(m,0x24)+=score;if(kind>=4){Word slot=kind==4?1:kind==5?2:3;at<Word>(m,0x50+4*slot)+=at<Word>(p,0x34+slot*4);}
 if(kind==3){Byte*plant=oakPlant(b,m);if(plant){float hp=at<float>(plant,0x4c)+float(at<Word>(p,0x34)),max=float(at<Word>(p,0x20));at<float>(plant,0x4c)=hp<max?hp:max;}}
 trace(b,"target scored",score);
}
static Word damage(Word b,Byte*z,Byte*hit){Byte*m=module(b);if(!m)return call<Word>(b,IRIS_OAK_TRAIN_DAMAGE,z,hit);
 Word result=call<Word>(b,IRIS_OAK_TRAIN_DAMAGE,z,hit);if(!alive(z))award(b,m,z);return result;
}
static void targetUpdate(Word b,Byte*z){Byte*board=battleBoard(b),*m=module(b);if(!m||!board)return;
 if(!alive(z)){call<void>(b,0x5dfc80,z);return;}if(at<Word>(board,0xa8)!=5||call<bool>(b,0x1872a8,board))return;
 float now=battleTime(b),dt=now-at<float>(z,0x1ac);if(dt<0||dt>0.25f)dt=0;at<float>(z,0x1ac)=now;
 // Native conditions and damage/death are retained, but enemy lawn walking
 // and eating are suspended for the aiming game's stationary/moving targets.
 Word a=at<Word>(z,0x68),c=at<Word>(z,0x70);at<Word>(z,0x68)=at<Word>(z,0x70)=0;at<Word>(z,0xa8)&=~1u;
 call<void>(b,0x5dfc80,z);at<Word>(z,0x68)=a;at<Word>(z,0x70)=c;if(!alive(z))return;
 if(at<Word>(z,0x150)&6u){at<float>(z,0x19c)+=dt;at<float>(z,0x1a4)+=dt;if(at<float>(z,0x198)>0)at<float>(z,0x198)+=dt;return;}
 Word kind=at<Word>(z,0x190);if(at<float>(z,0x198)>0&&now>=at<float>(z,0x198)){at<Word>(z,0x1a8)=1;call<void>(b,0x2708b4,z);trace(b,"target expired",kind);return;}
 if(kind>=3)return;
 Word phase=at<Word>(z,0x1a0);
 if(phase==0&&now>=at<float>(z,0x19c)){at<Word>(z,0x1a0)=1;at<float>(z,0x1a4)=now+(kind==2?2.0f:1.0f);animation(b,z,kind==2?"smash_left":"casting_start",false);}
 if(phase==1&&now>=at<float>(z,0x1a4)){Byte*p=oakPlant(b,m);if(p&&at<Word>(p,0x48)!=3){struct{Byte*source;float amount;Word flags;Word conditions[3];}hit={z,kind==0?50.0f:kind==1?100.0f:150.0f,0,{}};virt<void>(p,0x34,&hit);trace(b,"target attacked Oak",Word(hit.amount));}
  at<Word>(z,0x1a0)=0;at<float>(z,0x19c)=now+randomDelay(b,kind==2?5.0f:6.0f,kind==2?7.0f:8.0f);animation(b,z,"idle",true);}
}
static bool spawn(Word b,Byte*m,Byte*data){Word kind=at<Word>(data,4);if(kind>6)return false;Word type[2]={};if(!findZombieType(b,type,className(kind+2),true))return false;
 Byte*z=call<Byte*>(b,0x181a30,battleBoard(b),type,0u);call<void>(b,0x13dea0,type,0u,0u,0u);if(!z)return false;
 int col=at<int>(data,8),row=at<int>(data,12);if(col<0)col=3+int(call<Word>(b,0x7a3e90,6u));if(row<0)row=int(call<Word>(b,0x7a3e90,5u));
 float pos[3]={float(call<int>(b,0x17d518,battleBoard(b),col)),float(call<int>(b,0x1814a4,battleBoard(b),row)),0};virt<void>(z,0x58,pos);
 float now=battleTime(b);at<Word>(z,0x190)=kind;at<float>(z,0x194)=at<float>(z,0x1ac)=now;at<float>(z,0x198)=at<float>(data,16)>0?now+at<float>(data,16):0;
 at<float>(z,0x19c)=now+randomDelay(b,1,kind==1?3.0f:2.0f);at<Word>(z,0x1b0)=1;at<Word>(z,0xc0)=at<Word>(data,20)-1;
 animation(b,z,kind>=3?"idle":"idle",true);at<Word>(m,0x38)=at<Word>(data,20);trace(b,"target spawned",kind);return true;
}
static void tick(Word b,Byte*m){Byte*board=battleBoard(b),*p=properties(b,m);if(!board||!p||at<Word>(board,0xa8)!=5||call<bool>(b,0x1872a8,board))return;
 Byte*plant=oakPlant(b,m);if(!plant)return;
 if(!at<Word>(m,0x18)){at<Word>(m,0x18)=1;at<float>(m,0x1c)=battleTime(b);at<float>(plant,0x4c)=float(at<Word>(p,0x20));
  for(Word i=0;i<4;++i)at<Word>(m,0x50+4*i)=at<Word>(p,0x44+4*i);trace(b,"started aiming game",at<Word>(p,0x58));}
 // UIArrowBtn in Aster refills twelve ordinary arrows after a three-second
 // reload, automatically at zero or by its plus button while below twelve.
 if(at<float>(m,0x60)>0&&battleTime(b)>=at<float>(m,0x60)){at<Word>(m,0x50)=12;at<float>(m,0x60)=0;trace(b,"normal arrows reloaded",12);}
 Word count=at<Word>(p,0x58);if(count>256)count=256;
 while(at<Word>(m,0x20)<count){Byte*d=p+0x60+24*at<Word>(m,0x20);if(battleTime(b)-at<float>(m,0x1c)<at<float>(d,0))break;if(!spawn(b,m,d))break;++at<Word>(m,0x20);}
 if(at<Word>(m,0x20)==count){int rect[4]={-8,-1,40,7};MagnetList list={};call<void>(b,0x248120,&list,2u,rect);bool pending=false;
  for(Byte**q=list.begin;q!=list.end;++q)if(target(*q,b)&&alive(*q))pending=true;if(list.begin)call<void>(b,0xb36928,list.begin);
  if(!pending)at<Word>(m,0x3c)=1;
 }
}
static Byte*shot(Word b,Byte*p,Word action,float x,float y){Word old=at<Word>(p,0xb4);at<Word>(p,0xb4)=action;Byte*s=call<Byte*>(b,0x3a1b88,p);at<Word>(p,0xb4)=old;if(!s)return nullptr;
 float dx=x-at<float>(s,0x2c),dy=y-(at<float>(s,0x30)-at<float>(s,0x34)),length=__builtin_sqrtf(dx*dx+dy*dy);if(length<1)length=1;
 float speed=action==6?333.0f:666.0f;at<float>(s,0x38)=speed*dx/length;at<float>(s,0x3c)=speed*dy/length;at<float>(s,0x40)=0;
 for(Word o=0x44;o<=0x4c;o+=4)at<float>(s,o)=0;at<float>(s,0x78)=call<float>(b,0xe88a4,dy,dx);at<float>(s,0x7c)=0;return s;
}
static Word manual(Word b,Byte*p){Byte*m=module(b);if(!m||oakPlant(b,m)!=p)return 0;return 1;}
static float screenScale(Word b){Byte*app=**reinterpret_cast<Byte***>(b+0xd00838);float s=app?at<float>(app,0x6a0):1;return s>0&&s<16?s:1;}
static Word input(Word b,Word*args){Byte*m=module(b),*board=reinterpret_cast<Byte*>(args[0]);if(!m||board!=battleBoard(b)||at<Word>(board,0xa8)!=5||call<bool>(b,0x1872a8,board))return 0;
 float scale=screenScale(b),x=float(int(args[1]))/scale,y=float(int(args[2]))/scale;Word phase=args[3];at<float>(m,0x40)=x;at<float>(m,0x44)=y;
 if(phase==6){if(args[1]>=8&&args[1]<=11){at<Word>(m,0x28)=args[1]-8;return 1;}
  if(args[1]==46){if(at<Word>(m,0x50)<12&&!at<float>(m,0x60))at<float>(m,0x60)=battleTime(b)+3;return 1;}return 0;}
 float bottom=float(call<int>(b,0x1814a4,board,4));
 if(phase==4){at<Word>(m,0x4c)=0;return 0;}
 if(phase==3){Word tracked=at<Word>(m,0x4c);at<Word>(m,0x4c)=0;return tracked;}
 if(phase==1)return at<Word>(m,0x4c);
 if(x>=348&&x<370&&y>bottom+45&&y<bottom+68){if(phase==0){at<Word>(m,0x4c)=1;if(at<Word>(m,0x50)<12&&!at<float>(m,0x60))at<float>(m,0x60)=battleTime(b)+3;}return 1;}
 if(y>bottom+48&&y<bottom+90&&x>=310&&x<610){if(phase==0){at<Word>(m,0x28)=Word((x-310)/75);at<Word>(m,0x4c)=1;}return 1;}
 if(phase!=0)return phase==5&&x>=float(call<int>(b,0x17d518,board,1));
 Byte*p=oakPlant(b,m);if(!p||at<Word>(p,0x48)==3||x<float(call<int>(b,0x17d518,board,1))||y<70||y>bottom+10)return 0;
 at<Word>(m,0x4c)=1;Word kind=at<Word>(m,0x28);if(kind>3||!at<Word>(m,0x50+kind*4)||battleTime(b)<at<float>(m,0x2c)||(kind==0&&at<float>(m,0x60)>0))return 1;
 Word action=kind==0?3:kind==1?5:kind==2?4:6;Byte*s=shot(b,p,action,x,y);if(!s)return 1;
 --at<Word>(m,0x50+kind*4);at<float>(m,0x2c)=battleTime(b)+0.25f;
 if(!kind&&!at<Word>(m,0x50))at<float>(m,0x60)=battleTime(b)+3;
 if(kind==2){float dx=at<float>(s,0x38),dy=at<float>(s,0x3c);for(int i=-2;i<=2;++i){if(!i)continue;float a=float(i)*0.2617994f,cs=call<float>(b,0xe87d8,a),sn=call<float>(b,0xe87cc,a);Byte*q=shot(b,p,action,x,y);if(q){at<float>(q,0x38)=dx*cs-dy*sn;at<float>(q,0x3c)=dx*sn+dy*cs;}}}
 plantAnimation(b,p,"attack");trace(b,"manual arrow",kind);return 1;
}
static int worldAxis(Word b,Byte*g,int value,bool vertical){float scale=at<float>(g,vertical?0x14:0x10),origin=at<float>(g,vertical?0x1c:0x18);return scale>0&&scale<16?int(origin+(float(value)*screenScale(b)-origin)*scale):value;}
static int worldSize(Word b,Byte*g,int value,bool vertical){float scale=at<float>(g,vertical?0x14:0x10);return scale>0&&scale<16?int(float(value)*screenScale(b)*scale):value;}
static void drawImage(Word b,Byte*g,Word slot,const char*name,int x,int y,int w,int h){
 Byte*reference=state(b)+0x100+slot*24;at<const char*>(reference,0xc)=name;Byte*image=call<Byte*>(b,0x1524d8,reference);
 if(image)call<void>(b,0x7d53cc,g,image,worldAxis(b,g,x,false),worldAxis(b,g,y,true),worldSize(b,g,w,false),worldSize(b,g,h,true));
}
static Word decimal(Word value){return Word((static_cast<unsigned long long>(value)*0xcccccccdULL)>>35);}
static Word*numberText(Word b,const char*prefix,Word value){Word buffer[48],len=0,digits[10],n=0;
 while(*prefix&&len<30)buffer[len++]=Word(*prefix++);do{Word q=decimal(value);digits[n++]=value-q*10+'0';value=q;}while(value&&n<10);
 while(n)buffer[len++]=digits[--n];Byte*p=call<Byte*>(b,0xb363dc,12+4*(len+1));at<Word>(p,0)=at<Word>(p,4)=len;at<Word>(p,8)=0;
 Word*out=reinterpret_cast<Word*>(p+12);for(Word i=0;i<len;++i)out[i]=buffer[i];out[len]=0;return out;
}
static void hudNumber(Word b,Byte*m,Byte*g,Word slot,const char*prefix,Word value,int x,int y,int width,int height){
 x=worldAxis(b,g,x,false);y=worldAxis(b,g,y,true);width=worldSize(b,g,width,false);height=worldSize(b,g,height,true);
 Byte*cache=at<Byte*>(m,0x48);if(!cache){cache=call<Byte*>(b,0xb363dc,72u);for(Word i=0;i<72;i+=4)at<Word>(cache,i)=0;at<Byte*>(m,0x48)=cache;}
 Word*str=numberText(b,prefix,value);Byte*widget=at<Byte*>(cache,slot*4);
 if(!widget){Word color[4]={255,255,255,255};Word font=**reinterpret_cast<Word**>(b+0xd00b20);
  Byte*config=call<Byte*>(b,0xa321fc,font,float(x),float(y),float(width),float(height),&str,1u,1u,color);
  widget=call<Byte*>(b,0xb363dc,0xa8u);call<void>(b,0x846e0c,widget,config);at<Byte*>(cache,slot*4)=widget;
 }else{Byte*config=at<Byte*>(widget,0x9c);if(config){at<int>(config,0xc)=x;at<int>(config,0x10)=y;at<int>(config,0x14)=width;at<int>(config,0x18)=height;}call<void>(b,0x847294,widget,&str);}
 if(__atomic_fetch_sub(reinterpret_cast<int*>(str)-1,1,__ATOMIC_ACQ_REL)<=0)call<void>(b,0xb36928,reinterpret_cast<Byte*>(str)-12);
 virt<void>(widget,0x8c,g);
}
static void hideOrdinaryHud(Word b,Byte*m){Byte*cache=at<Byte*>(m,0x48);if(!cache)return;
 for(Word i=0;i<4;++i){Byte*saved=cache+24+12*i;if(at<Word>(saved,0)|at<Word>(saved,4))continue;
  char*n=text(b,i==0?"UIPlantfood":i==1?"UIPowerupHolder":i==2?"UIShovel":"UISunBank");Byte*node=call<Byte*>(b,0x536398,&n);drop(b,n);
  if(node){at<Word>(saved,8)=at<Word>(node,0x4c)&1u;call<void>(b,0x13dea0,saved,0u,at<Word>(node,8),at<Word>(node,12));call<void>(b,0x536ef8,node,0u);}
 }
}
static void hud(Word b,Byte*board,Byte*g){Byte*m=module(b),*app=**reinterpret_cast<Byte***>(b+0xd00838);if(!m||board!=battleBoard(b)||!g||!app||!at<Word>(m,0x18))return;
 Byte*manager=at<Byte*>(app,0x2b8),*modal=manager?at<Byte*>(manager,0xac):nullptr;if(modal&&modal!=manager+0xa8)return;
 call<void>(b,0x7d2810,g);int bottom=call<int>(b,0x1814a4,board,4);Word selected=at<Word>(m,0x28);
 drawImage(b,g,0,"IMAGE_UI_HUD_INGAME_OAK_ARROW_HOLDER_BG",300,bottom+48,320,42);
 for(Word i=0;i<4;++i){bool down=selected==i;const char*name=i==0?(down?"IMAGE_UI_HUD_INGAME_OAK_ARROW_NORMAL_DOWN":"IMAGE_UI_HUD_INGAME_OAK_ARROW_NORMAL"):i==1?(down?"IMAGE_UI_HUD_INGAME_OAK_ARROW_POWER_DOWN":"IMAGE_UI_HUD_INGAME_OAK_ARROW_POWER"):i==2?(down?"IMAGE_UI_HUD_INGAME_OAK_ARROW_MULTIPLE_DOWN":"IMAGE_UI_HUD_INGAME_OAK_ARROW_MULTIPLE"):(down?"IMAGE_UI_HUD_INGAME_OAK_ARROW_TRACK_DOWN":"IMAGE_UI_HUD_INGAME_OAK_ARROW_TRACK");
  int x=310+int(i)*75;drawImage(b,g,i+1,name,x,bottom+50,34,34);hudNumber(b,m,g,i,"",at<Word>(m,0x50+4*i),x+30,bottom+68,30,18);}
 drawImage(b,g,5,"IMAGE_UI_HUD_INGAME_OAK_ARROW_AMOUNT_ADD",348,bottom+45,20,20);
 Byte*p=oakPlant(b,m);hudNumber(b,m,g,4,"HP ",p&&at<float>(p,0x4c)>0?Word(at<float>(p,0x4c)):0,220,145,120,24);
 hudNumber(b,m,g,5,"SCORE ",at<Word>(m,0x24),600,145,190,24);hideOrdinaryHud(b,m);call<void>(b,0x7d2940,g);
}
static void destroyModule(Word b,Byte*m,bool free){Byte*cache=at<Byte*>(m,0x48);if(cache){for(Word i=0;i<6;++i){Byte*p=at<Byte*>(cache,4*i);if(p)virt<void>(p,0xc);}
  for(Word i=0;i<4;++i){Byte*saved=cache+24+12*i,*node=weakObject(b,reinterpret_cast<Word*>(saved));if(node)call<void>(b,0x536ef8,node,at<Word>(saved,8));call<void>(b,0x13dea0,saved,0u,0u,0u);}
  call<void>(b,0xb36928,cache);at<Word>(m,0x48)=0;}
 call<void>(b,0x13dea0,m+0x30,0u,0u,0u);at<void(*)(Byte*)>(reinterpret_cast<Byte*>(b+0xcd37b8),8)(m);if(free)call<void>(b,0xb36928,m);
}
extern "C" __attribute__((section(".text.entry")))
Word iris_oak_train(Word b,Word*args,Word mode){
 if(mode==0){call<void>(b,IRIS_OAK_TRAIN_REGISTER);metadata(b);return 0;}
 if(mode>=1&&mode<=9){Word k=mode-1,size=k==0?0x1860u:k==1?0x64u:0x1c0u;Byte*p=call<Byte*>(b,0xb363dc,size);for(Word o=0;o<size;o+=4)at<Word>(p,o)=0;if(k>=2)call<void>(b,0x5de8b8,p);at<Byte*>(p,0)=at<Byte*>(state(b),0x40+k*4);if(k>=2)at<Word>(p,0x190)=k-2;trace(b,"created owned class",k);return reinterpret_cast<Word>(p);}
 if(mode>=11&&mode<=19)return at<Word>(state(b),(mode-11)*4);
 if(mode>=21&&mode<=29){schema(b,reinterpret_cast<Byte*>(args[0]),reinterpret_cast<Byte*>(args[1]),mode-21);return 0;}
 Byte*p=reinterpret_cast<Byte*>(args[0]);
 if(mode==30){targetUpdate(b,p);return 0;}
 if(mode==31)return damage(b,p,reinterpret_cast<Byte*>(args[1]));
 if(mode==33||mode==34){call<void>(b,0x5deafc,p);if(mode==34)call<void>(b,0xb36928,p);return 0;}
 if(mode==35)return 0xffffffffu;if(mode==42)return 0;
 if(mode==36){Byte*m=module(b);return m?at<Word>(m,0x3c):call<Word>(b,IRIS_OAK_TRAIN_WINCON);}
 if(mode==37){Word result=call<Word>(b,IRIS_OAK_TRAIN_UPDATE,p);if(p==battleBoard(b)){Byte*m=module(b);if(m){Byte*s=state(b);if(at<Byte*>(s,0x94)!=p||at<Word>(s,0x90)!=at<Word>(p,0xa8)){at<Byte*>(s,0x94)=p;at<Word>(s,0x90)=at<Word>(p,0xa8);trace(b,"board stage",at<Word>(p,0xa8));}tick(b,m);}}return result;}
 if(mode==38)return manual(b,p);if(mode==39)return input(b,args);
 if(mode==40){hud(b,p,reinterpret_cast<Byte*>(args[1]));return 0;}
 if(mode==43||mode==44){destroyModule(b,p,mode==44);return 0;}
 return 0;
}
