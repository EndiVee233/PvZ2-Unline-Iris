// Tier-one Sun Bean. Reserved negative consumption states retain their
// sunlight budget and position through the original battle serializer.
using Byte=unsigned char; using Word=unsigned int;
template<class T> static T &at(Byte*p,Word n){return *reinterpret_cast<T*>(p+n);}
template<class R,class...A> static R call(Word b,Word n,A...a){return reinterpret_cast<R(*)(A...)>(b+n)(a...);}
template<class R,class...A> static R virt(Byte*p,Word n,A...a){return at<R(*)(Byte*,A...)>(at<Byte*>(p,0),n)(p,a...);}
static bool same(const char*a,const char*b){if(!a||!b)return false;while(*a&&*a==*b){++a;++b;}return *a==*b;}
static Byte* resolve(Word b,Word*w){
    Byte*r=call<Byte*>(b,0x8821a8);Word h[2]={};call<void>(b,0x8890c4,h,r,w);Byte*out=nullptr;
    if(h[0]||h[1]){Byte*q=call<Byte*>(b,0x888b8c,r,(h[1]<<1)>>18);if(q)out=call<Byte*>(b,0x884378,q,h);}
    call<void>(b,0x13dea0,h,0u,0u,0u);return out;
}
static bool ours(Word b,Byte*p){Byte*t=p?resolve(b,reinterpret_cast<Word*>(p+0xb8)):nullptr;return t&&same(at<const char*>(t,0x10),"POPANIM_PLANT_SUNBEAN");}
static bool zombie(Byte*p){
    Byte*t=p?virt<Byte*>(p,0):nullptr;
    for(Word i=0;t&&i<32;++i,t=at<Byte*>(t,8)){
        const char*n=at<const char*>(t,4);
        if(same(n,"ZombieGargantuar")||same(n,"ZombieZombossMech"))return false;
        if(same(n,"Zombie"))return true;
    }
    return false;
}
static Byte* board(Word b){Byte*a=**reinterpret_cast<Byte***>(b+0xd00838);return a?at<Byte*>(a,0x6c0):nullptr;}
static float now(Word b){Byte*c=*reinterpret_cast<Byte**>(b+0xd4ed90);return c?at<float>(c,0x1c):0;}
static char* text(Word b,const char*s){char*out,a;call<void>(b,0xb75560,&out,s,&a);return out;}
static void drop(Word b,char*s){char a;if(__atomic_fetch_sub(reinterpret_cast<int*>(s-4),1,__ATOMIC_ACQ_REL)<=0)call<void>(b,0xb76c4c,s-12,&a);}
static void animation(Word b,Byte*p,const char*label,bool loop){
    Byte*r=virt<Byte*>(p,0x70);if(!r)return;char*s=text(b,label);Word empty[6]={};
    call<void>(b,loop?0x44d220:0x44d0b0,r,&s,loop?3u:0u,empty,empty);drop(b,s);
}
static void trace(Word b,const char*s,Word n){
#if IRIS_DARK_TRACE
    call<int>(b,0xe8c10,3,"IrisDark","SunBean %s value=%u",s,n);
#endif
}
static float positive(float n){return n>0?n:0;}
static float health(Byte*z){return positive(at<float>(z,0xb0))+positive(at<float>(z,0x34));}
static bool marked(Byte*e){return (at<Word>(e,0x18)&0xf0000000u)==0x80000000u;}
static bool charged(Byte*e){return at<Word>(e,0x18)&0x01000000u;}
static Word position(Byte*z,Word flags){return 0x80000000u|flags|(Word(int(at<float>(z,0x10)))&0xfffu)|((Word(int(at<float>(z,0x14)))&0xfffu)<<12);}
static void point(Byte*e,Byte*z,float*p){
    Word v=at<Word>(e,0x18);p[0]=z?at<float>(z,0x10):float(int(v<<20)>>20);
    p[1]=z?at<float>(z,0x14):float(int(v<<8)>>20);p[2]=z?at<float>(z,0x18):0;
}
static void effect(Word b,const char*id,float*p){
    Byte*bd=board(b),*holder=**reinterpret_cast<Byte***>(b+0xd008bc);if(!bd||!holder)return;
    char*s=text(b,id);Word weak[2]={};Word kind=call<Word>(b,0x129ae0);
    at<void(*)(Word*,Byte*,Word,char**,Word)>(at<Byte*>(holder,0),8)(weak,holder,kind,&s,0u);drop(b,s);
    Byte*resource=resolve(b,weak);call<void>(b,0x13dea0,weak,0u,0u,0u);if(!resource)return;
    Byte*e=call<Byte*>(b,0x1809a8,bd);if(!e)return;call<void>(b,0x23a354,e,resource,0u);
    s=text(b,"animation");call<void>(b,0x23aa6c,e,&s,0u);drop(b,s);
    float q[3]={p[0],p[1]-p[2],0};call<void>(b,0x4e6bb8,e,q,0xffffffffu);call<void>(b,0x23a814,e,0u);
}
static Word suns(Word b,float amount,float*p){
    Word left=Word(positive(amount)*0.2f)*5,total=0;Byte*bd=board(b);if(!bd)return 0;
    while(left>=5){Word value=left>=25?25u:5u;char*s=text(b,value==25?"iris_dark_sun":"sun_small");
        Byte*c=call<Byte*>(b,0x17b6e4,bd,&s);drop(b,s);if(!c)break;
        virt<void>(c,0x58,p);float velocity[3]={float(int(total&7u)*12-36),5,200};float accel[3]={0,0,-600};
        call<void>(b,0x1d2fe0,c,velocity,accel,1u);call<void>(b,0x1d2cc4,c);total+=value;left-=value;
    }if(total)trace(b,"sun produced",total);return total;
}
static void mark(Word b,Byte*z,bool food){
    // Do not take ownership of another mechanic's invulnerability flag.
    if(at<Word>(z,0xa8)&0x1000u)return;
    Byte*bd=board(b);if(!bd)return;Byte*m=call<Byte*>(b,0x3d6f04,bd);if(!m||!call<bool>(b,0x3d9578,m,z))return;
    // Ordinary re-eating must not multiply the same damage stream.
    for(Byte*e=at<Byte*>(m,0x10);e!=at<Byte*>(m,0x14);e+=32){
        if(!marked(e)||resolve(b,reinterpret_cast<Word*>(e+8))!=z)continue;
        if(charged(e)||!food)return;at<Word>(e,0x18)=2;
    }
    Word words[8]={};Byte*e=reinterpret_cast<Byte*>(words);
    call<void>(b,0x13dea0,words+2,0u,at<Word>(z,8),at<Word>(z,0xc));
    at<float>(e,0x10)=food?now(b):health(z);at<float>(e,0x14)=food?health(z):300.0f;
    at<Word>(e,0x18)=position(z,food?0x01000000u:0u);
    call<void>(b,0x3d9ac4,m+0x10,e);call<void>(b,0x13dea0,words+2,0u,0u,0u);
    float p[3]={};point(e,z,p);effect(b,"POPANIM_EFFECTS_SUNBEAN_ZOMBIE_EFFECT",p);
    if(food){at<Word>(z,0xa8)|=0x1000u;call<void>(b,0x5e0ed8,z,2u,3.1f);}
    trace(b,food?"charged eaten":"eaten",Word(health(z)));
}
static void update(Word b,Byte*m){
    Byte*bd=board(b);if(!bd||at<Word>(bd,0xa8)!=5||call<bool>(b,0x1872a8,bd))return;
    for(Byte*e=at<Byte*>(m,0x10);e!=at<Byte*>(m,0x14);e+=32){
        if(!marked(e))continue;Byte*z=resolve(b,reinterpret_cast<Word*>(e+8));float p[3]={};point(e,z,p);
        bool dead=!z||(at<Word>(z,0x48)-4u<5u);float hp=dead?0:health(z);
        if(charged(e)){
            float elapsed=now(b)-at<float>(e,0x10);
            if(!dead&&elapsed>=1&&!(at<Word>(e,0x18)&0x02000000u)){
                at<Word>(e,0x18)|=0x02000000u;effect(b,"POPANIM_EFFECTS_SUNBEAN_PLANTFOOD_EFFECT_OVERLAY1",p);
            }
            if(dead||elapsed>=3){
                float value=(dead?at<float>(e,0x14):hp)*0.4f;if(value>600)value=600;
                suns(b,value,p);effect(b,"POPANIM_EFFECTS_SUNBEAN_PLANTFOOD_EFFECT_OVERLAY2",p);
                at<Word>(e,0x18)=2;
                if(z)at<Word>(z,0xa8)&=~0x1000u;
                if(!dead){call<void>(b,0x5e0b54,z);call<void>(b,0x5e147c,z,0u);}
            }
        }else{
            float &previous=at<float>(e,0x10),&remaining=at<float>(e,0x14);
            float lost=positive(previous-hp);float amount=lost*0.2f;if(amount>remaining)amount=remaining;
            Word produced=suns(b,amount,p);previous-=float(produced)*5.0f;remaining-=float(produced);
            if(hp>previous)previous=hp; // Healing is not sunlight debt.
            if(dead||remaining<5)at<Word>(e,0x18)=2;else at<Word>(e,0x18)=position(z,0);
        }
    }
}
extern "C" __attribute__((section(".text.entry")))
Word iris_sunbean(Word b,Word*args,Word mode){
    if(mode==3){Byte*m=reinterpret_cast<Byte*>(args[0]);update(b,m);return call<Word>(b,IRIS_SUNBEAN_UPDATE_ORIGINAL,m);}
    Byte*fw=reinterpret_cast<Byte*>(args[mode==0?1:0]),*p=at<Byte*>(fw,4);
    const Word original[]={0x3d6d54,0x3d7660,0x3ba2c0,0,0x13f290};
    if(!ours(b,p))return call<Word>(b,original[mode],args[0],args[1],args[2],args[3]);
    if(mode==0){Byte*in=reinterpret_cast<Byte*>(args[2]);Byte*z=at<Byte*>(in,0);
        if(at<float>(p,0x4c)>=0&&at<float>(in,4)>0&&at<float>(p,0x4c)<=at<float>(in,4)&&zombie(z))mark(b,z,at<Word>(p,0x88)==1);
        return call<Word>(b,0x13f310,args[0],fw,in);
    }
    if(mode==1){call<void>(b,0x3ba164,fw);at<Word>(p,0x48)=5;at<Word>(p,0x88)=1;animation(b,p,"plantfood_on",false);return 0;}
    if(mode==2){call<void>(b,0x3ba2c0,fw);at<Word>(p,0x48)=4;animation(b,p,"plantfood",true);return 0;}
    // No damage variants use this existing serialized Plant field here.
    if(at<Word>(p,0x48)==4&&at<Word>(p,0x88)==1){Byte*r=virt<Byte*>(p,0x70);if(r&&at<Word>(r,0x180)==1)animation(b,p,"plantfood",true);}
    return 0;
}
