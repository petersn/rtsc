#! /usr/bin/python
r"""
regexlex: An efficient one-pass lexer.

Lexer files are of the form:

	##comment
	foo  = regex1
	bar: = regex2

Each line is a rule, associating a name with a regex.
The lexer will attempt to match each regex in order against the input, and take the first one that successfully matches.
When a match is found, all matched input is consumed, and a 2-tuple is added to the output list: (name, matched)
The `name' used is the lhs of the rule that matched. If the rule name ends with a colon, output it matches will be ignored.
On error, a 2-tuple is returned, with the output matched so far first, followed by all unmatched input.
An example lexer for lexing expressions:

	## Expression lexer
	open_paren    = [(]
	close_paren   = [)]
	operator      = [+]|[-]|[*]|[/]
	float         = [1-9]?[0-9]*[.][0-9]*
	integer       = [0-9]+
	whitespace:   = [ ]+|\t+|\n+

An example of using this lexer:

	Python 2.6.4 (r264:75706, Dec  7 2009, 18:43:55) 
	[GCC 4.4.1] on linux2
	Type "help", "copyright", "credits" or "license" for more information.
	>>> from lexer import Lexer
	>>> l = Lexer("lexer.rxl")
	>>> l("3 / (17.-.0001)")
	[('integer', '3'), ('operator', '/'), ('open_paren', '('), ('float', '17.'), ('operator', '-'), ('float', '.0001'), ('close_paren', ')')]
	>>> l(" 3 + badinput ")
	([('integer', '3'), ('operator', '+')], 'badinput ')

"""

version = "0001"

import re

class Lexer:
	def __init__(self, text):
		self.names = [ ]

		for line in text.split("\n"):
			line = line.split("##")[0].strip()
			if not line:
				continue

			name, regex = line.split("=", 1)
			name, regex = name.strip(), regex.strip()
			self.names.append( (name, re.compile(regex)) )

	def lex(self, s):
		tokens = []
		while s:
			longest_match = None
			for name, regex in self.names:
				grab = regex.match(s)
				if grab and (longest_match == None): #or grab.end() > longest_match[1].end()):
					longest_match = (name, grab)
			if not longest_match:
				return tokens, s
			else:
				if longest_match[0][-1] != ":":
					tokens.append( (longest_match[0], s[:longest_match[1].end()]) )
				s = s[longest_match[1].end():]

		return tokens

	__call__ = lex

if __name__ == "__main__":
	try:
		lex = Lexer("lexer.rxl")
	except IOError, e:
		print e
		print "No lexer found. Make a lexer file, and try again."
		raise SystemExit

	while True:
		string = raw_input("> ")
		if not string:
			continue

		tokens = lex(string)

		print tokens

