// Theatre-specific paths, house protection and per-spawn rewards. Ordinary
// zombies and plant properties keep their original classes and vtables.
using Byte=unsigned char;using Word=unsigned int;
template<class T>static T&at(Byte*p,Word o){return *reinterpret_cast<T*>(p+o);}
template<class R,class...A>static R call(Word b,Word p,A...a){return reinterpret_cast<R(*)(A...)>(b+p)(a...);}
template<class R,class...A>static R virt(Byte*p,Word o,A...a){return at<R(*)(Byte*,A...)>(at<Byte*>(p,0),o)(p,a...);}
static char*text(Word b,const char*s){char*r,a;call<void>(b,0xb75560,&r,s,&a);return r;}
static void drop(Word b,char*s){char a;if(__atomic_fetch_sub(reinterpret_cast<int*>(s-4),1,__ATOMIC_ACQ_REL)<=0)call<void>(b,0xb76c4c,s-12,&a);}
static void trace(Word b,const char*s,Word n){
#if IRIS_DARK_TRACE
 call<int>(b,0xe8c10,3,"IrisDark","Theatre %s value=%x",s,n);
#endif
}
#include "magnet.inc"
static Byte*state(Word b){return reinterpret_cast<Byte*>(b+0xf81800);}
static float screenScale(Word b){Byte*app=**reinterpret_cast<Byte***>(b+0xd00838);float s=app?at<float>(app,0x6a0):1;return s>0&&s<16?s:1;}
static Word stub(Word b,Word i){return b+IRIS_THEATRE_STUB+40*i;}
static const char*name(Word k){switch(k){case 0:return "IrisTheatreProperties";case 1:return "IrisTheatre";case 2:return "IrisTheatreZombieProperties";default:return "ZombieIrisTheatre";}}
static Word parent(Word k){return k==0?0x134100:k==1?0x1341d8:k==2?0x12c65c:0x5e8c4c;}
static Word bytes(Word k){return k==0?0x280:k==1?0x8c0:k==2?0xe4:0x1c8;}
static void metadata(Word b){Byte*s=state(b);
 for(Word k=0;k<4;++k){if(!at<Word>(s,k*4)){
  Byte*m=call<Byte*>(b,0xb363dc,40u);call<void>(b,0x894ca0,m);at<Byte*>(s,k*4)=m;
  call<void>(b,0x895608,m,name(k),call<Byte*>(b,parent(k)),stub(b,1+k));
  Byte*prototype=k==2?call<Byte*>(b,0x12c770):nullptr;
  Byte*source=prototype?at<Byte*>(prototype,0):reinterpret_cast<Byte*>(b+(k==0?0xcdd658:k==1?0xcd37b8:0xced208));
  Word n=k==3?0x1ac:0x44;Byte*v=call<Byte*>(b,0xb363dc,n);
  for(Word i=0;i<n;i+=4)at<Word>(v,i)=at<Word>(source,i);
  if(prototype)virt<void>(prototype,0xc);
  at<Word>(v,0)=stub(b,5+k);at<Byte*>(s,0x20+k*4)=v;
  if(k==0)at<Word>(v,0x38)=stub(b,24);
  if(k==1){at<Word>(v,8)=stub(b,22);at<Word>(v,0xc)=stub(b,23);}
  if(k==3){at<Word>(v,0x64)=stub(b,13);at<Word>(v,0x34)=stub(b,14);at<Word>(v,8)=stub(b,15);at<Word>(v,0xc)=stub(b,16);
   at<Word>(v,0xb8)=stub(b,25);at<Word>(v,0x190)=at<Word>(v,0x194)=stub(b,21);}
 }
 Byte*m=call<Byte*>(b,0x851728),*r=m?call<Byte*>(b,0x851920,m):nullptr;
 if(r&&!(at<Word>(s,0x40)&(1u<<k))){at<Word>(s,0x40)|=1u<<k;char*n=text(b,name(k));virt<void>(r,0xc,&n,stub(b,9+k),bytes(k),0u);drop(b,n);}}
 at<Word>(s,0x50)=stub(b,26);at<Word>(s,0x54)=stub(b,27);
}
static Byte*module(Word b){return ownedLevelModule(b,battleBoard(b),at<Byte*>(state(b),4));}
static Byte*props(Word b,Byte*m){return m?weakObject(b,reinterpret_cast<Word*>(m+0x10)):nullptr;}
static Byte*zprops(Word b,Byte*z){Byte*t=weakObject(b,reinterpret_cast<Word*>(z+0x38));return t?call<Byte*>(b,0x6826ec,t):nullptr;}
static bool alive(Byte*z){return z&&at<float>(z,0xb0)>0&&at<Word>(z,0x48)-4u>=5u;}
static void field(Word b,Byte*r,Byte*d,const char*n,Word o,Word type){char*s=text(b,n);virt<void>(r,0x2c,d,&s,o,type);drop(b,s);}
static Word fifth(Word n){return Word((static_cast<unsigned long long>(n)*0xcccccccdULL)>>34);}
static void indexName(char*out,const char*prefix,Word n,const char*suffix){Word i=0,tens=Word((static_cast<unsigned long long>(n)*0xcccccccdULL)>>35);while(*prefix)out[i++]=*prefix++;out[i++]=char('0'+tens);out[i++]=char('0'+n-10*tens);while(*suffix)out[i++]=*suffix++;out[i]=0;}
static void schema(Word b,Byte*r,Byte*d,Word k){Byte*m=at<Byte*>(state(b),k*4);at<Byte*>(m,0x24)=d;at<Byte*>(d,0x5c)=m;
 char*n=text(b,k==0?"LevelModuleProperties":k==1?"LevelModule":k==2?"ZombiePropertySheet":"Zombie");Byte*p=virt<Byte*>(r,0x24,&n);drop(b,n);virt<void>(r,0x28,d,virt<Word>(p,0x34),0u);
 Word integer=virt<Word>(r,0x14,6u,4u),number=virt<Word>(r,0x14,8u,4u);
 if(k==0){
  for(Word i=0;i<5;++i)field(b,r,d,i==0?"HouseKind":i==1?"HouseHitpoints":i==2?"WaveHealthIncrement":i==3?"TreeCount":"BossSkillCount",0x20+i*4,i==2?number:integer);
  for(Word i=0;i<8;++i){char label[]="BossSkill0";label[9]=char('0'+i);field(b,r,d,label,0x34+i*4,integer);}
  for(Word i=0;i<45;++i){char label[32];indexName(label,"Road",i,"Distance");field(b,r,d,label,0x60+i*8,integer);indexName(label,"Road",i,"Image");field(b,r,d,label,0x64+i*8,integer);}
  for(Word i=0;i<4;++i){char label[]="Tree0Count";label[4]=char('0'+i);field(b,r,d,label,0x1d0+i*40,integer);
   for(Word j=0;j<3;++j)for(Word f=0;f<3;++f){char label[32]="Tree0Step0";label[4]=char('0'+i);label[9]=char('0'+j);const char*tail=f==0?"Plant":f==1?"Cost":"Interval";Word pos=10;while(*tail)label[pos++]=*tail++;label[pos]=0;field(b,r,d,label,0x1d4+i*40+j*12+f*4,f==2?number:integer);}}
 }else if(k==1){
  n=text(b,"Plant");Word plant=virt<Word>(r,0x24,&n);drop(b,n);Word weak=virt<Word>(r,0x20,3u,plant,0u,0u);
  field(b,r,d,"iris_theatre_started",0x18,integer);field(b,r,d,"iris_theatre_house",0x1c,weak);field(b,r,d,"iris_theatre_previous",0x24,number);field(b,r,d,"iris_theatre_selection",0x28,weak);
  for(Word i=0;i<45;++i){char label[32];indexName(label,"iris_tower",i,"Plant");field(b,r,d,label,0x40+i*16,weak);indexName(label,"iris_tower",i,"Tree");field(b,r,d,label,0x48+i*16,integer);indexName(label,"iris_tower",i,"Step");field(b,r,d,label,0x4c+i*16,integer);}
  for(Word i=0;i<45;++i){char label[32];indexName(label,"iris_launch",i,"Plant");field(b,r,d,label,0x320+i*32,weak);for(Word j=0;j<6;++j){indexName(label,"iris_launch",i,j==0?"Time":j==1?"X":j==2?"Y":j==3?"Z":j==4?"Velocity":"Active");field(b,r,d,label,0x328+i*32+j*4,j==5?integer:number);}}
 }else if(k==2){field(b,r,d,"IrisTheatreKind",0xd8,integer);field(b,r,d,"IrisTheatreSunDrop",0xdc,integer);field(b,r,d,"IrisTheatreHouseDamage",0xe0,number);
 }else{
  for(Word i=0;i<8;++i)field(b,r,d,i==0?"iris_theatre_initialized":i==1?"iris_theatre_destination":i==2?"iris_theatre_last":i==3?"iris_theatre_phase":i==4?"iris_theatre_phase_end":i==5?"iris_theatre_rewarded":i==6?"iris_theatre_next_skill":"iris_theatre_skill_index",0x190+i*4,i==2||i==4||i==6?number:integer);
  field(b,r,d,"iris_theatre_boost_until",0x1b0,number);field(b,r,d,"iris_theatre_skill_fired",0x1b4,integer);field(b,r,d,"iris_theatre_burn_next",0x1b8,number);
  n=text(b,"Effect_PopAnim");Word effect=virt<Word>(r,0x24,&n);drop(b,n);field(b,r,d,"iris_theatre_boost_effect",0x1bc,virt<Word>(r,0x20,3u,effect,0u,0u));
 }
}
static bool houseType(Byte*t){const char*s=t?at<const char*>(t,0x10):nullptr;const char*prefix="POPANIM_TOWERDEFEND_HOUSE_PIG_";if(!s)return false;while(*prefix)if(*s++!=*prefix++)return false;return true;}
static bool house(Word b,Byte*p){return houseType(p?weakObject(b,reinterpret_cast<Word*>(p+0xb8)):nullptr);}
static Byte*housePlant(Word b,Byte*m){Byte*p=weakObject(b,reinterpret_cast<Word*>(m+0x1c));if(p)return p;int rect[4]={0,4,1,1};MagnetList list={};call<void>(b,0x248120,&list,1u,rect);
 for(Byte**q=list.begin;q!=list.end;++q)if(house(b,*q)){p=*q;call<void>(b,0x13dea0,m+0x1c,0u,at<Word>(p,8),at<Word>(p,0xc));break;}if(list.begin)call<void>(b,0xb36928,list.begin);return p;}
