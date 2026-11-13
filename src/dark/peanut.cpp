// Peanut's two heads, damaged animations and rechargeable 4000-point shell.
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
static bool peanut(Word b,Byte*p){Byte*t=p?resolve(b,reinterpret_cast<Word*>(p+0xb8)):nullptr;return t&&same(at<const char*>(t,0x10),"POPANIM_PLANT_PEANUT");}
static void freeString(Word b,char*s){char a;if(__atomic_fetch_sub(reinterpret_cast<int*>(s-4),1,__ATOMIC_ACQ_REL)<=0)call<void>(b,0xb76c4c,s-12,&a);}
static char* string(Word b,const char*s){char*out;char a;call<void>(b,0xb75560,&out,s,&a);return out;}
static void trace(Word b,const char*s,Word a=0){
#if IRIS_DARK_TRACE
    call<int>(b,0xe8c10,3,"IrisDark","Peanut %s value=%x",s,a);
#endif
}
static Byte* rig(Byte*p){return virt<Byte*>(p,0x70);}
static float now(Word b){Byte*c=*reinterpret_cast<Byte**>(b+0xd4ed90);return c?at<float>(c,0x1c):0;}
static void animation(Word b,Byte*p,const char*label,bool loop){
    Byte*r=rig(p);if(!r)return;char*s=string(b,label);Word empty[6]={};
    call<void>(b,loop?0x44d220:0x44d0b0,r,&s,loop?3u:0u,empty,empty);freeString(b,s);
}
static void foodTick(Word b,Byte*f){
    Byte*p=at<Byte*>(f,4);float elapsed=now(b)-at<float>(f,0xc);
    if(elapsed<0)return;
    if(at<float>(f,0x1c)<1){at<float>(f,0x1c)=1;animation(b,p,"plantfood",true);}
    Word due=elapsed>=2?60u:Word(elapsed*30.0f);
    Word &done=at<Word>(f,0x10);
    while(done<due){
        Word action=at<Word>(p,0xb4);at<Word>(p,0xb4)=0;
        Byte*shot=call<Byte*>(b,0x3a1b88,p);
        at<Word>(p,0xb4)=action;
        if(shot){
            if(done&1u)call<void>(b,0x48a78c,shot,at<float>(shot,0x2c),at<float>(shot,0x30)+22.0f,at<float>(shot,0x34));
            at<Word>(shot,0x80)|=0x400u;
        }++done;
    }
    if(done==60&&at<float>(f,0x1c)<2){at<float>(f,0x1c)=2;animation(b,p,"plantfood_off",false);}
}
static Word damageState(Byte*p){float hp=at<float>(p,0x4c);return hp>=3000.0f?0u:hp>=2000.0f?1u:hp>=1000.0f?2u:3u;}
static void idle(Word b,Byte*p){Byte*r=rig(p);if(!r)return;at<Word>(r,0x188)=damageState(p);call<void>(b,0x3a50c4,r);}
static void shell(Word b,Byte*fw){
    Byte*r=rig(at<Byte*>(fw,4));if(!r)return;float hp=at<float>(fw,0x20);
    if(at<float>(fw,0x24)==hp)return;at<float>(fw,0x24)=hp;
    Word stage=hp>2666.6667f?0u:hp>1333.3334f?1u:2u;
    // Use PC-relative string literals. A table of pointers would require
    // loader relocations, which appended freestanding payloads do not have.
    for(Word i=0;i<3;++i){char*name=string(b,i==0?"Plantfood_Helmet2":i==1?"Plantfood_Helmet2_damage1":"Plantfood_Helmet2_Damage2");
        call<void>(b,0x44cd0c,r,&name,hp>0&&stage==i);freeString(b,name);}
    char*name=string(b,"peanut_plantfood_armor");
    call<void>(b,0x44cd0c,r,&name,hp>0);freeString(b,name);
}
struct List{Byte**begin,**end,**capacity;};
static Byte* plantForRig(Word b,Byte*r){
    Byte*a=**reinterpret_cast<Byte***>(b+0xd00838);if(!a||!at<Byte*>(a,0x6c0))return nullptr;
    List found={};int rect[4]={0,0,16,6};call<void>(b,0x248120,&found,1u,rect);Byte*out=nullptr;
    for(auto q=found.begin;q!=found.end;++q)if(*q&&rig(*q)==r&&peanut(b,*q)){out=*q;break;}
    if(found.begin)call<void>(b,0xb36928,found.begin);return out;
}
extern "C" __attribute__((section(".text.entry")))
Word iris_peanut(Word b,Word*args,Word mode){
    if(mode==10){
        Byte*f=reinterpret_cast<Byte*>(args[1]),*p=at<Byte*>(f,4);
        if(peanut(b,p)&&at<Word>(p,0x48)==5){char a;call<void>(b,0xb75560,args[0],"",&a);return args[0];}
        return call<Word>(b,0x3ba4f4,args[0],f);
    }
    if(mode==5){Byte*f=call<Byte*>(b,0xb363dc,0x28u);at<float>(f,0x20)=0;at<float>(f,0x24)=-1;return reinterpret_cast<Word>(f);}
    if(mode==6){
        Byte*reflection=reinterpret_cast<Byte*>(args[0]);
        call<void>(b,IRIS_PEANUT_REFLECT_ORIGINAL,reflection,args[1]);
        char*name=string(b,"iris_peanut_shell");Word type=virt<Word>(reflection,0x14,8u,4u);
        virt<void>(reflection,0x2c,args[1],&name,0x20u,type);freeString(b,name);return 0;
    }
    if(mode==7){
        Byte*r=reinterpret_cast<Byte*>(args[0]);
        Byte*p=at<Word>(r,0x188)?plantForRig(b,r):nullptr;
        char*name=nullptr;Word label=args[1];
        if(p){Word damage=damageState(p);if(damage){name=string(b,damage==1?"attack_damage1":damage==2?"attack_damage2":"attack_damage3");label=reinterpret_cast<Word>(&name);}}
        Word result=call<Word>(b,0x44d13c,r,label,args[2],args[3],args[6]);if(name)freeString(b,name);return result;
    }
    if(mode==8){
        Byte*f=reinterpret_cast<Byte*>(args[0]);Word result=call<Word>(b,0x3b963c,f,args[1],args[2],args[3]);
        Byte*p=at<Byte*>(f,4);if(peanut(b,p)){at<Word>(p,0x84)=3;at<float>(f,0x24)=-1;shell(b,f);}return result;
    }
    if(mode==9){Byte*f=reinterpret_cast<Byte*>(args[0]);if(!peanut(b,at<Byte*>(f,4)))return call<Word>(b,0x3fc524,f);foodTick(b,f);return 0;}
    Byte*fw=reinterpret_cast<Byte*>(args[mode==3?1:0]);Byte*p=at<Byte*>(fw,4);
    const Word original[]={0x3fc8b4,0x3fc43c,0x3fc59c,0x13f310,0x13f290};
    if(!peanut(b,p))return call<Word>(b,original[mode],args[0],args[1],args[2],args[3]);
    if(mode==0){
        trace(b,"normal callback",at<Word>(p,0x48));
        if(at<Word>(p,0x48)==5)return 0;
        Byte*shot=call<Byte*>(b,0x3a1b88,p,args[1],args[2]);
        trace(b,"upper projectile",reinterpret_cast<Word>(shot));
        if(shot&&damageState(p)<2){
            // Upper and lower mouths fire their own tier-one pea.
            Byte*lower=call<Byte*>(b,0x3a1b88,p,args[1],args[2]);
            trace(b,"lower projectile",reinterpret_cast<Word>(lower));
            if(lower)call<void>(b,0x48a78c,lower,at<float>(lower,0x2c),at<float>(lower,0x30)+22.0f,at<float>(lower,0x34));
        }
        return reinterpret_cast<Word>(shot);
    }
    if(mode==1){
        call<void>(b,0x3a05f4,p);at<float>(fw,0x20)=4000.0f;shell(b,fw);
        // Repeater's tenfold rig speed truncates Peanut's short food loop.
        // Drive the authored on / two-second burst / off sequence explicitly.
        Byte*r=rig(p);if(r)virt<void>(r,0x44);
        call<void>(b,0x3ba164,fw);at<Word>(p,0x48)=5;
        at<float>(fw,0xc)=now(b)+0.6f;at<Word>(fw,0x10)=0;at<Word>(fw,0x14)=60;
        at<float>(fw,0x1c)=0;at<float>(p,0x74)=now(b)+3.166667f;
        animation(b,p,"plantfood_on",false);trace(b,"food expected shots",60);return 0;
    }
    if(mode==2){
        if(at<Word>(p,0x48)==5&&now(b)>=at<float>(fw,0xc)+2.0f)foodTick(b,fw);
        trace(b,"food completed shots",at<Word>(fw,0x10));
        Byte*r=rig(p);if(r)virt<void>(r,0x44);
        call<void>(b,0x3ba2c0,fw);at<Word>(p,0x48)=4;idle(b,p);return 0;
    }
    if(mode==3){
        Byte*out=reinterpret_cast<Byte*>(args[0]);Byte*in=reinterpret_cast<Byte*>(args[2]);
        call<void>(b,0x13f310,out,fw,in);
        float &shield=at<float>(fw,0x20), &amount=at<float>(out,4);
        if(shield>0&&amount>0&&!(at<Word>(in,8)&2u)){
            float used=amount<shield?amount:shield;shield-=used;amount-=used;shell(b,fw);
        }return args[0];
    }
    // Iris stores the number of damaged variants, excluding intact.
    at<Word>(p,0x84)=3;shell(b,fw);
    Byte*r=rig(p);if(r&&at<Word>(p,0x48)==4&&at<Word>(r,0x180)==1&&at<Word>(r,0x188)!=damageState(p))idle(b,p);
    return 0;
}
