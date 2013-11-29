#! /usr/bin/python2.7
# Main compiler!

import sys, os, struct, time, pprint, copy, collections
import parsing

version = (0, 1)

normal = grey = red = green = yellow = blue = purple = teal = ""
if sys.stdout.isatty():
	normal = "\x1B\x5B\x30\x6D"
	grey   = "\x1B\x5B\x30\x31\x3B\x33\x30\x6D"
	red    = "\x1B\x5B\x30\x31\x3B\x33\x31\x6D"
	green  = "\x1B\x5B\x30\x31\x3B\x33\x32\x6D"
	yellow = "\x1B\x5B\x30\x31\x3B\x33\x33\x6D"
	blue   = "\x1B\x5B\x30\x31\x3B\x33\x34\x6D"
	purple = "\x1B\x5B\x30\x31\x3B\x33\x35\x6D"
	teal   = "\x1B\x5B\x30\x31\x3B\x33\x36\x6D"

class CompilationException(Exception):
	pass

local_dir = os.path.dirname(os.path.realpath(__file__))

class Compiler:
	BYTECODE_IDENTIFIER = "\x03RTSCv01"
	grammar = open(os.path.join(local_dir, "data", "grammar.bnf")).read()
	lexer = open(os.path.join(local_dir, "data", "lexer.rxl")).read()
	js_header = """// RTSC Generated JS code.
"""
	js_footer = """
//RTSC_main();
"""
	import_search_path = [os.path.join(local_dir, "libs")]

	def __init__(self):
		self.parser = parsing.Parser(self.grammar, self.lexer)
		self.import_stack = []
		self.imported = set()
		self.cache_hits = 0
		self.cache_misses = 0
		self.parsing_cache = {}
		self.cwd = "."
		self.newest_source_time = float("-inf")

	def chdir(self, path):
		if os.path.isabs(path):
			self.cwd = path
		else:
			self.cwd = os.path.normpath(os.path.join(self.cwd, path))
		self.cwd = os.path.realpath(self.cwd)

	def import_file(self, name):
		if name in self.imported:
			return
		if name in self.import_stack:
			self.import_stack.remove(name)
		self.import_stack.append(name)

	def load_parsing_cache(self, path=None):
		if path == None:
			path = os.path.join(local_dir, "data", "parse_cache")
		data = open(path).read()
		stmts = self.process_bytecode(data)
		assert stmts[0] == "parse_cache"
		for name, a, b in stmts[1:]:
			assert name == "cache"
			self.parsing_cache[tuple(a)] = b

	def save_parsing_cache(self, path=None):
		if path == None:
			path = os.path.join(local_dir, "data", "parse_cache")
		stmts = ["parse_cache"] + [["cache", list(a), b] for a, b in self.parsing_cache.iteritems()]
		bc = self.produce_bytecode(stmts)
		a = self.process_bytecode(bc)
		fd = open(path, "w")
		fd.write(bc)
		fd.close()

	def churn(self):
		code = []
		while self.import_stack:
			name = self.import_stack.pop(0)
			module_name = os.path.split(os.path.splitext(name)[0])[1]
			self.imported.add(name)
			mtime = lambda p : os.stat(p).st_mtime
			for prefix in [self.cwd] + self.import_search_path:
				base_path = os.path.join(prefix, name)
				bytes_path = os.path.splitext(base_path)[0] + ".bytes"
				statements = None
				try:
					time1 = mtime(bytes_path)
					time2 = float("-inf")
					try:
						time2 = mtime(base_path)
					except OSError:
						pass
					if time1 > time2:
						statements = self.process_bytecode(open(bytes_path).read())
					self.newest_source_time = max(self.newest_source_time, time1, time2)
				except OSError:
					pass
				if statements == None:
					try:
						data = open(base_path).read()
						self.newest_source_time = max(self.newest_source_time, mtime(base_path))
						statements = self.process(data)
						bytecode = self.produce_bytecode(statements)
						open(bytes_path, "w").write(bytecode)
					except IOError:
						pass
				if statements != None:
					self.scan_for_imports(statements)
					if code and code[0] == "expr_list":
						code = code[1:]
					code.insert(0, (module_name, statements))
					break
			else:
				raise CompilationException("Couldn't find source: %r" % name)
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
				for sub in statement[1:]:
					self.import_file(sub.string + ".rtsc")

	def process(self, code):
		compile_stack = [ ([], ["expr_list"], "normal") ]
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
			# If we're in raw mode, push the line.
			if compile_stack[-1][2] == "raw":
				compile_stack[-1][1].append(line)
				continue
			# Right before we parse, check our parsing cache.
			if tuple(tokens) in self.parsing_cache:
				self.cache_hits += 1
				p = copy.deepcopy(self.parsing_cache[tuple(tokens)])
			else:
				self.cache_misses += 1
				parsings = [ p for p in self.parser.parse(tokens) ]
				if len(parsings) == 0:
					raise Exception("No valid parsings: %r" % line)
				if len(parsings) != 1:
					for p in parsings:
						print(p)
						print(parsing.pretty(p))
					raise Exception("Multiple parsings.")
				p = parsings[0]
				self.parsing_cache[tuple(tokens)] = copy.deepcopy(p)
			for statement in p[1:]:
				if statement[0] in ("expr", "standalone", "valued", "declaration", "subclass", "auto_call", "expose"):
					compile_stack[-1][1].append(statement)
				elif statement[0] in ("function_definition", "loop", "class", "auto_func", "javascript"):
					# Make a list to contain the code we're going to insert.
					statement.append(["expr_list"])
					compile_stack[-1][1].append(statement)
					new_entry = [compile_stack[-1][0], statement[-1], "raw" if statement[0] == "javascript" else "normal"]
					compile_stack.append(new_entry)
					starting_block = True
				elif statement[0] == "import":
					if len(compile_stack) != 1:
						raise CompilationException("Non-top level imports not allowed.")
					compile_stack[-1][1].append(statement)
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

	def build(self, modules):
		self.wheres = []
		for module_name, statement in modules:
			where = Class(None)
			self.build_structure(statement, where)
			self.wheres.append( (module_name, where) )

	def write_js(self):
		where_code = [self.js_header]
		for module_name, where in self.wheres:
			where_code.append("var RTSC_%s = new (function() {\n" % module_name)
			where_code.append(where.write_js())
			where_code.append("})();\n")
		where_code.append(self.js_footer)
		where_code.append("\n")
		return "".join(where_code)

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
		self.state = collections.OrderedDict()
		# XXX: Reconsider putting this here.
		self["self"] = BuiltIn("self", "this")

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
		return "RTSC_%s" % self.name

	def write_js(self):
		self.inherits = [i.resolve() for i in self.inherits]
		s = []
		if self.name:
			s.append("// %s\n" % self.name)
		objs = self.state.values()
		if self.name:
			s.append("function _RTSC_class_%s() {\n" % (self.name,))
		subclassings = []
		i = 0
		for stmt in self.code[:]:
			if stmt[0] == "valued" and stmt[1].string == "subclass":
				subclassings.append(stmt)
				self.code.pop(i)
				continue
			i += 1
		assert len(subclassings) < 2, "Unfortunately, currently only single inheritance is supported."
		if self.name:
			s.append("}\n")
			s.append("defaultFillPrototype(_RTSC_class_%s.prototype);\n" % self.name)
		# Write out the class instantiator.
		if self.name:
			var_dict = { "ident" : self.identifier(), "name" : self.name }
			s.append("_RTSC_class_%(name)s.prototype.instantiate_class = function() {\n" % var_dict)
			if subclassings:
				subclassing = subclassings[0]
				preamble, tag = self.write_for(subclassing[2])
				s.append("""	var parent_init = %s.secret_class.prototype.instantiate_class;
	if (parent_init !== undefined)
		parent_init.apply(this);
""" % (tag,))
			s.append("\tRTSC_object_lists[%(ident)s].push(this);\n" % var_dict)
		# Write out the main code.
		if self.name:
			js = self.write_for(self.code, getValue=False)[0]
			s.append(indent(js))
		# Write out the non-executables.
		for obj in objs:
			if obj.executable:
				continue
			js = obj.write_js()
			if self.name:
				js = indent(js)
			s.append(js)
		# End the class.
		if self.name:
			s.append("}\n")
		# Write out the functions.
		for obj in objs:
			if not obj.executable:
				continue
			s.append(obj.write_js())
			if self.name:
				s.append("_RTSC_class_%s.prototype.%s = %s;\n" % (self.name, obj.identifier(), obj.identifier()))
		if self.name:
			s.append("""function %(ident)s() {
	obj = new _RTSC_class_%(name)s();
	obj.instantiate_class();
	obj.RTSC___init__.apply(obj, arguments);
	return obj;
}
RTSC_object_lists[%(ident)s] = [];
%(ident)s.secret_class = _RTSC_class_%(name)s;\n""" % { "ident" : self.identifier(), "name" : self.name })
		for subclassing in subclassings:
			preamble, tag = self.write_for(subclassing[2])
