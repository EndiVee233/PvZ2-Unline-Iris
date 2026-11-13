// Persistent Dark Ages potions and per-zombie stack ownership in Iris's ABI.
using Byte=unsigned char;using Word=unsigned int;
template<class T>static T&at(Byte*p,Word o){return *reinterpret_cast<T*>(p+o);}
template<class R,class...A>static R call(Word b,Word p,A...a){return reinterpret_cast<R(*)(A...)>(b+p)(a...);}
template<class R,class...A>static R virt(Byte*p,Word o,A...a){return at<R(*)(Byte*,A...)>(at<Byte*>(p,0),o)(p,a...);}
static char*text(Word b,const char*s){char*r,a;call<void>(b,0xb75560,&r,s,&a);return r;}
static void drop(Word b,char*s){char a;if(__atomic_fetch_sub(reinterpret_cast<int*>(s-4),1,__ATOMIC_ACQ_REL)<=0)call<void>(b,0xb76c4c,s-12,&a);}
static void trace(Word b,const char*s,Word n){
#if IRIS_DARK_TRACE
 call<int>(b,0xe8c10,3,"IrisDark","Potion %s value=%x",s,n);
#endif
}
#include "magnet.inc"
// 50 kind (1 speed,2 toughness,3 invisible stack owner),54 effect weak,
// 5c phase (0 alive,1 consumed,2 crushed),60 zombie weak,68/6c stacks,
// 70 appearance deadline (-1 after idle begins), or removal time when ended.
static Byte*state(Word b){return reinterpret_cast<Byte*>(b+0xf80e80);}
static Word stub(Word b,Word mode){return b+IRIS_POTION_STUB+40*mode;}
static const char*name(Word kind){return kind==0?"IrisSpeedPotion":kind==1?"IrisToughnessPotion":"IrisPotionBuff";}
static void metadata(Word b){
 Byte*s=state(b),*parent=call<Byte*>(b,0x283394);
 if(!at<Word>(s,0))for(Word i=0;i<3;++i){
  Byte*m=call<Byte*>(b,0xb363dc,40u);call<void>(b,0x894ca0,m);at<Byte*>(s,i*4)=m;
  call<void>(b,0x895608,m,name(i),parent,stub(b,1+i));
  Byte*t=call<Byte*>(b,0xb363dc,0x7cu);for(Word o=0;o<0x7c;o+=4)at<Word>(t,o)=*reinterpret_cast<Word*>(b+0xcdbc88+o);
  at<Word>(t,0)=stub(b,4+i);at<Word>(t,8)=stub(b,14);at<Word>(t,0xc)=stub(b,15);
  at<Word>(t,0x34)=stub(b,12);at<Word>(t,0x3c)=stub(b,13);at<Word>(t,0x64)=stub(b,11);at<Word>(t,0x70)=stub(b,10);
  at<Byte*>(s,0x10+i*4)=t;
 }
 Byte*m=call<Byte*>(b,0x851728),*r=m?call<Byte*>(b,0x851920,m):nullptr;
 if(r&&!at<Word>(s,0x20)){at<Word>(s,0x20)=1;for(Word i=0;i<3;++i){char*n=text(b,name(i));virt<void>(r,0xc,&n,stub(b,7+i),0x74u,0u);drop(b,n);}}
}
static void field(Word b,Byte*r,Byte*d,const char*label,Word offset,Word type){char*n=text(b,label);virt<void>(r,0x2c,d,&n,offset,type);drop(b,n);}
static void schema(Word b,Byte*r,Byte*d,Word kind){
 Byte*m=at<Byte*>(state(b),kind*4);at<Byte*>(m,0x24)=d;at<Byte*>(d,0x5c)=m;
 char*n=text(b,"GridItem");Byte*p=virt<Byte*>(r,0x24,&n);drop(b,n);virt<void>(r,0x28,d,virt<Word>(p,0x34),0u);
 Word integer=virt<Word>(r,0x14,6u,4u),number=virt<Word>(r,0x14,8u,4u);
 field(b,r,d,"iris_potion_kind",0x50,integer);field(b,r,d,"iris_potion_phase",0x5c,integer);
 field(b,r,d,"iris_potion_speed_stack",0x68,integer);field(b,r,d,"iris_potion_toughness_stack",0x6c,integer);field(b,r,d,"iris_potion_end",0x70,number);
 n=text(b,"Zombie");Word t=virt<Word>(r,0x24,&n);drop(b,n);field(b,r,d,"iris_potion_zombie",0x60,virt<Word>(r,0x20,3u,t,0u,0u));
 n=text(b,"Effect_PopAnim");t=virt<Word>(r,0x24,&n);drop(b,n);field(b,r,d,"iris_potion_effect",0x54,virt<Word>(r,0x20,3u,t,0u,0u));
}
static void clearVisual(Word b,Byte*p){Byte*e=weakObject(b,reinterpret_cast<Word*>(p+0x54));if(e)call<void>(b,0x2708b4,e);call<void>(b,0x13dea0,p+0x54,0u,0u,0u);}
static void visual(Word b,Byte*p,bool crushed=false){
 if(at<Word>(p,0x50)==3)return;Byte*e=weakObject(b,reinterpret_cast<Word*>(p+0x54));if(e)return;
 bool speed=at<Word>(p,0x50)==1,ended=at<Word>(p,0x5c)!=0;crushed=at<Word>(p,0x5c)==2;
 bool idle=!ended&&at<float>(p,0x70)<0;
 const char*id=ended?(speed?(crushed?"POPANIM_EFFECTS_SPEED_POTION_DESTROYED_EFFECT":"POPANIM_EFFECTS_SPEED_POTION_POOF_EFFECT"):(crushed?"POPANIM_EFFECTS_POWER_POTION_DESTROYED_EFFECT":"POPANIM_EFFECTS_POWER_POTION_POOF_EFFECT")):idle?(speed?"POPANIM_IRIS_POTION_SPEED_IDLE":"POPANIM_IRIS_POTION_POWER_IDLE"):(speed?"POPANIM_MINIGAME_POTION_SPEED":"POPANIM_MINIGAME_POTION_POWER");
 Byte*holder=**reinterpret_cast<Byte***>(b+0xd008bc);if(!holder)return;Word w[2]={};char*n=text(b,id);
 at<void(*)(Word*,Byte*,Word,char**,Word)>(at<Byte*>(holder,0),8)(w,holder,call<Word>(b,0x129ae0),&n,0u);drop(b,n);
 Byte*res=weakObject(b,w);call<void>(b,0x13dea0,w,0u,0u,0u);if(!res)return;
 e=call<Byte*>(b,0x1809a8,battleBoard(b));if(!e)return;call<void>(b,0x23a354,e,res,0u);call<void>(b,0x23a814,e,0u);
 if(!ended&&at<float>(p,0x70)==0)at<float>(p,0x70)=battleTime(b)+(speed?50.0f:100.0f)/30;
 n=text(b,"animation");call<void>(b,0x23aa6c,e,&n,idle?3u:0u);drop(b,n);call<void>(b,0x13dea0,p+0x54,0u,at<Word>(e,8),at<Word>(e,0xc));
 float pos[3]={at<float>(p,0x10)-150,at<float>(p,0x14)-120,0};call<void>(b,0x4e6bb8,e,pos,0xffffffffu);
}
static Byte*buff(Word b,Byte*z){
 int rect[4]={0,0,16,5};MagnetList list={};call<void>(b,0x248120,&list,4u,rect);Byte*found=nullptr;
 for(Byte**q=list.begin;q!=list.end;++q){Byte*p=*q;if(p&&virt<Byte*>(p,0)==at<Byte*>(state(b),8)&&weakObject(b,reinterpret_cast<Word*>(p+0x60))==z){found=p;break;}}
 if(list.begin)call<void>(b,0xb36928,list.begin);return found;
}
static Word drink(Word b,Byte*z,Word kind){
 Byte*p=buff(b,z);if(!p){char*n=text(b,"iris_potion_buff");p=call<Byte*>(b,0x17a8c4,battleBoard(b),&n,0u,0u);drop(b,n);if(!p)return 0;call<void>(b,0x13dea0,p+0x60,0u,at<Word>(z,8),at<Word>(z,0xc));}
 Word offset=kind==1?0x68u:0x6cu,level=at<Word>(p,offset);if(level>=3)return 0;++level;at<Word>(p,offset)=level;
 if(kind==1){at<Byte>(z,0x160)=1;float scale=call<float>(b,0x62c1e8,z+0x150);Byte*r=weakObject(b,reinterpret_cast<Word*>(z+0x40));if(r)call<void>(b,0x5ee918,r,scale);at<float>(z,0xa0)=scale;}
 trace(b,kind==1?"speed stack":"toughness stack",level);return level;
}
static bool giant(Byte*z){Byte*m=virt<Byte*>(z,0);for(Word i=0;m&&i<32;++i,m=at<Byte*>(m,8)){const char*n=at<const char*>(m,4);if(equalText(n,"ZombieGargantuar")||equalText(n,"ZombieGargantuarMech")||equalText(n,"ZombieZombossMech")||equalText(n,"ZombieDarkKing")||equalText(n,"ZombieIrisKing"))return true;}return false;}
static void damagePotion(Word b,Byte*p,Byte*hit){
 if(at<Word>(p,0x50)==3||at<Word>(p,0x5c)||at<float>(hit,4)<=0)return;
 Byte*z=at<Byte*>(hit,0);bool zombie=zombieClass(z),crushed=!zombie||(zombie&&giant(z));
 // Plant projectiles pass through potions. Mowers and giants break the jar;
 // ordinary melee consumes its remaining 50 HP before granting a stack.
 if(!zombie){if(!z)return;Byte*m=virt<Byte*>(z,0);bool mower=false;for(Word i=0;m&&i<32;++i,m=at<Byte*>(m,8))if(equalText(at<const char*>(m,4),"LawnMower"))mower=true;if(!mower)return;}
 float hp=at<float>(p,0x40)-at<float>(hit,4);at<float>(p,0x40)=hp;if(hp>0)return;
 Word gained=crushed?0:drink(b,z,at<Word>(p,0x50));at<Word>(p,0x5c)=crushed?2:1;at<Word>(p,0x38)=0;at<float>(p,0x40)=0;at<float>(p,0x70)=battleTime(b)+(crushed?34.0f:51.0f)/30;
 if(!crushed&&!gained){clearVisual(b,p);call<void>(b,0x2708b4,p);return;}
 const char*sound=crushed?"Play_Plant_Potion_Crushed_Glass_Any":at<Word>(p,0x50)==1?"Play_Plant_EvilShroom_Speed":"Play_Plant_EvilShroom_Toughness";
 if(crushed&&zombie){Byte*m=virt<Byte*>(z,0);for(Word i=0;m&&i<32;++i,m=at<Byte*>(m,8)){const char*n=at<const char*>(m,4);if(equalText(n,"ZombieGargantuar")||equalText(n,"ZombieGargantuarMech")){sound="Play_Plant_Potion_Crushed_Glass";break;}}}
 magnetSound(b,p,sound);
 clearVisual(b,p);visual(b,p,crushed);trace(b,crushed?"crushed":"consumed",at<Word>(p,0x50));
}
static Word damageZombie(Word b,Byte*z,Byte*hit){
 Byte*p=buff(b,z);Word level=p?at<Word>(p,0x6c):0;
 if(!level)return call<Word>(b,IRIS_POTION_ZOMBIE_DAMAGE,z,hit);
 if(level>3)level=3;
 struct Damage{Word source;float amount;Word flags;Word conditions[3];};
 Damage copy={at<Word>(hit,0),at<float>(hit,4),at<Word>(hit,8),{at<Word>(hit,12),at<Word>(hit,16),at<Word>(hit,20)}};
 // ROW applies this before helmet/body splitting, including instant damage.
 copy.amount*=level==1?0.85f:level==2?0.70f:0.55f;
 return call<Word>(b,IRIS_POTION_ZOMBIE_DAMAGE,z,&copy);
}
static void update(Word b,Byte*p){
 if(at<Word>(p,0x50)==3){Byte*z=weakObject(b,reinterpret_cast<Word*>(p+0x60));if(!z||at<Word>(z,0x48)-4u<5u)call<void>(b,0x2708b4,p);
  else if(at<Word>(p,0x68)){float scale=call<float>(b,0x62c1e8,z+0x150);if(at<float>(z,0xa0)!=scale){Byte*r=weakObject(b,reinterpret_cast<Word*>(z+0x40));if(r)call<void>(b,0x5ee918,r,scale);at<float>(z,0xa0)=scale;}}return;}
 Byte*board=battleBoard(b);if(!board||call<bool>(b,0x1872a8,board))return;
 if(at<Word>(p,0x5c)){if(battleTime(b)>=at<float>(p,0x70)){clearVisual(b,p);call<void>(b,0x2708b4,p);}else visual(b,p);return;}
 if(at<float>(p,0x70)>0&&battleTime(b)>=at<float>(p,0x70)){clearVisual(b,p);at<float>(p,0x70)=-1;}
 visual(b,p);
}
#include "potion_module.inc"
extern "C" __attribute__((section(".text.entry")))
Word iris_potions(Word b,Word*args,Word mode){
 if(mode==0){call<void>(b,IRIS_POTION_REGISTER);metadata(b);moduleMetadata(b);return 0;}
 if(mode>=1&&mode<=3){Byte*p=call<Byte*>(b,0xb363dc,0x74u);for(Word o=0;o<0x74;o+=4)at<Word>(p,o)=0;call<void>(b,0x282ae4,p);at<Byte*>(p,0)=at<Byte*>(state(b),0x10+4*(mode-1));at<Word>(p,0x50)=mode;return reinterpret_cast<Word>(p);}
 if(mode>=4&&mode<=6)return at<Word>(state(b),4*(mode-4));
 if(mode>=7&&mode<=9){schema(b,reinterpret_cast<Byte*>(args[0]),reinterpret_cast<Byte*>(args[1]),mode-7);return 0;}
 if(mode==19||mode==20){bool module=mode==20;Word size=module?0x20u:0x34u;Byte*p=call<Byte*>(b,0xb363dc,size);for(Word o=0;o<size;o+=4)at<Word>(p,o)=0;at<Byte*>(p,0)=at<Byte*>(moduleState(b),module?12:8);if(!module){at<Word>(p,0x24)=15;at<float>(p,0x28)=15;at<float>(p,0x2c)=25;at<Word>(p,0x30)=3;}return reinterpret_cast<Word>(p);}
 if(mode==21||mode==22||mode==25)return at<Word>(moduleState(b),mode==21?0:4);
 if(mode==23||mode==24){moduleSchema(b,reinterpret_cast<Byte*>(args[0]),reinterpret_cast<Byte*>(args[1]),mode==24);return 0;}
 if(mode==26){call<void>(b,IRIS_POTION_BOARD_UPDATE,args[0]);boardPotionTick(b,reinterpret_cast<Byte*>(args[0]));return 0;}
 if(mode>=27&&mode<=32){moduleTick(b,reinterpret_cast<Byte*>(args[0]),mode);return 0;}
 Byte*p=reinterpret_cast<Byte*>(args[0]);
 if(mode==10){bool owner=at<Word>(p,0x50)==3;at<Word>(p,0x38)=owner?0u:3u;at<float>(p,0x3c)=at<float>(p,0x40)=owner?0.0f:50.0f;return 0;}
 if(mode==11){update(b,p);return 0;}
 if(mode==12){damagePotion(b,p,reinterpret_cast<Byte*>(args[1]));return 0;}
 if(mode==13)return at<Word>(p,0x50)!=3&&!at<Word>(p,0x5c);
 if(mode==14||mode==15){clearVisual(b,p);call<void>(b,0x13dea0,p+0x60,0u,0u,0u);call<void>(b,0x282b78,p);if(mode==15)call<void>(b,0xb36928,p);return 0;}
 if(mode==16)return damageZombie(b,p,reinterpret_cast<Byte*>(args[1]));
 if(mode==17||mode==18){Byte*z=p-0x150,*owner=buff(b,z);Word level=owner?at<Word>(owner,0x68):0;
  if(!level)return call<Word>(b,mode==17?IRIS_POTION_SPEED:IRIS_POTION_ANIM_SPEED,p);
  // Keep potion stacks independent from Iris's pre-existing speed conditions.
  // The source gives potion speed priority over chill/other boosts, while
  // freeze, stun and butter still stop both movement and animation.
  float scale=at<Word>(p,0)&0xeu?0.0f:level==1?1.5f:level==2?2.0f:2.5f;
  at<float>(p,0x14)=at<float>(p,0x18)=scale;at<Byte>(p,0x10)=0;return at<Word>(p,0x14);
 }
 return 0;
}
