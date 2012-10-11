#! /usr/bin/python

import os, ConfigParser, StringIO, subprocess, time, socket
from gettext import gettext as _

import gtk
import gedit
import pango
from rtsc import rtsc
from rtsc import compilation

plugin_version = (0, 1)

ui_str = """
<ui>
	<menubar name="MenuBar">
		<menu name="FileMenu" action="File">
			<placeholder name="FileOps_2">
				<menuitem name="RTSC_NewProject" action="RTSC_NewProject"/>
				<menuitem name="RTSC_OpenProject" action="RTSC_OpenProject"/>
			</placeholder>
		</menu>
		<menu name="RTSCMenu" action="RTSC">
			<menuitem name="RTSC_Compile" action="RTSC_Compile"/>
			<menuitem name="RTSC_Run" action="RTSC_Run"/>
			<separator/>
			<menu name="RTSCVersioningMenu" action="RTSCVersioning">
				<menuitem name="RTSC_SaveCommit" action="RTSC_SaveCommit"/>
				<menuitem name="RTSC_Diff" action="RTSC_Diff"/>
				<menuitem name="RTSC_ViewHistory" action="RTSC_ViewHistory"/>
			</menu>
			<menu name="RTSCHelpersMenu" action="RTSCHelpers">
				<menuitem name="RTSC_SyntaxCheck" action="RTSC_SyntaxCheck"/>
				<menuitem name="RTSC_OpenProjectFiles" action="RTSC_OpenProjectFiles"/>
				<menuitem name="RTSC_CheckForUpdates" action="RTSC_CheckForUpdates"/>
				<menuitem name="RTSC_Version" action="RTSC_Version"/>
			</menu>
		</menu>
	</menubar>
</ui>
"""

class Timer:
	def __init__(self, msg, obj): self.msg, self.obj = msg, obj
	def __enter__(self): self.start = time.time()
	def __exit__(self, t, val, tb):
		end = time.time()
		obj.write(self.msg + "%.3fs" % (end - self.start) + "\n")

