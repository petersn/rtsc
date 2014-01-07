#! /usr/bin/python

import json
import wx
import sdigui
import sdi_data_model
import os, sys

data_directory = os.path.join(os.path.dirname(sys.argv[0]), "data")

class SDIMainFrame(wx.Frame):
	FILE_WILDCARD = "SDI Data (*.sdi)|*.sdi|All Files (*)|*"

	def __init__(self):
		wx.Frame.__init__(self, None, -1, "Structured Data Input", wx.DefaultPosition, wx.Size(800, 600))

		menubar = wx.MenuBar()
		filemenu = wx.Menu()
		filemenu.Append(100, '&New\tCtrl+N', 'New file')
		filemenu.Append(101, '&Open\tCtrl+O', 'Open file')
		filemenu.Append(102, '&Save\tCtrl+S', 'Save file')
		filemenu.Append(103, '&Save as\tCtrl+Shift+S', 'Save file as')
		filemenu.AppendSeparator()
		quit = wx.MenuItem(filemenu, 105, '&Quit\tCtrl+Q', 'Quit SDI')
		filemenu.AppendItem(quit)
		menubar.Append(filemenu, '&File')
		self.SetMenuBar(menubar)
		self.Bind(wx.EVT_MENU, self.OnNew, id=100)
		self.Bind(wx.EVT_MENU, self.OnOpen, id=101)
		self.Bind(wx.EVT_MENU, self.OnSave, id=102)
		self.Bind(wx.EVT_MENU, self.OnSaveAs, id=103)
		self.Bind(wx.EVT_MENU, self.OnQuit, id=105)

		self.splitter = wx.SplitterWindow(self, -1)

		# Here is the leftmost tree.
		self.data_tree = wx.TreeCtrl(self.splitter, -1, style=wx.TR_HAS_BUTTONS|wx.SUNKEN_BORDER|wx.TR_HIDE_ROOT|wx.TR_FULL_ROW_HIGHLIGHT)
		image_list = wx.ImageList(16, 16)
		for p in ["type_icon.png", "datum_icon.png", "gear_icon.png", "blocks_icon.png"]:
			image_list.Add(wx.Image(os.path.join(data_directory, p), wx.BITMAP_TYPE_PNG).Scale(16, 16).ConvertToBitmap())
		self.data_tree.AssignImageList(image_list)
		self.data_tree_root = None

		self.main_notebook = wx.Notebook(self.splitter, -1)
#		self.main_panel_sizer = wx.BoxSizer(wx.VERTICAL)
#		self.main_panel_sizer.Add(self.main_panel, 1, wx.EXPAND)

		self.outer_sizer = wx.BoxSizer(wx.VERTICAL)
		self.toolbar = wx.ToolBar(self, -1, style=wx.TB_HORIZONTAL|wx.NO_BORDER)
		for i, entry in enumerate([
				("type_icon_wp.png", "New Type", self.NewType),
				("datum_icon_wp.png", "New Datum", self.NewDatum),
				("gear_icon_wp.png", "New Code", self.NewCode),
				("blocks_icon_wp.png", "New Blocks", self.NewBlocks),
				("x_icon.png", "Delete Entry", self.DeleteEntry),
			]):
			self.toolbar.AddSimpleTool(i, wx.Image(os.path.join(data_directory, entry[0]), wx.BITMAP_TYPE_PNG).ConvertToBitmap(), entry[1], "")
			self.Bind(wx.EVT_TOOL, entry[2], id=i)
#		self.toolbar.AddSimpleTool(2, wx.Image('data/datum_icon_wp.png', wx.BITMAP_TYPE_PNG).ConvertToBitmap(), "New Datum", '')
#		self.toolbar.AddSimpleTool(3, wx.Image('data/gear_icon_wp.png', wx.BITMAP_TYPE_PNG).ConvertToBitmap(), "New Code", '')
#		self.toolbar.AddSimpleTool(10, wx.Image('data/x_icon.png', wx.BITMAP_TYPE_PNG).ConvertToBitmap(), "Delete Entry", '')
#		self.bar_sizer = wx.BoxSizer(wx.HORIZONTAL)
#		self.bar_sizer.Add(self.compile_button, 0, 0)
		self.splitter.SplitVertically(self.data_tree, self.main_notebook, 250)
