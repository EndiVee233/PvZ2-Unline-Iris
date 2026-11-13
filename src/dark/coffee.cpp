// Coffee Bean uses its authored animation and an owned, saved six-second buff.
// No Plant layout extension, shared property mutation or grade multiplier.
using Byte=unsigned char;using Word=unsigned int;
template<class T>static T&at(Byte*p,Word o){return *reinterpret_cast<T*>(p+o);}
template<class R,class...A>static R call(Word b,Word o,A...a){return reinterpret_cast<R(*)(A...)>(b+o)(a...);}
template<class R,class...A>static R virt(Byte*p,Word o,A...a){return at<R(*)(Byte*,A...)>(at<Byte*>(p,0),o)(p,a...);}
static char*text(Word b,const char*s){char*r,a;call<void>(b,0xb75560,&r,s,&a);return r;}
static void drop(Word b,char*s){char a;if(__atomic_fetch_sub(reinterpret_cast<int*>(s-4),1,__ATOMIC_ACQ_REL)<=0)call<void>(b,0xb76c4c,s-12,&a);}
static void trace(Word b,const char*s,Word n){
#if IRIS_DARK_TRACE
 call<int>(b,0xe8c10,3,"IrisDark","Coffee %s value=%x",s,n);
#endif
}
#include "magnet.inc"
static Byte*state(Word b){return reinterpret_cast<Byte*>(b+0xf81c00);}
static Word stub(Word b,Word i){return b+IRIS_COFFEE_STUB+i*40;}
static void clear(Word b,Byte*w){call<void>(b,0x13dea0,w,0u,0u,0u);}
static bool type(Byte*p,const char*name){Byte*m=p?virt<Byte*>(p,0):nullptr;for(Word i=0;m&&i<32;++i,m=at<Byte*>(m,8))if(equalText(at<const char*>(m,4),name))return true;return false;}
static void metadata(Word b,bool plant){Byte*s=state(b);Word k=plant?0:1;
 if(!at<Word>(s,k*4)){Byte*m=call<Byte*>(b,0xb363dc,40u);call<void>(b,0x894ca0,m);at<Byte*>(s,k*4)=m;
  call<void>(b,0x895608,m,plant?"PlantIrisCoffee":"IrisCoffeeBuff",call<Byte*>(b,plant?0x13b5a0:0x283394),stub(b,plant?1:6));
  Word size=plant?0xf8u:0x7cu;Byte*v=call<Byte*>(b,0xb363dc,size);for(Word o=0;o<size;o+=4)at<Word>(v,o)=*reinterpret_cast<Word*>(b+(plant?0xce4398:0xcdbc88)+o);
  at<Word>(v,0)=stub(b,plant?2:7);at<Byte*>(s,8+k*4)=v;
  if(plant){at<Word>(v,0x68)=stub(b,4);at<Word>(v,0x44)=stub(b,17);at<Word>(v,0x90)=stub(b,17);}
  else{at<Word>(v,0x64)=stub(b,9);at<Word>(v,8)=stub(b,10);at<Word>(v,0xc)=stub(b,11);at<Word>(v,0x70)=stub(b,12);at<Word>(v,0x3c)=stub(b,17);}}
 Byte*manager=call<Byte*>(b,0x851728),*r=manager?call<Byte*>(b,0x851920,manager):nullptr;
 if(r&&!at<Word>(s,0x10+k*4)){at<Word>(s,0x10+k*4)=1;char*n=text(b,plant?"PlantIrisCoffee":"IrisCoffeeBuff");virt<void>(r,0xc,&n,stub(b,plant?3:8),plant?0x14u:0x68u,0u);drop(b,n);}
}
static void field(Word b,Byte*r,Byte*d,const char*n,Word off,Word kind){char*s=text(b,n);virt<void>(r,0x2c,d,&s,off,kind);drop(b,s);}
static Word weakType(Word b,Byte*r,const char*n){char*s=text(b,n);Word t=virt<Word>(r,0x24,&s);drop(b,s);return virt<Word>(r,0x20,3u,t,0u,0u);}
static void schema(Word b,Byte*r,Byte*d,bool plant){Byte*m=at<Byte*>(state(b),plant?0:4);at<Byte*>(m,0x24)=d;at<Byte*>(d,0x5c)=m;
 char*n=text(b,plant?"PlantFramework":"GridItem");Byte*p=virt<Byte*>(r,0x24,&n);drop(b,n);virt<void>(r,0x28,d,virt<Word>(p,0x34),0u);
 Word integer=virt<Word>(r,0x14,6u,4u),number=virt<Word>(r,0x14,8u,4u);
 if(plant){field(b,r,d,"iris_coffee_phase",8,integer);field(b,r,d,"iris_coffee_start",12,number);field(b,r,d,"iris_coffee_emitted",16,integer);}
 else{field(b,r,d,"iris_coffee_target",0x50,weakType(b,r,"Plant"));field(b,r,d,"iris_coffee_effect",0x58,weakType(b,r,"Effect_PopAnim"));field(b,r,d,"iris_coffee_expiry",0x60,number);field(b,r,d,"iris_coffee_active",0x64,integer);}
}
static Byte*findBuff(Word b,Byte*plant){if(!plant)return nullptr;int rect[4]={-8,-1,32,7};MagnetList list={};call<void>(b,0x248120,&list,4u,rect);Byte*found=nullptr;
 for(Byte**q=list.begin;q!=list.end;++q){Byte*p=*q;if(p&&virt<Byte*>(p,0)==at<Byte*>(state(b),4)&&weakObject(b,reinterpret_cast<Word*>(p+0x50))==plant){found=p;break;}}
 if(list.begin)call<void>(b,0xb36928,list.begin);return found;
}
static void cleanup(Word b,Byte*p){Byte*e=weakObject(b,reinterpret_cast<Word*>(p+0x58));if(e)call<void>(b,0x2708b4,e);clear(b,p+0x58);at<Word>(p,0x64)=0;}
static void effect(Word b,Byte*buff,Byte*p){Byte*e=weakObject(b,reinterpret_cast<Word*>(buff+0x58));
 if(!e){Byte*h=**reinterpret_cast<Byte***>(b+0xd008bc);if(!h)return;char*n=text(b,"POPANIM_EFFECTS_PEACH_ATTACK_UP");Word w[2]={};at<void(*)(Word*,Byte*,Word,char**,Word)>(at<Byte*>(h,0),8)(w,h,call<Word>(b,0x129ae0),&n,0u);drop(b,n);Byte*res=weakObject(b,w);clear(b,reinterpret_cast<Byte*>(w));if(!res)return;
  e=call<Byte*>(b,0x1809a8,battleBoard(b));if(!e)return;call<void>(b,0x23a354,e,res,0u);call<void>(b,0x23a814,e,1u);n=text(b,"attack_up");call<void>(b,0x23aa6c,e,&n,3u);drop(b,n);call<void>(b,0x13dea0,buff+0x58,0u,at<Word>(e,8),at<Word>(e,0xc));}
 // This PAM uses a 390x390 attachment canvas with its ring axis at x195.
 // Let the engine centre it using the selected resource scale; subtracting
 // a fixed world-space canvas origin drifts at lower resource resolutions.
 float pos[3]={at<float>(p,0x10),at<float>(p,0x14)-32,at<float>(p,0x18)};call<void>(b,0x4e6bb8,e,pos,0xffffffffu);
}
static void updateBuff(Word b,Byte*s){Byte*p=weakObject(b,reinterpret_cast<Word*>(s+0x50));if(!at<Word>(s,0x64)||!p||at<Word>(p,0x48)==3||at<float>(p,0x4c)<=0||battleTime(b)>=at<float>(s,0x60)){cleanup(b,s);call<void>(b,0x2708b4,s);return;}effect(b,s,p);}
static bool eligible(Word b,Byte*p){Byte*t=p?weakObject(b,reinterpret_cast<Word*>(p+0xb8)):nullptr;const char*n=t?at<const char*>(t,4):nullptr;if(!n)return false;
 return !equalText(n,"iceburg")&&!equalText(n,"cherry_bomb")&&!equalText(n,"coffeebean")&&!equalText(n,"squash")&&!equalText(n,"jalapeno")&&!equalText(n,"powerlily");
}
static void wake(Word b,Byte*p){int rect[4]={-8,-1,32,7};MagnetList list={};call<void>(b,0x248120,&list,4u,rect);
 for(Byte**q=list.begin;q!=list.end;++q){Byte*s=*q;if(s&&type(s,"IrisSleepSpell")&&weakObject(b,reinterpret_cast<Word*>(s+0x50))==p)call<void>(b,0x2708b4,s);}
 if(list.begin)call<void>(b,0xb36928,list.begin);
}
static void activate(Word b,Byte*coffee){int col=int(at<Word>(coffee,0x5c)),row=int(at<Word>(coffee,0x58)),rect[4]={col-1,row-1,3,3};MagnetList list={};call<void>(b,0x248120,&list,1u,rect);Word count=0;
 for(Byte**q=list.begin;q!=list.end;++q){Byte*p=*q;if(!p||p==coffee||at<Word>(p,0x48)==3||at<float>(p,0x4c)<=0)continue;wake(b,p);if(!eligible(b,p))continue;
  Byte*s=findBuff(b,p);if(!s){char*n=text(b,"iris_coffee_buff");s=call<Byte*>(b,0x17a8c4,battleBoard(b),&n,at<Word>(p,0x5c),at<Word>(p,0x58));drop(b,n);if(!s)continue;call<void>(b,0x13dea0,s+0x50,0u,at<Word>(p,8),at<Word>(p,0xc));}
  at<float>(s,0x60)=battleTime(b)+6;at<Word>(s,0x64)=1;effect(b,s,p);++count;}
 if(list.begin)call<void>(b,0xb36928,list.begin);char*n=text(b,"Play_Plant_DarkAges_CoffeeBean");call<void>(b,0x1a4280,coffee,&n,0.0f);drop(b,n);trace(b,"activated plants",count);
}
static void updatePlant(Word b,Byte*f){Byte*board=battleBoard(b),*p=at<Byte*>(f,4);if(!p||!board||at<Word>(board,0xa8)!=5||call<bool>(b,0x1872a8,board)||at<Word>(p,0x48)==3)return;
 if(!at<Word>(f,8)){at<Word>(f,8)=1;at<float>(f,12)=battleTime(b);Byte*r=virt<Byte*>(p,0x70);if(r){char*n=text(b,"plantfood");Word empty[6]={};call<void>(b,0x44d0b0,r,&n,0u,empty,empty);drop(b,n);}}
 float age=battleTime(b)-at<float>(f,12);
 // The source PAM's use_special marker is frame 142, after plantfood at 80.
 if(!at<Word>(f,16)&&age>=62.0f/30){at<Word>(f,16)=1;activate(b,p);}
 if(age>=142.0f/30)call<void>(b,0x39ece8,p,0u);
}
static Word damage(Word b,Byte*target,Byte*hit){Byte*p=hit?at<Byte*>(hit,0):nullptr,*buff=p&&type(p,"Plant")?findBuff(b,p):nullptr;
 float old=hit?at<float>(hit,4):0;if(buff&&at<Word>(buff,0x64)&&battleTime(b)<at<float>(buff,0x60)&&old>0){at<float>(hit,4)=old*1.1f;trace(b,"attack bonus",Word(at<float>(hit,4)));}
 Word result=call<Word>(b,IRIS_COFFEE_DAMAGE,target,hit);if(hit)at<float>(hit,4)=old;return result;
}
extern "C" __attribute__((section(".text.entry")))
Word iris_coffee(Word b,Word*args,Word mode){
 if(mode==0||mode==5){call<void>(b,mode==0?IRIS_COFFEE_REGISTER_PLANT:IRIS_COFFEE_REGISTER_GRID);metadata(b,mode==0);return 0;}
 if(mode==1||mode==6){bool plant=mode==1;Word n=plant?0x14u:0x68u;Byte*p=call<Byte*>(b,0xb363dc,n);for(Word i=0;i<n;i+=4)at<Word>(p,i)=0;if(!plant)call<void>(b,0x282ae4,p);at<Byte*>(p,0)=at<Byte*>(state(b),plant?8:12);return reinterpret_cast<Word>(p);}
 if(mode==2||mode==7)return at<Word>(state(b),mode==2?0:4);
 if(mode==3||mode==8){schema(b,reinterpret_cast<Byte*>(args[0]),reinterpret_cast<Byte*>(args[1]),mode==3);return 0;}
 Byte*p=reinterpret_cast<Byte*>(args[0]);if(mode==4){updatePlant(b,p);return 0;}if(mode==9){updateBuff(b,p);return 0;}
 if(mode==10||mode==11){cleanup(b,p);clear(b,p+0x50);call<void>(b,0x282b78,p);if(mode==11)call<void>(b,0xb36928,p);return 0;}
 if(mode==12){at<Word>(p,0x38)=0;return 0;}if(mode==13)return damage(b,p,reinterpret_cast<Byte*>(args[1]));
 return 0;
}
