#! /usr/bin/python
"""
Manages a project directory, and exposes useful functionality.
"""

import dirtree
import os, sys, subprocess

class EditorHandler: pass

class PyAppHandler(EditorHandler):
	def open_file(self, path):
		subprocess.call([sys.executable, self.py_path, path])

class GenericOSEditor(EditorHandler):
	def open_file(self, path):
		pass

class SDI_Handler(PyAppHandler): py_path = os.path.join("sdi", "sdi_main.py")
class Blocks_Handler(PyAppHandler): py_path = "blocks.py"
class Image_Handler(PyAppHandler): py_path = "find_an_editor.py"
class Text_Handler(PyAppHandler): py_path = "find_an_editor.py"

file_handlers = {
	".sdi": SDI_Handler,
	".blocks": Blocks_Handler,
	".rtsc": Text_Handler,
	".txt": Text_Handler,
	".js": Text_Handler,
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

	def get_handler_for_node(self, node):
		if node.is_file():
			return file_handlers.get(os.path.splitext(node.name)[1], None)

	def get_nodes_by_handler(self, handler):
		return [node for node in self.tree.walk() if self.get_handler_for_node(node) == handler]

if __name__ == "__main__":
	p = Project("projects/mainproject")

