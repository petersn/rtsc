#! /usr/bin/python

blocks_signatures = {
	# Basic
	"if": ["<code>"],
	"while": ["<code>"],
	"for in": ["<code>"],
	"repeat": ["<code>"],
	"spawn": ["<code>"],
	"(organize)": ["<code>"],
	# Data
	# Events
	"on event": ["<code>"],
	# Code
	# User
}

class BlocksNode:
	def __init__(self, tree, name):
		self.tree, self.name = tree, name
		self.children = []
		self.replaceable = False

	def populate_from(self, data_list):
		for element in data_list:
			new = BlocksNode(self.tree, element["name"])
			self.add(new)
			new.populate_from(element["children"])
		for child in self.children:
			child.check_block_signature()

	def add(self, node):
		self.add_before(len(self.children)+1, node)

	def add_before(self, index, node):
		self.children.insert(index, node)
		node.build_in_before(index, self)

	def build_in(self, parent):
		self.build_in_before(len(self.children)+1, parent)

	def build_in_before(self, index, parent):
		self.parent = parent
		if index > self.tree.GetChildrenCount(parent.node, recursively=False):
			self.node = self.tree.AppendItem(parent.node, self.name)
		else:
			self.node = self.tree.InsertItemBefore(parent.node, index, self.name)
		self.tree.Expand(parent.node)
		self.tree.SetItemPyData(self.node, self)
		for child in self.children:
			child.build_in(self)

	def has_in_subtree(self, node):
		if self is node: return True
		return any(child.has_in_subtree(node) for child in self.children)

	def unbuild(self):
		for child in self.children:
			child.unbuild()
		self.tree.Delete(self.node)

	def orphan(self):
		self.parent.children.remove(self)
		# Check if this makes the parent no longer meet their block signature.
		self.parent.check_block_signature()

	def check_block_signature(self):
		if len(self.children) < len(blocks_signatures.get(self.name, [])):
			self.add(BlocksNode(self.tree, blocks_signatures[self.name][0]))

	def replace_with(self, node):
		self.parent.add_before(self.parent.children.index(self), node)
		self.unbuild()
		self.orphan()

	def get_replace_me(self):
		return self.name[:1] == "<" and self.name[-1:] == ">"

	def is_editable(self):
		return not self.get_replace_me()

	def serialize(self):
		return {
			"name": self.name,
			"children": [child.serialize() for child in self.children],
		}

	def __repr__(self):
		return "["+self.name+"]"

class BlocksEditor:
	def __init__(self, tree):
		self.tree = tree
		self.tree_root = BlocksNode(tree, None)
		self.tree_root.node = self.tree.AddRoot("Bug Bug Bug!")

	def add_new(self, name):
		new = BlocksNode(self.tree, name)
		self.tree_root.add(new)
		# Special magic.
		if name in blocks_signatures:
			for subname in blocks_signatures[name]:
				new.add(BlocksNode(self.tree, subname))
		self.tree.Expand(new.node)
		return new

	def drag(self, a, b):
		a, b = map(self.tree.GetItemPyData, (a, b))
		if None in (a, b):
			print "Invalid drag!", a, b
			return
		if a.has_in_subtree(b):
			print "Inconsistent drag!", a, b
			return
		if a.get_replace_me():
			print "Cannot drag place-holders!"
			return
		print "Performing drag:", a, b
		a.unbuild()
		a.orphan()
		# Check the target -- it may want to be replaced.
		if b.get_replace_me():
			print "Replacement drag."
			b.replace_with(a)
		else:
			print "Move before drag."
			b.parent.add_before(b.parent.children.index(b), a)

	def serialize(self):
		return self.tree_root.serialize()["children"]

	def populate_from(self, data_list):
		self.tree_root.populate_from(data_list)

