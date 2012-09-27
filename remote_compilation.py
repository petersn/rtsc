#! /usr/bin/python
# subprocess.check_output(["gmcs", "build/main.cs", "build/rtsc.cs"], stderr=subprocess.STDOUT)

import socket, subprocess, os, base64

class YARCSocket:
	def __init__(self, host="ubuntu.cba.mit.edu", port=50002, id_string="", channel=None, send=None):
		self._sock = self
		self.send = send
		self.sock = socket.socket()
		self.sock.connect((host, port))
		self.fd = self.sock.makefile()
		for s in ["login::\n", "id:%s\n" % id_string] + (["channel:%s\n" % channel] if channel != None else []):
			self.sock.send(s)
			self.yes()

	def yes(self):
		line = self.fd.readline()
		assert line == "yes\n", "Unexpected response: %r" % line

	def send(self, s):
		self.sock.send(":%s:%s\n" % (self.send, base64.b64encode(s)))

	def recv(self):
		line = self.fd.readline()
		return line.split(":", 1)[1].strip().decode("base64")

def escape(s):
	s = s.replace("\\", r"\b")
	s = s.replace("\n", r"\n")
	s = s.replace(":",  r"\a")
	return s

def unescape(s):
	s = s.replace(r"\a", ":")
	s = s.replace(r"\n", "\n")
	s = s.replace(r"\b", "\\")
	return s

def connect(channel, host="ubuntu.cba.mit.edu", port=50002, timeout=None):
	sock = socket.create_connection(("ubuntu.cba.mit.edu", 50002), timeout)
	fd = sock.makefile()
	def yes():
		assert fd.readline() == "yes\n"
	sock.send("login::\n")
	yes()
	sock.send("id:RTSC_Remote_Compilation\n")
	yes()
	sock.send("channel:%s\n" % channel)
	yes()
	return sock, fd

def remote_compile(code, timeout=None):
	uuid = "RTSCRCS_" + os.urandom(32).encode("hex")
	sock, fd = connect(uuid, timeout=timeout)
	sock.send("list:RTSCRCS\n")
	if fd.readline() == "=\n":
		return "f", ""
	sock.send(":RTSCRCS:%s,%s\n" % (uuid, escape(code)))
	datum = fd.readline()
	grab = "-%s:" % uuid
	assert datum.startswith(grab)
	datum = datum[len(grab):].strip()
	val, datum = datum.split(",", 1)
	datum = datum.decode("base64")
	return val, datum

def local_compile(code):
	write_fd = open("v8_base/code.js", "w")
	write_fd.write(code)
	write_fd.close()
	try:
		subprocess.check_output(["objcopy", "--input", "binary", "--output", "elf64-x86-64",
			"--binary-architecture", "i386:x86-64", "v8_base/code.js", "javascript.o"],
			stderr=subprocess.STDOUT)
		subprocess.check_output(["g++", "-o", "v8_base/main", "v8_base/launch.o", "v8_base/javascript.o",
			"v8_base/libs/libv8_base.a", "v8_base/libs/libv8_snapshot.a", "-lpthread"],
			stderr=subprocess.STDOUT)
		data = open("v8_base/main").read()
		return "g", data
	except subprocess.CalledProcessError, e:
		return "e", e.output

if __name__ == "__main__":
	import sys
	if sys.argv[1:] in ([], ["--help"]):
		print "Usage: %s file.cs [files.cs ...]\n       %s --server" % (sys.argv[0], sys.argv[0])
		print
		print "  --server -- Runs as a remote compilation server."
		print "  file.cs  -- Compiles file.cs into file.exe using the remote server."
	elif sys.argv[1:] == ["--server"]:
		print "Connecting...",
		sys.stdout.flush()

		sock, fd = connect("RTSCRCS")

		print "done."

		grab = "-RTSCRCS:"

		while True:
			request = fd.readline()
			if not request.startswith(grab):
				continue
			request = request[len(grab):]
			request = unescape(request)
			address, code = request.split(",", 1)
			print "Got %i bytes from %r." % (len(code), address)
			result, data = local_compile(code)
			if result == "g":
				print "Compiled to %i bytes." % (len(data),)
			else:
				print "Sent %i lines of error output." % (data.count("\n"),)
			sock.send(":%s:%s,%s\n" % (address, result, data.encode("base64").replace("\n", "")))
	else:
		for path in sys.argv[1:]:
			code = open(path).read()
			ret, bin = remote_compile(code)
			if ret == "g":
				bin_path = os.path.splitext(path)[0]
				if bin_path == path:
					bin_path += ".elf"
				print "Success: %i bytes of binary into %r." % (len(bin), bin_path)
				fd = open(bin_path, "w")
				fd.write(bin)
				fd.close()
				os.chmod(bin_path, 0755)
			elif ret == "e":
				print "Error:"
				print bin.strip()
				exit(1)
			elif ret == "f":
				print "Remote compilation server not running."

