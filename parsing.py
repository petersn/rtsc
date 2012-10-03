#! /usr/bin/python

from chomsky import *
from lexer import *
import re

class Token:
	def __init__(self, x, lists=None):
		self.type, self.string = x
		self.lists = lists
		self.__hash__ = self.string.__hash__

	def __eq__(self, s):
		if isinstance(s, Token):
			return self.string == s.string
		if self.lists and s.startswith("list:"):
			return self.string in self.lists[s[5:]] 
		if s.startswith("type:"):
			return self.type == s[5:]
		if s.startswith("spec:"):
			return [self.type, self.string] == s.split(":", 2)[1:]
		if s.startswith("match") and len(s) >= 6:
			splitter = s[5]
			args = s.split(splitter)[1:]
			return self.type == args[0] and self.string in args[1:]
		if s.startswith("regex"):
			splitter = s[5]
			typ, regex = s.split(splitter, 2)[1:]
			return self.type == typ and re.match(regex, self.string)
		if s.startswith("numbs:") and len(s) >= 6:
			args = s.split(":")[1:]
			args[1:] = [ "".join(map(chr, map(int, arg.split(",")))) for arg in args[1:] ]
			return self.type == args[0] and self.string in args[1:]
		return self.string == s

	def __copy__(self):
		return Token((self.type, self.string))

	def __deepcopy__(self, memo):
		return Token((self.type, self.string))

	def __repr__(self):
		return "<%s:%s>" % (self.type, self.string)

class Parser:
	def __init__(self, grammar_text, lexer_text, lists_text=None):
		self.grammar = build_up(empty_grammar(), grammar_text)
		self.lexer = Lexer(lexer_text)
		self.lists = None

		if lists_text:
			self.lists, name = { None : set() }, None
			for line in lists_text.split("\n"):
				line = line.split("#")[0].strip()
				if not line: continue
				if line.startswith("==="):
					name = line[3:].strip()
					if name not in self.lists:
						self.lists[name] = set()
				else:
					self.lists[name].add( line )

	def lex(self, line):
		return [ Token(token, self.lists) for token in self.lexer(line) ]

	def parse(self, tokens):
		for parsing in parse(tokens, self.grammar):
			yield parsing

