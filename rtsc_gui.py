#! /usr/bin/python

import sys, subprocess, time
import rtsc, rtsc_project, dirtree
import compilation, webbrowser
import json, os, wx
import wxLED
import wx.lib.buttons

class ProjectBuilder:
	last_issued = {}

	@staticmethod
	def create_empty_project(path):
		assert not os.path.exists(path), \
			"Won't blow away existing project!"
		os.mkdir(path)
		for sub_dir in ["sdi", "data", "bin", "src"]:
			os.mkdir(os.path.join(path, sub_dir))
		for sub_file, data in {"rtsc_gui.json": "{}\n"}.items():
			fd = open(os.path.join(path, sub_file), "w")
			fd.write(data)
			fd.close()

	@staticmethod
	def open_project(path):
		# Check for an rtsc_gui.json file within the project.
		if not os.path.exists(os.path.join(path, "rtsc_gui.json")):
			wx.MessageDialog(None, "This directory is not an RTSC project directory.", "Error", style=wx.ICON_ERROR).ShowModal()
			return False
		frame = RTSCMainFrame(path)
		frame.Show(True)
		return True

	@staticmethod
	def open_directory(path):
		# Try to protect against people clicking the button repeatedly because the thing is taking a while to open.
		# Don't issue the same path more than once per two seconds.
		if time.time() < ProjectBuilder.last_issued.get(path, 0)+2: return
		ProjectBuilder.last_issued[path] = time.time()
		if "linux" in sys.platform:
			cmd, shell = "xdg-open", False
		elif "darwin" in sys.platform:
			cmd, shell = "open", False
		else:
			# Windows
			cmd, shell = "start", True
		print "Opening", path
		subprocess.Popen([cmd, path], shell=shell)

class RTSCMainFrame(wx.Frame):
	checklist = [
		{"header": "Required to run:",
			"sub": ["At least one source", "All sources valid", "All resources exist", "One toolkit module imported", "Not more than one toolkit module imported", "Toolkit module configured"]},
		{"header": "Additionally required to build:",
			"sub": ["At least one target installed", "At least one target selected"]},
		{"header": "Additionally required to publish:",
			"sub": ["Publishing server set", "Publishing server keys", "Publishing server configured"]},
	]

	def __init__(self, project_path):
		wx.Frame.__init__(self, None, -1, "RTSC", wx.DefaultPosition, wx.Size(600, 500))

		self.project_path = project_path
		self.project_handle = rtsc_project.Project(project_path)

		font = wx.Font(14, wx.MODERN, wx.NORMAL, wx.BOLD)
		small_font = wx.Font(12, wx.MODERN, wx.NORMAL, wx.BOLD)

		menubar = wx.MenuBar()
		filemenu = wx.Menu()
#		filemenu.Append(100, '&New\tCtrl+N', 'New project')
#		filemenu.Append(101, '&Open\tCtrl+O', 'Open project')
		filemenu.Append(102, '&Save\tCtrl+S', 'Save project')
		filemenu.Append(103, '&Run\tF5', 'Run project')
		filemenu.Append(104, '&Build', 'Build project')
#		filemenu.AppendSeparator()
		quit = wx.MenuItem(filemenu, 105, '&Quit\tCtrl+Q', 'Quit RTSC')
		filemenu.AppendItem(quit)
		menubar.Append(filemenu, '&File')
		self.SetMenuBar(menubar)
