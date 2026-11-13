// Aster's existing Streetlamp behavior: authored illumination footprint,
// and 30 seconds of whole-board illumination following plant food.
static bool isStreetlamp(Word b,Byte*f){
    Byte*p=at<Byte*>(f,4);Byte*t=p?weakObject(b,reinterpret_cast<Word*>(p+0xb8)):nullptr;
    return t&&equalText(at<const char*>(t,0x10),"POPANIM_PLANT_STREETLAMP");
}
static Word streetlampEvent(Word b,Byte*f,Word mode){
    Byte*p=at<Byte*>(f,4);
    if(mode==5){
        call<void>(b,0x3ba164,f);at<Word>(p,0x48)=5;at<float>(f,0x10)=battleTime(b)+30;
        magnetAnimation(b,f,"attack02",false);trace(b,"streetlamp food illumination",30);
    }else if(mode==7){call<void>(b,0x3ba2c0,f);at<Word>(p,0x48)=4;}
    // No projectile action and no grade-based skill overrides.
    return 0;
}