#			s.append("// BEGIN PREAMBLE\n")
			s.append(preamble)
#			s.append("// END PREAMBLE: %s\n" % tag)
			s.append("_RTSC_class_%s.prototype.__proto__ = %s.secret_class.prototype;\n" % (self.name, tag))
		s.append("\n")
		# Write out the MAINEST code.
		if not self.name:
			js = self.write_for(self.code, getValue=False)[0]
			s.append(js)
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
			preamble = func[0] + "".join(i[0] for i in args)
			fmt = (func[1], ", ".join(i[1] for i in args))
			if getValue:
				tag = unique()
				return (preamble + "var %s = %s(%s);\n" % ((tag,)+fmt), tag)
			else:
				return (preamble + "%s(%s);\n" % fmt, "")
		elif code[0] == "float":
			return ("", "".join(i.string for i in code[1:]))
		elif code[0] == "literal":
			if code[1].type == "token":
				tok = code[1].string
				if tok in self:
					self[tok] = self[tok].resolve()
					return ("", self[tok].identifier())
				return ("", "RTSC_" + tok)
			elif code[1].type in ("string", "number"):
				return ("", code[1].string)
			assert False
		elif code[0] == "assignment":
			extra = preamble = ""
			var = "var "
			if isinstance(code[1], list):
				var = ""
				if code[1][0] == "getattr":
					preamble, lhs = self.write_for(code[1][1])
					extra = ".RTSC_" + code[1][2].string
				elif code[1][0] == "indexing":
					preamble, lhs = self.write_for(code[1][1])
					more_preamble, index = self.write_for(code[1][2])
					preamble += more_preamble
					extra = "[" + index + "]"
				else: assert False
				lhs = BuiltIn(lhs)
			else:
				lhs = code[1].string
				if lhs not in self:
					self[lhs] = Variable(lhs)
				lhs = self[lhs]
			rhs = self.write_for(code[-1])
			fmt = (var, lhs.identifier(), extra, (code[2].string if len(code) == 4 else ""), rhs[1])
			return (preamble + rhs[0] + "%s%s%s %s= %s;\n" % fmt, lhs.identifier())
		elif code[0] in ("op", "indexing"):
			lhs = self.write_for(code[1])
			rhs = self.write_for(code[-1])
			if code[0] == "op":
				op, post = "".join(i.string for i in code[2:-1]), ""
			else:
				op, post = "[]"
			tag = unique()
			if op == "^":
				return (lhs[0] + rhs[0] + "var %s = Math.pow(%s, %s);\n" % (tag, lhs[1], rhs[1]), tag)
			else:
				op = op.replace("and", "&&").replace("or", "||")
				return (lhs[0] + rhs[0] + "var %s = %s %s %s%s;\n" % (tag, lhs[1], op, rhs[1], post), tag)
		elif code[0] == "unop":
			rhs = self.write_for(code[-1])
			tag = unique()
			unop = code[1].string.replace("not", "!")
			return (rhs[0] + "var %s = %s%s;\n" % (tag, unop, rhs[1]), tag)
		elif code[0] == "list":
			args = map(self.write_for, code[1:])
			return ("".join(i[0] for i in args), "[" + ", ".join(i[1] for i in args) + "]")
		elif code[0] == "dict":
			args = map(self.write_for, code[1:])
			return ("".join(i[0] for i in args), "{" + ", ".join(a[1] + ":" + b[1] for a, b in zip(args[::2], args[1::2])) + "}")
		elif code[0] == "loop":
			if code[1].string == "for":
				# Check if iterating over an array.
				if len(code) == 5:
					itr = self.write_for(code[3])
					lhs = code[2].string
					self[lhs] = lhs = Variable(lhs)
					counter_tag = unique()
					loop_starter = "for (var %s = 0; %s < %s.length; %s++) {\n\tvar %s = %s[%s];\n" % \
						(counter_tag, counter_tag, itr[1], counter_tag, lhs.identifier(), itr[1], counter_tag)
					return (itr[0] + loop_starter + indent(self.write_for(code[4])[0]) + "}\n", "")
				# Check if iterating over a dictionary.
				elif len(code) == 6:
					itr = self.write_for(code[4])
					keyvar, valuevar = code[2].string, code[3].string
					self[keyvar] = keyvar = Variable(keyvar)
					self[valuevar] = valuevar = Variable(valuevar)
					loop_starter = "for (var %s in %s) {\n\tif (! %s.hasOwnProperty(%s)) continue;\n\tvar %s = %s[%s];\n" % \
						(keyvar.identifier(), itr[1], itr[1], keyvar.identifier(), valuevar.identifier(), itr[1], keyvar.identifier())
					return (itr[0] + loop_starter + indent(self.write_for(code[5])[0]) + "}\n", "")
				else: assert False
			elif code[1].string == "while":
				expr = self.write_for(code[2])
				return ("while (true) {\n%s\tif (!(%s)) break;\n%s}\n" % (indent(expr[0]), expr[1], indent(self.write_for(code[3])[0])), "")
			elif code[1].string == "if":
				expr = self.write_for(code[2])
				return (expr[0] + "if (%s) {\n%s}\n" % (expr[1], indent(self.write_for(code[3])[0])), "")
			elif code[1].string == "else":
				return ("else {\n%s}\n" % (indent(self.write_for(code[2])[0])), "")
		elif code[0] == "declaration":
			type_of = self.type_code(code[1])
			for dec_unit in code[2:]:
				new = self[dec_unit[1].string] = Variable(dec_unit[1].string)
				new.type_of = type_of
				preamble = new.write_js()
				if len(dec_unit) == 3:
					asgn, _ = self.write_for(["assignment", dec_unit[1], dec_unit[2]])
					preamble = preamble + asgn
				return (preamble, "")
		elif code[0] == "interval":
			if len(code) == 2:
				lhs = self.write_for(code[1])
				tag = unique()
				return (lhs[0] + "var %s = range(0, %s);\n" % (tag, lhs[1]), tag)
		elif code[0] == "list_comp":
			itr = self.write_for(code[3])
			lhs = code[2].string
			self[lhs] = lhs = Variable(lhs)
			tag = unique()
			expr = self.write_for(code[1])
			fmt = (tag, lhs.identifier(), itr[1], indent(expr[0]), tag, expr[1])
			return (itr[0] + "var %s = [];\nfor (%s in %s) {\n%s\t%s.push(%s);\n}\n" % fmt, tag)
		elif code[0] == "lambda":
			tag = unique()
			expr = self.write_for(code[-1])
			return ("var %s = function(%s) {\n%s\treturn %s;\n}\n" % (tag, ", ".join("RTSC_" + i[1].string for i in code[1:-1]), indent(expr[0]), expr[1]), tag)
		elif code[0] == "getattr":
			expr = self.write_for(code[1])
			return (expr[0], expr[1]+".RTSC_"+code[2].string)
		elif code[0] == "valued":
			if code[1].string == "return":
				lhs = self.write_for(code[2])
				return (lhs[0] + "return %s;\n" % (lhs[1],), "")
			elif code[1].string == "subclass":
				assert False, "Cannot subclass inside code structures."
		elif code[0] == "standalone":
			if code[1].string == "continue":
				return ("continue;\n", "")
			elif code[1].string == "break":
				return ("break;\n", "")
			else: assert False
		elif code[0] == "auto_call":
			return ("this.RTSC__autocall_%s(%s);\n" % (code[1].string, ", ".join("%r" % i.string for i in code[2:])), "")
		elif code[0] == "auto_func":
			tag = unique()
			expr = self.write_for(code[-1])
			function = "var %s = function(RTSC_event) {\n%s\treturn %s;\n}\n" % (tag, indent(expr[0]), expr[1])
			arguments = [tag] + ["%r" % i.string for i in code[2:-1]]
			return (function + "this.RTSC__autofunc_%s(this, %s);\n" % (code[1].string, ", ".join(arguments)), "")
		elif code[0] == "expose":
			return ("".join("this.RTSC_%s = RTSC_%s;\n" % ((i.string,)*2) for i in code[2:]), "")
		elif code[0] == "javascript":
			return ("".join(i+"\n" for i in code[1][1:]), "")
		else:
			print code
			assert False
		return (s, "")

