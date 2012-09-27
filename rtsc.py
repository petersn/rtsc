# Main compiler!

import sys, os, struct
import parsing

class Compiler:
	BYTECODE_IDENTIFIER = "\x03RTSCv01"
	grammar = open("grammar.bnf").read()
	lexer = open("lexer.rxl").read()
	csharp_header = """// RTSC Generated C# code.

using System.Collections.Generic;

public class EntryPoint {
	public static void Main() {
		RTSC_Main.RTSC_func_main();
	}
}

"""
	import_search_path = [".", "libs"]

	def __init__(self):
		self.parser = parsing.Parser(self.grammar, self.lexer)
		self.import_stack = []
		self.imported = set()
		self.where = Class(None)
		for name in ("int",):
			self.where[name] = BuiltIn(name)
		self.where["float"] = BuiltIn("double")
		self.where["print"] = BuiltIn("print", "System.Console.WriteLine")

	def import_file(self, name):
		if name in self.imported:
			return
		if name in self.import_stack:
			self.import_stack.remove(name)
		self.import_stack.append(name)

	def churn(self):
		code = []
		while self.import_stack:
			name = self.import_stack.pop(0)
			self.imported.add(name)
			mtime = lambda p : os.stat(p).st_mtime
			for prefix in self.import_search_path:
				base_path = os.path.join(prefix, name)
				statements = None
				try:
					time1 = mtime(base_path + ".bytes")
					time2 = 0
					try:
						time2 = mtime(base_path + ".rtsc")
					except OSError:
						pass
					if time1 > time2:
						statements = self.process_bytecode(open(base_path + ".bytes").read())
				except OSError:
					pass
				if statements == None:
					try:
						data = open(base_path + ".rtsc").read()
						statements = self.process(data)
						bytecode = self.produce_bytecode(statements)
						open(base_path + ".bytes", "w").write(bytecode)
					except IOError:
						pass
				if statements != None:
					self.scan_for_imports(statements)
					code = statements + code
					break
			else:
				raise Exception("Couldn't find source: %r" % name)
		return code

	def produce_bytecode(self, statements):
		def num(x):
			if x < 255:
				return struct.pack("<B", x)
			else:
				return "\xff" + struct.pack("<I", x)
		string_table = {}
		def string_id(s):
			if s not in string_table:
				string_table[s] = len(string_table)
			return string_table[s]
		def serialize(x):
			if type(x) == list:
				return "".join(map(serialize, x)) + "l" + num(len(x))
			elif type(x) == str:
				return "s" + num(string_id(x))
			elif isinstance(x, parsing.Token):
				return "t" + num(string_id(x.type)) + num(string_id(x.string))
			else: assert False
		code_block = "".join(map(serialize, statements))
		string_table = dict(i[::-1] for i in string_table.items())
		string_table_code = self.BYTECODE_IDENTIFIER + "d" + num(len(string_table)) + "".join( num(len(string_table[i])) + string_table[i] for i in xrange(len(string_table)) )
		return string_table_code + code_block

	def process_bytecode(self, bytes):
		def num(x):
			if x[0] == "\xff":
				return struct.unpack("<I", x[1:5])[0], x[5:]
			return struct.unpack("<B", x[0])[0], x[1:]
		string_table = {}
		stack = []
		while bytes:
			t, bytes = bytes[0], bytes[1:]
			if t == "s":
				index, bytes = num(bytes)
				stack.append(string_table[index])
			elif t == "t":
				index0, bytes = num(bytes)
				index1, bytes = num(bytes)
				stack.append(parsing.Token((string_table[index0], string_table[index1])))
			elif t == "l":
				count, bytes = num(bytes)
				stack[-count:] = [stack[-count:]]
			elif t == "d":
				string_table = {}
				string_count, bytes = num(bytes)
				for i in xrange(string_count):
					count, bytes = num(bytes)
					string_table[len(string_table)], bytes = bytes[:count], bytes[count:]
			elif t == "\x03":
				identifier, bytes = bytes[:7], bytes[7:]
				assert identifier == self.BYTECODE_IDENTIFIER[1:], "Invalid bytecode."
			else: assert False
		return stack

	def scan_for_imports(self, code):
		for statement in code:
			if statement[0] == "import":
				self.import_file(statement[1].string)

	def process(self, code):
		compile_stack = [ ([], ["expr_list"]) ]
		starting_block = False
		lines = code.split("\n")
		for line in lines:
			tokens = self.parser.lex(line)
			# Ignore empty lines, including lines that consist purely of whitespace.
			if all(i.type in ("space", "tab") for i in tokens):
				continue
			whitespace = []
			while tokens and tokens[0].type in ("space", "tab"):
				whitespace.append(tokens[0].type)
				tokens.pop(0)
			# Remove all remaining whitespace tokens.
			tokens = [token for token in tokens if token.type not in ("space", "tab")]
			# Make sure the whitespace corresponds.
			if not all(i == j for i, j in zip(whitespace, compile_stack[-1][0])):
				raise Exception("Ambiguous mix of tabs and spaces.")
			if starting_block:
				if len(whitespace) <= len(compile_stack[-1][0]):
					compile_stack.pop()
				else:
					compile_stack[-1][0] = whitespace
				starting_block = False
			while len(whitespace) < len(compile_stack[-1][0]):
				compile_stack.pop()
			parsings = [ p for p in self.parser.parse(tokens) ]
			if len(parsings) == 0:
				raise Exception("No valid parsings: %r" % line)
			if len(parsings) != 1:
				for p in parsings:
					print(p)
					print(parsing.pretty(p))
				raise Exception("Multiple parsings.")
			p = parsings[0]
			for statement in p[1:]:
				if statement[0] in ("expr", "standalone", "valued", "declaration", "subclass"):
					compile_stack[-1][1].append( statement )
				elif statement[0] in ("function_definition", "loop", "class"):
					# Make a list to contain the code we're going to insert.
					statement.append( ["expr_list"] )
					compile_stack[-1][1].append( statement )
					compile_stack.append([compile_stack[-1][0], statement[-1]])
					starting_block = True
				elif statement[0] == "import":
					if len(compile_stack) != 1:
						raise Exception("Non-top level imports not allowed.")
					compile_stack[-1][1].append( statement )
				else:
					assert False, "Unknown compile-time statement: %r" % statement
		return compile_stack[0][1]

	def build_structure(self, statement, where=None):
		if where == None:
			where = self.where
		if statement[0] == "import":
			pass # Imports have already been handled.
		elif statement[0] == "class":
			new = where[statement[1].string] = Class(statement[1].string, parent=where)
			self.build_structure(statement[2], new)
		elif statement[0] == "function_definition":
			if not isinstance(statement[2], parsing.Token): # Global function.
				new = where[statement[1].string] = Function(statement[1].string, parent=where)
				index = 2
			else:
				new = where[statement[1].string][statement[2].string] = Function(statement[2].string, parent=where)
				index = 3
			new.arguments = [ (ForwardsRef(where, arg[1][1].string) if len(arg) == 3 else None, arg[-1].string) for arg in statement[index:-1] ]
			self.build_structure(statement[-1], new)
		elif statement[0] in ("expr_list", "expr"):
			for sub in statement[1:]:
				self.build_structure(sub, where)
		elif statement[0] == "subclass":
			for inherit in [i.string for i in statement[1:]]:
				if inherit not in where.inherits:
					where.inherits.append(ForwardsRef(where, inherit))
		else:
			where.code_stack[-1].append(statement)

	def write_csharp(self):
		return self.csharp_header + self.where.write_csharp() + "\n"

