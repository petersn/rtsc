#! /usr/bin/python

import string
import wx

singularize = {
	"types": "type",
	"data": "datum",
	"code": "code",
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

	def insert(self):
		self.tree_item = self.parent.frame.data_tree.AppendItem(self.parent.frame.data_tree_top_levels[self.which], self.name)
		self.parent.frame.data_tree.SetItemImage(self.tree_item, ["types", "data", "code"].index(self.which), 0)
		self.parent.frame.data_tree.SetItemPyData(self.tree_item, self)

	def delete(self):
		self.parent.frame.data_tree.Delete(self.tree_item)

	def activate(self):
		# Take advantage of the fact that deleted references coerce to false.
		if not self.edit_frame:
			self.edit_frame = TopLevelEntryFrame(self)
			self.edit_frame.Show(True)
		else:
			self.edit_frame.Raise()

	def rename_entry(self, new_name):
		if self.parent.name_available(new_name):
			self.name = new_name
			self.parent.frame.data_tree.SetItemText(self.tree_item, self.name)

	def is_locked(self):
		return bool(self.edit_frame)

class TopLevelSelector(wx.Dialog):
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

class TopLevelEntryFrame(wx.Frame):
	def __init__(self, entry):
		wx.Frame.__init__(self, None, -1, "Edit", wx.DefaultPosition, wx.Size(400, 500))
		self.entry = entry

		self.notebook = wx.Notebook(self, -1)
		props_panel = wx.Panel(self.notebook, -1)
		self.notebook.AddPage(props_panel, "Props")

		# Build the props tab.
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

		# Add the inheritance list, if we're types.
		if self.entry.which == "types":
			self.parents_list = wx.ListCtrl(props_panel, -1, style=wx.LC_REPORT)
			self.parents_list.InsertColumn(0, "Parent Type")
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

		top_sizer = wx.BoxSizer(wx.VERTICAL)
		top_sizer.Add(self.notebook, 1, wx.EXPAND)
		self.SetSizer(top_sizer)

		randomId = wx.NewId()
		self.Bind(wx.EVT_MENU, self.OnClose, id=randomId)
		accel_tbl = wx.AcceleratorTable([(wx.ACCEL_CTRL,  ord('W'), randomId)])
		self.SetAcceleratorTable(accel_tbl)

		# Check the SDI model

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

	def OnClose(self, e):
		self.Close()

class DataModel:
	def __init__(self, frame):
		self.frame = frame
		self.top_levels = {"types": [], "data": [], "code": []}

	def new_of(self, which):
		entry = TopLevelEntry(self, which)
		self.top_levels[which].append(entry)
		entry.insert()

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
		# Don't delete locked entries. It may segfault the program!
		if entry.is_locked(): return
		for l in self.top_levels.itervalues():
			if entry in l:
				l.remove(entry)
		entry.delete()

