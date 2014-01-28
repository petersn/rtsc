#! /usr/bin/python

import string
import wx
import wx.stc
import blocks_editor
import os, sys

data_directory = os.path.join(os.path.dirname(sys.argv[0]), "data")

singularize = {
	"types": "type",
	"data": "datum",
	"code": "code",
	"blocks": "blocks",
}

def get_unique_name(s, dm):
	c = 1
	while True:
		name = "%s%i" % (s, c)
		if dm.name_available(name): return name
		c += 1

class TopLevelEntry:
	def __init__(self, parent, which):
		self.parent, self.which = parent, which
		self.name = get_unique_name(singularize[which], parent)
		self.edit_frame = None

		# Data for various things this could be.
		self.parents = []
		self.code_text = None
		self.blocks_data = []

	def serialize(self):
		everything = {
			"which": self.which,
			"name": self.name,
			"parents": [i.name for i in self.parents],
			"code": self.code_text,
			"blocks": self.blocks_data,
		}
		pruned = {}
		# Only store the fields we need to.
		for field in {
			"types": ("name", "which", "parents"),
			"data": ("name", "which", "parents"),
			"code": ("name", "which", "code"),
			"blocks": ("name", "which", "blocks"),
		}[self.which]: pruned[field] = everything[field]
		return pruned

	@staticmethod
	def load_from(obj, parent):
		entry = parent.new_of(obj["which"])
		entry.rename_entry(obj["name"])
		if entry.which in ("types", "data"):
			entry.parents = obj["parents"]
		if entry.which == "code":
			entry.code_text = obj["code"]
		if entry.which == "blocks":
			entry.blocks_data = obj["blocks"]
		return entry

	def link_up_references(self):
		# Look up named parents.
		# Note that self.parent is a DataModel, and self.parents is a list of TopLevelEntrys.
		self.parents = map(self.parent.get_by_name, self.parents)

	def insert(self):
		self.tree_item = self.parent.frame.data_tree.AppendItem(self.parent.frame.data_tree_top_levels[self.which], self.name)
		self.parent.frame.data_tree.SetItemImage(self.tree_item, ["types", "data", "code", "blocks"].index(self.which), 0)
		self.parent.frame.data_tree.SetItemPyData(self.tree_item, self)

	def delete(self):
		self.parent.frame.data_tree.Delete(self.tree_item)
		self.edit_frame = None

	def activate(self):
		# Take advantage of the fact that deleted references coerce to false.
		if not self.edit_frame:
			self.edit_frame = TopLevelEntryFrame(self.parent.frame.main_notebook, self)
			self.parent.frame.notebook_remove_page("Edit")
			self.parent.frame.main_notebook.AddPage(self.edit_frame, "Edit")

#			self.parent.frame.main_panel.Destroy()
#			self.parent.frame.splitter.SplitVertically(self.parent.frame.data_tree, self.edit_frame, 250)
#			self.dm.frame.main_panel = self.edit_frame
#			self.parent.frame.outer_sizer.Add(self.edit_frame, 1, wx.EXPAND)
#			self.edit_frame.Show(True)
#		else:
#			self.edit_frame.Raise()

	def rename_entry(self, new_name):
		if self.parent.name_available(new_name):
			self.name = new_name
			self.parent.frame.data_tree.SetItemText(self.tree_item, self.name)

	def is_locked(self):
		return bool(self.edit_frame)

class TopLevelSelector(wx.Dialog):
	"""
	Opens up a dialog that selects a top level.
	"""
	def __init__(self, parent, id, title, column_name, which, dm):
		wx.Dialog.__init__(self, parent, id, title, size=(300,500))
		self.dm, self.which = dm, which

		sizer = wx.BoxSizer(wx.VERTICAL)
		self.list_ctrl = wx.ListCtrl(self, -1, style=wx.LC_REPORT)
		self.list_ctrl.InsertColumn(0, column_name)
		self.list_ctrl.SetColumnWidth(0, 300)
		for e in dm.top_levels[which]:
			num_items = self.list_ctrl.GetItemCount()
			self.list_ctrl.InsertStringItem(num_items, e.name)
		sizer.Add(self.list_ctrl, 1, wx.EXPAND)
		self.list_ctrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnSelect)
		self.SetSizer(sizer)
		self.choice = None

	def OnSelect(self, e):
		index = self.list_ctrl.GetFocusedItem()
		self.choice = self.dm.top_levels[self.which][index]
		self.EndModal(wx.ID_OK)

