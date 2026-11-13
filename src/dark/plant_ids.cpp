// Extend every native PlantType enum mapper, preserving all 46 stock IDs.
// Resource-object order is not a plant's persistent unlock ID.
using Byte=unsigned char;using Word=unsigned int;
template<class R,class...A>static R call(Word b,Word p,A...a){return reinterpret_cast<R(*)(A...)>(b+p)(a...);}
static void add(Word b,Byte*object,const char*name,Word id){
#if IRIS_PLANT_IDS_TRACE
 call<int>(b,0xe8c10,3,"IrisPlantIds","add %s=%u object=%p",name,id,object);
#endif
 char*s,allocator;call<void>(b,0xb75560,&s,name,&allocator);
#if IRIS_PLANT_IDS_TRACE
 call<int>(b,0xe8c10,3,"IrisPlantIds","string ready=%p base=%08x",s,b);
#endif
 Word*value=call<Word*>(b,0x163f6c,object+4,&s);*value=id;
#if IRIS_PLANT_IDS_TRACE
 call<int>(b,0xe8c10,3,"IrisPlantIds","entry stored=%p",value);
#endif
 // This native operator[] takes an rvalue key. Insertion moves s into its
 // node and leaves the shared empty string behind; never release that rep.
 if(!*s)return;
 // Use the same libstdc++ release ABI as the original enum constructor.
 int previous=call<int>(b,0xb39a54,s-4,-1);
#if IRIS_PLANT_IDS_TRACE
 call<int>(b,0xe8c10,3,"IrisPlantIds","release previous=%d",previous);
#endif
 if(previous<=0)call<void>(b,0xb739d8,s-12,&allocator);
}
extern "C" __attribute__((section(".text.entry")))
Word iris_plant_ids(Word b,Word*args,Word){
#if IRIS_PLANT_IDS_TRACE
 call<int>(b,0xe8c10,3,"IrisPlantIds","constructor before object=%p",reinterpret_cast<Byte*>(args[0]));
#endif
 Byte*object=call<Byte*>(b,IRIS_PLANT_IDS_ORIGINAL,reinterpret_cast<Byte*>(args[0]));
#if IRIS_PLANT_IDS_TRACE
 call<int>(b,0xe8c10,3,"IrisPlantIds","constructor returned object=%p",object);
#endif
#include "iris_plant_ids.inc"
 // Growth forms share their base plant's ownership and statistics. Canonical
 // names sort before these aliases in the native reverse lookup.
 add(b,object,"sunshroom_grown",42);add(b,object,"sunshroom_stage3",42);
 add(b,object,"iris_iceshroom_stage2",52);add(b,object,"iris_iceshroom_stage3",52);
 add(b,object,"iris_fireshroom_stage2",53);add(b,object,"iris_fireshroom_stage3",53);
 return reinterpret_cast<Word>(object);
}
