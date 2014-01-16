#! /usr/bin/python

import os, socket, ssl, httplib, urllib2, json, StringIO, zipfile, hashlib
import rtsc_config

base_fetch_path = rtsc_config.global_config["settings"]["updater_url"]
global_cert_file = rtsc_config.fixup_path(rtsc_config.global_config["settings"]["updater_cert_path"])

# The following urllib code based on Eli Courtwright's http://stackoverflow.com/a/3551700/372643

class HTTPSConnection(httplib.HTTPConnection):
	def connect(self):
		sock = socket.create_connection((self.host, self.port))
		self.sock = ssl.wrap_socket(sock, ssl_version=ssl.PROTOCOL_TLSv1, ca_certs=global_cert_file, cert_reqs=ssl.CERT_REQUIRED)

class HTTPSHandler(urllib2.HTTPSHandler):
	def https_open(self, req):
		return self.do_open(HTTPSConnection, req)

ssl_opener = urllib2.build_opener(HTTPSHandler())

def get(path, relative=""):
	# Allow plain http at this point.
	# This is okay, because there's only one case where we might load an absolute path with a new domain: when loading zip files for actions.
	# However, in this case we have an authenticated hash to match, so it's okay.
	if path.startswith("https://") or path.startswith("http://"):
		pass
	elif path.startswith("/"):
		path = base_fetch_path + path[1:]
	else:
		path = base_fetch_path + relative + path
	print "Fetching", path
	return ssl_opener.open(path).read()

class Action:
	def __init__(self, parent, index):
		self.parent, self.index = parent, index
		self.data = self.parent.data["actions"][index]

	def perform(self):
		data = get(self.data["url"], relative=self.parent.base_path)
		print "Got", len(data), "bytes of zip archive."
		digest = hashlib.sha256(data).hexdigest()
		print "sha256(archive) =", digest
		# Verify the hash for security, in case the fetch was cross-domain.
		if self.data["sha256"] != "*" and digest != self.data["sha256"]:
			print "Error: Downloaded archive doesn't match SHA256 digest from repository."
			print "Was:   ", digest
			print "Wanted:", self.data["sha256"]
			raise ValueError("downloaded archive doesn't match sha256 digest")
		fd = StringIO.StringIO(data)
		with zipfile.ZipFile(fd) as zf:
			# Verify that the archive is not a zip bomb.
			prefixes = [i.split("/")[0] for i in zf.namelist()]
			assert prefixes[0] is not None and all(i == prefixes[0] for i in prefixes)
			prefix = prefixes[0]
			core = json.loads(zf.read(prefix+"/"+"core.json"))
			# Sanity check the archive.
			if core["version"] != self.parent.data["version"]:
				print "Error: Downloaded archive is for different RTSC version."
				print "Archive is for %s, but we're %s." % (core["version"], self.parent.data["version"])
				raise ValueError("downloaded archive for wrong RTSC version")
			if core["name"] != self.data["name"]:
				print "Error: Downloaded archive is wrong action."
				print "Was:   ", repr(core["name"])
				print "Wanted:", repr(self.data["name"])
				raise ValueError("downloaded archive is wrong action")
			# Finally, execute the python code in the archive.
			python_code = zf.read(prefix+"/"+"main.py")
			print "Executing: \"%s\"" % core["name"]
			exec python_code in globals(), locals()

class UpdateInspector:
	def __init__(self, version=None):
		# self.version = version or __import__("rtsc").version <-- overly cute, breaks dep scanners.
		if version is None:
			import rtsc
			self.version = rtsc.version
		self.base_path = "api/%i.%i/" % self.version
		self.data = json.loads(get(self.base_path + "options.json"))
		self.actions = [Action(self, i) for i in xrange(len(self.data["actions"]))]

def file_size_words(bytes):
	if bytes < 2**10:
		return "%i bytes" % bytes
	if bytes < 2**10*10:
		return "%.1f KiB" % (bytes/1024.0)
	if bytes < 2**20:
		return "%i KiB" % (bytes/1024)
	if bytes < 2**20*10:
		return "%.2f MiB" % (bytes/2**20.0)
	return "%i MiB" % (bytes/(2**20))

import wx