being_edited = {}

def open_editor_for_node(frame_parent, node):
	# If the frame has been closed, remove it from our dictionary.
	if node in being_edited:
		if not being_edited[node]:
			being_edited.pop(node)
	# Otherwise, pop open an editor.
	if node not in being_edited and node.is_editable():
		being_edited[node] = frame = BlocksNodeEditor(frame_parent, node)
		frame.Show(True)

class BlocksNodeEditor(wx.Frame):
	def __init__(self, frame_parent, node):
		wx.Frame.__init__(self, frame_parent, -1, "Edit blocks node", wx.DefaultPosition, wx.Size(300, 400))

class TopLevelEntryFrame(wx.Panel):
	blocks_setup = [
		{ "header": "Flow",
			"buttons": ["if", "while", "for in", "repeat", "spawn", "(organize)"] },
		{ "header": "Data",
			"buttons": ["set value", "create object", "delete object"] },
		{ "header": "Events",
			"buttons": ["on event", "send event", "wait until"] },
		{ "header": "Other",
			"buttons": ["run code", "user block"] },
	]

	def __init__(self, parent, entry):
		wx.Panel.__init__(self, parent, -1)#, "Edit", wx.DefaultPosition, wx.Size(400, 500))
		self.entry = entry

		self.notebook = wx.Notebook(self, -1)
		props_panel = wx.Panel(self.notebook, -1)
		self.notebook.AddPage(props_panel, "Properties")

		# Build the properties tab.
		column = wx.BoxSizer(wx.VERTICAL)
		name_row = wx.BoxSizer(wx.HORIZONTAL)
		name_row.Add(wx.StaticText(props_panel, -1, "Name:"), 0, wx.EXPAND)
		self.name_box = wx.TextCtrl(props_panel, -1)
		self.name_box.SetValue(self.entry.name)
		self.name_box.Bind(wx.EVT_KILL_FOCUS, self.OnNameChange)
		self.name_box.Bind(wx.EVT_CHAR, self.OnKeyPress)
		name_row.Add(self.name_box, 1, wx.EXPAND)
		column.Add(name_row, 0, wx.EXPAND)
		props_panel.SetSizer(column)

		# Add the inheritance list, if we're types or data.
		if self.entry.which in ("types", "data"):
			self.parents_list = wx.ListCtrl(props_panel, -1, style=wx.LC_REPORT)
			self.parents_list.InsertColumn(0, "Parent Type")
			for obj in self.entry.parents:
				self.parents_list.InsertStringItem(self.parents_list.GetItemCount(), obj.name)
			self.parents_list.SetColumnWidth(0, 400)
			edit_row = wx.BoxSizer(wx.HORIZONTAL)
			add_parent_button = wx.Button(props_panel, -1, "Add Parent")
			remove_parent_button = wx.Button(props_panel, -1, "Remove Parent")
			add_parent_button.Bind(wx.EVT_BUTTON, self.AddParent)
			remove_parent_button.Bind(wx.EVT_BUTTON, self.RemoveParent)
			edit_row.Add(add_parent_button, 1, wx.EXPAND)
			edit_row.Add(remove_parent_button, 1, wx.EXPAND)
			column.Add(self.parents_list, 1, wx.EXPAND)
			column.Add(edit_row, 0, wx.EXPAND)

		# Build the values tab, if we're types or data.
		if self.entry.which in ("types", "data"):
			values_panel = wx.Panel(self.notebook, -1)
			self.notebook.AddPage(values_panel, "Values")
			self.values_list = wx.ListCtrl(values_panel, -1, style=wx.LC_REPORT)
			self.values_list.InsertColumn(0, "Field")
			self.values_list.InsertColumn(1, "Type")
			self.values_list.InsertColumn(2, "Value")
			self.values_list.SetColumnWidth(0, 100)
			self.values_list.SetColumnWidth(1, 100)
			self.values_list.SetColumnWidth(2, 300)
			column = wx.BoxSizer(wx.VERTICAL)
			column.Add(self.values_list, 1, wx.EXPAND)
			values_panel.SetSizer(column)

		# Build the fields tab, if we're types.
		if self.entry.which == "types":
			fields_panel = wx.Panel(self.notebook, -1)
			self.notebook.AddPage(fields_panel, "Fields")
			column = wx.BoxSizer(wx.VERTICAL)
			self.fields_list = wx.ListCtrl(fields_panel, -1, style=wx.LC_REPORT)
			self.fields_list.InsertColumn(0, "Field")
			self.fields_list.InsertColumn(1, "Type")
			self.fields_list.SetColumnWidth(0, 100)
			self.fields_list.SetColumnWidth(1, 300)
			column.Add(self.fields_list, 1, wx.EXPAND)
			fields_panel.SetSizer(column)

		# Build the editor tab, if we're types or data.
		if self.entry.which in ("types", "data"):
			self.editor_panel = wx.Panel(self.notebook, -1)
			self.notebook.AddPage(self.editor_panel, "Editor")
			self.editor_column = wx.BoxSizer(wx.VERTICAL)
			self.editor_panel.SetSizer(self.editor_column)

		# Build the code tab, if we're code.
		if self.entry.which == "code":
			code_panel = wx.Panel(self.notebook, -1)
			self.notebook.AddPage(code_panel, "Code")
			code_font = wx.Font(12, wx.MODERN, wx.NORMAL, wx.NORMAL)
			self.code_text = wx.stc.StyledTextCtrl(code_panel, -1, style=wx.stc.STC_STYLE_LINENUMBER)
			self.code_text.StyleSetFont(wx.stc.STC_STYLE_DEFAULT, code_font)
			self.code_text.Bind(wx.EVT_CHAR, self.OnCodeEdit)
			self.code_text.Bind(wx.EVT_KILL_FOCUS, self.OnCodeEdit)
			self.code_text.AddText(self.entry.code_text or "")
			column = wx.BoxSizer(wx.VERTICAL)
			column.Add(self.code_text, 1, wx.EXPAND)
			code_panel.SetSizer(column)

		# Build the blocks tab, if we're blocks.
		if self.entry.which == "blocks":
			blocks_panel = wx.Panel(self.notebook, -1)
			self.notebook.AddPage(blocks_panel, "Blocks")
			row = wx.BoxSizer(wx.HORIZONTAL)
			self.blocks_tree = wx.TreeCtrl(blocks_panel, -1, style=wx.TR_HAS_BUTTONS|wx.TR_HIDE_ROOT|wx.TR_FULL_ROW_HIGHLIGHT)
			self.blocks_editor = blocks_editor.BlocksEditor(self.blocks_tree)
			self.blocks_editor.populate_from(entry.blocks_data)
			self.blocks_tree.Bind(wx.EVT_TREE_BEGIN_DRAG, self.OnBeginDrag)
			self.blocks_tree.Bind(wx.EVT_TREE_END_DRAG, self.OnEndDrag)
			self.blocks_tree.Bind(wx.EVT_RIGHT_DOWN, self.OnBlocksRightClick)
			row.Add(self.blocks_tree, 2, wx.EXPAND)
			self.blocks_nb = wx.Notebook(blocks_panel, -1, style=wx.NB_RIGHT)
			for i, section in enumerate(self.blocks_setup):
				buttons_page = wx.Panel(self.blocks_nb, -1, style=wx.NO_BORDER)
				column = wx.BoxSizer(wx.VERTICAL)