class BuiltIn:
	executable = False

	def __init__(self, name, result=None):
		self.name, self.result = name, result or name

	def resolve(self):
		return self

	def identifier(self):
		return self.result

	def write_js(self):
		return ""

unique_counter = 0
def unique():
	global unique_counter
	unique_counter += 1
	return "tag%i" % unique_counter

class Function(Class):
	executable = True

	def identifier(self):
		return "RTSC_%s" % self.name

	def write_js(self):
		self.arguments = [ (resolve_type(arg[0]), arg[1]) for arg in self.arguments ]
		for arg in self.arguments:
			self[arg[1]] = Variable(arg[1])
		fmt = (self.identifier(), ", ".join(self[arg[1]].identifier() for arg in self.arguments))
		s = ["function %s(%s) {\n" % fmt]
		s.append(indent(self.write_for(self.code, getValue=False)[0]))
		s.append("}\n")
		return "".join(s)

def resolve_type(x):
	if x == None:
		return BuiltIn("var")
	return x.resolve()

class Variable(Class):
	executable = False
	type_of = None

	def identifier(self):
		return "RTSC_%s" % self.name

	def write_js(self):
		self.type_of = resolve_type(self.type_of)
		return "%s %s;\n" % (self.type_of.identifier(), self.identifier())

def determine_arch():
	import sys, platform
	if "linux" in sys.platform:
		base = "elf"
	elif "darwin" in sys.platform:
		base = "mac"
	elif "win" in sys.platform:
		base = "win"
	else:
		print red + "Unknown platform string:" + normal, repr(sys.platform)
		exit(1)
	bits = ["32", "64"]["64" in platform.uname()[-2]]
	return base + bits

