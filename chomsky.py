#! /usr/bin/python
# coding: utf-8
"""
Makes CNF grammars from input text.
"""

import cyk
from string import strip

tmp_counter = 1000
def tmp():
	global tmp_counter
	tmp_counter += 1
	return tmp_counter

def rnf2cnf(s):
	initial = ("main",)
	grammar, cache, scache = [], {}, {}
	unmarked = set()
	invisible = set()

	renaming = {}

	for l in s.split("\n"):
		l = l.strip()
		if not l: continue
		lhs, rhs = map(strip, l.split("=", 1))

		if lhs.endswith(":"):
			lhs = lhs[:-1]
			unmarked.add( lhs )

		renaming[lhs] = lhs

		if ":" in lhs:
			lhs, new_name = lhs.split(":", 1)
			renaming[lhs] = new_name

		def make_rule(t):
			raw_label = t
			invis, unmark = False, False
			if t.endswith("~"):
				invis = True
				t = t[:-1]
			if t.endswith(":"):
				unmark = True
				t = t[:-1]
			if t.startswith('"') and t.endswith('"'):
				s = t[1:-1]
				if s not in scache:
					v = tmp()
					grammar.append( (v, s) )
					scache[raw_label] = v
				if invis:
					invisible.add( scache[raw_label] )
				return scache[raw_label]
			if t not in cache:
				cache[t] = tmp()
			if invis:
				invisible.add( cache[t] )
			if unmark:
				unmarked.add( cache[t] )
			return cache[t]

		tokens = [ make_rule(i.strip()) for i in rhs.split(" ") if i.strip() ]

		while len(tokens) > 1:
			if (tokens[0], tokens[1]) in cache:
				tokens[:2] = [ cache[(tokens[0], tokens[1])] ]
			else:
				v = tmp()
				cache[ (tokens[0], tokens[1]) ] = v
				grammar.append( (v, (tokens[0], tokens[1])) )
				tokens[:2] = [ v ]

		if lhs not in cache:
			cache[lhs] = tmp()

		if len(tokens) == 1:
			grammar.append( (cache[lhs], (tokens[0],)) )
		else:
			grammar.append( (cache[lhs],) )

	names = dict( (k, v) for k, v in cache.items() if type(k) == str )

	return grammar, names, unmarked, invisible, renaming

def bnf2rnf(s):
	# First do a replacement such that @@ becomes the current symbol.
	o = ""
	for l in s.split("\n"):
		l = l.split("#")[0].strip()
		if not l: continue
		lhs, rhs = map(strip, l.split("=", 1))
		raw_lhs = lhs[:-1] if lhs.endswith(":") else lhs
		rhs = rhs.replace("@@", raw_lhs)
		for p in rhs.split("|"):
			o += "%s = %s\n" % (lhs, p.strip())

	return o

def prune(grammar):
	ll = 0
	while len(grammar) != ll:
		ll = len(grammar)
		lhses = set( i[0] for i in grammar )
		grammar = [ i for i in grammar if len(i) == 1 or (len(i) == 2 and type(i[1]) == str) or all(j in lhses for j in i[1]) ]
	return grammar

def empty_grammar():
	return [], {}, set(), set(), {}

def build_up(grammar, text):
	cnf, names, unmarked, invisible, renaming = rnf2cnf( bnf2rnf(text) )
	cnf.extend(grammar[0])
	names.update(grammar[1])
	unmarked.update(grammar[2])
	invisible.update(grammar[3])
	renaming.update(grammar[4])
	cnf = prune(cnf)

	return cnf, names, unmarked, invisible, renaming

def parse(s, grammar):
	cnf, names, unmarked, invisible, renaming = grammar
	rnames = dict( (v, k) for k, v in names.items() )

	def translate(t, o, stack):
		dont_mark = False
		# Invert from grammar rule index to rule number, to determine if the current tree should be skipped.
		for i, rule in enumerate(cnf):
			if rule[0] in invisible and i == t[0]:
				return
			if rule[0] in unmarked and i == t[0]:
				dont_mark = True

#		if type(t) == int:
#			n = cnf[t]
#			if len(n) == 2 and type(n[1]) == str:
#				stack[-1].append( n[1] )
		if type(t) == list:
			#print t[0] in rnames, rnames[t[0]] if t[0] in rnames else "..."
			if not dont_mark and t[0] in rnames and not rnames[t[0]] in unmarked:
				stack[-1].append( [ renaming[rnames[t[0]]] ] )
				stack.append( stack[-1][-1] )
			#if t[0] in invisible:
			#	print "!!!"
			stack[-1].append( t[1] )
			if not dont_mark and t[0] in rnames and not rnames[t[0]] in unmarked:
				stack.pop()
		elif len(t) in (2, 3):
			n = cnf[t[0]]
			if not dont_mark and n[0] in rnames and not rnames[n[0]] in unmarked:
				name = rnames[n[0]]
				if ":" in name:
					name = name.split(":",1)[1]
				stack[-1].append( [ renaming[name] ] )
				stack.append( stack[-1][-1] )
			for i in t[1:]:
				translate(i, o, stack)
			if not dont_mark and n[0] in rnames and not rnames[n[0]] in unmarked:
				stack.pop()

	for deriv in cyk.cyk(s, cnf, names["main"]):
		#print deriv
		o = []
		stack = [o]
		translate( deriv, o, stack )

		assert len(o) == 1, "Actual: %r" % o
		assert stack == [o]

		yield o[0]

def pretty(x, depth=0):
	r = ""
#	while type(x) == list and len(x) == 1 and type(x[0]) == list:
#		x = x[0]
	if type(x) == list:
#		if not x:
#			return " "*depth + "{ }\n"
		n = x[0]
		if len(x) == 2 and type(x[1]) != list:
			r += " "*depth + n + ": " + str(x[1]) + "\n"
		else:
			r += " "*depth + "%s {" % n + "\n"
			for o in x[1:]:
				r += pretty(o, depth+2)
			r += " "*depth + "}" + "\n"
	else:
		r += " "*depth + str(x) + "\n"
	return r

if __name__ == "__main__":
	grammar = build_up(empty_grammar(), """
nexpr = "(" ")" | "(" expr ")"
expr = nexpr | nexpr expr
main = expr
""")
	for d in parse("(((()())()))", grammar):
		print d
		print pretty(d)

