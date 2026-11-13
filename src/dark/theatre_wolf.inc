// Authored theatre-only wolf effects. These are not ordinary Dark Ages actors.
static Byte*theatreEffect(Word b,const char*id,const char*label,bool loop){Byte*h=**reinterpret_cast<Byte***>(b+0xd008bc);if(!h)return nullptr;char*n=text(b,id);Word w[2]={};
 at<void(*)(Word*,Byte*,Word,char**,Word)>(at<Byte*>(h,0),8)(w,h,call<Word>(b,0x129ae0),&n,0u);drop(b,n);Byte*res=weakObject(b,w);call<void>(b,0x13dea0,w,0u,0u,0u);if(!res)return nullptr;
 Byte*e=call<Byte*>(b,0x1809a8,battleBoard(b));if(!e)return nullptr;call<void>(b,0x23a354,e,res,0u);call<void>(b,0x23a814,e,1u);n=text(b,label);call<void>(b,0x23aa6c,e,&n,loop?3u:0u);drop(b,n);return e;
}
static void clearBoostEffect(Word b,Byte*z){Byte*e=weakObject(b,reinterpret_cast<Word*>(z+0x1bc));if(e)call<void>(b,0x2708b4,e);call<void>(b,0x13dea0,z+0x1bc,0u,0u,0u);}
static void boostVisual(Word b,Byte*z){bool active=battleTime(b)<at<float>(z,0x1b0);Byte*r=weakObject(b,reinterpret_cast<Word*>(z+0x40));
 if(Word(active)!=at<Word>(z,0x1c4)){if(r)call<void>(b,0x5ee918,r,call<float>(b,0x62c1e8,z+0x150)*(active?2.0f:1.0f));at<Word>(z,0x1c4)=active;}
 if(!active){clearBoostEffect(b,z);return;}Byte*e=weakObject(b,reinterpret_cast<Word*>(z+0x1bc));
 if(!e){e=theatreEffect(b,"POPANIM_EFFECTS_ZOMBIE_SPEEDUP_EFFECT","animation",true);if(!e)return;call<void>(b,0x13dea0,z+0x1bc,0u,at<Word>(e,8),at<Word>(e,0xc));}
 float pos[3]={at<float>(z,0x10),at<float>(z,0x14)-32,at<float>(z,0x18)};call<void>(b,0x4e6bb8,e,pos,0xffffffffu);
}
static void boostAll(Word b){int rect[4]={-8,-1,32,7};MagnetList list={};call<void>(b,0x248120,&list,2u,rect);Word count=0;
 for(Byte**q=list.begin;q!=list.end;++q){Byte*z=*q;if(z&&alive(z)&&virt<Byte*>(z,0)==at<Byte*>(state(b),12)){at<float>(z,0x1b0)=battleTime(b)+10;++count;}}
 if(list.begin)call<void>(b,0xb36928,list.begin);trace(b,"wolf speed boost",count);
}
static Byte*wolfTarget(Word b,Byte*z){int rect[4]={0,0,9,5};MagnetList list={};call<void>(b,0x248120,&list,1u,rect);Byte*chosen=nullptr;float best=40.0f*40.0f;
 for(Byte**q=list.begin;q!=list.end;++q){Byte*p=*q;if(!p||house(b,p)||at<Word>(p,0x48)==3||at<float>(p,0x4c)<=0)continue;
  float dx=at<float>(p,0x10)-at<float>(z,0x10),dy=at<float>(p,0x14)-at<float>(z,0x14);if(dx<0)dx=-dx;if(dy<0)dy=-dy;
  // Reach is measured to the tower's tile bounds, not its centre. A
  // centre-only 40-pixel radius cannot touch towers beside a 64-pixel road.
  dx=dx>32?dx-32:0;dy=dy>38?dy-38:0;float dist=dx*dx+dy*dy;if(dist<best){chosen=p;best=dist;}}
 if(list.begin)call<void>(b,0xb36928,list.begin);return chosen;
}
static void burnPlant(Word b,Byte*z,Byte*p){if(!p)return;Byte*e=theatreEffect(b,"POPANIM_EFFECTS_PLANT_BE_FIRED","animation",false);
 if(e){float pos[3]={at<float>(p,0x10),at<float>(p,0x14)-32,at<float>(p,0x18)};call<void>(b,0x4e6bb8,e,pos,0xffffffffu);}
 char*n=text(b,"Play_Zomb_Egypt_Explorer_Mvmt_Burn");call<void>(b,0x1a4280,z,&n,0.0f);drop(b,n);Word id=at<Word>(p,8);call<void>(b,0x39ece8,p,0u);trace(b,"wolf burned plant",id);
}
static Byte*launchedPlant(Byte*m,Byte*p){if(!m||!p)return nullptr;for(Word i=0;i<45;++i){Byte*r=m+0x320+i*32;if(at<Word>(r,0)==at<Word>(p,8)&&at<Word>(r,4)==at<Word>(p,12))return r;}return nullptr;}
static void updateLaunches(Word b,Byte*m){for(Word i=0;i<45;++i){Byte*r=m+0x320+i*32;Byte*p=weakObject(b,reinterpret_cast<Word*>(r));if(!p){call<void>(b,0x13dea0,r,0u,0u,0u);continue;}
 float t=battleTime(b)-at<float>(r,8);if(t<0)t=0;if(t>1)t=1;
 float pos[3]={at<float>(r,12)+at<float>(r,24)*t,at<float>(r,16),at<float>(r,20)+800*t*(1-t)};virt<void>(p,0x58,pos);
 if(t>=1||at<Word>(p,0x48)==3){at<Byte>(p,0x61)=Byte(at<Word>(r,28));if(at<Word>(p,0x48)!=3)call<void>(b,0x39ece8,p,0u);call<void>(b,0x13dea0,r,0u,0u,0u);}}
}
static void blowPlant(Word b,Byte*z,Byte*p){Byte*m=module(b);if(!m||!p||launchedPlant(m,p))return;
 for(Word i=0;i<45;++i){Byte*r=m+0x320+i*32;if(weakObject(b,reinterpret_cast<Word*>(r)))continue;
  call<void>(b,0x13dea0,r,0u,at<Word>(p,8),at<Word>(p,12));at<float>(r,8)=battleTime(b);for(Word j=0;j<3;++j)at<float>(r,12+j*4)=at<float>(p,0x10+j*4);
  at<float>(r,24)=float(int(call<Word>(b,0x7a3e90,201u))-100);at<Word>(r,28)=at<Byte>(p,0x61);at<Byte>(p,0x61)=0;trace(b,"wolf launched plant",at<Word>(p,8));return;}
}
static float wolfRandom(Word b,float low,float high){return low+(high-low)*call<float>(b,0x7a3ee0,1.0f);}
static bool wolfSkill(Word b,Byte*z,Byte*config,float dt){Byte*zp=zprops(b,z);Word kind=zp?at<Word>(zp,0xd8):0;
 if(kind==7){if(battleTime(b)>=at<float>(z,0x1b8)){Byte*p=wolfTarget(b,z);if(p){burnPlant(b,z,p);at<float>(z,0x1b8)=battleTime(b)+.5f;}}return false;}
 if(kind!=9)return false;float now=battleTime(b);Word phase=at<Word>(z,0x19c);
 if(at<Word>(z,0x150)&0xeu){if(at<float>(z,0x1a8)>0)at<float>(z,0x1a8)+=dt;if(phase)at<float>(z,0x1a0)+=dt;return phase!=0;}
 if(!at<float>(z,0x1a8))at<float>(z,0x1a8)=now+wolfRandom(b,7,9);
 if(!phase&&now>=at<float>(z,0x1a8)){Word count=at<Word>(config,0x30);if(!count||count>8)return false;
  Word pick=call<Word>(b,0x7a3e90,count),skill=at<Word>(config,0x34+pick*4);if(skill>2)return false;
  at<Word>(z,0x19c)=phase=skill+1;at<Word>(z,0x1b4)=0;at<float>(z,0x1a0)=now+(phase==1?160.0f:130.0f)/30;at<float>(z,0x1a8)=now+wolfRandom(b,12,15);animation(b,z,phase==1?"intro":"chui",false);trace(b,"wolf skill started",phase);
 }
 if(!phase)return false;float remaining=at<float>(z,0x1a0)-now;
 if(!at<Word>(z,0x1b4)&&remaining<=(phase==1?89.0f:53.0f)/30){at<Word>(z,0x1b4)=1;if(phase==1)boostAll(b);else if(phase==2)burnPlant(b,z,wolfTarget(b,z));else blowPlant(b,z,wolfTarget(b,z));}
 if(remaining<=0){at<Word>(z,0x19c)=0;animation(b,z,"walk");trace(b,"wolf skill ended",phase);}return true;
}