static const char*plantName(Word i){switch(i){case 0:return "bloomerang";case 1:return "bonkchoy";case 2:return "citron";case 3:return "coconutcannon";case 4:return "fumeshroom";case 5:return "laser_bean";case 6:return "lightningreed";case 7:return "melonpult";case 8:return "peanut";case 9:return "peashooter";case 10:return "puffshroom";case 11:return "repeater";case 12:return "snapdragon";case 13:return "snowpea";case 14:return "splitpea";case 15:return "starfruit";case 16:return "threepeater";default:return "wintermelon";}}
static bool plantType(Word b,Word kind,Word*out){if(kind>=18)return false;const char*name=plantName(kind);Byte*map=*reinterpret_cast<Byte**>(b+0xd4ec98),*node=map?at<Byte*>(map,8):nullptr;
 for(Word i=0;node&&i<256;++i){const char*a=name,*c=at<const char*>(node,0x10);if(!c)return false;while(*a&&*a==*c){++a;++c;}int order=int(Byte(*a))-int(Byte(*c));
  if(!order){call<void>(b,0x13dea0,out,0u,at<Word>(node,0x18),at<Word>(node,0x1c));return out[0]||out[1];}node=at<Byte*>(node,order<0?8:0xc);
 }return false;}
static Byte*towerRecord(Byte*m,Byte*p){int x=at<int>(p,0x5c),y=at<int>(p,0x58);return x>=0&&x<9&&y>=0&&y<5?m+0x40+16*(x*5+y):nullptr;}
static void localInterval(Word b,Byte*p,float factor){if(!(factor>0&&factor<100))return;
 // Plant's own serialized MinMaxFloat initial/repeat launch intervals are
 // at 34/3c. Never alter the shared PlantPropertySheet or a global grade.
 for(Word o=0x34;o<=0x40;o+=4)at<float>(p,o)*=factor;
 float remaining=at<float>(p,0x70)-battleTime(b);if(remaining>0&&remaining<60)at<float>(p,0x70)=battleTime(b)+remaining*factor;
}
static void trackTowers(Word b,Byte*m,Byte*props){int rect[4]={0,0,9,5};MagnetList list={};call<void>(b,0x248120,&list,1u,rect);Word trees=at<Word>(props,0x2c);if(trees>4)trees=4;
 for(Byte**q=list.begin;q!=list.end;++q){Byte*p=*q,*record=p?towerRecord(m,p):nullptr;if(!record||house(b,p)||at<Word>(p,0x48)==3)continue;
  if(at<Word>(record,0)==at<Word>(p,8)&&at<Word>(record,4)==at<Word>(p,12))continue;
  call<void>(b,0x13dea0,record,0u,0u,0u);bool found=false;
  for(Word tree=0;tree<trees&&!found;++tree){Word count=at<Word>(props,0x1d0+40*tree);if(count>3)count=3;
   for(Word step=0;step<count;++step){Word type[2]={};Byte*info=props+0x1d4+40*tree+12*step;bool valid=plantType(b,at<Word>(info,0),type);
    bool match=valid&&type[0]==at<Word>(p,0xb8)&&type[1]==at<Word>(p,0xbc);call<void>(b,0x13dea0,type,0u,0u,0u);if(!match)continue;
    call<void>(b,0x13dea0,record,0u,at<Word>(p,8),at<Word>(p,12));at<Word>(record,8)=tree;at<Word>(record,12)=step;localInterval(b,p,at<float>(info,8));found=true;trace(b,"tower tracked",tree|(step<<8));break;
   }
  }
 }if(list.begin)call<void>(b,0xb36928,list.begin);
}
static Byte*nextUpgrade(Word b,Byte*m,Byte*p){Byte*config=props(b,m),*record=p?towerRecord(m,p):nullptr;if(!config||!record||at<Word>(record,0)!=at<Word>(p,8)||at<Word>(record,4)!=at<Word>(p,12))return nullptr;
 Word tree=at<Word>(record,8),step=at<Word>(record,12)+1;if(tree>=4||step>=3||step>=at<Word>(config,0x1d0+40*tree))return nullptr;return config+0x1d4+40*tree+12*step;
}
static bool upgrade(Word b,Byte*m,Byte*p){Byte*next=nextUpgrade(b,m,p),*board=battleBoard(b);if(!next||!board||at<Word>(p,0x48)!=4)return false;
 Word type[2]={};if(!plantType(b,at<Word>(next,0),type))return false;
 // Aster records the price of leaving the current tier, with zero on the
 // final tier. The next tier's cost is not the price of this upgrade.
 Word cost=at<Word>(next-12,4);if(cost>100000||!weakObject(b,type)){call<void>(b,0x13dea0,type,0u,0u,0u);return false;}
 if(!call<bool>(b,0x185658,board,cost)){call<void>(b,0x13dea0,type,0u,0u,0u);return false;}
 Byte*record=towerRecord(m,p);Word col=at<Word>(p,0x5c),row=at<Word>(p,0x58);Byte active=at<Byte>(p,0x61);
 call<void>(b,0x39df1c,p,col,row,type);call<void>(b,0x13dea0,type,0u,0u,0u);at<Byte>(p,0x61)=active;
 ++at<Word>(record,12);localInterval(b,p,at<float>(next,8));trace(b,"tower upgraded",at<Word>(next,0));return true;
}
static void updateLaunches(Word b,Byte*m);
static void tick(Word b,Byte*m){Byte*board=battleBoard(b),*p=props(b,m);if(!board||!p||at<Word>(board,0xa8)!=5||call<bool>(b,0x1872a8,board))return;
 updateLaunches(b,m);
 if(!at<Word>(m,0x18)){Byte*h=housePlant(b,m);if(!h)return;at<float>(h,0x4c)=float(at<Word>(p,0x24));at<Word>(m,0x18)=1;trace(b,"house initialized",at<Word>(p,0x24));}
 trackTowers(b,m,p);at<float>(m,0x24)=battleTime(b);
}
static Word input(Word b,Word*args){Byte*m=module(b),*board=reinterpret_cast<Byte*>(args[0]);if(!m||board!=battleBoard(b)||at<Word>(board,0xa8)!=5||call<bool>(b,0x1872a8,board))return 0;
 Byte*selected=weakObject(b,reinterpret_cast<Word*>(m+0x28));Word phase=args[3];if(phase==6)return args[1]==49&&selected?Word(upgrade(b,m,selected)):0;
 if(phase==4){call<void>(b,0x13dea0,m+0x28,0u,0u,0u);return selected!=nullptr;}
 if(phase!=0)return 0;float scale=screenScale(b),x=float(int(args[1]))/scale,y=float(int(args[2]))/scale;
 if(selected&&nextUpgrade(b,m,selected)){float dx=x-at<float>(selected,0x10),dy=y-at<float>(selected,0x14);if(dx>=16&&dx<=54&&dy>=-100&&dy<=-62){upgrade(b,m,selected);return 1;}}
 Byte*cursor=at<Byte*>(board,0x640);if(cursor&&!at<Byte>(cursor,0x10)&&!at<Word>(cursor,0x14)&&virt<Word>(cursor,0x2c))return 0;
 int rect[4]={0,0,9,5};MagnetList list={};call<void>(b,0x248120,&list,1u,rect);Byte*chosen=nullptr;
 for(Byte**q=list.begin;q!=list.end;++q){Byte*p=*q;if(!p||!nextUpgrade(b,m,p))continue;float dx=x-at<float>(p,0x10),dy=y-at<float>(p,0x14);if(dx>=-28&&dx<=28&&dy>=-58&&dy<=8){chosen=p;break;}}
 if(list.begin)call<void>(b,0xb36928,list.begin);if(chosen){call<void>(b,0x13dea0,m+0x28,0u,at<Word>(chosen,8),at<Word>(chosen,12));return 1;}call<void>(b,0x13dea0,m+0x28,0u,0u,0u);return 0;
}
static void priceNumber(Word b,Byte*m,Byte*g,Word value,int x,int y){Word digits[10],n=0;do{Word q=Word((static_cast<unsigned long long>(value)*0xcccccccdULL)>>35);digits[n++]=value-q*10+'0';value=q;}while(value&&n<10);
 Byte*str=call<Byte*>(b,0xb363dc,12+4*(n+1));at<Word>(str,0)=at<Word>(str,4)=n;at<Word>(str,8)=0;Word*out=reinterpret_cast<Word*>(str+12);for(Word i=0;i<n;++i)out[i]=digits[n-i-1];out[n]=0;
 Byte*widget=at<Byte*>(m,0x310);if(!widget){Word color[4]={255,255,255,255},font=**reinterpret_cast<Word**>(b+0xd00b20);Byte*config=call<Byte*>(b,0xa321fc,font,float(x),float(y),80.0f,24.0f,&out,1u,1u,color);
  widget=call<Byte*>(b,0xb363dc,0xa8u);call<void>(b,0x846e0c,widget,config);at<Byte*>(m,0x310)=widget;
 }else{Byte*config=at<Byte*>(widget,0x9c);if(config){at<int>(config,0xc)=x;at<int>(config,0x10)=y;}call<void>(b,0x847294,widget,&out);}
 if(__atomic_fetch_sub(reinterpret_cast<int*>(out)-1,1,__ATOMIC_ACQ_REL)<=0)call<void>(b,0xb36928,reinterpret_cast<Byte*>(out)-12);virt<void>(widget,0x8c,g);
}
static void upgradeHud(Word b,Byte*board,Byte*g){Byte*m=module(b),*p=m?weakObject(b,reinterpret_cast<Word*>(m+0x28)):nullptr;if(board!=battleBoard(b)||!p||!g||call<bool>(b,0x1872a8,board))return;Byte*next=nextUpgrade(b,m,p);if(!next)return;
 Byte*ref=state(b)+0x100+7*24;at<const char*>(ref,0xc)="IMAGE_UI_HUD_INGAME_PLANT_LEVEL_UP";Byte*image=call<Byte*>(b,0x1524d8,ref);if(!image)return;
 float scale=screenScale(b),sx=at<float>(g,0x10),sy=at<float>(g,0x14),ox=at<float>(g,0x18),oy=at<float>(g,0x1c);
 int x=int(ox+((at<float>(p,0x10)+16)*scale-ox)*sx),y=int(oy+((at<float>(p,0x14)-100)*scale-oy)*sy);
 call<void>(b,0x7d53cc,g,image,x,y,int(38*scale*sx),int(38*scale*sy));
 priceNumber(b,m,g,at<Word>(next-12,4),x-int(20*scale*sx),y+int(36*scale*sy));
}
static void animation(Word b,Byte*z,const char*label,bool loop=true){Byte*r=weakObject(b,reinterpret_cast<Word*>(z+0x40));if(!r)return;char*s=text(b,label);Word empty[6]={};call<void>(b,loop?0x44d220:0x44d0b0,r,&s,loop?3u:0u,empty,empty);drop(b,s);}
static int row(Word b,float y){Word chosen=0;float best=100000;for(Word i=0;i<5;++i){float d=float(call<int>(b,0x1814a4,battleBoard(b),i))-y;if(d<0)d=-d;if(d<best){best=d;chosen=i;}}return int(chosen);}
static int nextCell(Byte*p,int current){int x=int(fifth(Word(current))),y=current-x*5,dist=at<int>(p,0x60+current*8);if(dist<=0)return -1;int candidates[4]={x?current-5:-1,x<8?current+5:-1,y?current-1:-1,y<4?current+1:-1};
 for(Word i=0;i<4;++i)if(candidates[i]>=0&&at<int>(p,0x60+candidates[i]*8)==dist-1)return candidates[i];return -1;}
