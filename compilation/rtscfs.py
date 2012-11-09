#! /usr/bin/python

import struct

def pack(kv, initial_alignment=0, mod=16, flags={}):
	ds = []
	ds.append(struct.pack("<2Q", len(kv), 16))
	strings_pointer = 16 + 5*8*len(kv)
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
	fs_count, fs_offset = struct.unpack("<2Q", s[:16])
	d = {}
	for i in xrange(fs_count):
		entry_name_size, entry_name_offset, entry_size, entry_offset, entry_flags = struct.unpack("<5Q", s[fs_offset:fs_offset+5*8])
		entry_name = s[entry_name_offset:entry_name_offset+entry_name_size]
		entry = s[entry_offset:entry_offset+entry_size]
		d[entry_name] = entry
		fs_offset += 5*8
	return d