class Timer:
	def __init__(self, msg): self.msg = msg
	def __enter__(self): self.start = time.time()
	def __exit__(self, t, val, tb):
		end = time.time()
		if args.v:
			print green+self.msg+normal, "%.3fs" % (end - self.start)

from dirtree import Chdir

if __name__ == "__main__":
	import argparse

	def address_validator(s):
		if s.count(":") > 1:
			raise argparse.ArgumentTypeError("addresses may have at most one port specifier")
		if ":" in s:
			address, port = s.split(":")
			try:
				port = int(port)
			except ValueError:
				raise argparse.ArgumentTypeError("invalid port")
			if not 0 >= port >= 65535:
				raise argparse.ArgumentTypeError("port out of range, must be in [0, 2^16)")
		else:
			address, port = s, 50002
		return address, port

	epilog = """
If --project is used, command line options supercede options selected in the project file.
The options --{host,chan,key} are equivalent to the project file options {host,chan,key} in the [config] section.
"""

	parser = argparse.ArgumentParser(prog="rtsc", description="RTSC command line compiler, v%s.%s" % version, epilog=epilog)
	parser.add_argument("-o", "--out", default=None, help="set the output file (default: Main+possible extension)")
	parser.add_argument("-v", action="store_const", const=True, default=False, help="be verbose")
	#, choices=("native", "32", "64", "elf32", "elf64", "win32", "win64", "mac32", "mac64")
	parser.add_argument("--arch", default="native", help="choose an output architecture (default: native)")
	parser.add_argument("--project", help="input .rtsc-proj project file, in leu of sources")
	parser.add_argument("--remote", action="store_const", const=True, default=False, help="use remote compilation, rather than quick-links")
	parser.add_argument("--host", type=address_validator, default=("ubuntu.cba.mit.edu", 50002), help="select the remote host to compile the binary with\n(default: ubuntu.cba.mit.edu:50002)")
	parser.add_argument("--chan", default="stockserv", help="the channel to use to connect to the remote compiler (default: stockserv)")
	parser.add_argument("--key", type=argparse.FileType("r"), help="path to the remote host's public key certificate")
	parser.add_argument("--ls", action="store_const", const=True, default=False, help="list all channels on the remote host -- then exit")
