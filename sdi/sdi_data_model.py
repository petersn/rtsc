#! /usr/bin/python

import wx

singularize = {
	"types": "type",
	"data": "datum",
	"code": "code",
}

def get_unique_name(s, l):
	c = 1
	while True:
		name = "%s%i" % (s, c)
		for e in l:
			if e.name == name:
				c += 1
				break
		else: return name

class TopLevelEntry:
	def __init__(self, parent, which):
		self.parent, self.which = parent, which
		self.name = get_unique_name(singularize[which], parent.top_levels[which])
		self.edit_frame = None

	def insert(self):
		item = self.parent.frame.data_tree.AppendItem(self.parent.frame.data_tree_top_levels[self.which], self.name)
		self.parent.frame.data_tree.SetItemImage(item, ["types", "data", "code"].index(self.which), 0)
		self.parent.frame.data_tree.SetItemPyData(item, self)

	def activate(self):
		# Take advantage of the fact that deleted references coerce to false.
		if not self.edit_frame:
			self.edit_frame = TopLevelEntryFrame(self)
			self.edit_frame.Show(True)
		else:
			self.edit_frame.Raise()

class TopLevelEntryFrame(wx.Frame):
	def __init__(self, entry):
		wx.Frame.__init__(self, None, -1, "Entry Data", wx.DefaultPosition, wx.Size(700, 500))
		self.entry = entry
		top_sizer = wx.BoxSizer(wx.HORIZONTAL)
		left_column = wx.BoxSizer(wx.VERTICAL)
		name_row = wx.BoxSizer(wx.HORIZONTAL)
		name_row.Add(wx.StaticText(self, -1, "Name:"), 0, wx.EXPAND)
		self.name_box = wx.TextCtrl(self, -1)
		self.name_box.SetValue(self.entry.name)
		name_row.Add(self.name_box, 1, wx.EXPAND)
		left_column.Add(name_row, 0, wx.EXPAND)
		top_sizer.Add(left_column, 1, wx.EXPAND)
		top_sizer.Add(wx.Panel(self, -1), 2, wx.EXPAND)
		self.SetSizer(top_sizer)

class DataModel:
	def __init__(self, frame):
		self.frame = frame
		self.top_levels = {
			"types": [],
			"data": [],
			"code": [],
		}

	def new_of(self, which):
		entry = TopLevelEntry(self, which)
		self.top_levels[which].append(entry)
		entry.insert()

