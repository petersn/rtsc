#! /usr/bin/python
# subprocess.check_output(["gmcs", "build/main.cs", "build/rtsc.cs"], stderr=subprocess.STDOUT)

import socket, subprocess, os, base64, array, struct
from PIL import Image
import rtscfs

flag_verbose = "RTSC_VERBOSE" in os.environ

local_dir = os.path.dirname(os.path.realpath(__file__))

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

def connect(channel, host="localhost", port=50002, timeout=None):
	sock = socket.create_connection((host, port), timeout)
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

def remote_channels(host, port, timeout=None):
	uuid = "RTSCRCS_" + os.urandom(32).encode("hex")
	sock, fd = connect(uuid, host, port, timeout=None)
	sock.send("rooms\n")
	rooms = fd.readline()[1:].split(":")[:-1]
	return [room[6:] for room in rooms if room.startswith("@RTSC_")]

def remote_compile(code, chan, host, port, target, timeout=None):
	uuid = "RTSCRCS_" + os.urandom(32).encode("hex")
	sock, fd = connect(uuid, host, port, timeout=timeout)
	sock.send("list:@RTSC_%s\n" % chan)
	if fd.readline() == "=\n":
		return "f", ""
	sock.send(":@RTSC_%s:%s,%s,%s\n" % (chan, uuid, target, escape(code)))
	datum = fd.readline()
	grab = "-%s:" % uuid
	assert datum.startswith(grab)
	datum = datum[len(grab):].strip()
	val, datum = datum.split(",", 1)
	datum = datum.decode("base64")
	return val, datum

def check_output(*args, **kwargs):
	sub = subprocess.Popen(*args, stdout=subprocess.PIPE, **kwargs)
	stdout, _ = sub.communicate()
	if sub.returncode != 0:
		exception = subprocess.CalledProcessError(sub.returncode, args[0])
		exception.output = stdout
		raise exception
	return stdout

read_file_cache = {}
def read_file(path):
	if path not in read_file_cache:
		fd = open(path)
		data = fd.read()
		fd.close()
		read_file_cache[path] = data
	return read_file_cache[path]

def byte_swap(s, bpp):
	s = array.array("B", s)
	for i in xrange(0, len(s), bpp):
		s[i], s[i+2] = s[i+2], s[i]
	return s.tostring()

RTSCFS_FLAG_BZ2 = 1<<0

def get_file_data(name, path, flags):
	if "::" in path:
		oper, path = path.split("::", 1)
		if oper == "none":
			return open(path).read()
		elif oper == "texture":
			img = Image.open(path)
			if img.mode in ("LA", "RGBA"):
				data_str = img.convert("RGBA").tostring()
				bpp = 4
			else:
				data_str = img.convert("RGB").tostring()
				bpp = 3
			# Convert RGB to BGR and RGBA to BGRA, as naively used by OpenGL.
			data_str = byte_swap(data_str, bpp)
			return "\x03TEX" + struct.pack("<IIB", img.size[0], img.size[1], bpp) + "\0\0\0" + data_str
		elif oper == "jpeg2k":
			pass
		else: assert False
	return open(path).read()