#	parser.add_argument("--updates", help="ask the remote compilation server about RTSC updates (doesn't actually update)")
	parser.add_argument("--ls-ql", action="store_const", const=True, default=False, help="list all local quick-link targets")
	parser.add_argument("file", nargs="*", help="input .rtsc/.bytes/suffixless files to compile")

	args = parser.parse_args()

	if args.ls:
		import compilation
		print "Connecting to:", "%s:%s" % (args.host[0], args.host[1])
		chans = compilation.remote_channels(args.host[0], args.host[1])
		print "Remote compilation channels:", len(chans)
		for chan, strings in chans:
			print "\t%s" % chan
			print "\t\t%s" % strings
		exit()

	if args.ls_ql:
		import compilation
		print "Quick-link targets:", ", ".join(compilation.capabilities())
		exit()

	if args.file and args.project:
		print "rtsc: cannot pass both --project and additional source files"
		exit()

	if args.v:
		os.environ["RTSC_VERBOSE"] = "1"

	# Determine the correct architecture if an arch "relative" to native is chosen.
	if args.v:
		print green+"Selected arch:"+normal, args.arch

	if args.arch in ("native", "32", "64"):
		real = determine_arch()
		if args.v:
			print green+"Detected arch:"+normal, real
		# If the mode is 32 or 64, then replace the suffix as appropriate.
		if args.arch != "native":
			real = real[:-2] + args.arch
		args.arch = real
		if args.v:
			print green+"Using arch:"+normal, args.arch

	default_binary = "Main"
	if "win" in args.arch:
		default_binary = "Main.exe"
	if args.arch == "rtscfs":
		default_binary = "Main.rtscfs"
	if args.out == None:
		args.out = default_binary

	with Timer("Time to load:"):
		ctx = Compiler()
		try:
			ctx.load_parsing_cache()
		except IOError:
			print red + "No parsing cache." + normal

	if args.v:
		print green + "Parse cache size:" + normal, len(ctx.parsing_cache)

	parser = None
	if args.project:
		project_root = os.path.dirname(os.path.realpath(args.project))
		try:
			fd = open(args.project)
			text = fd.read()
			fd.close()
		except IOError, e:
			print "rtsc:", e
			exit()
		import ConfigParser, StringIO
		parser = ConfigParser.SafeConfigParser()
		parser.readfp(StringIO.StringIO(text))
		if not parser.has_section("config"):
			print "rtsc: project file has no config section"
			exit()
		if not parser.has_option("config", "main_file"):
			print "rtsc: project file's config section has no main_file"
			exit()
		compilation_inputs = [ os.path.join(project_root, parser.get("config", "main_file")) ]
	else:
		project_root = "."
		compilation_inputs = args.file

	if not compilation_inputs:
		print "rtsc: no input files"
		exit()

	with Timer("Time to parse:"):
		with Chdir(project_root):
			for path in compilation_inputs:
				ctx.import_file(path)
			statements = ctx.churn()

	if args.v and ctx.cache_hits + ctx.cache_misses:
		print green + "Parse cache hits:" + normal, "%.2f%%" % (ctx.cache_hits * 100.0 / (ctx.cache_hits + ctx.cache_misses))

	ctx.save_parsing_cache()

	with Timer("Time to compile:"):
		ctx.build(statements)
		js = ctx.write_js()
		import compilation
		with Chdir(project_root if args.project else "."):
			code = compilation.make_rtscfs(js, target=args.arch, config=parser)
		if args.remote:
			if args.v:
				print green+"Remotely compiling:"+normal, "chan=%s host=%s:%s" % (args.chan, args.host[0], args.host[1])
			status, binary = compilation.remote_compile(code, args.chan, args.host[0], args.host[1], args.arch)
		else:
			if args.v:
				print green+"Using quick-links."+normal
			status, binary = compilation.quick_link(code, target=args.arch, config=parser)

	if status == "g":
		fd = open(args.out, "w")
		fd.write(binary)
		fd.close()
		# Don't mark raw rtscfs images as executable.
		if args.arch != "rtscfs":
			os.chmod(args.out, 0755)
	elif status == "e":
		print red + "Error:" + normal
		print binary.strip()
		exit(1)
	elif status == "f":
		print red + "Remote compilation server not running." + normal
	else:
		assert False

