// Magnet-shroom's state is part of PlantIrisDark's battle schema. Held
// objects are real Iris ZombieParticles, not replacement sprite effects.
static bool equalText(const char*a,const char*b){if(!a||!b)return false;while(*a&&*a==*b){++a;++b;}return *a==*b;}
static Byte* weakObject(Word b,Word*w){
    Byte*r=call<Byte*>(b,0x8821a8);Word h[2]={};call<void>(b,0x8890c4,h,r,w);Byte*out=nullptr;
    if(h[0]||h[1]){Byte*q=call<Byte*>(b,0x888b8c,r,(h[1]<<1)>>18);if(q)out=call<Byte*>(b,0x884378,q,h);}
    call<void>(b,0x13dea0,h,0u,0u,0u);return out;
}
static bool isMagnet(Word b,Byte*f){Byte*p=at<Byte*>(f,4);Byte*t=p?weakObject(b,reinterpret_cast<Word*>(p+0xb8)):nullptr;return t&&equalText(at<const char*>(t,0x10),"POPANIM_PLANT_MAGNETSHROOM");}
static float battleTime(Word b){Byte*c=*reinterpret_cast<Byte**>(b+0xd4ed90);return c?at<float>(c,0x1c):0;}
static Byte* battleBoard(Word b){Byte*a=**reinterpret_cast<Byte***>(b+0xd00838);return a?at<Byte*>(a,0x6c0):nullptr;}
// The native GetModule dereferences a null result when a weak entry has
// expired during restart. Resolve each entry before asking its runtime type.
static Byte* ownedLevelModule(Word b,Byte*board,Byte*meta){
    if(!board||!meta)return nullptr;
    Byte*manager=at<Byte*>(board,0x62c);if(!manager)return nullptr;
    Word begin=at<Word>(manager,4),end=at<Word>(manager,8);
    if(!begin||end<begin||(end-begin)&7u||(end-begin)>256u*8u)return nullptr;
    for(Word p=begin;p<end;p+=8){Byte*m=weakObject(b,reinterpret_cast<Word*>(p));
        if(m&&virt<bool>(m,0x10,meta))return m;
    }return nullptr;
}
static void magnetAnimation(Word b,Byte*f,const char*label,bool loop){
    Byte*p=at<Byte*>(f,4),*r=virt<Byte*>(p,0x70);if(!r)return;char*s=text(b,label);Word empty[6]={};
    call<void>(b,loop?0x44d220:0x44d0b0,r,&s,loop?3u:0u,empty,empty);drop(b,s);
}
static void magnetSound(Word b,Byte*p,const char*event){char*s=text(b,event);call<void>(b,0x1a4280,p,&s,0.0f);drop(b,s);}
struct MagnetList{Byte**begin,**end,**capacity;};
static Byte* magnetItem(Byte*f,Word i){return f+0x40+i*32;}
static void releaseMagnetItem(Word b,Byte*item,bool remove){
    Byte*p=weakObject(b,reinterpret_cast<Word*>(item));
    if(p&&remove)call<void>(b,0x2708b4,p);
    call<void>(b,0x13dea0,item,0u,0u,0u);call<void>(b,0x13dea0,item+0x18,0u,0u,0u);at<Word>(item,8)=0;
}
static bool zombieClass(Byte*z){
    Byte*t=z?virt<Byte*>(z,0):nullptr;
    for(Word i=0;t&&i<32;++i,t=at<Byte*>(t,8))if(equalText(at<const char*>(t,4),"Zombie"))return true;
    return false;
}
static bool magneticZombie(Byte*z){
    if(!z||!zombieClass(z)||at<Word>(z,0x48)-4u<5u||!virt<bool>(z,0x3c,1u))return false;
    // Iris's enums include poncho: Aster's numeric values are different.
    const Word helm=at<Word>(z,0x30);
    return (helm==2||helm==6||helm==9)&&at<float>(z,0x34)>0;
}
static Byte* removeMetal(Word b,Byte*z){
    const Word helm=at<Word>(z,0x30);
    Byte*rig=weakObject(b,reinterpret_cast<Word*>(z+0x40));if(!rig)return nullptr;
    // The same authored piece list and skeleton component used by native
    // helmet loss. Allocation registers the object in the board's pool.
    Word pieces=virt<Word>(rig,0x114,helm);if(!pieces)return nullptr;
    Word component=0;at<void(*)(Word*,Byte*,Word)>(at<Byte*>(rig,0),0xf0)(&component,rig,helm);
    Byte*meta=call<Byte*>(b,0x453994);Byte*part=call<Byte*>(b,0x270400,meta,0x1cu);
    if(part){
        virt<void>(part,0x70,z,pieces,&component,0.75f);
        virt<void>(part,0x74,z);
        // Original physics/fade is suspended only for owned pieces.
        at<Word>(part,0x48)=0x49524953u;
        at<float>(part,0x38)=0;
        for(Word off=0x5c;off<=0x70;off+=4)at<float>(part,off)=0;
        at<float>(z,0x34)=0;at<Word>(z,0x30)=0;
        virt<void>(rig,0xe4,0u);virt<void>(rig,0xf4);
        trace(b,"magnet removed helmet",helm);
    }
    drop(b,reinterpret_cast<char*>(component));return part;
}
static Word takeMetal(Word b,Byte*f,bool food){
    Byte*p=at<Byte*>(f,4);int col=int(at<Word>(p,0x5c)),row=int(at<Word>(p,0x58));
    int rect[4]={food?0:col-3,food?0:row-2,food?16:7,food?5:5};MagnetList list={};
    call<void>(b,0x248120,&list,2u,rect);Word count=0;
    for(Byte**q=list.begin;q!=list.end;++q){
        Byte*z=*q;if(!magneticZombie(z))continue;
        Word slot=0;for(;slot<20&&at<Word>(magnetItem(f,slot),8);++slot){}
        if(slot==20)break;Byte*part=removeMetal(b,z);if(!part)continue;
        Byte*item=magnetItem(f,slot);call<void>(b,0x13dea0,item,0u,at<Word>(part,8),at<Word>(part,0xc));
        at<Word>(item,8)=food?3u:1u;at<float>(item,0xc)=0;
        at<float>(item,0x10)=battleTime(b)+13;at<float>(item,0x14)=300;
        ++count;if(!food)break;
    }
    if(list.begin)call<void>(b,0xb36928,list.begin);
    return count;
}
static Byte* magnetTarget(Word b,Byte*part){
    int rect[4]={0,0,16,5};MagnetList list={};call<void>(b,0x248120,&list,2u,rect);
    Byte*best=nullptr;Word eligible=0;
    for(Byte**q=list.begin;q!=list.end;++q){Byte*z=*q;
        if(!zombieClass(z)||at<Word>(z,0x48)-4u<5u||!virt<bool>(z,0x3c,3u))continue;
        ++eligible;if(call<Word>(b,0x7a3e90,eligible)==0)best=z;
    }if(list.begin)call<void>(b,0xb36928,list.begin);return best;
}
static void magnetPieces(Word b,Byte*f,float elapsed){
    Byte*p=at<Byte*>(f,4);bool busy=false;float time=battleTime(b);
    for(Word i=0;i<20;++i){Byte*item=magnetItem(f,i);Word phase=at<Word>(item,8);if(!phase)continue;
        Byte*part=weakObject(b,reinterpret_cast<Word*>(item));if(!part){releaseMagnetItem(b,item,false);continue;}
        at<float>(part,0x44)=time; // Keep native render alpha opaque while held.
        float target[3]={at<float>(p,0x10),at<float>(p,0x14),65};
        if(phase==3||phase==4||phase==6){Word row=Word((static_cast<unsigned long long>(i)*0xcccccccdULL)>>34),column=i-row*5;target[0]+=float(int(column)-2)*12;target[2]+=float(row)*12;}
        if(phase==6){
            virt<void>(part,0x58,target);if(time<at<float>(item,0x10))continue;
            phase=5;at<Word>(item,8)=5;
            Byte*z=magnetTarget(b,part);if(z)call<void>(b,0x13dea0,item+0x18,0u,at<Word>(z,8),at<Word>(z,0xc));
            trace(b,"magnet threw helmet",i);
        }
        if(phase==5){
            Byte*z=weakObject(b,reinterpret_cast<Word*>(item+0x18));
            if(!z||at<Word>(z,0x48)-4u<5u||!virt<bool>(z,0x3c,3u)){
                z=magnetTarget(b,part);if(z)call<void>(b,0x13dea0,item+0x18,0u,at<Word>(z,8),at<Word>(z,0xc));
            }
            if(!z){releaseMagnetItem(b,item,true);continue;}
            target[0]=at<float>(z,0x10);target[1]=at<float>(z,0x14);target[2]=35;
            float dx=target[0]-at<float>(part,0x10),dy=target[1]-at<float>(part,0x14);
            if(dx*dx+dy*dy<35.0f*35.0f){
                struct{Byte*source;float amount;Word flags;Word cond[3];}damage={p,300,0x400,{0,0,0}};
                virt<void>(z,0x34,&damage);trace(b,"magnet projectile hit",300);magnetSound(b,p,"Play_Plant_DarkAges_MagnetShroom_Impact_Helmet_Zombie");
                releaseMagnetItem(b,item,true);continue;
            }
        }
        if(phase==7){busy=true;if(time>=at<float>(item,0x10)){at<Word>(item,8)=2;at<float>(item,0x10)=time+11.7f;magnetAnimation(b,f,"busy",true);}continue;}
        if(phase==2){if(time>=at<float>(item,0x10)){releaseMagnetItem(b,item,true);magnetAnimation(b,f,"idle",true);}else busy=true;continue;}
        if(phase==4)continue;
        float dx=target[0]-at<float>(part,0x10),dy=target[1]-at<float>(part,0x14),dz=target[2]-at<float>(part,0x18);
        float distance=__builtin_sqrtf(dx*dx+dy*dy+dz*dz);
        float &speed=at<float>(item,0xc);speed=phase==5?650.0f:speed+2700.0f*elapsed;
        float travel=speed*elapsed;
        if(travel>=distance||distance<0.01f){
            virt<void>(part,0x58,target);
            if(phase==1){at<Word>(item,8)=7;at<float>(item,0x10)=time+1.3f;magnetAnimation(b,f,"catch",false);}
            else if(phase==3)at<Word>(item,8)=4;
        }else{float q[3]={at<float>(part,0x10)+dx*travel/distance,at<float>(part,0x14)+dy*travel/distance,at<float>(part,0x18)+dz*travel/distance};virt<void>(part,0x58,q);}
        if(phase==1)busy=true;
    }
    if(at<Word>(f,0xc)==1&&!busy)at<Word>(f,0xc)=0;
}
static void magnetVisuals(Word b,Byte*f){
    if(at<Word>(f,0x24))return;Byte*r=virt<Byte*>(at<Byte*>(f,4),0x70);if(!r)return;
    char*n=text(b,"Magnet_Item");call<void>(b,0x44cd0c,r,&n,0u);drop(b,n);at<Word>(f,0x24)=1;
}
static void magnetUpdate(Word b,Byte*f){
    magnetVisuals(b,f);
    Byte*bd=battleBoard(b),*p=at<Byte*>(f,4);if(!bd||at<Word>(bd,0xa8)!=5||call<bool>(b,0x1872a8,bd))return;
    float time=battleTime(b),elapsed=time-at<float>(f,0x14);at<float>(f,0x14)=time;
    if(elapsed<0||elapsed>0.2f)elapsed=0;
    magnetPieces(b,f,elapsed);
    Word phase=at<Word>(f,0xc);
    if(phase==2){
        if(time<at<float>(f,0x10))return;
        Word count=takeMetal(b,f,true);trace(b,"magnet PF collected",count);at<Word>(f,0xc)=3;at<float>(f,0x10)=time+1.5f;
        magnetAnimation(b,f,"plantfood_collection",true);return;
    }
    if(phase==3){
        if(time<at<float>(f,0x10))return;
        Word count=0;
        for(Word i=0;i<20;++i){Byte*e=magnetItem(f,i);if(at<Word>(e,8)){at<Word>(e,8)=6;at<float>(e,0xc)=650;at<float>(e,0x10)=time+0.166667f+float(count++)*(11.0f/30.0f);}}
        at<float>(p,0x74)=time+0.166667f+float(count)*(11.0f/30.0f)+0.6f;
        at<Word>(f,0xc)=4;magnetAnimation(b,f,"plantfood",true);return;
    }
    if(phase==4)return;
    if(phase==0&&time>=at<float>(f,8)){
        at<float>(f,8)=time+0.2f;
        if(takeMetal(b,f,false)){at<Word>(f,0xc)=1;magnetAnimation(b,f,"special",false);}
    }
}