#		self.Bind(wx.EVT_MENU, self.OnNew, id=100)
#		self.Bind(wx.EVT_MENU, self.OnOpen, id=101)
		self.Bind(wx.EVT_MENU, self.OnSave, id=102)
		self.Bind(wx.EVT_MENU, self.OnRun, id=103)
		self.Bind(wx.EVT_MENU, self.OnBuild, id=104)
		self.Bind(wx.EVT_MENU, self.OnQuit, id=105)

		self.notebook = wx.Notebook(self, -1)

		# Build the settings panel
		settings_panel = wx.Panel(self.notebook, -1)
		self.notebook.AddPage(settings_panel, "Main")
		column = wx.BoxSizer(wx.VERTICAL)
		column.Add((0,5))
		text = wx.StaticText(settings_panel, -1, "Project: %s" % os.path.split(project_path)[1])
		text.SetFont(font)
		column.Add(text)
		column.Add((0,0), 1)
		for text, func in [
				("Open Projects Directory", lambda e: ProjectBuilder.open_directory(project_path)),
				("Run Project", self.OnRun),
				("Build Project", self.OnBuild),
			]:
			button = wx.Button(settings_panel, -1, text)
			button.Bind(wx.EVT_BUTTON, func)
			column.Add(button, 0, wx.EXPAND)
		settings_panel.SetSizer(column)

		# Build the checklist panel
		checklist_panel = wx.Panel(self.notebook, -1)
		self.notebook.AddPage(checklist_panel, "Checklist")
		column = wx.BoxSizer(wx.VERTICAL)
		self.indicators = []
		for i, section in enumerate(RTSCMainFrame.checklist):
			column.Add((0,5))
			column.Add(wx.StaticText(checklist_panel, -1, section["header"]))
			column.Add((0,5))
			for requirement in section["sub"]:
				self.indicators.append(wxLED.LED(checklist_panel, -1))
				self.indicators[-1].SetState(0)
				row = wx.BoxSizer(wx.HORIZONTAL)
				row.Add(self.indicators[-1])
				row.Add((10,0))
				row.Add(wx.StaticText(checklist_panel, -1, requirement))
				column.Add(row)
				column.Add((0,5))
		checklist_panel.SetSizer(column)

		self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnUpdateIndicators)

		compilation_panel = wx.Panel(self.notebook, -1)
		self.notebook.AddPage(compilation_panel, "Targets")

		# Build the targets panel
		self.comp_data = {}
		for target in global_config["targets"]:
			self.comp_data[target["name"]] = {
				"build": False,
				"path": "(PROJECT)"+target["default_path"],
			}

		row = wx.BoxSizer(wx.HORIZONTAL)
		target_list = wx.ListCtrl(compilation_panel, -1, style=wx.LC_REPORT)
		target_list.InsertColumn(0, "Target")
		target_list.InsertColumn(1, "Build")
		target_list.InsertColumn(2, "Can")
		target_list.InsertColumn(3, "Have")
		for target in global_config["targets"]:
			i = target_list.GetItemCount()
			target_list.InsertStringItem(i, target["name"])
			target_list.SetStringItem(i, 2, "Yes")
			target_list.SetStringItem(i, 3, ("", "Yes")[target["name"] in global_config["target_size"]])
		row.Add(target_list, 1, wx.EXPAND)
		self.target_list = target_list

		right_panel = wx.Panel(compilation_panel, -1)
		column = wx.BoxSizer(wx.VERTICAL)
		self.target_name = wx.StaticText(right_panel, -1, "Target")
		self.target_name.SetFont(font)
		self.target_desc = wx.TextCtrl(right_panel, -1, style=wx.TE_MULTILINE)
		self.target_desc.SetEditable(False)
		self.target_values = [wx.StaticText(right_panel, -1, "") for i in xrange(1)]
		column.Add(self.target_name, 0, wx.EXPAND)
		column.Add(self.target_desc, 1, wx.EXPAND)
		for obj in self.target_values:
			obj.SetFont(small_font)
			column.Add(obj, 0, wx.EXPAND)
		self.target_selected = wx.CheckBox(right_panel, -1, label="Build for this target")
		self.target_selected.Bind(wx.EVT_CHECKBOX, self.OnStoreTargetInfo)
		self.target_selected.Enable(False)
		self.target_path = wx.TextCtrl(right_panel, -1)
		path_row = wx.BoxSizer(wx.HORIZONTAL)
		self.target_path.Bind(wx.EVT_KILL_FOCUS, self.OnStoreTargetInfo)
		self.target_path.SetEditable(False)
		path_row.Add(wx.StaticText(right_panel, -1, "Path:"))
		path_row.Add(self.target_path, 1, wx.EXPAND)
		column.Add(self.target_selected, 0, wx.EXPAND)
		column.Add(path_row, 0, wx.EXPAND)
		right_panel.SetSizer(column)
		target_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnTargetSelect)

		row.Add(right_panel, 1, wx.EXPAND)
		compilation_panel.SetSizer(row)

		# Build the resources panel
		resources_panel = wx.Panel(self.notebook, -1)
		self.notebook.AddPage(resources_panel, "Resources")
		column = wx.BoxSizer(wx.VERTICAL)
		self.resource_tree = wx.TreeCtrl(resources_panel, -1, style=wx.TR_HAS_BUTTONS|wx.TR_HIDE_ROOT|wx.TR_FULL_ROW_HIGHLIGHT)
		image_list = wx.ImageList(16, 16)
		image_list.Add(wx.ArtProvider.GetBitmap(wx.ART_FOLDER))
		image_list.Add(wx.ArtProvider.GetBitmap(wx.ART_EXECUTABLE_FILE))
		image_list.Add(wx.ArtProvider.GetBitmap(wx.ART_NORMAL_FILE))
		image_list.Add(wx.ArtProvider.GetBitmap(wx.ART_REPORT_VIEW))
		icon_mapping = {
			rtsc_project.SDI_Handler: 3,
			rtsc_project.Text_Handler: 2,
			rtsc_project.Blocks_Handler: 1,
			rtsc_project.Image_Handler: 2,
		}
