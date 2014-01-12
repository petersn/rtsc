#! /usr/bin/python
"""
Manages a project directory, and exposes useful functionality.
"""

import dirtree
import os, sys, subprocess

from rtsc_config import global_config

class EditorHandler: pass

class PyAppHandler(EditorHandler):
	def open_file(self, path=None, chdir=None):
		subprocess.Popen([sys.executable, os.path.abspath(self.py_path)] + ([path] if path is not None else []), cwd=chdir)

class FromSettingsEditor(EditorHandler):
	def open_file(self, path=None, chdir=None):
		subprocess.Popen([global_config["settings"][self.var]] + ([path] if path is not None else []), cwd=chdir)

class SDI_Handler(PyAppHandler): py_path = os.path.join("sdi", "main.py")
class Image_Handler(FromSettingsEditor): var = "image_editor"
class Text_Handler(FromSettingsEditor): var = "text_editor"

file_handlers = {
	".sdi": SDI_Handler,
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

	def get_nodes(self):
		return list(self.tree.walk())

if __name__ == "__main__":
	p = Project("projects/mainproject")

