// Tier-one Fume-shroom: line damage and the five-second three-row food cloud.
// Uses Iris's combat/effect objects; no ranked plant or zombie subsystem.
using Byte=unsigned char;
using Word=unsigned int;
template<class T> static T &at(Byte *p,Word n){return *reinterpret_cast<T*>(p+n);}
template<class R,class... A> static R call(Word b,Word p,A... a){return reinterpret_cast<R(*)(A...)>(b+p)(a...);}
template<class R,class... A> static R virt(Byte*p,Word n,A... a){return at<R(*)(Byte*,A...)>(at<Byte*>(p,0),n)(p,a...);}
static bool same(const char*a,const char*b){if(!a||!b)return false;while(*a&&*a==*b){++a;++b;}return *a==*b;}
static Byte *resolve(Word b,Word*weak){
    Byte *reg=call<Byte*>(b,0x8821a8);Word w[2]={};
    call<void>(b,0x8890c4,w,reg,weak);Byte *out=nullptr;
    if(w[0]||w[1]){Byte *bucket=call<Byte*>(b,0x888b8c,reg,(w[1]<<1)>>18);if(bucket)out=call<Byte*>(b,0x884378,bucket,w);}
    call<void>(b,0x13dea0,w,0u,0u,0u);return out;
}
static bool ours(Word b,Byte *fw){
    Byte *plant=at<Byte*>(fw,4);if(!plant)return false;
    Byte *type=resolve(b,reinterpret_cast<Word*>(plant+0xb8));
    return type&&same(at<const char*>(type,0x10),"POPANIM_PLANT_FUMESHROOM");
}
static float now(Word b){Byte *clock=*reinterpret_cast<Byte**>(b+0xd4ed90);return clock?at<float>(clock,0x1c):0;}
static Byte *board(Word b){Byte *app=**reinterpret_cast<Byte***>(b+0xd00838);return app?at<Byte*>(app,0x6c0):nullptr;}
static void dropString(Word b,char*s){char a;if(__atomic_fetch_sub(reinterpret_cast<int*>(s-4),1,__ATOMIC_ACQ_REL)<=0)call<void>(b,0xb76c4c,s-12,&a);}
static void animation(Word b,Byte *plant,const char*label,bool loop){
    Byte *rig=virt<Byte*>(plant,0x70);if(!rig)return;
    char *s;char a;Word empty[6]={};call<void>(b,0xb75560,&s,label,&a);
    call<void>(b,loop?0x44d220:0x44d0b0,rig,&s,loop?3:0,empty,empty);dropString(b,s);
}
static void cloud(Word b,Byte *plant,bool food){
    Byte *bd=board(b);Byte *holder=**reinterpret_cast<Byte***>(b+0xd008bc);if(!bd||!holder)return;
    char *name;char a;Word weak[2]={};
    call<void>(b,0xb75560,&name,"POPANIM_EFFECTS_FUMESHROOM_BUBBLES",&a);
    Word kind=call<Word>(b,0x129ae0);
    // The resource lookup returns a non-trivial weak handle through an ARM
    // hidden result pointer: result first, then this. It is not an ordinary
    // this-first virtual call.
    at<void(*)(Word*,Byte*,Word,char**,Word)>(at<Byte*>(holder,0),8)(weak,holder,kind,&name,0u);
    dropString(b,name);
    Byte *resource=resolve(b,weak);call<void>(b,0x13dea0,weak,0u,0u,0u);if(!resource)return;
    Byte *effect=call<Byte*>(b,0x1809a8,bd);if(!effect)return;
    // 1809a8 allocates the board effect; 23a354 assigns its PopAnim resource.
    // The assignment's return value is not an effect pointer.
    call<void>(b,0x23a354,effect,resource,0u);
    call<void>(b,0xb75560,&name,food?"plantfood":"special",&a);
    call<void>(b,0x23aa6c,effect,&name,0u);dropString(b,name);
    float point[3]={at<float>(plant,0x10)-55.0f,at<float>(plant,0x14)-(food?115.0f:110.0f),0};
    call<void>(b,0x4e6bb8,effect,point,0xffffffffu);
    // Aster uses the authored canvas origin. Iris's true flag recentres
    // the entire cloud canvas and shifts the gas away from the mouth.
    call<void>(b,0x23a814,effect,0u);
}
struct Damage {Byte *source;float amount;Word flags;Word conditions[3];};
struct List {Byte **begin,**end,**capacity;};
static bool zombie(Byte *p){
    Byte *type=p?virt<Byte*>(p,0):nullptr;
    for(Word depth=0;type&&depth<32;++depth,type=at<Byte*>(type,8))
        if(same(at<const char*>(type,4),"Zombie"))return true;
    return false;
}
static bool heavy(Byte *p){
    Byte *type=virt<Byte*>(p,0);
    for(Word depth=0;type&&depth<32;++depth,type=at<Byte*>(type,8)){
        const char*n=at<const char*>(type,4);
        if(same(n,"ZombieGargantuar")||same(n,"ZombieGargantuarMech")||same(n,"ZombieDarkKing")||same(n,"ZombieIrisKing")
           ||same(n,"ZombieZombossMech")||same(n,"ZombieMech")||same(n,"ZombieBull"))return true;
    }return false;
}
static void push(Word b,Byte*z,float distance,float duration){
    Byte *bd=board(b);Byte *manager=bd?call<Byte*>(b,0x28b850,bd):nullptr;if(!manager)return;
    float point[3]={at<float>(z,0x10)+distance,at<float>(z,0x14),0};
    Word context[10]={};char a;call<void>(b,0xb75560,context+2,"",&a);context[3]=b+0xccbfd8;
    call<void>(b,0x67a3d8,manager,z,point,0.0f,duration,context,1u);
}
static void hit(Word b,Byte *fw,bool food,float amount,float elapsed){
    Byte *plant=at<Byte*>(fw,4);int row=int(at<Word>(plant,0x58)),col=int(at<Word>(plant,0x5c));
    int rect[4]={col,row-(food?1:0),15,food?3:1};List found={};
    call<void>(b,0x248120,&found,6u,rect);
    Damage damage={plant,amount,0,{0,0,0}};
    for(auto p=found.begin;p!=found.end;++p){
        Byte *entity=*p;if(!entity)continue;
        float dx=at<float>(entity,0x10)-at<float>(plant,0x10);
        if(dx<0||dx>(food?700.0f:290.0f))continue;
        // Respect the native target filters for flying/removed/invulnerable
        // zombies, while retaining grave damage in the same attack volume.
        const bool isZombie=zombie(entity);
        if(!isZombie){Byte*t=virt<Byte*>(entity,0);const char*n=t?at<const char*>(t,4):nullptr;
            if(same(n,"IrisIceHole")||same(n,"IrisFireWall"))continue;}
        Word flags=virt<Word>(fw,0x78,food?1u:0u);
        if(isZombie&&!virt<bool>(entity,0x3c,flags))continue;
        if(food&&isZombie&&!heavy(entity))push(b,entity,120.0f*elapsed,elapsed);
        virt<void>(entity,0x34,&damage);
    }
    if(found.begin)call<void>(b,0xb36928,found.begin);
#if IRIS_DARK_TRACE
    call<int>(b,0xe8c10,3,"IrisDark","Fume %s damage=%u",food?"PF":"attack",Word(amount));
#endif
}
extern "C" __attribute__((section(".text.entry")))
Word iris_fumeshroom(Word b,Word *args,Word mode){
    Byte *fw=reinterpret_cast<Byte*>(args[0]);
    const Word original[]={0x3e997c,0x3e9200,0x3e9354,0x3e991c,0x3e917c};
    if(!ours(b,fw))return call<Word>(b,original[mode],fw,args[1],args[2],args[3]);
    Byte *plant=at<Byte*>(fw,4);
    // The inherited line-attacker's idle-after-laser flag belongs to its
    // beam rig. Fume-shroom's generic rig has no such transition.
    if(mode==4)return 0;
    if(mode==0){
        if(at<Word>(plant,0x48)==5){
            // The authored food animation charges for forty frames before
            // use_action. The gas, damage and push must begin at that marker.
            if(!at<Byte>(fw,0x18)){
                float remaining=at<float>(fw,0x14)-now(b);
                if(remaining>0){
                    at<float>(fw,0x20)=1500.0f/remaining;
                    at<float>(fw,0x1c)=now(b);at<Byte>(fw,0x18)=1;
                    cloud(b,plant,true);
                }
            }
        }else{hit(b,fw,false,20.0f,0);cloud(b,plant,false);}
        return 0;
    }
    if(mode==1){
        call<void>(b,0x3ba164,fw);at<Word>(plant,0x48)=5;
        at<float>(fw,0x14)=now(b)+5.0f;at<float>(fw,0x1c)=now(b);at<Byte>(fw,0x18)=0;
        at<float>(fw,0x20)=0;animation(b,plant,"plantfood",false);return 0;
    }
    if(mode==2){
        Byte *bd=board(b);if(!at<Byte>(fw,0x18)||!bd||call<bool>(b,0x1872a8,bd))return 0;
        float end=at<float>(fw,0x14),time=now(b);if(time>end)time=end;
        float elapsed=time-at<float>(fw,0x1c);
        if(elapsed>=0.1f||(time==end&&elapsed>0)){
            at<float>(fw,0x1c)=time;hit(b,fw,true,at<float>(fw,0x20)*elapsed,elapsed);
        }return 0;
    }
    at<Byte>(fw,0x18)=0;call<void>(b,0x3ba2c0,fw);at<Word>(plant,0x48)=4;
    animation(b,plant,"idle",true);return 0;
}
