#! /usr/bin/python

import wx
import sdigui
import sdi_data_model

class SDIMainFrame(wx.Frame):
	def __init__(self):
		wx.Frame.__init__(self, None, -1, "Structured Data Input", wx.DefaultPosition, wx.Size(800, 600))

		menubar = wx.MenuBar()
		filemenu = wx.Menu()
		filemenu.Append(101, '&Open\tCtrl+O', 'Open file')
		filemenu.Append(102, '&Save\tCtrl+S', 'Save file')
		filemenu.Append(103, '&Save as\tCtrl+Shift+S', 'Save file as')
		filemenu.AppendSeparator()
		quit = wx.MenuItem(filemenu, 105, '&Quit\tCtrl+Q', 'Quit SDI')
		filemenu.AppendItem(quit)
		menubar.Append(filemenu, '&File')
		self.SetMenuBar(menubar)
		self.Bind(wx.EVT_MENU, self.OnOpen, id=101)
		self.Bind(wx.EVT_MENU, self.OnSave, id=102)
		self.Bind(wx.EVT_MENU, self.OnSaveAs, id=103)
		self.Bind(wx.EVT_MENU, self.OnQuit, id=105)

		self.splitter = wx.SplitterWindow(self, -1)

		# Here is the leftmost tree.
		self.data_tree = wx.TreeCtrl(self.splitter, -1, style=wx.TR_HAS_BUTTONS|wx.SUNKEN_BORDER|wx.TR_HIDE_ROOT|wx.TR_FULL_ROW_HIGHLIGHT)
		image_list = wx.ImageList(16, 16)
		image_list.Add(wx.Image('data/type_icon.png', wx.BITMAP_TYPE_PNG).Scale(16, 16).ConvertToBitmap())
		image_list.Add(wx.Image('data/datum_icon.png', wx.BITMAP_TYPE_PNG).Scale(16, 16).ConvertToBitmap())
		image_list.Add(wx.Image('data/gear_icon.png', wx.BITMAP_TYPE_PNG).Scale(16, 16).ConvertToBitmap())
		self.data_tree.AssignImageList(image_list)
		self.data_tree_root = self.data_tree.AddRoot("Bug Bug Bug!")

		self.main_panel = wx.Panel(self.splitter, -1)

		self.outer_sizer = wx.BoxSizer(wx.VERTICAL)
		self.toolbar = wx.ToolBar(self, -1, style=wx.TB_HORIZONTAL|wx.NO_BORDER)
		self.toolbar.AddSimpleTool(1, wx.Image('data/type_icon_wp.png', wx.BITMAP_TYPE_PNG).ConvertToBitmap(), "New Type", '')
		self.toolbar.AddSimpleTool(2, wx.Image('data/datum_icon_wp.png', wx.BITMAP_TYPE_PNG).ConvertToBitmap(), "New Datum", '')
		self.toolbar.AddSimpleTool(3, wx.Image('data/gear_icon_wp.png', wx.BITMAP_TYPE_PNG).ConvertToBitmap(), "New Code", '')
		self.toolbar.AddSimpleTool(10, wx.Image('data/x_icon.png', wx.BITMAP_TYPE_PNG).ConvertToBitmap(), "Delete Entry", '')
#		self.bar_sizer = wx.BoxSizer(wx.HORIZONTAL)
#		self.bar_sizer.Add(self.compile_button, 0, 0)
		self.splitter.SplitVertically(self.data_tree, self.main_panel, 250)
#		self.top_sizer = wx.BoxSizer(wx.HORIZONTAL)
#		self.top_sizer.Add(self.data_tree, 1, wx.EXPAND)
#		self.top_sizer.Add(self.main_panel, 2, wx.EXPAND)
		self.outer_sizer.Add(self.toolbar, 0, wx.EXPAND)
		self.outer_sizer.Add(self.splitter, 1, wx.EXPAND)
		self.SetSizer(self.outer_sizer)

		self.rebuild_data_tree()

		self.Bind(wx.EVT_TOOL, self.NewType, id=1)
		self.Bind(wx.EVT_TOOL, self.NewDatum, id=2)
		self.Bind(wx.EVT_TOOL, self.NewCode, id=3)
		self.Bind(wx.EVT_TOOL, self.DeleteEntry, id=10)

		self.data_tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnTreeSelect)

		self.dm = sdi_data_model.DataModel(self)

	def rebuild_data_tree(self):
		self.data_tree_top_levels = {}
		for name in ("Types", "Data", "Code"):
			self.data_tree_top_levels[name.lower()] = self.data_tree.AppendItem(self.data_tree_root, name)

	def OnOpen(self, e): pass
	def OnSave(self, e): pass
	def OnSaveAs(self, e): pass

	def NewType(self, e): self.dm.new_of("types")
	def NewDatum(self, e): self.dm.new_of("data")
	def NewCode(self, e): self.dm.new_of("code")

	def DeleteEntry(self, e):
		sel = self.data_tree.GetSelection()
		entry = self.data_tree.GetItemPyData(sel)
		if not entry: return
		# Don't let a locked entry be deleted.
		if entry.is_locked():
			# If locked, then bring the edit frame to the front,
			# so the user sees why the entry can't be deleted.
			entry.activate()
		else:
			dlg = wx.MessageDialog(None, "Delete %s?" % repr(entry.name), "Deleting", wx.YES_NO | wx.ICON_QUESTION)
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
		frame.Show(True)
		return True

if __name__ == "__main__":
	app = SDIMainApp(0)
	app.MainLoop()