static void reward(Word b,Byte*z){if(at<Word>(z,0x1a4))return;at<Word>(z,0x1a4)=1;Byte*p=zprops(b,z);if(!p)return;Word left=at<Word>(p,0xdc),total=0;if(left>10000)return;
 while(left>=5){Word value=left>=25?25u:5u;char*s=text(b,value==25?"iris_dark_sun":"sun_small");Byte*c=call<Byte*>(b,0x17b6e4,battleBoard(b),&s);drop(b,s);if(!c)break;
  float position[3]={at<float>(z,0x10),at<float>(z,0x14),0};virt<void>(c,0x58,position);float velocity[3]={float(int(total&7u)*12-36),5,200},accel[3]={0,0,-600};call<void>(b,0x1d2fe0,c,velocity,accel,1u);call<void>(b,0x1d2cc4,c);total+=value;left-=value;}
 trace(b,"authored sun reward",total);
}
#include "theatre_wolf.inc"
static void actorUpdate(Word b,Byte*z){Byte*m=module(b),*p=props(b,m),*board=battleBoard(b);if(!m||!p||!board){call<void>(b,0x5dfc80,z);return;}
 if(!alive(z)){reward(b,z);call<void>(b,0x5dfc80,z);return;}if(at<Word>(board,0xa8)!=5||call<bool>(b,0x1872a8,board))return;
 if(!at<Word>(z,0x190)){at<Word>(z,0x190)=1;int r=row(b,at<float>(z,0x14));at<Word>(z,0x194)=40+r;
  Word wave=at<Word>(z,0xc0);if(wave>1000)wave=0;float multiplier=1.0f+float(wave)*at<float>(p,0x28);at<float>(z,0xb0)*=multiplier;at<float>(z,0x34)*=multiplier;at<float>(z,0xbc)*=multiplier;animation(b,z,"walk");}
 Word destination=at<Word>(z,0x194);if(destination>=45)return;
 // Use the native displacement, including freeze, slow and speed changes.
 // Reorient only that displacement along the authored adjacent carpet.
 float x=at<float>(z,0x10),y=at<float>(z,0x14);Word a=at<Word>(z,0x68),c=at<Word>(z,0x70);at<Word>(z,0x68)=at<Word>(z,0x70)=0;at<Word>(z,0xa8)|=1u;
 call<void>(b,0x5dfc80,z);at<Word>(z,0x68)=a;at<Word>(z,0x70)=c;if(!alive(z)){reward(b,z);return;}
 float dt=battleTime(b)-at<float>(z,0x198);if(dt<0||dt>1)dt=0;at<float>(z,0x198)=battleTime(b);boostVisual(b,z);
 if(wolfSkill(b,z,p,dt)){float still[3]={x,y,at<float>(z,0x18)};virt<void>(z,0x58,still);return;}
 float travel=at<float>(z,0x10)-x;if(travel<0)travel=-travel;if(travel>100)travel=0;if(battleTime(b)<at<float>(z,0x1b0))travel*=2;
 Word column=fifth(destination);float tx=float(call<int>(b,0x17d518,board,column)),ty=float(call<int>(b,0x1814a4,board,destination-column*5));float dx=tx-x,dy=ty-y,distance=__builtin_sqrtf(dx*dx+dy*dy);
 if(distance<=travel+0.01f){x=tx;y=ty;int next=nextCell(p,int(destination));
  if(next<0){float goal[3]={tx,ty,at<float>(z,0x18)};virt<void>(z,0x58,goal);Byte*h=housePlant(b,m),*zp=zprops(b,z);if(h&&zp){struct{Byte*source;float amount;Word flags;Word conditions[3];}hit={z,at<float>(zp,0xe0),0,{}};virt<void>(h,0x34,&hit);trace(b,"house reached",Word(hit.amount));}at<Word>(z,0x1a4)=1;call<void>(b,0x5e147c,z,0u);return;}
  at<Word>(z,0x194)=Word(next);
 }else if(distance>0){x+=dx*travel/distance;y+=dy*travel/distance;}
 if(dx>0.01f)at<Word>(z,0xac)=1;else if(dx< -0.01f)at<Word>(z,0xac)=0;
 float point[3]={x,y,at<float>(z,0x18)};virt<void>(z,0x58,point);at<float>(z,0x198)=battleTime(b);
}
static Word planting(Word b,Byte*board,int*cell,Word*type){Byte*m=module(b),*p=props(b,m);if(p&&board==battleBoard(b)&&cell&&cell[0]>=0&&cell[0]<9&&cell[1]>=0&&cell[1]<5){
 int index=cell[0]*5+cell[1];if(at<int>(p,0x60+index*8)>=0&&!houseType(weakObject(b,type)))return 10;}
 return call<Word>(b,IRIS_THEATRE_PLANTING,board,cell,type);}
