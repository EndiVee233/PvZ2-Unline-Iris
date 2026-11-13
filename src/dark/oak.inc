// Source tier-two intrinsic split arrows, with tier-one damage and health.
static bool isOak(Word b,Byte*f){Byte*p=at<Byte*>(f,4),*t=p?weakObject(b,reinterpret_cast<Word*>(p+0xb8)):nullptr;return t&&equalText(at<const char*>(t,0x10),"POPANIM_PLANT_OAKSHOOTER");}
static Byte*oakShot(Word b,Byte*p,Word action){Word prev=at<Word>(p,0xb4);at<Word>(p,0xb4)=action;Byte*s=call<Byte*>(b,0x3a1b88,p);at<Word>(p,0xb4)=prev;return s;}
static void oakRain(Word b,Byte*f,Word index){
 Byte*p=at<Byte*>(f,4),*board=battleBoard(b);if(!board)return;
 // Aster rains forty shots in 1.2 seconds. Every fourth arrow favours an
 // enemy's predicted position; remaining arrows cover the authored lawn.
 float x=float(call<int>(b,0x17d518,board,0))+float(call<Word>(b,0x7a3e90,512u));
 int row=int(call<Word>(b,0x7a3e90,5u));float y=float(call<int>(b,0x1814a4,board,row));float z=98;
 if((index&3u)==1){int rect[4]={0,0,16,5};MagnetList list={};call<void>(b,0x248120,&list,2u,rect);Byte*target=nullptr;Word count=0;
  for(Byte**q=list.begin;q!=list.end;++q){Byte*t=*q;if(zombieClass(t)&&virt<bool>(t,0x3c,3u)&&call<Word>(b,0x7a3e90,++count)==0)target=t;}
  if(target){x=at<float>(target,0x10)-60;y=at<float>(target,0x14);}
  if(list.begin)call<void>(b,0xb36928,list.begin);
 }
 Byte*s=oakShot(b,p,1);if(!s)return;
 at<float>(s,0x2c)=x;at<float>(s,0x30)=y;at<float>(s,0x34)=z;
 at<float>(s,0x38)=150;at<float>(s,0x3c)=5;at<float>(s,0x40)=-160;
 at<float>(s,0x44)=0;at<float>(s,0x48)=0;at<float>(s,0x4c)=-400;
 at<float>(s,0x78)=1.2f;at<float>(s,0x7c)=0;
}
static Word oakEvent(Word b,Byte*f,Word mode){
 Byte*p=at<Byte*>(f,4);
 if(mode==4){if(at<Word>(p,0x48)==5)return 0;Word result=0;
  for(Word i=0;i<3;++i){Byte*s=oakShot(b,p,i==1?0u:2u);if(!s)continue;result=reinterpret_cast<Word>(s);
   at<float>(s,0x38)=i==1?333.0f:288.38645f;at<float>(s,0x3c)=i==1?0:i==0?-166.5f:166.5f;
   at<float>(s,0x40)=0;at<float>(s,0x78)=i==1?0:i==0?-0.5235988f:0.5235988f;at<float>(s,0x7c)=0;
  }trace(b,"oak split attack",3);return result;
 }
 if(mode==5){call<void>(b,0x3ba164,f);at<Word>(p,0x48)=5;at<Word>(f,0xc)=1;at<Word>(f,0x18)=0;
  at<float>(f,0x10)=battleTime(b)+1.413f;at<float>(p,0x74)=battleTime(b)+80.0f/30;
  magnetAnimation(b,f,"plantfood",false);trace(b,"oak food started",40);return 0;
 }
 if(mode==7){call<void>(b,0x3ba2c0,f);at<Word>(p,0x48)=4;at<Word>(f,0xc)=0;magnetAnimation(b,f,"idle",true);return 0;}
 if(mode==8){Byte*board=battleBoard(b);if(!board||at<Word>(board,0xa8)!=5||call<bool>(b,0x1872a8,board))return 0;
  if(at<Word>(f,0xc)&&at<Word>(p,0x48)==5){float now=battleTime(b);
   while(at<Word>(f,0x18)<40&&now>=at<float>(f,0x10)){Word index=at<Word>(f,0x18)++;at<float>(f,0x10)+=0.03f;oakRain(b,f,index);}
  }
 }
 return 0;
}
