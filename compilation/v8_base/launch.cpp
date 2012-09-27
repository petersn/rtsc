// Intro code to launch V8.

#include <v8.h>
#include <string.h>
#include <iostream>

using namespace v8;
using namespace std;

extern char _binary_code_js_start;
extern char _binary_code_js_end;

Handle<Value> print(const Arguments& x) {
	int length = x.Length();
	for (int ii=0; ii<length; ii++) {
		cout << *String::AsciiValue(x[ii]);
		if (ii<length-1)
			cout << " ";
	}
	cout << endl;
	Local<Value> result;
	return result;
}

int main(int argc, char* argv[]) {
	// Create a stack-allocated handle scope.
	HandleScope handle_scope;

	// Create a template for the global object and set the
	// built-in global functions.
	Handle<ObjectTemplate> global = ObjectTemplate::New();

#define FUNC(x) global->Set(String::New(#x), FunctionTemplate::New(x))

	FUNC(print);

	// Each processor gets its own context so different processors
	// do not affect each other.
	Persistent<Context> context = Context::New(NULL, global);

	// Enter the created context for compiling and
	// running the game script.
	Context::Scope context_scope(context);

	// Load up the Javascript source that is bundled in our binary.
	size_t source_length = (&_binary_code_js_end) - (&_binary_code_js_start);
	char* javascript_source = new char[source_length + 1];
	memcpy(javascript_source, &_binary_code_js_start, source_length);
	javascript_source[source_length] = 0;

	// Create a string containing the JavaScript source code.
	Handle<String> source = String::New(javascript_source);

	// Compile the source code.
	Handle<Script> script = Script::Compile(source);

	// Run the script to get the result.
	Handle<Value> result = script->Run();

	// Dispose of the persistent context.
	context.Dispose();
}

