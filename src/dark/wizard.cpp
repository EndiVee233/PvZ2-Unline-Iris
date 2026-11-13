// Preserve Iris's native sheep bookkeeping, death/shovel restoration and
// serializer. Only the two scalar casting deadlines need Aster's ranges.
using Byte=unsigned char;using Word=unsigned int;
template<class T>static T&at(Byte*p,Word o){return *reinterpret_cast<T*>(p+o);}
template<class R,class...A>static R call(Word b,Word p,A...a){return reinterpret_cast<R(*)(A...)>(b+p)(a...);}
extern "C" __attribute__((section(".text.entry")))
Word iris_wizard(Word b,Word*args,Word){
 Byte*z=reinterpret_cast<Byte*>(args[0]);
 if(at<float>(z,0x184)<0)at<float>(z,0x184)=7.0f+float(call<Word>(b,0x7a3e90,2001u))*0.001f;
 Word state=at<Word>(z,0x48);Word result=call<Word>(b,IRIS_WIZARD_ORIGINAL,z);
 if(state!=13&&at<Word>(z,0x48)==13){at<float>(z,0x184)=11.0f+float(call<Word>(b,0x7a3e90,3001u))*0.001f;
#if IRIS_DARK_TRACE
 call<int>(b,0xe8c10,3,"IrisDark","Wizard cast started zombie=%p",z);
#endif
 }
 return result;
}
