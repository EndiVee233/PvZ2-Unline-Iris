// Level properties stay data-driven; all spawned jars are saved GridItems.
static Byte*moduleState(Word b){return reinterpret_cast<Byte*>(b+0xf80f00);}
static void moduleMetadata(Word b){
 Byte*s=moduleState(b);
 if(!at<Word>(s,0))for(Word i=0;i<2;++i){
  Byte*m=call<Byte*>(b,0xb363dc,40u);call<void>(b,0x894ca0,m);at<Byte*>(s,i*4)=m;
  call<void>(b,0x895608,m,i?"ZombiePotionModule":"ZombiePotionModuleProperties",call<Byte*>(b,i?0x1341d8:0x134100),stub(b,19+i));
  Byte*t=call<Byte*>(b,0xb363dc,0x44u);for(Word o=0;o<0x44;o+=4)at<Word>(t,o)=*reinterpret_cast<Word*>(b+(i?0xcd37b8:0xcdd658)+o);
  at<Word>(t,0)=stub(b,21+i);at<Byte*>(s,8+i*4)=t;
  if(!i)at<Word>(t,0x38)=stub(b,25);
  // Base LevelModule slots are lifecycle events, not per-frame updates.
 }
 Byte*m=call<Byte*>(b,0x851728),*r=m?call<Byte*>(b,0x851920,m):nullptr;
 if(r&&!at<Word>(s,0x10)){at<Word>(s,0x10)=1;for(Word i=0;i<2;++i){char*n=text(b,i?"ZombiePotionModule":"ZombiePotionModuleProperties");virt<void>(r,0xc,&n,stub(b,23+i),i?0x20u:0x34u,0u);drop(b,n);}}
}
static void moduleSchema(Word b,Byte*r,Byte*d,bool module){
 Byte*m=at<Byte*>(moduleState(b),module?4:0);at<Byte*>(m,0x24)=d;at<Byte*>(d,0x5c)=m;
 char*n=text(b,module?"LevelModule":"LevelModuleProperties");Byte*p=virt<Byte*>(r,0x24,&n);drop(b,n);virt<void>(r,0x28,d,virt<Word>(p,0x34),0u);
 Word integer=virt<Word>(r,0x14,6u,4u),number=virt<Word>(r,0x14,8u,4u);
 if(module){field(b,r,d,"iris_next_potion_spawn",0x18,number);field(b,r,d,"iris_initial_potions_spawned",0x1c,integer);}
 else{field(b,r,d,"InitialPotionCount",0x20,integer);field(b,r,d,"MaxPotionCount",0x24,integer);
  field(b,r,d,"IrisMinSpawnDelay",0x28,number);field(b,r,d,"IrisMaxSpawnDelay",0x2c,number);field(b,r,d,"IrisPotionMask",0x30,integer);}
}
static bool isPotion(Word b,Byte*p){if(!p)return false;Byte*m=virt<Byte*>(p,0);return (m==at<Byte*>(state(b),0)||m==at<Byte*>(state(b),4))&&!at<Word>(p,0x5c);}
static bool spawnPotion(Word b,Byte*props,Word*count){
 bool occupied[45]={},potions[45]={};int rect[4]={0,0,9,5};MagnetList list={};call<void>(b,0x248120,&list,5u,rect);*count=0;
 for(Byte**q=list.begin;q!=list.end;++q){Byte*p=*q;if(!p)continue;Byte*m=virt<Byte*>(p,0);if(m==at<Byte*>(state(b),8))continue;
  bool plant=false;for(Word i=0;m&&i<32;++i,m=at<Byte*>(m,8))if(equalText(at<const char*>(m,4),"Plant")){plant=true;break;}
  int x=int(at<Word>(p,plant?0x5c:0x44)),y=int(at<Word>(p,plant?0x58:0x48));if(x<0||x>8||y<0||y>4)continue;
  occupied[y*9+x]=true;if(isPotion(b,p)){potions[y*9+x]=true;++*count;}
 }
 if(list.begin)call<void>(b,0xb36928,list.begin);
 Word max=at<Word>(props,0x24);if(*count>=max)return false;
 int columns[5];Word weights[5]={},sum=0;
 for(int y=0;y<5;++y){columns[y]=-1;Word n=0;for(int x=8;x>=0;--x){if(potions[y*9+x]){++n;continue;}if(occupied[y*9+x])continue;columns[y]=x;weights[y]=n<9?360u>>n:0;sum+=weights[y];break;}}
 if(!sum)return false;Word choice=call<Word>(b,0x7a3e90,sum);int row=0;for(;row<5;++row){if(choice<weights[row])break;choice-=weights[row];}if(row==5)return false;
 Word mask=at<Word>(props,0x30);bool speed=mask==3?call<Word>(b,0x7a3e90,2u)==0:(mask&1)!=0;if(!(mask&3))return false;
 char*n=text(b,speed?"zombiepotion_speed":"zombiepotion_toughness");Byte*p=call<Byte*>(b,0x17a8c4,battleBoard(b),&n,columns[row],row);drop(b,n);
 if(p){++*count;trace(b,"spawned jar",Word(columns[row])|(Word(row)<<8)|(speed?0x10000u:0x20000u));}return p!=nullptr;
}
static float potionDelay(Word b,Byte*p){float min=at<float>(p,0x28),max=at<float>(p,0x2c);if(min<0.1f)min=0.1f;if(max<min)max=min;Word span=Word((max-min)*1000)+1;return min+float(call<Word>(b,0x7a3e90,span))/1000;}
static void moduleTick(Word b,Byte*m,Word callback){
 Byte*board=battleBoard(b);if(!board)return;Word stage=at<Word>(board,0xa8);if(stage!=4&&stage!=5)return;
 Byte*p=weakObject(b,reinterpret_cast<Word*>(m+0x10));if(!p)return;
 Byte*s=moduleState(b);if(!at<Word>(s,0x14)){at<Word>(s,0x14)=1;trace(b,"battle update connected",callback);}
 if(call<bool>(b,0x1872a8,board))return;float now=battleTime(b);Word count=0;
 if(!at<Word>(m,0x1c)){at<Word>(m,0x1c)=1;Word initial=at<Word>(p,0x20);if(initial>45)initial=45;for(Word i=0;i<initial;++i)if(!spawnPotion(b,p,&count))break;at<float>(m,0x18)=now+potionDelay(b,p);}
 if(stage==5&&now>=at<float>(m,0x18)){spawnPotion(b,p,&count);at<float>(m,0x18)=now+potionDelay(b,p);}
}
static void boardPotionTick(Word b,Byte*board){
 if(!board||board!=battleBoard(b)||at<Byte>(board,0x671))return;
 Byte*manager=at<Byte*>(board,0x62c),*meta=at<Byte*>(moduleState(b),4);if(!manager||!meta)return;
 // Ask the current board for its owned module on every update. No transient
 // module pointer survives a restart, map transition or deserialization.
 Byte*m=ownedLevelModule(b,board,meta);if(m)moduleTick(b,m,26);
}