#				toolbar_one = wx.ToolBar(buttons_page, -1, style=wx.TB_VERTICAL)
				for i, name in enumerate(section["buttons"]):
					bttn = wx.Button(buttons_page, -1, name)
					# Silly workaround for Python closure semantics.
					(lambda _name: bttn.Bind(wx.EVT_BUTTON, lambda e: self.OnBlocksButton(_name, e)))(name)
					column.Add(bttn, 0, wx.EXPAND)
#				toolbar_one.AddSimpleTool(i, wx.Image(os.path.join(data_directory, "datum_icon.png"), wx.BITMAP_TYPE_PNG).ConvertToBitmap(), "Datum", "")
#				column.Add(toolbar_one, 1, wx.EXPAND)
				buttons_page.SetSizer(column)
				self.blocks_nb.AddPage(buttons_page, section["header"])
			row.Add(self.blocks_nb, 0, wx.EXPAND)
			blocks_panel.SetSizer(row)

		top_sizer = wx.BoxSizer(wx.VERTICAL)
		top_sizer.Add(self.notebook, 1, wx.EXPAND)
		self.SetSizer(top_sizer)

		# Add ctrl+w to close.
		randomId = wx.NewId()
		self.Bind(wx.EVT_MENU, self.OnClose, id=randomId)
		accel_tbl = wx.AcceleratorTable([(wx.ACCEL_CTRL,  ord('W'), randomId)])
		self.SetAcceleratorTable(accel_tbl)

		# Check the SDI model

	def OnBeginDrag(self, e):
		print "Begin"
		e.Allow()
		self.blocks_drag_item = e.GetItem()

	def OnEndDrag(self, e):
		print "End"
		if not e.GetItem().IsOk(): return
		new = e.GetItem()
		self.blocks_editor.drag(self.blocks_drag_item, new)
		self.entry.blocks_data = self.blocks_editor.serialize() # TODO: Make this less inefficient!

	def OnBlocksButton(self, name, e):
		self.blocks_editor.add_new(name)
		self.entry.blocks_data = self.blocks_editor.serialize() # TODO: Make this less inefficient!

	def OnBlocksRightClick(self, e):
		pt = e.GetPosition();
		item, flags = self.blocks_tree.HitTest(pt)
		node = self.blocks_tree.GetPyData(item)
		open_editor_for_node(self, node)
		e.Skip()

	def AddParent(self, e):
		dlg = TopLevelSelector(self, -1, "Choose a type...", "Types", "types", self.entry.parent)
		if dlg.ShowModal() == wx.ID_OK:
			if dlg.choice not in self.entry.parents:
				self.parents_list.InsertStringItem(self.parents_list.GetItemCount(), dlg.choice.name)
				self.entry.parents.append(dlg.choice)
		dlg.Destroy()

	def RemoveParent(self, e):
		index = self.parents_list.GetFocusedItem()
		if index == -1: return
		choice = self.entry.parents[index]
		assert self.parents_list.GetItemText(index) == choice.name, "Inconsistent list!"
		self.entry.parents.pop(index)
		self.parents_list.DeleteItem(index)

	def OnNameChange(self, e):
		new_name = self.name_box.GetValue()
		# Early out, to avoid renaming.
		if new_name == self.entry.name: return
		self.entry.rename_entry(new_name)
		self.name_box.SetValue(self.entry.name)

	def OnKeyPress(self, e):
		kc = e.GetKeyCode()
		if kc == wx.WXK_RETURN:
			self.OnNameChange(None)
			self.name_box.SetInsertionPoint(len(self.name_box.GetValue()))
		else: e.Skip()

	def OnCodeEdit(self, e):
		self.entry.code_text = self.code_text.GetText()
		e.Skip()

	def OnClose(self, e):
		self.Close()