#		self.top_sizer = wx.BoxSizer(wx.HORIZONTAL)
#		self.top_sizer.Add(self.data_tree, 1, wx.EXPAND)
#		self.top_sizer.Add(self.main_panel, 2, wx.EXPAND)
		self.outer_sizer.Add(self.toolbar, 0, wx.EXPAND)
		self.outer_sizer.Add(self.splitter, 1, wx.EXPAND)
		self.SetSizer(self.outer_sizer)

		self.rebuild_data_tree()

		self.data_tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnTreeSelect)

		self.dm = sdi_data_model.DataModel(self)
		self.save_to_path = None

	def notebook_remove_page(self, s):
		for i in xrange(self.main_notebook.GetPageCount()):
			name = self.main_notebook.GetPageText(i)
			if name == s:
				self.main_notebook.DeletePage(i)
				return

	def rebuild_data_tree(self):
		if self.data_tree_root:
			self.data_tree.DeleteAllItems()
		self.data_tree_root = self.data_tree.AddRoot("Bug Bug Bug!")
		self.data_tree_top_levels = {}
		for name in ("Types", "Data", "Code", "Blocks"):
			self.data_tree_top_levels[name.lower()] = self.data_tree.AppendItem(self.data_tree_root, name)

	def OnNew(self, e):
		dlg = wx.MessageDialog(None, "Start new data?", "New data", wx.YES_NO | wx.ICON_QUESTION)
		if dlg.ShowModal() == wx.ID_YES:
			self.save_to_path = None
			self.dm.clear_data_model()
		dlg.Destroy()

	def OnOpen(self, e):
		dlg = wx.FileDialog(self, style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST, message="Load data...",
			wildcard=SDIMainFrame.FILE_WILDCARD, defaultDir=".")
		try:
			if dlg.ShowModal() != wx.ID_OK:
				return
			save_to_path = dlg.GetPath()
		finally:
			dlg.Destroy()
		self.load_from_path(save_to_path)

	def load_from_path(self, path):
		print "Loading from", path
		self.save_to_path = path
		fd = open(path)
		data = fd.read()
		fd.close()
		obj = json.loads(data)
		self.dm.load_from(obj["dm"])

	def OnSave(self, e):
		if self.save_to_path is None:
			self.OnSaveAs(None)
		else:
			print "Saving to", self.save_to_path
			obj = {}
			obj["dm"] = self.dm.serialize()
			s = json.dumps(obj, indent=2)
			fd = open(self.save_to_path, "w")
			fd.write(s)
			fd.close()

	def OnSaveAs(self, e):
		dlg = wx.FileDialog(self, style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT, message="Save data as...",
			wildcard=SDIMainFrame.FILE_WILDCARD, defaultDir=".")
		try:
			if dlg.ShowModal() != wx.ID_OK:
				return
			self.save_to_path = dlg.GetPath()
			if not self.save_to_path.endswith(".sdi"):
				self.save_to_path += ".sdi"
		finally:
			dlg.Destroy()
		self.OnSave(None)

	def NewType(self, e): self.dm.new_of("types")
	def NewDatum(self, e): self.dm.new_of("data")
	def NewCode(self, e): self.dm.new_of("code")
	def NewBlocks(self, e): self.dm.new_of("blocks")

	def DeleteEntry(self, e):
		sel = self.data_tree.GetSelection()
		entry = self.data_tree.GetItemPyData(sel)
		if not entry: return
		# Don't let a locked entry be deleted.
		if True:
#		if entry.is_locked():
#			# If locked, then bring the edit frame to the front,
#			# so the user sees why the entry can't be deleted.
#			entry.activate()
#		else:
			dlg = wx.MessageDialog(None, "Delete %s?" % entry.name, "Deleting", wx.YES_NO | wx.ICON_QUESTION)
			if dlg.ShowModal() == wx.ID_YES:
				self.dm.delete_entry(entry)
			dlg.Destroy()

	def OnTreeSelect(self, e):
		sel = self.data_tree.GetSelection()
		entry = self.data_tree.GetItemPyData(sel)
		if not entry: return
		entry.activate()

	def OnQuit(self, e):
		app.Exit()

class SDIMainApp(wx.App):
	def OnInit(self):
		frame = SDIMainFrame()
		if len(sys.argv) == 2:
			frame.load_from_path(sys.argv[1])
		frame.Show(True)
		return True

if __name__ == "__main__":
	app = SDIMainApp(0)
	app.MainLoop()

