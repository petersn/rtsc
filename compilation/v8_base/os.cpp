// OpenGL linking.

#include <math.h>
#include <time.h>
#include "os.h"

v8::Handle<v8::Value> os_sleep(const v8::Arguments& x) {
	double t = x[0]->NumberValue();
	struct timespec ts;
	double integ;
	double frac = modf(t, &integ);
	ts.tv_sec = integ;
	ts.tv_nsec = frac * 1e9;
	nanosleep(&ts, NULL);
	return v8::Integer::New(0);
}

v8::Handle<v8::Value> os_exit(const v8::Arguments& x) {
	exit(x[0]->Int32Value());
	return v8::Integer::New(0);
}

void os_init(v8::Handle<v8::ObjectTemplate>& global) {
	SCOPE(os);
	SET(global, os, os);
	FUNC(os, sleep, os_sleep);
	FUNC(os, exit, os_exit);
}

