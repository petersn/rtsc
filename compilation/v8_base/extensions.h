// RTSC extension header.

#ifndef _RTSC_EXTENSIONS
#define _RTSC_EXTENSIONS

#include <v8.h>
#include <iostream>

using namespace std;

#define SCOPE(name) v8::Handle<v8::ObjectTemplate> name = v8::ObjectTemplate::New()
#define FUNC(obj, name, callback)                              \
  obj->Set(v8::String::NewSymbol("RTSC_" #name),                                   \
           v8::FunctionTemplate::New(callback)->GetFunction())
//#define FUNC2(obj, name, callback)                              \
//  obj->Set(v8::String::NewSymbol("RTSC_" #name),                                   \
//           v8::FunctionTemplate::New(callback)->GetFunction())
//#define FUNC(s, n, f) \
//	/*v8::Handle<v8::FunctionTemplate> s##n##f = v8::FunctionTemplate::New(f);*/ \
//	v8::Handle<v8::ObjectTemplate>::Cast(s)->Set(v8::String::New("RTSC_" #n), v8::FunctionTemplate::New(f))
#define FUNC2(s, n, f) \
	s->Set(v8::String::New("RTSC_" #n), v8::FunctionTemplate::New(f));
#define SET(s, n, x) s->Set(v8::String::New("RTSC_" #n), x)
#define DEC_FUNC(f) v8::Handle<v8::Value> f(const v8::Arguments& x)

#endif