#		image_list.Add(wx.Image('data/gear_icon.png', wx.BITMAP_TYPE_PNG).Scale(16, 16).ConvertToBitmap())
		self.resource_tree.AssignImageList(image_list)
		self.resource_tree_root = self.resource_tree.AddRoot("Bug Bug Bug!")
		mapping = {}
		for node in self.project_handle.tree.walk():
			mapping[node] = self.resource_tree.AppendItem(mapping.get(node.parent, self.resource_tree_root), node.name)
			self.resource_tree.SetItemPyData(mapping[node], node)
			if isinstance(node, dirtree.treeDirectory):
				self.resource_tree.SetItemImage(mapping[node], 0, 0)
			handler = self.project_handle.get_handler_for_node(node)
			if handler in icon_mapping:
				self.resource_tree.SetItemImage(mapping[node], icon_mapping[handler], 0)
		self.resource_tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnResourceDoubleClick)
		column.Add(self.resource_tree, 1, wx.EXPAND)
		resources_panel.SetSizer(column)

		main_frame_sizer = wx.BoxSizer(wx.VERTICAL)
		main_frame_sizer.Add(self.notebook, 1, wx.EXPAND)
		self.SetSizer(main_frame_sizer)

		# Reload all data.
		self.OnReload(None)
		self.OnUpdateIndicators(None)
		self.OnUpdateTargetInfo(None)

	def OnUpdateIndicators(self, e):
		pass
		# Not two toolkit modules.
#		self.indicators[3].SetState(2)
		# Check if we have at least one target installed.
#		self.indicators[5].SetState(2*bool(global_config["target_size"]))
		# Check if we have at least one target set.
#		self.indicators[6].SetState(2*any(i["build"] for i in self.comp_data.itervalues()))

	def OnTargetSelect(self, e):
		index = self.target_list.GetFocusedItem()
		target = global_config["targets"][index]
		self.current_target_index = index
		self.current_target = target["name"]
		have = target["name"] in global_config["target_size"]
		self.target_name.SetLabel(target["desc"])
		self.target_desc.SetValue(target["long_desc"].replace("\n", " "))
		if have: s = "Base size: %.1f MiB" % (global_config["target_size"][target["name"]]/(2**20.0))
		else: s = "Target not installed."
		self.target_values[0].SetLabel(s)
		self.target_selected.Enable(have)
		self.target_selected.SetValue(self.comp_data[target["name"]]["build"])
		self.target_path.SetEditable(have)
		self.target_path.SetValue(self.comp_data[target["name"]]["path"])

	def OnStoreTargetInfo(self, e):
		build = self.comp_data[self.current_target]["build"] = self.target_selected.GetValue()
		self.comp_data[self.current_target]["path"] = self.target_path.GetValue()
		self.target_list.SetStringItem(self.current_target_index, 1, ("", "Yes")[build])

	def OnUpdateTargetInfo(self, e):
		for i, target in enumerate(global_config["targets"]):
			self.target_list.SetStringItem(i, 1, ("", "Yes")[self.comp_data[target["name"]]["build"]])

	def OnResourceDoubleClick(self, e):
		node = self.resource_tree.GetItemPyData(e.GetItem())
		self.project_handle.get_handler_for_node(node)().open_file(node.full_path)

	def OnSave(self, e):
		print "Saving project"
		obj = {}
		obj["comp_data"] = self.comp_data
		s = json.dumps(obj, indent=2)
		fd = open(os.path.join(self.project_path, "rtsc_gui.json"), "w")
		fd.write(s+"\n")
		fd.close()

	def OnReload(self, e):
		print "Reloading project"
		fd = open(os.path.join(self.project_path, "rtsc_gui.json"))
		obj = json.loads(fd.read())
		fd.close()
		if "comp_data" in obj:
			self.comp_data = obj["comp_data"]

	def OnRun(self, e):
		print "Running!"

	def OnBuild(self, e):
		print "Building!"

	def OnQuit(self, e):
		app.Exit()