static const char*roadImage(Word i){switch(i){case 0:return "IMAGE_BACKGROUNDS_THEATRE_DARK_RUG_BOTOOM_LEFT";case 1:return "IMAGE_BACKGROUNDS_THEATRE_DARK_RUG_BOTOOM_RIGHT";case 2:return "IMAGE_BACKGROUNDS_THEATRE_DARK_RUG_D_TOP";case 3:return "IMAGE_BACKGROUNDS_THEATRE_DARK_RUG_LEFT";case 4:return "IMAGE_BACKGROUNDS_THEATRE_DARK_RUG_TOP_CENTRE";case 5:return "IMAGE_BACKGROUNDS_THEATRE_DARK_RUG_TOP_LEFT";default:return "IMAGE_BACKGROUNDS_THEATRE_DARK_RUG_TOP_RIGHT";}}
static void draw(Word b,Byte*board,Byte*g){Byte*m=module(b),*p=props(b,m);if(!p||board!=battleBoard(b)||!g)return;call<void>(b,0x7d2810,g);
 float scale=screenScale(b),sx=at<float>(g,0x10),sy=at<float>(g,0x14),ox=at<float>(g,0x18),oy=at<float>(g,0x1c);
 for(Word i=0;i<45;++i)if(at<int>(p,0x60+i*8)>=0){Word kind=at<Word>(p,0x64+i*8);if(kind>=7)continue;Byte*ref=state(b)+0x100+kind*24;at<const char*>(ref,0xc)=roadImage(kind);Byte*image=call<Byte*>(b,0x1524d8,ref);Word column=fifth(i);if(image)call<void>(b,0x7d53cc,g,image,int(ox+((200+int(column)*64)*scale-ox)*sx),int(oy+((160+int(i-column*5)*76)*scale-oy)*sy),int(64*scale*sx),int(76*scale*sy));}
 call<void>(b,0x7d2940,g);
}
static void destroyModule(Word b,Byte*m,bool remove){Byte*label=at<Byte*>(m,0x310);if(label)virt<void>(label,0xc);call<void>(b,0x13dea0,m+0x1c,0u,0u,0u);call<void>(b,0x13dea0,m+0x28,0u,0u,0u);for(Word i=0;i<45;++i){call<void>(b,0x13dea0,m+0x40+i*16,0u,0u,0u);Byte*r=m+0x320+i*32,*p=weakObject(b,reinterpret_cast<Word*>(r));if(p){float pos[3]={at<float>(r,12),at<float>(r,16),at<float>(r,20)};at<Byte>(p,0x61)=Byte(at<Word>(r,28));virt<void>(p,0x58,pos);}call<void>(b,0x13dea0,r,0u,0u,0u);}at<void(*)(Byte*)>(reinterpret_cast<Byte*>(b+0xcd37b8),8)(m);if(remove)call<void>(b,0xb36928,m);}
extern "C" __attribute__((section(".text.entry")))
Word iris_theatre(Word b,Word*args,Word mode){
 if(mode==0){call<void>(b,IRIS_THEATRE_REGISTER);metadata(b);return 0;}
 if(mode==31){Word ready=call<Word>(b,IRIS_THEATRE_READY,args[0],args[1]);
#if IRIS_DARK_TRACE
  if(!ready&&battleBoard(b)){Word&count=at<Word>(state(b),0x70);if(!count){Byte*v=reinterpret_cast<Byte*>(args[1]);Word begin=at<Word>(v,0),end=at<Word>(v,4);
   if(begin&&end>=begin&&end-begin<=2048)for(Word p=begin;p<end;p+=4)if(!call<bool>(b,0x2c8658,args[0],p))call<int>(b,0xe8c10,3,"IrisDark","Theatre pending resource group %s",*reinterpret_cast<const char**>(p));}
   if(++count>=120)count=0;
  }
#endif
  return ready;
 }
 if(mode>=1&&mode<=4){Word k=mode-1,n=bytes(k);Byte*p=call<Byte*>(b,0xb363dc,n);for(Word i=0;i<n;i+=4)at<Word>(p,i)=0;
  if(k==2){Byte*base=call<Byte*>(b,0x12c770);for(Word i=0;i<0xd8;i+=4)at<Word>(p,i)=at<Word>(base,i);call<void>(b,0xb36928,base);}
  if(k==3)call<void>(b,0x5de8b8,p);at<Byte*>(p,0)=at<Byte*>(state(b),0x20+k*4);trace(b,"created owned class",k);return reinterpret_cast<Word>(p);}
 if(mode>=5&&mode<=8)return at<Word>(state(b),(mode-5)*4);
 if(mode>=9&&mode<=12){schema(b,reinterpret_cast<Byte*>(args[0]),reinterpret_cast<Byte*>(args[1]),mode-9);return 0;}
 Byte*p=reinterpret_cast<Byte*>(args[0]);
 if(mode==13){actorUpdate(b,p);return 0;}
 if(mode==14){Word value=call<Word>(b,0x5e0b74,p,reinterpret_cast<Byte*>(args[1]));if(!alive(p))reward(b,p);return value;}
 if(mode==15||mode==16){clearBoostEffect(b,p);call<void>(b,0x5deafc,p);if(mode==16)call<void>(b,0xb36928,p);return 0;}
 if(mode==17){Word value=call<Word>(b,IRIS_THEATRE_UPDATE,p);if(p==battleBoard(b)){Byte*m=module(b);if(m)tick(b,m);}return value;}
 if(mode==18)return planting(b,p,reinterpret_cast<int*>(args[1]),reinterpret_cast<Word*>(args[2]));
 if(mode==19){Word value=call<Word>(b,IRIS_THEATRE_COLLECT,args[0],args[1]);Byte*board=battleBoard(b),*m=module(b);Word*count=reinterpret_cast<Word*>(args[1]);
  if(m&&props(b,m)&&board&&*count<4096){Byte*item=p+36*(*count);for(Word i=0;i<36;i+=4)if(i!=8)at<Word>(item,i)=0;at<Word>(item,0)=14;at<Word>(item,4)=100002;at<Byte*>(item,0xc)=board;at<Word>(item,0x1c)=stub(b,20);++*count;}return value;}
 if(mode==20){draw(b,at<Byte*>(p,4),reinterpret_cast<Byte*>(args[1]));return 0;}
 if(mode==21)return 0xffffffffu;if(mode==25)return 0;
 if(mode==22||mode==23){destroyModule(b,p,mode==23);return 0;}
 if(mode==24)return at<Word>(state(b),4);
 if(mode==26)return input(b,args);if(mode==27){upgradeHud(b,p,reinterpret_cast<Byte*>(args[1]));return 0;}
 if(mode==28){Byte*m=module(b);if(m&&launchedPlant(m,p))return 0;return call<Word>(b,IRIS_THEATRE_PLANT_UPDATE,p);}
 return 0;
}
