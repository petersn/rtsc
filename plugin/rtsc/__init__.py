#! /usr/bin/python

import os, ConfigParser, StringIO, subprocess, time, socket
from gettext import gettext as _

import gtk
import gedit
import pango
from rtsc import rtsc
from rtsc import compilation

ui_str = """
<ui>
	<menubar name="MenuBar">
		<menu name="FileMenu" action="File">
			<placeholder name="FileOps_2">
				<menuitem name="RTSC_Helper_NewProject" action="RTSC_Helper_NewProject"/>
				<menuitem name="RTSC_Helper_OpenProject" action="RTSC_Helper_OpenProject"/>
			</placeholder>
		</menu>
		<menu name="RTSCMenu" action="RTSC">
			<menuitem name="RTSC_Syntax_Check" action="RTSC_Syntax_Check"/>
			<menuitem name="RTSC_Compile" action="RTSC_Compile"/>
			<menuitem name="RTSC_Run" action="RTSC_Run"/>
			<separator/>
			<menu name="RTSCHelpersMenu" action="RTSCHelpers">
				
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
	def __init__(self, plugin, window):
		self._window = window
		self._plugin = plugin

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
		add(('RTSCHelpers', None, _('RTSC Helpers'), None, _("RTSC code-writing helpers"), None))

		# Add various commands.
		add(("RTSC_Syntax_Check", None, _("Check RTSC"), None, _("Check RTSC project for syntax errors"), self.on_rtsc_check))
		add(("RTSC_Compile", None, _("Compile RTSC"), None, _("Force recompile the current project"), self.on_rtsc_compile))
		add(("RTSC_Run", None, _("Run RTSC"), None, _("Compile (if needed) and run the current project"), self.on_rtsc_run))

		add(("RTSC_Helper_NewProject", None, _("New RTSC Project"), None, _("Make a new project"), self.on_new_project))
		add(("RTSC_Helper_OpenProject", None, _("Open RTSC Project"), None, _("Open an existing project"), self.on_open_project))

		# Insert the action group
		manager.insert_action_group(self._action_group, -1)

		# Merge the UI
		self._ui_id = manager.add_ui_from_string(ui_str)

		# Insert the bottom panel console
		self.console = RTSCConsole()
		bottom = self._window.get_bottom_panel()
		bottom.add_item(self.console, _('Compilation Console'), gtk.STOCK_EXECUTE)

		manager.ensure_update()

	def _remove_menu(self):
		# Get the GtkUIManager
		manager = self._window.get_ui_manager()

		# Remove the ui
		manager.remove_ui(self._ui_id)

		# Remove the action group
		manager.remove_action_group(self._action_group)

		# Make sure the manager updates
		manager.ensure_update()

		# Remove the bottom panel console
		bottom = self._window.get_bottom_panel()
		bottom.remove_item(self.console)

	def update_ui(self):
		self._action_group.set_sensitive(self._window.get_active_document() != None)

	def error_dialog(self, msg):
		dlg = gtk.MessageDialog(self._window, gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE, msg)
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
		pass

	def on_rtsc_compile(self, action=None):
		# Start by clearing the console.
		self.console.buf.set_text("")
		start = time.time()
		self.console.write("Reading project file... ")
		result = self.parse_project()
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
			ctx.build(statements)
			js = ctx.write_js()
		except rtsc.CompilationException, e:
			self.console.write("error!\n")
			self.console.write(e.message + "\n")
			return
		end = time.time()
		self.console.write("done: %.2fs\n" % (end-start))
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
		result = self.on_rtsc_compile()
		if not result:
			return
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
		new_tab.get_document().connect("loaded", self.open_project_files, new_tab.get_view())

	def open_project_files(self, *args):
		result = self.parse_project()
		if not result:
			return
		main_source = result["config"].get("config", "main_file")
		os.chdir(result["dir"])
		self._window.create_tab_from_uri("file://" + os.path.abspath(main_source), None, 0, False, False)

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