class ForwardsRef:
	def __init__(self, where, name):
		self.where, self.name = where, name
		self.prebind = where[name] if name in where else None

	def resolve(self):
		if self.prebind != None:
			return self.prebind
		return self.where[self.name]

def indent(s):
	return "\n".join(("\t" + line).rstrip() for line in s.split("\n"))

class Class:
	executable = False

	def __init__(self, name, parent=None):
		self.name = name
		self.inherits = []
		self.code = ["expr_list"]
		self.code_stack = [self.code]
		self.parent = parent
		self.state = {}

	def __contains__(self, index):
		if index in self.state:
			return True
		elif self.parent and index in self.parent:
			return True
		return False

	def __getitem__(self, index):
		if index not in self:
			raise KeyError, "Undefined variable: %r" % index
		if index in self.state:
			return self.state[index]
		return self.parent[index]

	def __setitem__(self, index, value):
		self.state[index] = value

	def resolve(self):
		return self

	def identifier(self):
		if self.name == None:
			return "RTSC_Main"
		return "RTSC_class_%s" % self.name

	def write_csharp(self):
		self.inherits = [i.resolve() for i in self.inherits]
		s = []
		objs = self.state.values()
		deferred = []
		if self.name == None:
			deferred = [i for i in objs if not isinstance(i, (Function, BuiltIn, Variable))]
			objs = [i for i in objs if i not in deferred]
		s.append("public class %s : %s {\n" % (self.identifier(), ", ".join(["RTSCClass"] + [i.identifier() for i in self.inherits])))
		for obj in objs:
			s.append(indent(obj.write_csharp()))
		s.append("}\n")
		for obj in deferred:
			s.append(obj.write_csharp())
		return "".join(s)

