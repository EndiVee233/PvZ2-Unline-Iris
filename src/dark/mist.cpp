// Serializable Iris LevelModule implementation of Aster's WarMist.
// Metadata and transient pointers occupy the framework's separate RW page.
using Byte=unsigned char;using Word=unsigned int;
template<class T>static T&at(Byte*p,Word o){return *reinterpret_cast<T*>(p+o);}
template<class R,class...A>static R call(Word b,Word p,A...a){return reinterpret_cast<R(*)(A...)>(b+p)(a...);}
template<class R,class...A>static R virt(Byte*p,Word o,A...a){return at<R(*)(Byte*,A...)>(at<Byte*>(p,0),o)(p,a...);}
static char*text(Word b,const char*s){char*r,a;call<void>(b,0xb75560,&r,s,&a);return r;}
static void drop(Word b,char*s){char a;if(__atomic_fetch_sub(reinterpret_cast<int*>(s-4),1,__ATOMIC_ACQ_REL)<=0)call<void>(b,0xb76c4c,s-12,&a);}
static void log(Word b,const char*s,Word v){
#if IRIS_DARK_TRACE
 call<int>(b,0xe8c10,3,"IrisDark","Mist %s value=%x",s,v);
#endif
}
static bool same(const char*a,const char*b){if(!a||!b)return false;while(*a&&*a==*b){++a;++b;}return *a==*b;}
static Byte*rw(Word b){return reinterpret_cast<Byte*>(b+0xf80100);}
static Byte*resolve(Word b,Word*w){
 Byte*r=call<Byte*>(b,0x8821a8);Word h[2]={};call<void>(b,0x8890c4,h,r,w);Byte*out=nullptr;
 if(h[0]||h[1]){Byte*q=call<Byte*>(b,0x888b8c,r,(h[1]<<1)>>18);if(q)out=call<Byte*>(b,0x884378,q,h);}
 call<void>(b,0x13dea0,h,0u,0u,0u);return out;
}
static Word stub(Word b,Word i){return b+IRIS_MIST_STUB+i*40;}
static void registerTypes(Word b){
 Byte*s=rw(b);
 if(!at<Word>(s,0)){
  const Word parents[]={0x134100,0x1341d8},tables[]={0xcdd658,0xcd37b8};
  for(Word i=0;i<2;++i){
   Byte*m=call<Byte*>(b,0xb363dc,40u);call<void>(b,0x894ca0,m);at<Byte*>(s,i*4)=m;
   call<void>(b,0x895608,m,i?"WarMistModule":"WarMistProperties",call<Byte*>(b,parents[i]),stub(b,i+1));
   Byte*t=call<Byte*>(b,0xb363dc,0x44u);
   for(Word o=0;o<0x44;o+=4)at<Word>(t,o)=*reinterpret_cast<Word*>(b+tables[i]+o);
   at<Word>(t,0)=stub(b,i+3);at<Byte*>(s,8+i*4)=t;
   if(i==0)at<Word>(t,0x38)=stub(b,7);
   else{at<Word>(t,8)=stub(b,8);at<Word>(t,0xc)=stub(b,9);}
  }
  log(b,"runtime classes created",1);
 }
 Byte*manager=call<Byte*>(b,0x851728);if(!manager||at<Word>(s,0x14))return;
 Byte*r=call<Byte*>(b,0x851920,manager);if(!r)return;at<Word>(s,0x14)=1;
 for(Word i=0;i<2;++i){char*n=text(b,i?"WarMistModule":"WarMistProperties");virt<void>(r,0xc,&n,stub(b,5+i),i?0x180u:0x2cu,0u);drop(b,n);}
}
static void reflect(Word b,Byte*r,Byte*d,bool module){
 Byte*s=rw(b),*meta=at<Byte*>(s,module?4:0);at<Byte*>(meta,0x24)=d;at<Byte*>(d,0x5c)=meta;
 char*n=text(b,module?"LevelModule":"LevelModuleProperties");Byte*p=virt<Byte*>(r,0x24,&n);drop(b,n);
 virt<void>(r,0x28,d,virt<Word>(p,0x34),0u);
 Word count=module?6u:3u;
 for(Word i=0;i<count;++i){const char*label=module?(i==0?"iris_started":i==1?"iris_previous":i==2?"iris_offset":i==3?"iris_blow_end":i==4?"iris_blover_uid_low":"iris_blover_uid_high"):(i==0?"m_iNormValX":i==1?"m_iBloverEffectInterval":"m_iInitMistPosX");n=text(b,label);Word type=virt<Word>(r,0x14,((!module&&i==2)||(module&&i>=4))?6u:8u,4u);
  virt<void>(r,0x2c,d,&n,(module?0x18:0x20)+i*4,type);drop(b,n);}
}
struct List{Byte**begin,**end,**capacity;};
struct ImageRef{Word prefix[3];const char*name;Word weak[2];};
static float now(Word b){Byte*c=*reinterpret_cast<Byte**>(b+0xd4ed90);return c?at<float>(c,0x1c):0;}
static bool lamp(Word b,Byte*p){Byte*t=resolve(b,reinterpret_cast<Word*>(p+0xb8));return t&&same(at<const char*>(t,0x10),"POPANIM_PLANT_STREETLAMP");}
static void lighting(Word b,bool*lit,float time){
 int rect[4]={0,0,16,5};List list={};call<void>(b,0x248120,&list,1u,rect);
 for(Byte**q=list.begin;q!=list.end;++q){Byte*p=*q;if(!p||at<Word>(p,0x48)==3||!lamp(b,p))continue;
  Byte*f=at<Byte*>(p,0x30);bool food=f&&time<at<float>(f,0x10);
  int pc=int(at<Word>(p,0x5c)),pr=int(at<Word>(p,0x58));
  for(int y=-1;y<6;++y)for(int x=0;x<9;++x){int dx=x-pc,dy=y-pr;int ax=dx<0?-dx:dx,ay=dy<0?-dy:dy;
   // Aster removes the four diagonal corners and leaves only the centre
   // column on the outermost rows, rather than a rectangular floodlight.
   if(food||(ay<=2&&ax<=3&&(ay==2?ax==0:ax+ay!=4)))lit[(y+1)*9+x]=true;
  }
 }
 if(list.begin)call<void>(b,0xb36928,list.begin);
}
static void drawMist(Word b,Byte*board,Byte*g){
 Byte*s=rw(b),*m=at<Byte*>(s,0x10);if(!m||!board)return;
 Byte*app=**reinterpret_cast<Byte***>(b+0xd00838);if(!app||at<Byte*>(app,0x6c0)!=board)return;
 Byte*props=resolve(b,reinterpret_cast<Word*>(m+0x10));if(!props)return;
 Word stage=at<Word>(board,0xa8);if(stage!=4&&stage!=5)return;
 float time=now(b),dt=time-at<float>(m,0x1c);if(dt<0||dt>0.2f)dt=0;
 if(at<Byte>(board,0x671))dt=0;
 if(at<float>(m,0x18)<0){at<float>(m,0x18)=time;log(b,"battle active",at<Word>(props,0x28));log(b,"app scale",at<Word>(app,0x6a0));log(b,"graphics scale",at<Word>(g,0x10));Byte*root=at<Byte*>(board,0x590);if(root){Byte*vt=at<Byte*>(root,0);log(b,"root drawer",reinterpret_cast<Word>(vt)-b);log(b,"root draw",at<Word>(vt,0)-b);}}
 at<float>(m,0x1c)=time;
 int first=int(at<Word>(props,0x28));if(first<0)first=0;if(first>9)first=9;
 float target=-float(9-first)*64;
 bool blown=time<at<float>(m,0x24);if(blown)target=64;
 float&offset=at<float>(m,0x20);float delta=target-offset;
 float speed=at<float>(props,0x20);if(speed<1||speed>2000)speed=700;
 if(delta>speed*dt)delta=speed*dt;if(delta< -speed*dt)delta=-speed*dt;offset+=delta;
 bool lit[63]={};lighting(b,lit,time);
 auto*refs=reinterpret_cast<ImageRef*>(m+0x30);
 Byte*images[3]={};for(Word i=0;i<3;++i){refs[i].name=i==0?"IMAGE_UI_MISTY_MISTY_1":i==1?"IMAGE_UI_MISTY_MISTY_2":"IMAGE_UI_MISTY_MISTY_3";images[i]=call<Byte*>(b,0x1524d8,refs+i);}
 // Each cell is clipped independently, so plants, zombies and shots remain
 // genuinely hidden while a lamp opens a hole through the moving mist.
 for(int row=-1;row<6;++row)for(int col=0;col<9;++col){
  Word cell=Word((row+1)*9+col);
  float&a=at<float>(m,0x80+cell*4);float goal=lit[cell]?0.0f:1.0f;
  if(a<goal){a+=dt*0.5f;if(a>goal)a=goal;}else{a-=dt*0.5f;if(a<goal)a=goal;}
  if(a<0.004f)continue;
  int left=200+col*64,top=160+row*76;
  int rgba[4]={255,255,255,int(a*255)};
  // Original three fog variants, anchored at the right edge and moving in
  // from off-board. Fourfold repetitions cover the authored 9x5 lawn.
  for(int x=0;x<9;++x){int fx=180+9*64+x*64+int(offset);
   if(fx>left+64||fx+257<left)continue;
   for(int y=-1;y<6;++y){int fy=140+y*76;if(fy>top+76||fy+296<top)continue;
    Word n=Word(x+y+3),quotient=Word((static_cast<unsigned long long>(n)*0xaaaaaaabULL)>>33);
    Word index=n-quotient*3;Byte*im=images[index];if(!im)continue;
    int x0=fx>left?fx:left,y0=fy>top?fy:top;
    int x1=fx+257<left+64?fx+257:left+64,y1=fy+296<top+76?fy+296:top+76;
    if(x0>=x1||y0>=y1)continue;
    // Clip the source rectangle as well as its destination. Graphics' old
    // backend-only ClipRect is overwritten by DrawImage and would leak
    // over the HUD; fragment geometry respects the board's zoom matrix.
    float sx=float(at<int>(im,0x28))/257.0f,sy=float(at<int>(im,0x2c))/296.0f;
    float scale=at<float>(app,0x6a0),zx=at<float>(g,0x10),zy=at<float>(g,0x14);
    float ox=at<float>(g,0x18),oy=at<float>(g,0x1c);
    int dx0=int(at<float>(g,8)+ox+(float(x0)*scale-ox)*zx);
    int dy0=int(at<float>(g,0xc)+oy+(float(y0)*scale-oy)*zy);
    int dx1=int(at<float>(g,8)+ox+(float(x1)*scale-ox)*zx);
    int dy1=int(at<float>(g,0xc)+oy+(float(y1)*scale-oy)*zy);
    int dest[4]={dx0,dy0,dx1-dx0,dy1-dy0};
    int source[4]={int(float(x0-fx)*sx),int(float(y0-fy)*sy),int(float(x1-x0)*sx+0.5f),int(float(y1-y0)*sy+0.5f)};
    if(source[2]<1||source[3]<1)continue;
    call<void>(b,0x7d27f0,g);
    virt<void>(at<Byte*>(g,0x6c),0x4c,im,dest,source,g+0x20,rgba,at<Word>(g,0x60),at<Byte>(g,0x65),0u);
   }
  }
 }
}
extern "C" __attribute__((section(".text.entry")))
Word iris_mist(Word b,Word*args,Word mode){
 if(mode==0){call<void>(b,IRIS_MIST_REGISTER_ORIGINAL);registerTypes(b);return 0;}
 Byte*s=rw(b);
 if(mode==1||mode==2){bool mod=mode==2;Word size=mod?0x180u:0x2cu;
  Byte*p=call<Byte*>(b,0xb363dc,size);for(Word o=0;o<size;o+=4)at<Word>(p,o)=0;
  at<Byte*>(p,0)=at<Byte*>(s,mod?0xc:8);
  if(mod){at<float>(p,0x18)=-1;at<float>(p,0x1c)=-1;at<Byte*>(s,0x10)=p;log(b,"module created",reinterpret_cast<Word>(p));}
  else{at<float>(p,0x20)=700;at<float>(p,0x24)=15;at<Word>(p,0x28)=5;}
  return reinterpret_cast<Word>(p);
 }
 if(mode==3||mode==4||mode==7)return at<Word>(s,mode==3?0:4);
 if(mode==5||mode==6){reflect(b,reinterpret_cast<Byte*>(args[0]),reinterpret_cast<Byte*>(args[1]),mode==6);return 0;}
 if(mode==8||mode==9){Byte*m=reinterpret_cast<Byte*>(args[0]);if(at<Byte*>(s,0x10)==m)at<Byte*>(s,0x10)=nullptr;
  auto*refs=reinterpret_cast<ImageRef*>(m+0x30);for(Word i=0;i<3;++i)call<void>(b,0x13dea0,refs[i].weak,0u,0u,0u);
  return call<Word>(b,mode==8?0x141444:0x14148c,m);
 }
 if(mode==11){
  Word result=call<Word>(b,IRIS_MIST_REGISTER_ORIGINAL+12,args[0]);
  Byte*m=at<Byte*>(s,0x10);Byte*p=m?resolve(b,reinterpret_cast<Word*>(m+0x10)):nullptr;
  Byte*f=reinterpret_cast<Byte*>(args[0]),*plant=at<Byte*>(f,4);
  if(p&&plant&&(at<Word>(m,0x28)!=at<Word>(plant,8)||at<Word>(m,0x2c)!=at<Word>(plant,0xc))){
   at<Word>(m,0x28)=at<Word>(plant,8);at<Word>(m,0x2c)=at<Word>(plant,0xc);
   at<float>(m,0x24)=now(b)+at<float>(p,0x24);log(b,"blover cleared fog",15);
  }
  return result;
 }
 if(mode==13){
  if(!at<Word>(s,0x18)){log(b,"collector entered",args[0]);at<Word>(s,0x18)=1;}
  Word result=call<Word>(b,0x537e38,args[0],args[1]);
  Byte*m=at<Byte*>(s,0x10);Byte*a=**reinterpret_cast<Byte***>(b+0xd00838);Byte*board=a?at<Byte*>(a,0x6c0):nullptr;
  Word*count=reinterpret_cast<Word*>(args[1]);
  if(m&&!at<Word>(s,0x1c)){log(b,"collector active count",*count);log(b,"collector board",reinterpret_cast<Word>(board));log(b,"collector props",at<Word>(m,0x10));for(Word i=0;i<*count&&i<64;++i){Byte*q=reinterpret_cast<Byte*>(args[0])+i*36;log(b,"initial render item",(at<Word>(q,0)<<24)|(at<Word>(q,4)&0xffffffu));}at<Word>(s,0x1c)=1;}
  if(m&&board&&*count<4096u&&resolve(b,reinterpret_cast<Word*>(m+0x10))){
   Byte*item=reinterpret_cast<Byte*>(args[0])+(*count)*36;
   // +8 is the fixed delegate vtable. RenderItem's sorter deliberately
   // preserves it in place and moves only the callable payload at +c..20.
   for(Word o=0;o<36;o+=4)if(o!=8)at<Word>(item,o)=0;
   // Iris's HUD renderers use 600000, followed by the 700000 cursor.
   // Keep mist over every lawn row but underneath those original widgets.
   at<Word>(item,0)=14;at<Word>(item,4)=599999;at<Byte*>(item,0xc)=board;at<Word>(item,0x1c)=stub(b,12);++*count;
   if(!at<Word>(s,0x20)){log(b,"render item appended",*count);at<Word>(s,0x20)=1;}
  }return result;
 }
 if(mode==12)drawMist(b,at<Byte*>(reinterpret_cast<Byte*>(args[0]),4),reinterpret_cast<Byte*>(args[1]));
 if(mode==10)drawMist(b,reinterpret_cast<Byte*>(args[0]),reinterpret_cast<Byte*>(args[1]));return 0;
}
