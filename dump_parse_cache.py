#! /usr/bin/python

import rtsc
import pprint

normal = "\x1B\x5B\x30\x6D"
grey   = "\x1B\x5B\x30\x31\x3B\x33\x30\x6D"
red    = "\x1B\x5B\x30\x31\x3B\x33\x31\x6D"
green  = "\x1B\x5B\x30\x31\x3B\x33\x32\x6D"
yellow = "\x1B\x5B\x30\x31\x3B\x33\x33\x6D"
blue   = "\x1B\x5B\x30\x31\x3B\x33\x34\x6D"
purple = "\x1B\x5B\x30\x31\x3B\x33\x35\x6D"
teal   = "\x1B\x5B\x30\x31\x3B\x33\x36\x6D"

ctx = rtsc.Compiler()
ctx.load_parsing_cache()
for i, (a, b) in enumerate(ctx.parsing_cache.iteritems()):
	print red + "[%i/%i] " % (i+1, len(ctx.parsing_cache)) + normal + green + " ".join(i.string for i in a) + normal
	pprint.pprint(b)

