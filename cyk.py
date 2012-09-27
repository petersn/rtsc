#! /usr/bin/python
# coding: utf-8
"""
Implements Cocke-Younger-嵩.
"""

def cyk(string, grammar, initial):
	"""cyk(string, grammar, initial) -> generator for all possible derivations of string given the grammar

	`string' is the string to derive in the context free grammar given by `productions' and `initial'.
	This argument may be any iteratable that yields terminals, noting the restrictions on what types terminals may be below.

	`grammar' is a list of productions of the form either (nonterminal,), (nonterminal, (nonterminal,)), (nonterminal, (nonterminal, nonterminal)), or (nonterminal, terminal).
	You may use any objects you wish to represent your terminals and nonterminals, so long as they are hashable, comparable, and not tuples.
	The first three cases correspond to rules of production where one nonterminal becomes zero to two other nonterminals.
	The last case corresponds to the leaf nodes of the rules of production.

	`initial' is the starting symbol whence all derivations are derived.

	A generator is returned which yields each possible derivation. (This may be zero derivations!)
	If infinfitely many derivations are possible, valid derivations will be returned forever.
	No guarantee is given that enumerating through all derivations will reach every possible derivation if infinitely many are possible! 
	"""
	n = len(string)
	epsilons = { }
	#conversions = { } # conversions[x] -> All nonterminals that may become the nonterminal x.
	conversions = [ ]
	productions = [ ]
	nonterminals = set()
	leaves = [ ]
	P = { } # P[production][span][position] -> None or [all possible derivations]

	epsilon = conversion = plain = leafs = 0

	for i, p in enumerate(grammar):
		# Check for epsilon productions
		if len(p) == 1:
			epsilon += 1
#			print "Epsilon."
			epsilons[ p[0] ] = i
			nonterminals.add( p[0] )

		# Check for conversion productions
		elif len(p) == 2 and type(p[1]) == tuple and len(p[1]) == 1:
			conversion += 1
#			print "Conversion."
#			if p[0] not in conversions:
#				 conversions[p[0]] = []
#			if p[1][0] not in conversions[p[0]]:
#				conversions[p[0]].append( p[1][0] )
			conversions.append( (i, (p[0], p[1][0])) )
			nonterminals.add( p[0] )

		# Check for plain old Chomsky Normal Form productions:
		elif len(p) == 2 and type(p[1]) == tuple and len(p[1]) == 2:
			plain += 1
#			print "Production."
			productions.append( (i, p) )
			nonterminals.add( p[0] )

		# Check for leaf productions
		elif len(p) == 2 and type(p[1]) != tuple:
			leafs += 1
#			print "Leaf."
			leaves.append( (i, p) )
			nonterminals.add( p[0] )

		else:
			raise ValueError("unknown production type: %r" % p)

	# Next, we build the data structure for our dynamic programming operations.
	for a in nonterminals:
		P[a] = [ [ None for i in xrange(n-j+1) ] for j in xrange(0, n+1) ]
		# Check if the nonterminal has an epsilon production. If so, fill in the first row appropriately.
		if a in epsilons:
			v = [ ((epsilons[a],),) ]
			P[a][0] = [ v for i in xrange(n+1) ]

	# We can discard leaf productions immediately by simply applying them everywhere where possible.
	for i, (a, b) in leaves:
		for j in xrange(n):
			if b == string[j]:
				P[a][1][j] = [ ([i, string[j]],) ]

#	print "Input length:       ", n
#	print "Epsilon productions:", epsilon
#	print "Conversions:        ", conversion
#	print "Plain productions:  ", plain
#	print "Leaf productions:   ", leafs
#	print "Time takers:        ", conversion+leafs
#	print "Space takers:       ", len(P)
#	print "Operations:         ", (n+1) * (n) * (conversion+leafs)

	# Search span lengths.
	for span in xrange(1, n+1):
		# Search start positions.
		for start in xrange(n - span + 1):
			deriv = True
			used = set()
			# Keep rederiving at this level while we still have productions to apply.
			while deriv:
				deriv = False
				# First apply conversions
				for i, (a, b) in conversions:
					if i in used: continue
					#print "Checking conversion", i, "from", start, "to", start+span
					if P[b][span][start]:
						new_derivation = (i, P[b][span][start])
						if not P[a][span][start]:
							P[a][span][start] = [new_derivation]
						else:
							P[a][span][start].append(new_derivation)
						deriv = True
						used.add( i )

				# Then check Chomsky productions:
				# Search partition points.
				# To allow for epsilon productions, we search span+1.
				for partition in xrange(span+1):
					# Check every rule.
					for i, (a, (b, c)) in productions:
						if (i, partition) in used: continue
						#print "Checking", i, "from", start, "to", start+partition, "to", start+span, "(", a, b, c, ")"
						# Make sure the LHS rule is derivable.
						if not P[b][partition][start]: #or (b in epsilons and partition == 0)):
							continue
						# Make sure the RHS rule is derivable.
						if not P[c][span-partition][start+partition]: #or (c in epsilons and partition == span)):
							continue
						# Add the derivation
						new_derivation = (i, P[b][partition][start], P[c][span-partition][start+partition])
						if not P[a][span][start]:
							P[a][span][start] = [new_derivation]
						else:
							P[a][span][start].append(new_derivation)
						deriv = True
						used.add( (i, partition) )

	t = P[initial][n][0]

	if t == None:
		return

	def expand(t):
		if len(t) == 1:
			yield t[0]
		elif len(t) == 2:
			for i in t[1]:
				for k in expand(i):
					yield (t[0], k)
		else:
			for i in t[1]:
				for j in t[2]:
					for k in expand(i):
						for l in expand(j):
							yield (t[0], k, l)

	for derivation in t:
		for tree in expand(derivation):
			yield tree

if __name__ == "__main__":
	def pretty(x, depth=0):
		if type(x) == list:
			print " "*depth + grammar[x[0]][0], "=>", x[1]
		else:
			print " "*depth + grammar[x[0]][0] + " {"
			for i in x[1:]:
				pretty(i, depth+4)
			print " "*depth + "}"

	grammar = [
		("Char", "a"), # The non-terminal Char may become the terminal "a".
		("Tree", ("Char", "Tree")), # The non-terminal Tree can produce the non-terminal Tree, and itself again.
		("Tree",), # Epsilon production for the non-terminal Tree.
		("Tree", ("Tree", "TwoForOne")), # Left recursions okay!
		("TwoForOne", ("Char", "Char")),
		("Char", ("TwoForOne",)), # Conversion productions okay! This is equivalent to the productions: ("Tree", ("Char", "PlaceHolder")), and ("Placeholder",)
	]

	for j in cyk("a"*3, grammar, "Tree"):
		print "==>", j
		pretty(j)