class GlobalSettingsFrame(wx.Frame):
	def __init__(self):
		wx.Frame.__init__(self, None, -1, "Global RTSC Settings", wx.DefaultPosition, wx.Size(500, 300))
		column = wx.BoxSizer(wx.VERTICAL)
		self.ctrl = wx.ListCtrl(self, -1, style=wx.LC_REPORT)
		self.ctrl.InsertColumn(0, "Field")
		self.ctrl.InsertColumn(1, "Value")
		self.ctrl.SetColumnWidth(0, 150)
		self.ctrl.SetColumnWidth(1, 350)
		self.keys = global_config["settings"].keys()
		for key in self.keys:
			i = self.ctrl.GetItemCount()
			self.ctrl.InsertStringItem(i, key)
			self.ctrl.SetStringItem(i, 1, global_config["settings"][key])
		column.Add(self.ctrl, 1, wx.EXPAND)
		button = wx.Button(self, -1, "Reset to defaults")
		button.Bind(wx.EVT_BUTTON, self.OnReset)
		column.Add(button, 0, wx.EXPAND)
		self.SetSizer(column)
		self.ctrl.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnEdit)

	def OnEdit(self, e):
		index = e.GetIndex()
		key = self.keys[index]
		dlg = wx.TextEntryDialog(self, "Variable value:", "Set value...", defaultValue=global_config["settings"][key])
		try:
			if dlg.ShowModal() != wx.ID_OK:
				return
			value = dlg.GetValue()
			self.ctrl.SetStringItem(index, 1, value)
			global_config["settings"][key] = value
		finally:
			dlg.Destroy()
		self.OnSave(None)

	def OnSave(self, e):
		fd = open(os.path.join("data", "global_settings.json"), "w")
		fd.write(json.dumps(global_config["settings"], indent=2)+"\n")
		fd.close()

	def OnReset(self, e):
		dlg = wx.MessageDialog(None, "Reset all values to factory defaults?", "Reset", wx.YES_NO | wx.ICON_QUESTION)
		if dlg.ShowModal() == wx.ID_YES:
			global_config["settings"] = global_config["default_settings"].copy()
			for i, key in enumerate(self.keys):
				self.ctrl.SetStringItem(i, 1, global_config["settings"][key])
			self.OnSave(None)
		dlg.Destroy()

class RTSCManagerFrame(wx.Frame):
	def __init__(self):
		wx.Frame.__init__(self, None, -1, "Project Manager (v%i.%i)" % rtsc.version, wx.DefaultPosition, wx.Size(280, 55+40*6))

		menubar = wx.MenuBar()
		filemenu = wx.Menu()
		filemenu.Append(100, '&New\tCtrl+N', 'New project')
		filemenu.Append(101, '&Open\tCtrl+O', 'Open project')
		filemenu.Append(102, '&Tutorial\tCtrl+T', 'Tutorial')
		filemenu.Append(103, '&Project Directory\tCtrl+P', 'Project Directory')
		filemenu.AppendSeparator()
		quit = wx.MenuItem(filemenu, 105, '&Quit\tCtrl+Q', 'Quit RTSC')
		filemenu.AppendItem(quit)
		menubar.Append(filemenu, '&File')
		self.SetMenuBar(menubar)
		self.Bind(wx.EVT_MENU, self.OnNew, id=100)
		self.Bind(wx.EVT_MENU, self.OnOpen, id=101)
		self.Bind(wx.EVT_MENU, self.OnTutorial, id=102)
		self.Bind(wx.EVT_MENU, self.OnDirectory, id=103)
		self.Bind(wx.EVT_MENU, self.OnQuit, id=105)

		top_sizer = wx.BoxSizer(wx.HORIZONTAL)
		sizer = wx.BoxSizer(wx.VERTICAL)

		sizer.Add((0, 15))

		for p in [
				{"art": wx.ART_NEW, "label": "New Project", "f": self.OnNew},
				{"art": wx.ART_FILE_OPEN, "label": "Open Project", "f": self.OnOpen},
				{"art": wx.ART_HELP_BOOK, "label": "Tutorial", "f": self.OnTutorial},
				{"art": wx.ART_FOLDER_OPEN, "label": "Projects Directory", "f": self.OnDirectory},
				{"art": wx.ART_INFORMATION, "label": "Global Settings", "f": self.OnGlobalSettings},
				{"art": wx.ART_QUIT, "label": "Quit", "f": self.OnQuit},
#				{"art": wx.ART_HARDDISK, "label": "Foobar", "f": self.OnNew},
#				{"art": wx.ART_CROSS_MARK, "label": "Foobar", "f": self.OnNew},
			]:
			button = wx.lib.buttons.GenBitmapTextButton(self, -1, wx.ArtProvider.GetBitmap(p["art"]), p["label"], size=(250, 40))
			button.SetBezelWidth(1)
			button.Bind(wx.EVT_BUTTON, p["f"])
