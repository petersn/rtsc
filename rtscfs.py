#! /usr/bin/python

import struct

RTSCFS_MAGIC = 0x3073666373747203
RTSCFS_FLAG_BZ2 = 1<<0

def pack(kv, initial_alignment=0, mod=16, flags={}):
	# Optimize the filesystem.
	for name in kv:
		# Check if we can do better with bz2.
		bz2_data = struct.pack("<Q", len(kv[name])) + kv[name].encode("bz2")
		if len(bz2_data) < len(kv[name]):
			flags[name] = flags.get(name, 0) | RTSCFS_FLAG_BZ2
			kv[name] = bz2_data
	# Now pack the optimized filesystem's header.
	ds = []
	ds.append(struct.pack("<3Q", RTSCFS_MAGIC, len(kv), 24))
	strings_pointer = 24 + 5*8*len(kv)
	data_pointer = strings_pointer + sum(map(len, kv))
	# Put the entries in.
	for key, value in kv.iteritems():
		data_pointer += -data_pointer % mod
		ds.append(struct.pack("<5Q", len(key), strings_pointer, len(value), data_pointer, flags.get(key, 0)))
		strings_pointer += len(key)
		data_pointer += len(value)
	# Put the key strings in.
	for key, value in kv.iteritems():
		ds.append(key)
	# Put the value strings in.
	alignment = initial_alignment + sum(map(len, ds))
	for key, value in kv.iteritems():
		ds.append("\0" * (-alignment % mod))
		alignment += len(ds[-1])
		ds.append(value)
		alignment += len(value)
	return "".join(ds)

def unpack(s):
	fs_magic, fs_count, fs_offset = struct.unpack("<3Q", s[:24])
	assert fs_magic == RTSCFS_MAGIC
	d = {}
	for i in xrange(fs_count):
		entry_name_size, entry_name_offset, entry_size, entry_offset, entry_flags = struct.unpack("<5Q", s[fs_offset:fs_offset+5*8])
		entry_name = s[entry_name_offset:entry_name_offset+entry_name_size]
		entry = s[entry_offset:entry_offset+entry_size]
		if entry_flags & RTSCFS_FLAG_BZ2:
			proper_length = struct.unpack("<Q", entry[:8])[0]
			entry = entry[8:].decode("bz2")
			if len(entry) != proper_length:
				print "Weirdly formed rtscfs image."
				print "BZ2 compressed entry reports decompressed length of:", proper_length
				print "But actually has length:", len(entry)
		d[entry_name] = entry
		fs_offset += 5*8
	return d

# Run as a program compressing/decompressing with directories.
if __name__ == "__main__":
	import sys, os
	if len(sys.argv) != 2:
		print "Usage: rtscfs.py directory"
		print "       rtscfs.py image.rtscfs"
		print
		print "In the first case, create an archive out of directory."
		print "In the second case, unpack the archive."
		exit(1)

	p = os.path.normpath(sys.argv[1])

	if not os.path.exists(p):
		print "error: path does not exist."

	if os.path.isdir(p):
		# Pack.
		print "Packing %(p)s to %(p)s.rtscfs." % locals()
		d = {}
		prefix = len(os.path.relpath(p))
		for dirpath, dirnames, filenames in os.walk(p):
			for path in filenames:
				key = (dirpath+"/"+path)[prefix+1:]
				fd = open(os.path.join(dirpath, path))
				d[key] = fd.read()
				fd.close()
		data = pack(d)
		fd = open(p+".rtscfs", "w")
		fd.write(data)
		fd.close()
	else:
		# Unpack.
		dest = os.path.splitext(os.path.normpath(p))[0]
		print "Unpacking to", dest
		fd = open(p)
		data = fd.read()
		fd.close()
		kv = unpack(data)
		def mkdirs(x):
			x = os.path.normpath(x)
			if os.path.exists(x):
				return
			mkdirs(os.path.dirname(x))
			os.mkdir(x)
		for k, v in kv.items():
			path = os.path.join(dest, *k.split("/"))
			print path
			mkdirs(os.path.dirname(path))
			fd = open(path, "wb")
			fd.write(v)
			fd.close()

