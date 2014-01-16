#! /usr/bin/python
"""
Anyone who needs the global configuration file can import this.
"""

import os, json
import compilation

def fixup_path(path):
	"""fixup_path = lambda path: os.path.join(*path.split("/"))

	Converts Linux path separator convention to whatever is local.
	"""
	return os.path.join(*path.split("/"))

print "Loading configuration file."
# Load up the static configuration file.
txt = []
for line in open(os.path.join("data", "extensions.json")):
	line = line.split("#")[0].strip()
	if not line: continue
	txt.append(line)
global_config = json.loads("\n".join(txt))

# Load up the user-editable settings.
try:
	path = os.path.join("data", "global_settings.json")
	fd = open(path)
except:
	print path, "missing -- using defaults."
	global_config["settings"] = global_config["default_settings"].copy()
else:
	global_config["settings"] = json.load(fd)
	fd.close()

# Read in the sizes of various compilation targets.
global_config["target_size"] = {}
for target in compilation.capabilities():
	global_config["target_size"][target] = compilation.get_size(target)

