#! /usr/bin/python
"""
Manages a project directory, and exposes useful functionality.
"""

import dirtree
import os

class EditorHandler: pass
class SDI_Handler(EditorHandler): pass
class RTSC_Code_Handler(EditorHandler): pass
class Blocks_Handler(EditorHandler): pass
class Image_Handler(EditorHandler): pass
class Text_Handler(EditorHandler): pass

file_handlers = {
	".sdi": SDI_Handler,
	".rtsc": RTSC_Code_Handler,
	".blocks": Blocks_Handler,
	".txt": Text_Handler,
	".json": Text_Handler,
}

for ext in [".png", ".jpg", ".jpeg", ".bmp"]:
	file_handlers[ext] = Image_Handler

class Project:
	def __init__(self, path):
		self.path = path
		self.reload_cache()

	def reload_cache(self):
		with dirtree.Chdir(self.path):
			self.tree = dirtree.build_tree(os.path.realpath("."))

	def get_nodes_by_handler(self, handler):
		nodes = []
		for node in self.tree.walk():
			if node.is_file() and file_handlers.get(os.path.splitext(node.name)[1], None) == handler:
				nodes.append(node)
		return nodes

if __name__ == "__main__":
	p = Project("projects/mainproject")