class ProgressFrame(wx.Frame):
	def __init__(self, action):
		self.action = action
		wx.Frame.__init__(self, None, -1, "Action Progress", wx.DefaultPosition, wx.Size(900, 600))
		small_font = wx.Font(12, wx.MODERN, wx.NORMAL, wx.BOLD)
		sizer = wx.BoxSizer(wx.VERTICAL)
		self.text = wx.TextCtrl(self, -1, style=wx.TE_MULTILINE)
		self.text.SetFont(small_font)
		self.text.SetEditable(False)
		sizer.Add(self.text, 1, wx.EXPAND)
		self.SetSizer(sizer)

	def launch(self):
		import thread
		# Let's be pedantic and have no race conditions, however small.
		lock = thread.allocate_lock()
		lock.acquire()
		def _work_thread():
			import sys
			self.io_buffer = sys.stdout = StringIO.StringIO()
			lock.release()
			self.action.perform()
		thread.start_new_thread(_work_thread, ())
		lock.acquire()
		self.text_value = None
		self.update_text()

	def update_text(self):
		new_value = self.io_buffer.getvalue()
		# Check if it's changed just because SetValue does GUI stuff we don't want to do 10 times per second otherwise.
		if new_value != self.text_value:
			self.text.SetValue(new_value)
			self.text_value = new_value
		wx.CallLater(100, self.update_text)

class UpdaterFrame(wx.Frame):
	def __init__(self):
		wx.Frame.__init__(self, None, -1, "RTSC Updater", wx.DefaultPosition, wx.Size(300, 500))
		small_font = wx.Font(12, wx.MODERN, wx.NORMAL, wx.BOLD)

		def t(s):
			st = wx.StaticText(self, -1, s)
			st.SetFont(small_font)
			return st

		menubar = wx.MenuBar()
		filemenu = wx.Menu()
		quit = wx.MenuItem(filemenu, 100, '&Quit\tCtrl+Q', 'Quit Updater')
		self.Bind(wx.EVT_MENU, lambda e: self.Close(), id=100)
		filemenu.AppendItem(quit)
		menubar.Append(filemenu, '&File')
		self.SetMenuBar(menubar)

		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(t("Action:"))
		self.combo = wx.ComboBox(self, -1, choices=[], style=wx.CB_READONLY)
		sizer.Add(self.combo, 0, wx.EXPAND)
		sizer.Add(t("Details:"))
		self.text = wx.TextCtrl(self, -1, style=wx.TE_MULTILINE)
		self.text.SetFont(small_font)
		self.text.SetEditable(False)
		self.text.SetValue("Downloading package index...")
		sizer.Add(self.text, 1, wx.EXPAND)
		self.go_button = wx.Button(self, -1, "Perform Action")
		sizer.Add(self.go_button, 0, wx.EXPAND)
		self.go_button.Bind(wx.EVT_BUTTON, self.OnPerformAction)
		self.SetSizer(sizer)

		self.combo.Bind(wx.EVT_COMBOBOX, self.OnPickAction)
		self.selected_index = None

		import thread
		thread.start_new_thread(self.download_index, ())

	def download_index(self):
		try:
			self.inspector = UpdateInspector()
		except (urllib2.URLError, urllib2.HTTPError):
			wx.CallAfter(lambda: \
				self.text.SetValue("Downloading package index... failed\nTry manually updating from http://rtsc.mit.edu/"))
		else:
			def _():
				self.combo.SetItems([action.data["name"] for action in self.inspector.actions])
				self.text.SetValue("Downloading package index... success\nGot %i actions." % len(self.inspector.actions))
			wx.CallAfter(_)

	def OnPickAction(self, e):
		self.selected_index = e.GetSelection()
		action = self.inspector.actions[self.selected_index]
		s = "Download size: %s\n%s" % (file_size_words(action.data["size"]), action.data["desc"])
		self.text.SetValue(s)

	def OnPerformAction(self, e):
		if self.selected_index is None:
			return
		action = self.inspector.actions[self.selected_index]
		dlg = wx.MessageDialog(None, "Perform action \"%s\"?" % action.data["name"], "Action", wx.YES_NO | wx.ICON_WARNING)
		do = dlg.ShowModal() == wx.ID_YES
		dlg.Destroy()
		if do:
			new_frame = ProgressFrame(action)
			new_frame.Show(True)
			new_frame.launch()
			self.Close()

class UpdaterApp(wx.App):
	def OnInit(self):
		frame = UpdaterFrame()
		frame.Show(True)
		return True

if __name__ == "__main__":
	app = UpdaterApp(0)
	app.MainLoop()