#			button.SetBackgroundColour("#c2e6f8")
			sizer.Add(button)

		top_sizer.Add((15, 0))
		top_sizer.Add(sizer)
		self.SetSizer(top_sizer)

		self.done_tutorial = False
		self.global_settings_frame = None

	def OnOpen(self, new=False):
		dlg = wx.DirDialog(self, style=wx.DD_DEFAULT_STYLE|wx.DD_DIR_MUST_EXIST,
			message="Open project...", defaultPath="projects")
		try:
			if dlg.ShowModal() != wx.ID_OK:
				return
			project_path = dlg.GetPath()
		finally:
			dlg.Destroy()
		print "Opening project", project_path
		if ProjectBuilder.open_project(project_path):
			self.do_destroy()

	def OnNew(self, new=False):
		dlg = wx.TextEntryDialog(self, "Project file name:\n(Good style is all lowercase, no symbols or spaces.)", "New project...")
		try:
			if dlg.ShowModal() != wx.ID_OK:
				return
			project_path = dlg.GetValue()
		finally:
			dlg.Destroy()
		project_path = os.path.join("projects", project_path)
		if os.path.exists(project_path):
			wx.MessageDialog(self, "Project already exists.", "Error", style=wx.ICON_ERROR).ShowModal()
			return
		print "Creating project", project_path
		ProjectBuilder.create_empty_project(project_path)
		if ProjectBuilder.open_project(project_path):
			self.do_destroy()

	def do_destroy(self):
		if self.global_settings_frame:
			self.global_settings_frame.Destroy()
		self.Destroy()

	def OnTutorial(self, e):
		if not self.done_tutorial:
			url = "http://rtsc.mit.edu/docs/%s.%s/tutorial" % rtsc.version
			self.done_tutorial = True
			print "Directing browser to", url
			webbrowser.open(url)

	def OnDirectory(self, e):
		ProjectBuilder.open_directory("projects")

	def OnGlobalSettings(self, e):
		if not self.global_settings_frame:
			self.global_settings_frame = GlobalSettingsFrame()
			self.global_settings_frame.Show(True)
		else:
			self.global_settings_frame.Raise()

	def OnQuit(self, e):
		app.Exit()

class RTSCMainApp(wx.App):
	def OnInit(self):
		frame = RTSCManagerFrame()
		frame.Show(True)
		return True

# Load up the static configuration file.
txt = []
for line in open(os.path.join("data", "extensions.config")):
	line = line.split("#")[0].strip()
	if not line: continue
	txt.append(line)
global_config = json.loads("\n".join(txt))

# Load up the user-editable settings.
try:
	path = os.path.join("data", "global_settings.json")
	fd = open(path)
except:
	print path, "missing -- using defaults."
	global_config["settings"] = global_config["default_settings"].copy()
else:
	global_config["settings"] = json.load(fd)
	fd.close()

# Read in the sizes of various compilation targets.
global_config["target_size"] = {}
for target in compilation.capabilities():
	global_config["target_size"][target] = compilation.get_size(target)

if __name__ == "__main__":
	app = RTSCMainApp(0)
	app.MainLoop()