class RTSCWindowHelper:
	versioning_file_ignore_filter = ["versioning", "Main", "*.bytes"]

	def __init__(self, plugin, window):
		self._window = window
		self._plugin = plugin

		self.diff_console = None
		self.to_disconnect = []

		# Insert menu items
		self._insert_menu()

	def deactivate(self):
		# Remove any installed menu items
		self._remove_menu()

		self._window = None
		self._plugin = None
		self._action_group = None

	def _insert_menu(self):
		# Get the GtkUIManager
		manager = self._window.get_ui_manager()

		# Create a new action group
		self._action_group = gtk.ActionGroup("RTSCPluginActions")
		self._action_group.set_translation_domain('gedit')
		add = lambda x : self._action_group.add_actions([x])

		# Add the menu names.
		add(('RTSC', None, _('RTSC'), None, _("RTSC Tools"), None))
		add(('RTSCHelpers', None, _('Helpers'), None, _("RTSC code-writing helpers"), None))
		add(('RTSCVersioning', None, _('Versioning'), None, _("Simple version control"), None))

		# Add various commands.
		add(("RTSC_NewProject", None, _("New RTSC Project"), None, _("Make a new project"), self.on_new_project))
		add(("RTSC_OpenProject", None, _("Open RTSC Project"), None, _("Open an existing project"), self.on_open_project))
		add(("RTSC_Compile", None, _("Compile"), None, _("Force recompile the current project"), self.on_rtsc_compile))
		add(("RTSC_Run", None, _("Run"), "F5", _("Compile (if needed) and run the current project"), self.on_rtsc_run))

		add(("RTSC_SaveCommit", None, _("Save Commit"), None, _("Commit a new version of the project"), self.on_save_commit))
		add(("RTSC_Diff", None, _("Differences"), None, _("Differences from previous version"), self.on_diff))
		add(("RTSC_ViewHistory", None, _("Project History"), None, _("View project history"), self.on_view_history))

		add(("RTSC_SyntaxCheck", None, _("Check Syntax"), None, _("Check project for syntax errors"), self.on_rtsc_check))
		add(("RTSC_OpenProjectFiles", None, _("Open Project Files"), None, _("Open all the files associated with this project"), self.open_project_files))
		add(("RTSC_CheckForUpdates", None, _("Network Updates"), None, _("Check for updates to RTSC or this plugin over the network"), self.on_rtsc_update))
		add(("RTSC_Version", None, _("Version"), None, _("Tells you some version crap"), self.on_version))

		# Insert the action group
		manager.insert_action_group(self._action_group, -1)

		# Merge the UI
		self._ui_id = manager.add_ui_from_string(ui_str)

		# Insert the bottom panel console
		self.console = RTSCConsole()
		bottom = self._window.get_bottom_panel()
		bottom.add_item(self.console, _('Compilation Console'), gtk.STOCK_EXECUTE)

		manager.ensure_update()

		self.to_disconnect.append((self._window, self._window.connect("tab-added", self.tab_added_cb)))

	def _remove_menu(self):
		# Get the GtkUIManager
		manager = self._window.get_ui_manager()

		# Disconnect all signals.
		for obj, handler_id in self.to_disconnect:
			obj.disconnect(handler_id)

		# Remove the ui
		manager.remove_ui(self._ui_id)

		# Remove the action group
		manager.remove_action_group(self._action_group)

		# Make sure the manager updates
		manager.ensure_update()

		# Remove the bottom panel console
		bottom = self._window.get_bottom_panel()
		bottom.remove_item(self.console)

		if self.diff_console != None:
			bottom = self._window.get_bottom_panel()
			bottom.remove_item(self.diff_console)

	def update_ui(self):
		self._action_group.set_sensitive(self._window.get_active_document() != None)

	def tab_added_cb(self, window, tab):
		doc = tab.get_document()
		self.to_disconnect.append((doc, doc.connect("loaded", self.check_if_doc_should_launch_more, tab.get_view())))

	def check_if_doc_should_launch_more(self, doc, *args):
		# Don't open more unless we have nothing else open.
		# This is a heuristic for "we double clicked on the project".
		if len(self._window.get_documents()) == 1 and os.path.splitext(doc.get_short_name_for_display())[1] == ".rtsc-proj":
			self.open_project_files()

	def error_dialog(self, msg):
		dlg = gtk.MessageDialog(self._window, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE, msg)
		dlg.run()
		dlg.destroy()

	def success_dialog(self, msg):
		dlg = gtk.MessageDialog(self._window, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO, gtk.BUTTONS_OK, msg)
		dlg.run()
		dlg.destroy()

	def get_rtsc_main_project(self):
		candidates = []
		for doc in self._window.get_documents():
			if os.path.splitext(doc.get_short_name_for_display())[1] == ".rtsc-proj":
				candidates.append(doc)
		if len(candidates) != 1:
			msg = ["You have %i RTSC projects open. You must have exactly one to perform this action." % len(candidates),
				"You must have an RTSC project open to perform this action."][len(candidates) == 0]
			self.error_dialog(msg)
			return
		return candidates[0]

	def get_text_from_doc(self, doc):
		return doc.get_text(doc.get_start_iter(), doc.get_end_iter())

	def parse_project(self):
		doc = self.get_rtsc_main_project()
		if doc == None:
			return
		text = self.get_text_from_doc(doc)
		parser = ConfigParser.SafeConfigParser()
		parser.readfp(StringIO.StringIO(text))
		# Sanity check!
		if not parser.has_section("config"):
			self.error_dialog("Project file %s has no section [config]\nConsider adding the line:\n\n[config]" % doc.get_short_name_for_display())
			return
		if not parser.has_option("config", "main_file"):
			self.error_dialog("Project file %s's [config] section has no main_file option." % doc.get_short_name_for_display())
			return
		result = { "doc" : doc, "config" : parser }
		result["dir"] = os.path.realpath(os.path.split(doc.get_uri_for_display())[0])
		return result

	def on_rtsc_check(self, action=None):
		self.on_rtsc_compile(go_all_the_way=False)

	def on_rtsc_compile(self, action=None, go_all_the_way=True, binary_timestamp=None, result=None):
		# Start by clearing the console.
		self.console.buf.set_text("")
		start = time.time()
		self.console.write("Reading project file... ")
		result = result or self.parse_project()
		if not result:
			self.console.write("error!\n")
			return
		main_file = result["config"].get("config", "main_file")
		end = time.time()
		self.console.write("done: %.2fs\n" % (end-start))
		start = time.time()
		self.console.write("Building... ")
		ctx = rtsc.Compiler()
		ctx.chdir(result["dir"])
		ctx.import_file(main_file)
		try:
			statements = ctx.churn()
			# Early out!
			if binary_timestamp != None and ctx.newest_source_time < binary_timestamp:
				self.console.write("no source newer than binary -- skipping.")
				return result
			ctx.build(statements)
			js = ctx.write_js()
		except rtsc.CompilationException, e:
			self.console.write("error!\n")
			self.console.write(e.message + "\n")
			return
		end = time.time()
		self.console.write("done: %.2fs\n" % (end-start))
		if not go_all_the_way:
			self.success_dialog("All syntax good.")
			return True
		start = time.time()
		self.console.write("Compiling... ")
		try:
			status, binary = compilation.remote_compile(js)
		except socket.error, e:
			self.console.write("error!\n")
			self.error_dialog("Remote YARC server not reachable.")
			return
		end = time.time()
		if status == "g":
			fd = open("Main", "w")
			fd.write(binary)
			fd.close()
			os.chmod("Main", 0755)
			self.console.write("done: %.2fs\n" % (end-start))
			self.console.write("Compiled to: %i KiB\n" % (len(binary)/1024))
			return result
		elif status == "e":
			fd = open("compilation_error.txt", "w")
			fd.write(binary.strip())
			fd.close()
			self.console.write("error!\n")
			self.error_dialog("Compilation crashed!\nError saved to compilation_error.txt")
		elif status == "f":
			self.console.write("remote server not running.\n")
			self.error_dialog("Remote compilation server not running.")
		else:
			self.console.write("internal error!\n")
			self.error_dialog("Unknown internal error status: %r" % ((status, binary),))

	def on_rtsc_run(self, action=None):
		result = self.parse_project()
		if not result:
			return
		binary_timestamp = None
		try:
			binary_timestamp = os.stat(os.path.join(result["dir"], "Main")).st_mtime
		except OSError, e:
			pass
		result = self.on_rtsc_compile(binary_timestamp=binary_timestamp, result=result)
		subprocess.Popen([os.path.join(result["dir"], "Main")], cwd=result["dir"], close_fds=True)

	def on_new_project(self, action=None):
		chooser = gtk.FileChooserDialog(title="New Project", action=gtk.FILE_CHOOSER_ACTION_SAVE,
			buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
		response = chooser.run()
		if response == gtk.RESPONSE_CANCEL:
			chooser.destroy()
			return
		path = chooser.get_filename()
		proj_name = os.path.split(path)[1]
		chooser.destroy()
		try:
			os.mkdir(path)
		except OSError, e:
			self.error_dialog("Couldn't create project.\n%s" % str(e))
		os.chdir(path)
		proj_file_path = "%s.rtsc-proj" % proj_name
		fd = open(proj_file_path, "w")
		fd.write("""[config]

main_file = main.rtsc

""")
		fd.close()
		fd = open("main.rtsc", "w")
		fd.write("# %s\n\n" % proj_name)
		fd.close()
		self._window.create_tab_from_uri("file://" + os.path.abspath(proj_file_path), None, 4, False, True)
		self._window.create_tab_from_uri("file://" + os.path.abspath("main.rtsc"), None, 3, False, False)
		return True

	def on_open_project(self, action=None):
		chooser = gtk.FileChooserDialog(title="Open Project", action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER,
			buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
		response = chooser.run()
		if response == gtk.RESPONSE_CANCEL:
			chooser.destroy()
			return
		path = chooser.get_filename()
		proj_name = os.path.split(path)[1]
		chooser.destroy()
		proj_file_paths = [ i for i in os.listdir(path) if i.endswith(".rtsc-proj") ]
		if len(proj_file_paths) == 0:
			self.error_dialog("Selected directory contains no .rtsc-proj file.")
			return
		if len(proj_file_paths) != 1:
			self.error_dialog("Selected directory contains multiple .rtsc-proj files!")
			return
		proj_file_path = proj_file_paths[0]
		new_tab = self._window.create_tab_from_uri("file://" + os.path.abspath(os.path.join(path, proj_file_path)), None, 0, False, True)
		doc = new_tab.get_document()
		self.to_disconnect.append((doc, doc.connect("loaded", self.open_project_files, new_tab.get_view())))

	def open_project_files(self, *args):
		result = self.parse_project()
		if not result:
			return
		main_source = result["config"].get("config", "main_file")
		os.chdir(result["dir"])
		self._window.create_tab_from_uri("file://" + os.path.abspath(main_source), None, 0, False, False)

	def on_rtsc_update(self, action=None):
		self.success_message("Already updated to the most recent version.")

	def on_version(self, action=None):
		msg = "Originally the \"RTS Compiler\"\nRTSC version: %i.%i\nGedit plugin version: %i.%i"
		self.success_dialog(msg % (plugin_version + rtsc.version))

	def guarantee_versioning(self):
		result = self.parse_project()
		if not result:
			return
		os.chdir(result["dir"])
		try:
			os.mkdir("versioning")
		except OSError, e:
			pass
		vers = os.listdir("versioning")
		result["max_version_num"] = int(max(vers)[1:]) if vers else 0
		result["last_version_path"] = os.path.join("versioning", max(vers)) if vers else None
		return result

	def on_diff(self, action=None, just_check=False):
		import difflib, filecmp, glob
		result = self.guarantee_versioning()
		if not result:
			return
		most_recent = result["last_version_path"]
		if most_recent == None:
			if just_check:
				result["does_differ"] = None
				return result
			self.error_dialog("No previous version to show differences from.")
			return
		dirdiff = filecmp.dircmp(".", result["last_version_path"], self.versioning_file_ignore_filter + glob.glob("*.bytes"))
		if just_check:
			result["does_differ"] = bool(dirdiff.diff_files or dirdiff.left_only or dirdiff.right_only)
			return result
		text = ""
		for path in dirdiff.left_only:
			text += "Deleted: " + path + "\n"
		for path in dirdiff.right_only:
			text += "New file:" + path + "\n"
		for path in dirdiff.diff_files:
			a_lines, b_lines = open(path).readlines(), open(os.path.join(result["last_version_path"], path)).readlines()
			text += "".join(difflib.unified_diff(b_lines, a_lines, fromfile="Previous %s" % path, tofile="Current  %s" % path))
		if self.diff_console == None:
			#bottom = self._window.get_bottom_panel()
			#bottom.remove_item(self.diff_console)
			self.diff_console = RTSCConsole()
			bottom = self._window.get_bottom_panel()
			bottom.add_item(self.diff_console, _('Differences'), gtk.STOCK_FILE)
		self.diff_console.buf.set_text(text or "No differences.")

	def on_save_commit(self, action=None):
		import shutil
		result = self.on_diff(just_check=True)
		if result["does_differ"] == False:
			self.error_dialog("No differences to commit.")
			return
		new_version = os.path.join("versioning", "v%06i" % (result["max_version_num"]+1))
		shutil.copytree(".", new_version, ignore=shutil.ignore_patterns("*.bytes", *self.versioning_file_ignore_filter))

	def on_view_history(self, action=None):
		pass

class RTSCConsole(gtk.ScrolledWindow):

	__gsignals__ = {
		'grab-focus' : 'override',
	}

	def __init__(self):
		gtk.ScrolledWindow.__init__(self)

		self.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
		self.set_shadow_type(gtk.SHADOW_IN)
		self.view = gtk.TextView()
		self.view.modify_font(pango.FontDescription('Monospace'))
		self.view.set_editable(False)
		self.view.set_wrap_mode(gtk.WRAP_WORD_CHAR)
		self.add(self.view)
		self.view.show()
		self.buf = self.view.get_buffer()

	def write(self, s):
		self.buf.insert(self.buf.get_end_iter(), s)

class RTSCPlugin(gedit.Plugin):
	def __init__(self):
		gedit.Plugin.__init__(self)
		self._instances = {}

	def activate(self, window):
		helper = self._instances[window] = RTSCWindowHelper(self, window)

	def deactivate(self, window):
		self._instances[window].deactivate()
		del self._instances[window]

	def update_ui(self, window):
		self._instances[window].update_ui()

