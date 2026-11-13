// Scoped Ice-shroom projectile behavior. Ordinary Projectile instances and
// every other projectile vtable retain their original collision callbacks.
using Byte=unsigned char;using Word=unsigned int;
template<class T>static T&at(Byte*p,Word o){return *reinterpret_cast<T*>(p+o);}
template<class R,class...A>static R call(Word b,Word p,A...a){return reinterpret_cast<R(*)(A...)>(b+p)(a...);}
template<class R,class...A>static R virt(Byte*p,Word o,A...a){return at<R(*)(Byte*,A...)>(at<Byte*>(p,0),o)(p,a...);}
static char*text(Word b,const char*s){char*r,a;call<void>(b,0xb75560,&r,s,&a);return r;}
static void drop(Word b,char*s){char a;if(__atomic_fetch_sub(reinterpret_cast<int*>(s-4),1,__ATOMIC_ACQ_REL)<=0)call<void>(b,0xb76c4c,s-12,&a);}
static void trace(Word b,const char*s,Word v){
#if IRIS_DARK_TRACE
 call<int>(b,0xe8c10,3,"IrisDark","Growth shot %s value=%x",s,v);
#endif
}
#include "magnet.inc"
static Byte*shotProps(Word b,Byte*p){Byte*s=at<Byte*>(p,0x10);return s?s:weakObject(b,reinterpret_cast<Word*>(p+0x18));}
static bool iceShot(Byte*s){return s&&equalText(at<const char*>(s,0x70),"POPANIM_EFFECTS_ICESHROOM_BULLET");}
static bool fireShot(Byte*s){return s&&(equalText(at<const char*>(s,0x70),"POPANIM_EFFECTS_FIRESHROOM_BULLET")||equalText(at<const char*>(s,0x70),"POPANIM_EFFECTS_IRIS_FIRE_STONE"));}
static Word fireCollision(Word b,Byte*p,Byte*target,Byte*props){
    if(virt<bool>(target,0x40,p))return 0;
    struct Damage{Byte*source;float amount;Word flags;Word conditions[3];}damage={};
    call<void>(b,0x4896d8,p,&damage);
    // The user's second-tier intrinsic effect adds 15%, independently of
    // rank multipliers. The underlying tier-one property value is retained.
    damage.amount*=1.15f;virt<void>(target,0x34,&damage);
    if(damage.conditions[0])call<void>(b,0xb36928,damage.conditions[0]);
    Word result=virt<Word>(p,0x4c,target);
    const char*sound=at<const char*>(props,0xa8);
    if(!(at<Byte>(target,0x2c)&2)&&sound&&*sound)call<void>(b,0x1a4280,target,props+0xa8,at<float>(props,0xac));
    return result;
}
static void splitIce(Word b,Byte*p,Byte*hit,Byte*props,Byte*source){
    const float damage=at<float>(props,0x14);
    if(damage!=60.0f&&damage!=30.0f)return;
    // Private special actions expose the two split projectile weak handles
    // without needing Aster's incompatible Projectile subclass layout.
    Word plantProps[2]={};call<void>(b,0x39e838,plantProps,source);
    Byte*sheet=weakObject(b,plantProps);call<void>(b,0x13dea0,plantProps,0u,0u,0u);if(!sheet)return;
    Byte*actions=at<Byte*>(sheet,0x30);Word index=damage==60.0f?1u:2u;
    if(!actions||at<Byte*>(sheet,0x34)<actions+(index+1)*0x60)return;
    Word shot[2]={};call<void>(b,0x13dea0,shot,0u,at<Word>(actions,index*0x60+8),at<Word>(actions,index*0x60+0xc));
    if(!shot[0]&&!shot[1])return;
    int row=int(at<Word>(p,0x5c)),rect[4]={0,row-1,16,3};MagnetList candidates={};
    call<void>(b,0x248120,&candidates,6u,rect);Word count=0;
    for(Byte**q=candidates.begin;q!=candidates.end&&count<2;++q){Byte*z=*q;
        if(!z||z==hit||at<Word>(z,0x48)==3)continue;
        if(at<Word>(p,0x98)==at<Word>(z,8)&&at<Word>(p,0x9c)==at<Word>(z,0xc))continue;
        if(!virt<bool>(z,0x3c,3u))continue;
        float dx=at<float>(z,0x10)-at<float>(hit,0x10),dy=at<float>(z,0x14)-at<float>(hit,0x14);
        if(dx*dx+dy*dy>92.16f*92.16f)continue;
        Byte*child=call<Byte*>(b,0x180cd0,battleBoard(b),at<float>(p,0x2c),at<float>(p,0x30),at<float>(p,0x34),shot,source);
        if(!child)continue;
        // Aster aims split shots at the selected point with a half-second
        // flight, rather than continuously homing after a moving target.
        at<float>(child,0x38)=(at<float>(z,0x10)-8.0f-at<float>(child,0x2c))*2.0f;
        at<float>(child,0x3c)=(at<float>(z,0x14)-at<float>(child,0x30))*2.0f;
        at<float>(child,0x40)=0;
        call<void>(b,0x13dea0,child+0x98,0u,at<Word>(hit,8),at<Word>(hit,0xc));
        ++count;
    }
    if(candidates.begin)call<void>(b,0xb36928,candidates.begin);
    call<void>(b,0x13dea0,shot,0u,0u,0u);trace(b,"ice splits",count);
}
static Byte*stoneState(Word b){return reinterpret_cast<Byte*>(b+0xf80200);}
static Word stoneStub(Word b,Word mode){return b+IRIS_GROWTH_SHOT_STUB+mode*40;}
static void registerStone(Word b){
    Byte*s=stoneState(b);
    if(!at<Word>(s,0)){
        Byte*m=call<Byte*>(b,0xb363dc,40u);call<void>(b,0x894ca0,m);at<Byte*>(s,0)=m;
        call<void>(b,0x895608,m,"IrisFireStone",call<Byte*>(b,0x16a72c),stoneStub(b,3));
        Byte*t=call<Byte*>(b,0xb363dc,0x58u);
        for(Word i=0;i<0x58;i+=4)at<Word>(t,i)=*reinterpret_cast<Word*>(b+0xce8518+i);
        at<Word>(t,0)=stoneStub(b,4);at<Word>(t,0x48)=stoneStub(b,6);at<Byte*>(s,4)=t;
    }
    Byte*m=call<Byte*>(b,0x851728);Byte*r=m?call<Byte*>(b,0x851920,m):nullptr;
    if(!r||at<Word>(s,8))return;at<Word>(s,8)=1;
    char*n=text(b,"IrisFireStone");virt<void>(r,0xc,&n,stoneStub(b,5),0xa8u,0u);drop(b,n);
}
static void stoneSchema(Word b,Byte*r,Byte*d){
    Byte*m=at<Byte*>(stoneState(b),0);at<Byte*>(m,0x24)=d;at<Byte*>(d,0x5c)=m;
    char*n=text(b,"Projectile");Byte*p=virt<Byte*>(r,0x24,&n);drop(b,n);
    virt<void>(r,0x28,d,virt<Word>(p,0x34),0u);
    for(Word i=0;i<2;++i){n=text(b,i?"iris_impacted":"iris_age");Word t=virt<Word>(r,0x14,i?6u:8u,4u);
        virt<void>(r,0x2c,d,&n,0xa0+i*4,t);drop(b,n);}
}
static void updateStone(Word b,Byte*p,float dt){
    Byte*board=battleBoard(b);if(!board||call<bool>(b,0x1872a8,board))return;
    if(dt<0||dt>0.2f)dt=0;float&age=at<float>(p,0xa0);age+=dt;
    // Aster damages when the ten-frame ANIM_STAGE4_IN finishes, while
    // the following 27 impact frames continue playing above the target.
    if(!at<Word>(p,0xa4)&&age>=10.0f/30.0f){
        at<Word>(p,0xa4)=1;Byte*target=weakObject(b,reinterpret_cast<Word*>(p+0x98));
        if(target)virt<Word>(p,0x34,target);else virt<Word>(p,0x4c,target);
        trace(b,"fire stone impact",75);
    }
    if(age>=37.0f/30.0f)call<void>(b,0x2708b4,p);
}
extern "C" __attribute__((section(".text.entry")))
Word iris_growth_projectile(Word b,Word*args,Word mode){
    if(mode==2){call<void>(b,IRIS_GROWTH_SHOT_REGISTER);registerStone(b);return 0;}
    if(mode==3){Byte*p=call<Byte*>(b,0xb363dc,0xa8u);call<void>(b,0x488238,p);at<Byte*>(p,0)=at<Byte*>(stoneState(b),4);at<Word>(p,0xa0)=0;at<Word>(p,0xa4)=0;return reinterpret_cast<Word>(p);}
    if(mode==4)return at<Word>(stoneState(b),0);
    if(mode==5){stoneSchema(b,reinterpret_cast<Byte*>(args[0]),reinterpret_cast<Byte*>(args[1]));return 0;}
    if(mode==6){float dt=*reinterpret_cast<float*>(args+1);updateStone(b,reinterpret_cast<Byte*>(args[0]),dt);return 0;}
    Byte*p=reinterpret_cast<Byte*>(args[0]),*target=reinterpret_cast<Byte*>(args[1]);Byte*props=shotProps(b,p);
    if(mode==0){
        // The excluded previous impact target is a native serialized weak
        // handle. Ignore it before native damage, avoiding duplicate hits.
        if(iceShot(props)&&target&&at<Word>(p,0x98)==at<Word>(target,8)&&at<Word>(p,0x9c)==at<Word>(target,0xc))return 0;
        if(fireShot(props)&&target)return fireCollision(b,p,target,props);
        return call<Word>(b,0x48958c,p,target);
    }
    if(iceShot(props)&&target){
        Byte*source=weakObject(b,reinterpret_cast<Word*>(p+0x20));
        Byte*type=source?virt<Byte*>(source,0):nullptr;bool plant=false;
        for(Word i=0;type&&i<32;++i,type=at<Byte*>(type,8))if(equalText(at<const char*>(type,4),"Plant")){plant=true;break;}
        if(plant){
            float damage=at<float>(props,0x14);
            // Only the primary mature shot and the ordinary shots receive
            // the fixed second-tier freeze chance; split generations do not.
            if(damage!=30.0f&&damage!=15.0f&&zombieClass(target)&&call<Word>(b,0x7a3e90,1000u)<75u){
                trace(b,"ice freeze begin",reinterpret_cast<Word>(target));
                call<void>(b,0x5e0ed8,target,1u,5.0f);trace(b,"ice freeze",5);
            }
            splitIce(b,p,target,props,source);
        }
    }
    if(fireShot(props)){
        // Native impact computes splash from the property sheet, overriding
        // the Damage record. Scope this synchronous value for that call and
        // restore it immediately; normal property/base stats stay unchanged.
        float splash=at<float>(props,0x20);at<float>(props,0x20)=splash*1.15f;
        Word result=call<Word>(b,0x489930,p,target);at<float>(props,0x20)=splash;return result;
    }
    return call<Word>(b,0x489930,p,target);
}
