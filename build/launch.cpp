// Intro code to launch V8.

#include <v8.h>
#include <string.h>
#include <iostream>

#include "rtscfs.h"
#include "opengl.h"
#include "os.h"

using namespace v8;
using namespace std;

#ifdef BIFURCATED_LAUNCHER
# include <sys/types.h>
# include <sys/stat.h>
# include <unistd.h>
#endif

#ifndef BIFURCATED_LAUNCHER
// On Windows we need an extra section to reuse for loading user data.
# ifdef WIN32
int _useless_filler_variable __attribute__((section(".ponies")));
# endif

// This variable will be overwritten in the binary by a fixup script.
void* fs_image_vma_pointer __attribute__((section(".unicorn"))) = (void*) 0xdeadbeef;
#endif

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
#if WRAP_WORKAROUND
	s->Set(v8::String::New("RTSC_pointer"), v8::Integer::New(reinterpret_cast<signed int>(string)));
#else
	s->Set(v8::String::New("RTSC_pointer"), v8::External::Wrap(string));
#endif
	s->Set(v8::String::New("RTSC_length"), v8::Integer::New(string_length));
	s->Set(v8::String::New("RTSC_source"), v8::String::New(*arg, arg.length()));
	return handle_scope.Close(s);
}

Handle<Value> _fs_data_length(const Arguments& x) {
	HandleScope handle_scope;
	v8::String::AsciiValue arg(x[0]);
	size_t string_length;
	void* string = rtscfs_find(*arg, &string_length);
	return v8::Integer::New(string == NULL ? -1 : string_length);
}

Handle<Value> _data_to_string(const Arguments& x) {
	HandleScope handle_scope;
	Handle<Object> data = x[0]->ToObject();
	if (not data->Has(v8::String::New("RTSC_pointer"))) {
		cerr << "Attempted _data_to_string() on something that isn't a data object." << endl;
	}
#if WRAP_WORKAROUND
	char* data_ptr = reinterpret_cast<char*>(data->Get(v8::String::New("RTSC_pointer"))->Int32Value());
#else
	char* data_ptr = (char*) v8::External::Unwrap(data->Get(v8::String::New("RTSC_pointer")));
#endif
	int length = data->Get(v8::String::New("RTSC_length"))->Int32Value();
	return v8::String::New(data_ptr, length);
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
	FUNC2(global, _fs_data_length, _fs_data_length);
	FUNC2(global, _data_to_string, _data_to_string);

	// Each processor gets its own context so different processors
	// do not affect each other.
	Persistent<Context> context = Context::New(NULL, global);

	// Enter the created context for compiling and
	// running the game script.
	Context::Scope context_scope(context);

#ifdef BIFURCATED_LAUNCHER
	if (argc != 2) {
		cerr << "Usage: rtsc_launcher game.rtscfs" << endl;
		return 2;
	}
	struct stat sb;
	if (stat(argv[1], &sb) == -1) {
		cerr << "Couldn't stat input file." << endl;
		return 1;
	}
	void* fs_image_vma_pointer = (void*) new char[sb.st_size];
	FILE* fd = fopen(argv[1], "rb");
	if (fread(fs_image_vma_pointer, 1, sb.st_size, fd) != sb.st_size) {
		cerr << "Couldn't read the number of bytes we expected." << endl;
		cerr << "Continuing anyway." << endl;
	}
	fclose(fd);
#endif

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