class DataModel:
	def __init__(self, frame):
		self.frame = frame
		self.clear_data_model()

	def clear_data_model(self):
		self.frame.rebuild_data_tree()
		self.frame.notebook_remove_page("Edit")
		self.top_levels = {"types": [], "data": [], "code": [], "blocks": []}

	def new_of(self, which):
		entry = TopLevelEntry(self, which)
		self.top_levels[which].append(entry)
		entry.insert()
		return entry

	def get_by_name(self, name):
		for l in self.top_levels.itervalues():
			for e in l:
				if name == e.name: return e
		print "Can't find name:", repr(name)

	def name_available(self, name):
		# Names can't be empty.
		if not name: return False
		# Names must be valid C tokens.
		if name[0] not in string.ascii_letters + "_": return False
		if not all(c in string.ascii_letters + "_" + string.digits for c in name[1:]): return False
		# Check that the name isn't taken.
		for l in self.top_levels.itervalues():
			for e in l:
				if name == e.name: return False
		return True

	def delete_entry(self, entry):
		# Don't delete locked entries without cleaning up the page. It may segfault the program!
		if entry.is_locked():
			self.frame.notebook_remove_page("Edit")
		for l in self.top_levels.itervalues():
			if entry in l:
				l.remove(entry)
		entry.delete()

	def serialize(self):
		obj = {}
		for key, val in self.top_levels.iteritems():
			obj[key] = [i.serialize() for i in val]
		return {"top_levels": obj}

	def load_from(self, obj):
		self.clear_data_model()
		for key, val in obj["top_levels"].iteritems():
			self.top_levels[key] = [TopLevelEntry.load_from(i, self) for i in val]
		# There are some inter-entry references that are by name.
		# Give objects a chance to look them up, and convert them over.
		for l in self.top_levels.itervalues():
			for i in l:
				i.link_up_references()