class BuiltIn:
	def __init__(self, name, result=None):
		self.name, self.result = name, result or name

	def resolve(self):
		return self

	def identifier(self):
		return self.result

	def write_csharp(self):
		return ""

unique_counter = 0
def unique():
	global unique_counter
	unique_counter += 1
	return "tag%i" % unique_counter

class Function(Class):
	executable = True

	def identifier(self):
		return "RTSC_func_%s" % self.name

	def write_csharp(self):
		self.arguments = [ (resolve_type(arg[0]), arg[1]) for arg in self.arguments ]
		# Confusing, but top level functions are two down from the top.
		staticness = " static" if self.parent.parent == None else ""
		for arg in self.arguments:
			self[arg[1]] = Variable(arg[1])
		fmt = (staticness, self.identifier(), ", ".join(arg[0].identifier() + " " + self[arg[1]].identifier() for arg in self.arguments))
		s = ["public%s dynamic %s(%s) {\n" % fmt]
		s.append(indent(self.write_for(self.code, getValue=False)[0]))
		s.append("\treturn null;\n")
		s.append("}\n")
		return "".join(s)

	def type_code(self, typ):
		def _type_code(typ):
			if isinstance(typ, parsing.Token):
				return self[typ.string].identifier()
			elif typ[0] == "type":
				return _type_code(typ[1])
			elif typ[0] == "array_type":
				return _type_code(typ[1]) + "[]"
			assert False, "Unknown type: %r" % typ
		return BuiltIn(_type_code(typ))

	def write_for(self, code, getValue=True):
		if code[0] == "expr":
			return self.write_for(code[1], getValue)
		elif code[0] == "expr_list":
			s = []
			for i in code[1:]:
				v = self.write_for(i, getValue=False)
				s.append(v[0])
			return ("".join(s), "")
		elif code[0] == "function_call":
			func = self.write_for(code[1])
			args = map(self.write_for, code[2:])
			preamble = "".join(i[0] for i in args)
			fmt = (func[1], ", ".join(i[1] for i in args))
			if getValue:
				tag = unique()
				return (preamble + "dynamic %s = %s(%s);\n" % ((tag,)+fmt), tag)
			else:
				return (preamble + "%s(%s);\n" % fmt, "")
		elif code[0] == "float":
			return ("", "".join(i.string for i in code[1:]))
		elif code[0] == "literal":
			if code[1].type == "token":
				tok = code[1].string
				self[tok] = self[tok].resolve()
				return ("", self[tok].identifier())
			elif code[1].type in ("string", "number"):
				return ("", code[1].string)
			assert False
		elif code[0] == "assignment":
			var = extra = preamble = ""
			if isinstance(code[1], list):
				if code[1][0] == "getattr":
					preamble, lhs = self.write_for(code[1][1])
					extra = "." + code[1][2].string
				elif code[1][0] == "indexing":
					preamble, lhs = self.write_for(code[1][1])
					lhs = lhs[1]
					#extra = "[" + code[1][2].string
			else:
				lhs = code[1].string
				if lhs not in self:
					self[lhs] = Variable(lhs)
					var = "dynamic "
				lhs = self[lhs]
			rhs = self.write_for(code[-1])
			fmt = (var, lhs.identifier(), extra, code[3].string if len(code) == 4 else "", rhs[1])
			return (preamble + rhs[0] + "%s%s%s %s= %s;\n" % fmt, lhs.identifier())
		elif code[0] in ("op", "indexing"):
			lhs = self.write_for(code[1])
			rhs = self.write_for(code[-1])
			if code[0] == "op":
				op, post = "".join(i.string for i in code[2:-1]), ""
			else:
				op, post = "[]"
			tag = unique()
			return (lhs[0] + rhs[0] + "dynamic %s = %s%s%s%s;\n" % (tag, lhs[1], op, rhs[1], post), tag)
		elif code[0] == "unop":
			rhs = self.write_for(code[-1])
			tag = unique()
			return (rhs[0] + "dynamic %s = %s%s;\n" % (tag, code[1].string, rhs[1]), tag)
		elif code[0] == "list":
			args = map(self.write_for, code[1:])
			return ("".join(i[0] for i in args), "new dynamic[] {" + ", ".join(i[1] for i in args) + "}")
		elif code[0] == "loop":
			if code[1].string == "for":
				itr = self.write_for(code[3])
				lhs = code[2].string
				self[lhs] = lhs = Variable(lhs)
				return (itr[0] + "foreach (dynamic %s in %s) {\n" % (lhs.identifier(), itr[1]) + indent(self.write_for(code[4])[0]) + "}\n", "")
		elif code[0] == "declaration":
			type_of = self.type_code(code[1])
			for dec_unit in code[2:]:
				new = self[dec_unit[1].string] = Variable(dec_unit[1].string)
				new.type_of = type_of
				preamble = new.write_csharp()
				if len(dec_unit) == 3:
					asgn, _ = self.write_for(["assignment", dec_unit[1], dec_unit[2]])
					preamble = preamble + asgn
				return (preamble, "")
		elif code[0] == "interval":
			if len(code) == 2:
				lhs = self.write_for(code[1])
				tag = unique()
				return (lhs[0] + "int[] %s = RTSC.range(0, %s);\n" % (tag, lhs[1]), tag)
		elif code[0] == "list_comp":
			itr = self.write_for(code[3])
			lhs = code[2].string
			self[lhs] = lhs = Variable(lhs)
			tag = unique()
			expr = self.write_for(code[1])
			fmt = (tag, lhs.identifier(), itr[1], indent(expr[0]), tag, expr[1])
			return (itr[0] + "List<dynamic> %s = new List<dynamic>();\nforeach (dynamic %s in %s) {\n%s\t%s.Add((dynamic)%s);\n}\n" % fmt, tag)
		elif code[0] == "valued":
			if code[1].string == "return":
				lhs = self.write_for(code[2])
				return (lhs[0] + "return %s;\n" % (lhs[1],), "")
		else:
			print code
			assert False
		return (s, "")

def resolve_type(x):
	if x == None:
		return BuiltIn("dynamic")
	return x.resolve()

class Variable(Class):
	executable = False
	type_of = None

	def identifier(self):
		return "RTSC_var_%s" % self.name

	def write_csharp(self):
		self.type_of = resolve_type(self.type_of)
		return "%s %s;\n" % (self.type_of.identifier(), self.identifier())

ctx = Compiler()
ctx.import_file(sys.argv[1])
ctx.build_structure(ctx.churn())
csharp = ctx.write_csharp()

import remote_compilation
status, binary = remote_compilation.remote_compile(csharp)

if status == "g":
	fd = open("Main.exe", "w")
	fd.write(binary)
	fd.close()
elif status == "e":
	print "Error:"
	print binary.strip()
	exit(1)
elif status == "f":
	print "Remote compilation server not running."
else:
	assert False

