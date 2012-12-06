// Intro code to launch V8.

#include <v8.h>
#include <string.h>
#include <iostream>

#include "rtscfs.h"
#include "opengl.h"
#include "os.h"

using namespace v8;
using namespace std;

// On Windows we need an extra section to reuse for loading user data.
#ifdef WIN32
int _useless_filler_variable __attribute__((section(".ponies")));
#endif

// This variable will be overwritten in the binary by a fixup script.
void* fs_image_vma_pointer __attribute__((section(".unicorn"))) = (void*) 0xdeadbeef;

Handle<Value> print(const Arguments& x) {
	int length = x.Length();
	for (int ii=0; ii<length; ii++) {
		v8::String::AsciiValue argstr(x[ii]);
		cout << *argstr;
		if (ii<length-1)
			cout << " ";
	}
	cout << endl;
	Local<Value> result;
	return result;
}

Handle<Value> _load_c_extension(const Arguments& x) {
	v8::String::AsciiValue arg(x[0]);
	if (strcmp(*arg, "opengl") == 0) {
		v8::Handle<v8::Object> scope(x[1]->ToObject());
		opengl_init(scope);
	} else if (strcmp(*arg, "os") == 0) {
		v8::Handle<v8::Object> scope(x[1]->ToObject());
		os_init(scope);
	} else {
		cerr << "Unknown argument to _load_c_extension: " << *arg << endl;
		return v8::Integer::New(1);
	}
	return v8::Integer::New(0);
}

Handle<Value> _load_fs_data(const Arguments& x) {
	HandleScope handle_scope;
	v8::String::AsciiValue arg(x[0]);
	size_t string_length;
	void* string = rtscfs_find(*arg, &string_length);
	if (string == NULL) {
		cerr << "Couldn't load fs data: \"" << *arg << "\"" << endl;
		return v8::Integer::New(0);
	}
	v8::Handle<v8::Object> s = v8::Object::New();
	s->Set(v8::String::New("RTSC_pointer"), v8::External::Wrap(string));
	s->Set(v8::String::New("RTSC_length"), v8::Integer::New(string_length));
	s->Set(v8::String::New("RTSC_source"), v8::String::New(*arg, arg.length()));
	return handle_scope.Close(s);
}

int main(int argc, char* argv[]) {
	// Create a stack-allocated handle scope.
	HandleScope handle_scope;

	// Create a template for the global object and set the
	// built-in global functions.

	SCOPE(global);
	FUNC2(global, print, print);
	FUNC2(global, _load_c_extension, _load_c_extension);
	FUNC2(global, _load_fs_data, _load_fs_data);

	// Each processor gets its own context so different processors
	// do not affect each other.
	Persistent<Context> context = Context::New(NULL, global);

	// Enter the created context for compiling and
	// running the game script.
	Context::Scope context_scope(context);

	// Load up the rtscfs that is bundled in our binary, and loaded into memory.
	rtscfs_init(fs_image_vma_pointer);

	// Find the Javascript within this structure.
	size_t javascript_string_length;
	void* javascript_string = rtscfs_find("js", &javascript_string_length);

	if (javascript_string == NULL) {
		cerr << "Bundled rtscfs image has no \"js\" entry." << endl;
		return 2;
	}

	// Create a string containing the JavaScript source code.
	Handle<String> source = String::New((char*) javascript_string, javascript_string_length);

	// Compile the source code.
	Handle<Script> script = Script::Compile(source);

	// Run the script to get the result.
	Handle<Value> result = script->Run();

	// Dispose of the persistent context.
	context.Dispose();
}