def quick_link(code, target="elf64", config=None):
	get_standard_header()
	import struct
	code = standard_header + code
	fs = {"js" : code}
	flags = {}
	if config != None:
		if config.has_section("files"):
			for name, value in config.items("files"):
				fs[name] = get_file_data(name, value, flags)
		if config.has_section("vars"):
			for name, value in config.items("vars"):
				fs[name] = value.strip()
	savings = 0
	# Optimize the filesystem.
	for name in fs:
		# Check if we can do better with bz2.
		bz2_data = struct.pack("<Q", len(fs[name])) + fs[name].encode("bz2")
		if len(bz2_data) < len(fs[name]):
			if flag_verbose:
				print "(%5.2f%%)" % (100.0 * len(bz2_data) / len(fs[name]),), "Using bz2 for", name
			flags[name] = RTSCFS_FLAG_BZ2
			savings += len(fs[name]) - len(bz2_data)
			fs[name] = bz2_data
	code = rtscfs.pack(fs, flags=flags)
	sizeof_lookup = { 1: "<B", 2: "<H", 4: "<I", 8: "<Q" }
	quick_links_root = os.path.join(local_dir, "quick_links", target)
	data   = read_file(quick_links_root+"_data")
	relocs = read_file(quick_links_root+"_relocs")
	symbols = { "fs_size" : len(code) }
	data = array.array("B", data)
	# Do some fixups -- pseudo-linking!
	for line in relocs.split("\n"):
		line = line.split("#")[0].strip()
		if not line: continue
		command = line.split(",")
		if command[0] == "add":
			addr, sizeof, symbol = command[1:]
			addr, sizeof, symbol = int(addr), int(sizeof), symbol.strip()
			format = sizeof_lookup[sizeof]
			current_value = sum(c*256**(i) for i, c in enumerate(data[addr:addr+sizeof]))
			current_value += symbols[symbol]
			current_value %= 256**sizeof
			data[addr:addr+sizeof] = array.array("B", struct.pack(format, current_value))
		elif command[0] == "nullpad":
			modulus = int(command[1])
			code += ("\0" * (-len(code)%modulus))
			symbols["fs_size"] = len(code)
		else: assert False, repr(command)
	data.extend(array.array("B", code))
	if flag_verbose and savings:
		print "Compressed to: %5.2f%%" % (100.0 * (len(data) - savings) / len(data),)
	# Round the binary off to the next 32-byte mark.
	data.extend(array.array("B", [0] * (-len(data)%32)))
	return "g", data.tostring()

header_write_time = -float("inf")
def get_standard_header():	
	global standard_header, header_write_time
	std_js_path = os.path.join(local_dir, "data", "std.js")
	newest = os.stat(std_js_path).st_mtime
	if newest > header_write_time:
		standard_header = open(std_js_path).read()
		header_write_time = newest

def local_compile(code):
	get_standard_header()
	write_fd = open("v8_base/code.js", "w")
	write_fd.write(standard_header)
	write_fd.write(code)
	write_fd.close()
	try:
		check_output(["objcopy", "--input", "binary", "--output", "elf64-x86-64",
			"--binary-architecture", "i386:x86-64", "code.js", "javascript.o"],
			stderr=subprocess.STDOUT, cwd="v8_base")
		check_output(["g++", "-o", "main", "launch.o", "opengl.o", "os.o", "javascript.o",
			"libs64/libv8_base.a", "libs64/libv8_snapshot.a", "-lpthread", "-lGLU", "-lSDL"],
			stderr=subprocess.STDOUT, cwd="v8_base")
		data = open("v8_base/main").read()
		return "g", data
	except subprocess.CalledProcessError, e:
		return "e", e.output

def capabilities():
	return ("elf64", "win32")

if __name__ == "__main__":
	import sys
	if sys.argv[1:] in ([], ["--help"]):
		print "Usage: %s file.js [files.js ...]\n       %s --server" % (sys.argv[0], sys.argv[0])
		print
		print "  --server -- Runs as a remote compilation server."
		print "  file.js  -- Compiles file.js into file using the remote server."
	elif sys.argv[1:] == ["--server"]:
		print "Connecting...",
		sys.stdout.flush()

		chan = "@RTSC_stockserv"

		sock, fd = connect(chan)

		print "done."

		grab = "-%s:" % chan

		while True:
			request = fd.readline()
			if not request.startswith(grab):
				continue
			request = request[len(grab):]
			request = unescape(request)
			address, target, code = request.split(",", 2)
			print "Got %i bytes from %r for %s." % (len(code), address, target)
#			result, data = local_compile(code)
			if target not in capabilities():
				result, data = "e", "No support for given arch: %r" % target
			else:
				result, data = quick_link(code, target=target)
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

