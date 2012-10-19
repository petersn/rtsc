#! /usr/bin/python
# objcopy --input binary --output elf64-x86-64 --binary-architecture i386:x86-64 --rename-section .data=.unicorns code.js javascript.o
# g++ -o prod launch.o opengl.o os.o javascript.o libs64/libv8_base.a libs64/libv8_snapshot.a -lpthread -lGLU -lSDL

import struct, pprint

half, word = "H", "I"
xword = addr = off = "Q"
elf_header_format = [
	("e_ident", "16s"),
	("e_type", half),
	("e_machine", half),
	("e_version", word),
	("e_entry", addr),
	("e_phoff", off),
	("e_shoff", off),
	("e_flags", word),
	("e_ehsize", half),
	("e_phentsize", half),
	("e_phnum", half),
	("e_shentsize", half),
	("e_shnum", half),
	("e_shstrndx", half),
]

program_header_format = [
	("p_type", word),
	("p_flags", word),
	("p_offset", off),
	("p_vaddr", addr),
	("p_paddr", addr),
	("p_filesz", xword),
	("p_memsz", xword),
	("p_align", xword),
]

section_header_format = [
	("sh_name", word),
	("sh_type", word),
	("sh_flags", xword),
	("sh_addr", addr),
	("sh_offset", off),
	("sh_size", xword),
	("sh_link", word),
	("sh_info", word),
	("sh_addralign", xword),
	("sh_entsize", xword),
]

symbol_entry_format = [
	("st_name", word),
	("st_info", "B"),
	("st_other", "B"),
	("st_shndx", half),
	("st_value", addr),
	("st_size", xword),
]

def format_size(fields):
	format = "<" + "".join(i[1] for i in fields)
	return struct.calcsize(format)

def parse(fields, data):
	format = "<" + "".join(i[1] for i in fields)
	header = struct.unpack(format, data[:struct.calcsize(format)])
	return dict(zip((i[0] for i in fields), header))

patches = []

def write_back(fields, d):
	addr = d["OFFSET"]
	for name, fmt in fields:
		sizeof = struct.calcsize(fmt)
		patches.append( (addr, addr+sizeof, struct.pack(fmt, d[name])) )
		addr += sizeof

def read_str(data, index):
	i = index
	while data[i] != "\0": i += 1
	return data[index:i]

data = open("prod").read()
header = parse(elf_header_format, data)
pprint.pprint(header)
addr = header["e_shoff"]
section_headers = []
for i in xrange(header["e_shnum"]):
	section = parse(section_header_format, data[addr:])
	section["OFFSET"] = addr
	section_headers.append(section)
	addr += header["e_shentsize"]

addr = header["e_phoff"]
program_headers = []
for i in xrange(header["e_phnum"]):
	program = parse(program_header_format, data[addr:])
	program["OFFSET"] = addr
	program_headers.append(program)
	addr += header["e_phentsize"]

section_strings_base = data[section_headers[header["e_shstrndx"]]["sh_offset"]:]

for section in section_headers:
	section["sh_name"] = read_str(section_strings_base, section["sh_name"])
	if section["sh_name"] == ".strtab":
		strings_base = data[section["sh_offset"]:]

padding = -len(data)%32
print "Padding with", padding, "null bytes."
data += "\0" * padding
end_of_binary_addr = struct.pack("<Q", len(data))

locs = []

reasonable_vma = 0

#NOTUSED
# Find a reasonable VMA to dump to.
for header in program_headers:
	max_hit = header["p_vaddr"] + header["p_memsz"]
	reasonable_vma = max(max_hit, reasonable_vma)

for section in section_headers:
	if section["sh_name"] == ".unicorns":
		print "Found .unicorns section."
		offset, size = section["sh_offset"], section["sh_size"]
		addr = section["OFFSET"]
		# Compute the ELF load offset.
		elf_load_offset = section["sh_addr"] - offset
		print "ELF load offset:", hex(elf_load_offset)
		# Don't edit this section of the ELF!
		# It appears to only be link-time information, and doesn't do what we need.
#		patches.append( (addr+24, addr+24+8, end_of_binary_addr) )
#		patches.append( (addr+32, addr+32+8, "\0"*8) )
#		patch_address = addr+32
		pprint.pprint(section)
#		data[offset]
		#print repr(data[offset:offset+size])
	# Find the section with type SHT_SYMTAB.

# Round the VMA up to have the appropriate offset.
reasonable_vma = len(data) + elf_load_offset

print "Reasonable VMA:", hex(reasonable_vma)

for section in section_headers:
	if section["sh_type"] == 2:
		addr = section["sh_offset"]
		fs = format_size(symbol_entry_format)
		while addr < section["sh_offset"] + section["sh_size"]:
			entry = parse(symbol_entry_format, data[addr:])
			entry["st_name"] = read_str(strings_base, entry["st_name"])
			if entry["st_name"] in ("_binary_code_js_start", "_binary_code_js_end"):
#				patches.append( (addr+8, addr+8+8, end_of_binary_addr) )
				if entry["st_name"] == "_binary_code_js_start":
					pointer_target = entry["st_value"]
					file_offset = entry["st_value"] - elf_load_offset
					patches.append( (file_offset, file_offset+8, struct.pack("<Q", reasonable_vma)) )
					#patches.append( (file_offset+8, file_offset+16, "\0"*8) )
					locs.append(file_offset+8)
#				if entry["st_name"] == "_binary_code_js_end":
#					add_length = addr+8
				print "Found symbol to patch."
				pprint.pprint(entry)
			addr += fs

PT_LOAD  = 1
PT_RELRO = 0x6474e552

for header in program_headers:
	if header["p_type"] == PT_RELRO:
		print "Found program header to mangle:"
		pprint.pprint(header)
		header["p_align"] = 2**3
		header["p_flags"] = 6
		header["p_type"] = PT_LOAD
		header["p_memsz"] = 0
		header["p_offset"] = len(data)
		header["p_vaddr"] = header["p_paddr"] = reasonable_vma
		header["p_filesz"] = 0
#		shy = hex(len(data) - (header["p_filesz"] + header["p_offset"]))
#		print "eof %s - (offset %s + size %s) = %s" % (hex(len(data)), hex(header["p_offset"]), hex(header["p_filesz"]), shy)
#		patches.append( (header["OFFSET"]+32, header["OFFSET"]+40, struct.pack("<Q", len(data) - header["p_offset"])) )
#		patches.append( (header["OFFSET"]+40, header["OFFSET"]+48, struct.pack("<Q", len(data) - header["p_offset"])) )
		locs.append(header["OFFSET"]+32)
		locs.append(header["OFFSET"]+40)
		print "Newly mangled:"
		pprint.pprint(header)
		write_back(program_header_format, header)

# Patch-up the binary.
print "Patching up."
data = list(data)
for start, stop, new in patches:
	previous = "".join(data[start:stop])
#	print "Instances:", "".join(data).count(previous)
	print "\t[%08x:%08x] (%r) = %r" % (start, stop, previous.encode("hex"), new.encode("hex"))
	assert len(new) == stop - start
	data[start:stop] = list(new)
data = "".join(data)

fd = open("../quick_links/elf64_data", "w")
fd.write(data)
fd.close()

fd = open("../quick_links/elf64_relocs", "w")
for loc in locs:
	print "Adding relocation at:", hex(loc)
	fd.write("%s,8,js_size\n" % loc)
#fd.write("%s,8,js_size\n" % (add_length,))
fd.close()

