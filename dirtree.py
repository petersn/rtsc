#! /usr/bin/python

import os

class Chdir:
	def __init__(self, path): self.path = path
	def __enter__(self):
		self.old_path = os.getcwd()
		os.chdir(self.path)
	def __exit__(self, t, val, tb):
		os.chdir(self.old_path)

class treeNode:
	def __init__(self):
		self.parent = None

	def is_file(self):
		return False

class treeFile(treeNode):
	def __init__(self, full_path):
		treeNode.__init__(self)
		self.name = os.path.split(full_path)[1]
		self.full_path = full_path

	def is_file(self):
		return True

	def __repr__(self):
		return "<%s>" % self.name

	def walk(self):
		yield self

	def open(self, *args):
		return open(self.full_path, *args)

	# Slurping convenience functions.
	def read(self):
		fd = self.open()
		data = fd.read()
		fd.close()
		return data

	def write(self, s):
		fd = self.open("w")
		fd.write(s)
		fd.close()

	def pprint(self, depth=0):
		print " "*depth + self.name

class treeLink(treeFile):
	def __repr__(self):
		return "symlink:<%s>" % self.name

class treeDirectory(treeNode):
	def __init__(self, full_path):
		treeNode.__init__(self)
		self.name = os.path.split(full_path)[1]
		self.full_path = full_path
		self.children = []

	def __getitem__(self, path):
		if "/" in path:
			for comp in path.split("/"):
				self = self[comp]
			return self
		for child in self.children:
			if child.name == path:
				return child

	def __repr__(self):
		return "<%s/>" % self.name

	def walk(self):
		yield self
		for child in self.children:
			for node in child.walk():
				yield node

	def pprint(self, depth=0):
		print " "*depth + self.name+"/"
		for child in self.children:
			child.pprint(depth+2)

def build_tree(path):
	name = os.path.split(path)[1]
	if os.path.islink(path):
		return treeLink(path)
	elif os.path.isdir(path):
		x = treeDirectory(path)
		for child_path in os.listdir(path):
			child = build_tree(os.path.join(path, child_path))
			child.parent = x
			x.children.append(child)
		return x
	elif os.path.isfile(path):
		return treeFile(path)

