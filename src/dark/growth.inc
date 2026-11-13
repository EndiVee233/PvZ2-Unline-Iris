// Growth is serialized on the existing framework. Stage mutation uses the
// same native Plant operation as Sun-shroom, preserving the object's UID.
static Word growthKind(Word b,Byte*f){
    Byte*p=at<Byte*>(f,4),*t=p?weakObject(b,reinterpret_cast<Word*>(p+0xb8)):nullptr;
    const char*n=t?at<const char*>(t,0x10):nullptr;
    if(equalText(n,"POPANIM_PLANT_ICESHROOM"))return 1;
    if(equalText(n,"POPANIM_PLANT_ICESHROOM_IRIS_STAGE2"))return 2;
    if(equalText(n,"POPANIM_PLANT_ICESHROOM_IRIS_STAGE3"))return 3;
    if(equalText(n,"POPANIM_PLANT_FIRESHROOM"))return 4;
    if(equalText(n,"POPANIM_PLANT_FIRESHROOM_IRIS_STAGE2"))return 5;
    if(equalText(n,"POPANIM_PLANT_FIRESHROOM_IRIS_STAGE3"))return 6;
    return 0;
}
static int compareGrowthName(const char*a,const char*b){
    if(!a)return -1;while(*a&&*a==*b){++a;++b;}return int(static_cast<Byte>(*a))-int(static_cast<Byte>(*b));
}
static bool growthType(Word b,const char*name,Word*weak){
    Byte*map=*reinterpret_cast<Byte**>(b+0xd4ec98);
    Byte*node=map?at<Byte*>(map,8):nullptr;
    // Bounded traversal also makes a malformed development registry fail
    // closed instead of dereferencing an unbounded chain.
    for(Word i=0;node&&i<256;++i){
        int order=compareGrowthName(name,at<const char*>(node,0x10));
        if(!order){call<void>(b,0x13dea0,weak,0u,at<Word>(node,0x18),at<Word>(node,0x1c));return weak[0]||weak[1];}
        node=at<Byte*>(node,order<0?8:0xc);
    }return false;
}
static float growthInterval(Word kind){
    // Fixed second-tier intrinsic growth factor, with no rank/stat table.
    return kind<=3?22.5f:kind==4?15.0f:30.0f;
}
static Byte* changeGrowth(Word b,Byte*f,Word kind,Word next){
    const char*name=kind<=3?(next==2?"iris_iceshroom_stage2":"iris_iceshroom_stage3"):
                               (next==5?"iris_fireshroom_stage2":"iris_fireshroom_stage3");
    Word type[2]={};if(!growthType(b,name,type)){trace(b,"missing growth type",next);return nullptr;}
    Byte*p=at<Byte*>(f,4);float hp=at<float>(p,0x4c);Word col=at<Word>(p,0x5c),row=at<Word>(p,0x58);
    Byte active=at<Byte>(p,0x61);
    // This destroys f. Do not inspect the old framework after the call.
    call<void>(b,0x39df1c,p,col,row,type);call<void>(b,0x13dea0,type,0u,0u,0u);
    // Sun-shroom generates resources in its framework update. These two
    // attackers also need the native Plant action scheduler reactivated:
    // Plant::Reset explicitly clears this byte during every mutation.
    at<Byte>(p,0x61)=active;at<float>(p,0x4c)=hp;Byte*current=at<Byte*>(p,0x30);if(!current)return nullptr;
    at<float>(current,8)=battleTime(b)+growthInterval(next);
    float duration=kind<=3?(next==2?32.0f:27.0f)/30.0f:(next==5?65.0f:53.0f)/30.0f;
    at<float>(p,0x70)=battleTime(b)+duration;
    magnetAnimation(b,current,(next==2||next==5)?"growth_stage1":"growth_stage2",false);
    trace(b,"growth changed stage",next);return current;
}
static Word fireStone(Word b,Byte*f){
    Byte*p=at<Byte*>(f,4);int row=int(at<Word>(p,0x58)),col=int(at<Word>(p,0x5c));
    int rect[4]={col,row,16,1};MagnetList list={};call<void>(b,0x248120,&list,6u,rect);
    Byte*target=nullptr;float closest=1000000.0f;
    for(Byte**q=list.begin;q!=list.end;++q){Byte*entity=*q;if(!entity)continue;
        if(!virt<bool>(entity,0x3c,3u))continue;
        float x=at<float>(entity,0x10);if(x<at<float>(p,0x10)||x>=closest)continue;
        closest=x;target=entity;
    }
    if(list.begin)call<void>(b,0xb36928,list.begin);if(!target)return 0;
    Word previous=at<Word>(p,0xb4);at<Word>(p,0xb4)=1;
    Byte*shot=call<Byte*>(b,0x3a1b88,p);at<Word>(p,0xb4)=previous;if(!shot)return 0;
    at<float>(shot,0x2c)=at<float>(target,0x10)+10.0f;
    at<float>(shot,0x30)=at<float>(target,0x14)-at<float>(target,0x18)-30.0f;
    at<float>(shot,0x34)=0;
    call<void>(b,0x13dea0,shot+0x98,0u,at<Word>(target,8),at<Word>(target,0xc));
    trace(b,"fire stone summoned",reinterpret_cast<Word>(shot));return reinterpret_cast<Word>(shot);
}
static bool growthEntityClass(Byte*p,const char*name){Byte*t=p?virt<Byte*>(p,0):nullptr;for(Word i=0;t&&i<32;++i,t=at<Byte*>(t,8))if(equalText(at<const char*>(t,4),name))return true;return false;}
static Byte* growthTrap(Word b,Byte*p,bool fire,int col,int row){
    char*n=text(b,fire?"iris_fire_wall":"iris_ice_hole");
    Byte*t=call<Byte*>(b,0x17a8c4,battleBoard(b),&n,col,row);drop(b,n);
    trace(b,"ground effect spawned",reinterpret_cast<Word>(t));
    if(t)trace(b,"ground effect vtable",at<Word>(t,0));
    if(t)call<void>(b,0x13dea0,t+0x74,0u,at<Word>(p,8),at<Word>(p,0xc));return t;
}
static void growthGroundFood(Word b,Byte*p,bool fire){
    Byte*board=battleBoard(b);if(!board)return;
    if(fire){
        Word most=0,ties=0;int chosen=-1;
        for(int col=0;col<9;++col){int rect[4]={col,0,1,5};MagnetList list={};call<void>(b,0x248120,&list,6u,rect);Word enemies=0;bool wall=false;
            for(Byte**q=list.begin;q!=list.end;++q){Byte*z=*q;if(growthEntityClass(z,"IrisFireWall"))wall=true;
                else if(zombieClass(z)&&virt<bool>(z,0x3c,1u))++enemies;}
            if(list.begin)call<void>(b,0xb36928,list.begin);if(wall)continue;
            if(enemies>most){most=enemies;ties=0;}
            if(enemies==most&&call<Word>(b,0x7a3e90,++ties)==0)chosen=col;
        }
        if(chosen>=0)for(int row=0;row<5;++row)growthTrap(b,p,true,chosen,row);
        trace(b,"fire food wall column",Word(chosen));return;
    }
    for(Word spawned=0;spawned<2;++spawned){
        int freeCells[21],nearCells[21];Word count=0,near=0;
        for(int col=1;col<8;++col)for(int row=1;row<4;++row){int rect[4]={col-1,row-1,3,3};MagnetList list={};call<void>(b,0x248120,&list,6u,rect);bool hole=false,enemy=false;
            for(Byte**q=list.begin;q!=list.end;++q){Byte*z=*q;if(growthEntityClass(z,"IrisIceHole"))hole=true;else if(zombieClass(z)&&virt<bool>(z,0x3c,1u))enemy=true;}
            if(list.begin)call<void>(b,0xb36928,list.begin);if(hole)continue;
            freeCells[count++]=col*5+row;if(enemy)nearCells[near++]=col*5+row;
        }
        if(!count)break;int cell=near?nearCells[call<Word>(b,0x7a3e90,near)]:freeCells[call<Word>(b,0x7a3e90,count)];
        Word col=Word((static_cast<unsigned long long>(Word(cell))*0xcccccccdULL)>>34);
        growthTrap(b,p,false,int(col),cell-int(col)*5);
    }
    trace(b,"ice food holes",2);
}
static Word growthEvent(Word b,Byte*f,Word mode,Word kind){
    Byte*p=at<Byte*>(f,4);
    if(mode==5){
        bool fire=kind>3;bool grow=kind!=(fire?6u:3u);
        if(grow){f=changeGrowth(b,f,kind,fire?6u:3u);if(!f)return 0;}
        call<void>(b,0x3ba164,f);at<Word>(p,0x48)=5;
        at<Word>(f,0xc)=grow?1u:2u;float time=battleTime(b);
        float intro=grow?(fire?65.0f:35.0f)/30:0;
        at<float>(f,0x10)=time+intro;at<float>(p,0x74)=time+intro+(fire?100.0f:92.0f)/30;
        magnetAnimation(b,f,grow?"growth_stage3":"plantfood",false);
        trace(b,"growth food started",kind);return 0;
    }
    if(mode==7){
        // Mark first: native food end can be reached twice through an
        // animation callback and the duration fallback on the same tick.
        if(at<Word>(f,0xc)){at<Word>(f,0xc)=0;growthGroundFood(b,p,kind>3);}
        call<void>(b,0x3ba2c0,f);at<Word>(p,0x48)=4;magnetAnimation(b,f,"idle",true);return 0;
    }
    if(mode==4){
        if(at<Word>(p,0x48)==5)return 0;
        if(kind==6)return fireStone(b,f);
        trace(b,"growth fire begin",kind);
        Word previous=at<Word>(p,0xb4);at<Word>(p,0xb4)=0;
        Word shot=call<Word>(b,0x3a1b88,p);at<Word>(p,0xb4)=previous;
        if(shot){
            Byte*q=reinterpret_cast<Byte*>(shot);float scale=at<float>(p,0x44);
            at<float>(q,0x2c)=at<float>(p,0x10)-2.0f*scale;
            at<float>(q,0x30)=at<float>(p,0x14)+(kind<=3?(kind==3?-5.0f:5.0f):-25.0f)*scale;
            at<float>(q,0x34)=-0.32f*scale;
        }
        trace(b,"growth fire end",shot);return shot;
    }
    if(mode==8){
        Byte*board=battleBoard(b);
        if(!board||at<Word>(board,0xa8)!=5||call<bool>(b,0x1872a8,board))return 0;
        if(at<Word>(p,0x48)==5){if(at<Word>(f,0xc)==1&&battleTime(b)>=at<float>(f,0x10)){at<Word>(f,0xc)=2;magnetAnimation(b,f,"plantfood",false);}return 0;}
        if(at<Word>(p,0x48)!=4)return 0;
        if(kind==3||kind==6)return 0;
        float now=battleTime(b);float &deadline=at<float>(f,8);
        if(deadline<=0){deadline=now+growthInterval(kind);return 0;}
        if(now>=deadline){trace(b,"growth changing stage",kind);changeGrowth(b,f,kind,kind+1);}
    }
    return 0;
}
