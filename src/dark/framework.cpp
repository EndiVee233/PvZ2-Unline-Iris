// Own runtime class and battle schema for the ported Dark Ages frameworks.
// Runtime metadata pointers live on a separate non-executable RW page.
using Byte=unsigned char;using Word=unsigned int;
template<class T> static T&at(Byte*p,Word n){return *reinterpret_cast<T*>(p+n);}
template<class R,class...A> static R call(Word b,Word n,A...a){return reinterpret_cast<R(*)(A...)>(b+n)(a...);}
template<class R,class...A> static R virt(Byte*p,Word n,A...a){return at<R(*)(Byte*,A...)>(at<Byte*>(p,0),n)(p,a...);}
static char* text(Word b,const char*s){char*out,a;call<void>(b,0xb75560,&out,s,&a);return out;}
static void drop(Word b,char*s){char a;if(__atomic_fetch_sub(reinterpret_cast<int*>(s-4),1,__ATOMIC_ACQ_REL)<=0)call<void>(b,0xb76c4c,s-12,&a);}
static void trace(Word b,const char*s,Word n){
#if IRIS_DARK_TRACE
    call<int>(b,0xe8c10,3,"IrisDark","Framework %s value=%x",s,n);
#endif
}
#include "magnet.inc"
#include "streetlamp.inc"
#include "growth.inc"
#include "oak.inc"
static Byte* state(Word b){return reinterpret_cast<Byte*>(b+IRIS_DARK_STATE);}
#if IRIS_DARK_SMOKE_TEST
// Integration fixture only. Real ARM engine objects execute their normal
// food callbacks without capturing the user's mouse or modifying main saves.
static bool smokeFood(Word b,Byte*f){
    Byte*board=battleBoard(b),*p=at<Byte*>(f,4),*s=state(b);
    if(!board)return false;
    if(at<Word>(board,0xa8)!=5){at<Word>(s,0x28)=0;return false;}
    if(call<bool>(b,0x1872a8,board))return false;
    float now=battleTime(b);if(!at<Word>(s,0x28)){at<Word>(s,0x28)=1;at<float>(s,0x20)=now;at<Word>(s,0x24)=0;}
    float elapsed=now-at<float>(s,0x20);Word kind=growthKind(b,f),bit=0;
    int row=int(at<Word>(p,0x58)),col=int(at<Word>(p,0x5c));
    if(col==2&&row==0&&kind&&kind<=3&&elapsed>=22)bit=1;
    if(col==3&&row==0&&kind>=4&&elapsed>=34)bit=2;
    if(col==2&&row==2&&isOak(b,f)&&elapsed>=46)bit=4;
    if(!bit||(at<Word>(s,0x24)&bit)||at<Word>(p,0x48)!=4)return false;
    at<Word>(s,0x24)|=bit;trace(b,"automatic fixture food",bit);
    if(bit<=2){
        // Put a real integration target inside the authored effect's range.
        // This is compiled out of production together with automatic food.
        int rect[4]={0,0,16,5};MagnetList list={};call<void>(b,0x248120,&list,2u,rect);
        for(Byte**q=list.begin;q!=list.end;++q){Byte*z=*q;if(!zombieClass(z)||!virt<bool>(z,0x3c,1u))continue;
            float pos[3]={float(call<int>(b,0x17d518,board,bit==1?4:6)),at<float>(z,0x14),at<float>(z,0x18)};
            virt<void>(z,0x58,pos);if(bit==1)break;
        }
        if(list.begin)call<void>(b,0xb36928,list.begin);
    }
    if(bit==4)oakEvent(b,f,5);else growthEvent(b,f,5,kind);
    return true; // Growth can have destroyed the caller's old framework.
}
#endif
static void registerClass(Word b){
    Byte*s=state(b);
    if(!at<Byte*>(s,0)){
        Byte*meta=call<Byte*>(b,0xb363dc,40u);call<void>(b,0x894ca0,meta);at<Byte*>(s,0)=meta;
        Byte*parent=call<Byte*>(b,0x13b5a0);
        call<void>(b,0x895608,meta,"PlantIrisDark",parent,b+IRIS_DARK_STUB+40);
        // Copy relocated parent entries at runtime; the appended payload
        // must not contain an absolute pointer table requiring relocations.
        Byte*table=call<Byte*>(b,0xb363dc,0xf8u);
        for(Word i=0;i<0xf8;i+=4)at<Word>(table,i)=*reinterpret_cast<Word*>(b+0xce4398+i);
        at<Word>(table,0)=b+IRIS_DARK_STUB+80;
        const Word slots[]={0x44,0x94,0x6c,0x98,0x68,0x48,4,8};
        for(Word i=0;i<8;++i)at<Word>(table,slots[i])=b+IRIS_DARK_STUB+(i+4)*40;
        at<Word>(table,0x20)=b+IRIS_DARK_STUB+13*40;
        // The bare parent deliberately rejects plant food. Both implemented
        // subclasses supply it; preserve LaserBean's native true predicate.
        at<Word>(table,0x90)=b+0x3e91f8;
        at<Byte*>(s,4)=table;
        trace(b,"metadata created",reinterpret_cast<Word>(meta));
    }
    Byte*manager=call<Byte*>(b,0x851728);
    if(!at<Word>(s,8)&&manager){
        Byte*r=call<Byte*>(b,0x851920,manager);if(r){
            // Mark before registration: the callback can query its class.
            at<Word>(s,8)=1;char*n=text(b,"PlantIrisDark");
            trace(b,"registry",reinterpret_cast<Word>(r));
            virt<void>(r,0xc,&n,b+IRIS_DARK_STUB+120,0x2c0u,0u);drop(b,n);
            trace(b,"save schema registered",1);
        }
    }
}
extern "C" __attribute__((section(".text.entry")))
Word iris_dark_framework(Word b,Word*args,Word mode){
    if(mode==0){call<void>(b,IRIS_DARK_REGISTER_ORIGINAL);registerClass(b);return 0;}
    Byte*s=state(b);
    if(mode==1){
        Byte*f=call<Byte*>(b,0xb363dc,0x2c0u);for(Word i=0;i<0x2c0;i+=4)at<Word>(f,i)=0;
        at<Byte*>(f,0)=at<Byte*>(s,4);trace(b,"instance created",reinterpret_cast<Word>(f));return reinterpret_cast<Word>(f);
    }
    if(mode==2)return at<Word>(s,0);
    if(mode==12){Byte*p=reinterpret_cast<Byte*>(args[0]);if(at<Word>(p,0x48)==0x49524953u)return 0;return call<Word>(b,0x64c468,p);}
    if(mode==13){Byte*f=reinterpret_cast<Byte*>(args[0]);Word result=call<Word>(b,0x3b963c,f,args[1],args[2],args[3]);if(isMagnet(b,f))magnetVisuals(b,f);return result;}
    // Target selection has an ARM hidden result before the framework this.
    if(mode==9){Byte*f=reinterpret_cast<Byte*>(args[1]);auto manual=*reinterpret_cast<Word(**)(Byte*)>(b+0xf8108c);bool aiming=manual&&manual(at<Byte*>(f,4));if(aiming||isMagnet(b,f)||isStreetlamp(b,f)){
        // This is an ARM hidden return object, not an existing weak handle.
        // Native 3b9948/4c construct it by zeroing both words. Releasing its
        // uninitialized stack bytes can dereference an arbitrary pool slot.
        Word*out=reinterpret_cast<Word*>(args[0]);out[0]=out[1]=0;return args[0];
    }return call<Word>(b,0x3b9918,args[0],f,args[2],args[3],args[6]);}
    if(mode>=4){
        Byte*f=reinterpret_cast<Byte*>(args[0]);
#if IRIS_DARK_SMOKE_TEST
        if(mode==8&&smokeFood(b,f))return 0;
#endif
        if(mode==10||mode==11){
            for(Word i=0;i<20;++i)releaseMagnetItem(b,magnetItem(f,i),true);
            if(mode==11){call<void>(b,0xb36928,f);return 0;}
            return call<Word>(b,0x13f61c,f);
        }
        if(isStreetlamp(b,f))return streetlampEvent(b,f,mode);
        if(isOak(b,f))return oakEvent(b,f,mode);
        Word growth=growthKind(b,f);if(growth)return growthEvent(b,f,mode,growth);
        if(!isMagnet(b,f)){
            const Word fallback[]={IRIS_FUME_0,IRIS_FUME_1,IRIS_FUME_2,IRIS_FUME_3,IRIS_FUME_4,0x3b9918};
            return call<Word>(b,fallback[mode-4],f,args[1],args[2],args[3]);
        }
        Byte*p=at<Byte*>(f,4);
        if(mode==4)return 0; // No generic projectile/action list.
        if(mode==5){
            call<void>(b,0x3ba164,f);at<Word>(p,0x48)=5;at<Word>(f,0xc)=2;
            float time=battleTime(b);at<float>(f,0x10)=time+0.4f;at<float>(f,0x14)=time;at<float>(p,0x74)=time+4;
            for(Word i=0;i<20;++i){Byte*e=magnetItem(f,i);if(at<Word>(e,8))at<Word>(e,8)=3;}
            magnetAnimation(b,f,"plantfood_on",false);return 0;
        }
        if(mode==7){call<void>(b,0x3ba2c0,f);at<Word>(p,0x48)=4;at<Word>(f,0xc)=0;magnetAnimation(b,f,"plantfood_off",false);return 0;}
        // Update runs in ordinary and food states; the food-specific
        // callback is intentionally empty to avoid a double time step.
        if(mode==8)magnetUpdate(b,f);return 0;
    }
    Byte*r=reinterpret_cast<Byte*>(args[0]),*desc=reinterpret_cast<Byte*>(args[1]);
    trace(b,"reflect manager",args[0]);trace(b,"reflect descriptor",args[1]);
    at<Byte*>(at<Byte*>(s,0),0x24)=desc;at<Byte*>(desc,0x5c)=at<Byte*>(s,0);
    char*n=text(b,"PlantFramework");Byte*parent=virt<Byte*>(r,0x24,&n);drop(b,n);
    trace(b,"parent type",reinterpret_cast<Word>(parent));
    virt<void>(r,0x28,desc,virt<Word>(parent,0x34),0u);
    // Fume's combat window, active marker, previous tick and DPS are now
    // saved explicitly instead of depending on a borrowed class layout.
    for(Word i=0;i<7;++i){
        char label[]="iris_state0";label[10]=char('0'+i);n=text(b,label);
        Word type=virt<Word>(r,0x14,(i==1||i==4)?6u:8u,4u);
        virt<void>(r,0x2c,desc,&n,8+i*4,type);drop(b,n);
    }
    n=text(b,"ZombieParticle");Word particle=virt<Word>(r,0x24,&n);drop(b,n);
    Word weak=virt<Word>(r,0x20,3u,particle,0u,0u);
    n=text(b,"Zombie");Word zombie=virt<Word>(r,0x24,&n);drop(b,n);
    Word zombieWeak=virt<Word>(r,0x20,3u,zombie,0u,0u);
    for(Word i=0;i<20;++i){
        Word tens=i>=10?1u:0u;char label[]="iris_metal00w";label[10]=char('0'+tens);label[11]=char('0'+i-tens*10);
        n=text(b,label);virt<void>(r,0x2c,desc,&n,0x40+i*32,weak);drop(b,n);
        for(Word j=0;j<4;++j){label[12]=char('a'+j);n=text(b,label);Word type=virt<Word>(r,0x14,j==0?6u:8u,4u);
            virt<void>(r,0x2c,desc,&n,0x48+i*32+j*4,type);drop(b,n);}
        label[12]='t';n=text(b,label);virt<void>(r,0x2c,desc,&n,0x58+i*32,zombieWeak);drop(b,n);
    }
    trace(b,"schema reflected",args[1]);return 0;
}
