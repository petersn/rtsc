#! /usr/bin/python
# Produces a quick_links executable.

import struct, pprint

# Magic colored text constants
normal = "\x1B\x5B\x30\x6D"
grey   = "\x1B\x5B\x30\x31\x3B\x33\x30\x6D"
red    = "\x1B\x5B\x30\x31\x3B\x33\x31\x6D"
green  = "\x1B\x5B\x30\x31\x3B\x33\x32\x6D"
yellow = "\x1B\x5B\x30\x31\x3B\x33\x33\x6D"
blue   = "\x1B\x5B\x30\x31\x3B\x33\x34\x6D"
purple = "\x1B\x5B\x30\x31\x3B\x33\x35\x6D"
teal   = "\x1B\x5B\x30\x31\x3B\x33\x36\x6D"

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

# Read in our ELF binary.
data = open("elf64_base").read()
header = parse(elf_header_format, data)
print green + "ELF header:" + normal
pprint.pprint(header)

# Read in the section header table.
addr = header["e_shoff"]
section_headers = []
for i in xrange(header["e_shnum"]):
	section = parse(section_header_format, data[addr:])
	section["OFFSET"] = addr
	section_headers.append(section)
	addr += header["e_shentsize"]

# Read in the program header table.
addr = header["e_phoff"]
program_headers = []
for i in xrange(header["e_phnum"]):
	program = parse(program_header_format, data[addr:])
	program["OFFSET"] = addr
	program_headers.append(program)
	addr += header["e_phentsize"]

# Figure out where section names are.
section_strings_base = data[section_headers[header["e_shstrndx"]]["sh_offset"]:]

# Figure out where symbol names are.
for section in section_headers:
	section["sh_name"] = read_str(section_strings_base, section["sh_name"])
	if section["sh_name"] == ".strtab":
		strings_base = data[section["sh_offset"]:]

# Pad the binary out to a multiple of 32 bytes.
padding = -len(data)%32
print green + "Padding binary out to multiple of 32 with null bytes:" + normal, padding
data += "\0" * padding

# These are places where the length of the Javascript program has to be added.
relocation_addresses = []

# Find the difference between 
for section in section_headers:
	if section["sh_name"] == ".unicorn":
		print green + "Found .unicorn section." + normal
		offset, size = section["sh_offset"], section["sh_size"]
		addr = section["OFFSET"]
		# Compute the ELF load offset.
		elf_load_offset = section["sh_addr"] - offset
		print green + "ELF load offset:" + normal, hex(elf_load_offset)
		# Don't edit this section of the ELF!
		# It appears to only be link-time information, and doesn't do what we need.
		pprint.pprint(section)

# The address at which the Javascript program will be loaded.
javascript_load_vma = len(data) + elf_load_offset

print green + "Javascript load VMA:" + normal, hex(javascript_load_vma)

SHT_SYMTAB = 2

# Find the symbol table (SYMTAB) section to modify the .unicorn pointer, _binary_code_js_start.
for section in section_headers:
	if section["sh_type"] == SHT_SYMTAB:
		addr = section["sh_offset"]
		fs = format_size(symbol_entry_format)
		# Read through the symbol tale.
		while addr < section["sh_offset"] + section["sh_size"]:
			entry = parse(symbol_entry_format, data[addr:])
			entry["st_name"] = read_str(strings_base, entry["st_name"])
			if entry["st_name"] == "_binary_code_js_start":
				print green + "Found symbol to edit:" + normal
				pprint.pprint(entry)
				pointer_target = entry["st_value"]
				file_offset = entry["st_value"] - elf_load_offset
				patches.append( (file_offset, file_offset+8, struct.pack("<Q", javascript_load_vma)) )
				patches.append( (file_offset+8, file_offset+16, "\0"*8) )
				relocation_addresses.append(file_offset+8)
				break
			addr += fs

PT_LOAD  = 1
PT_RELRO = 0x6474e552

# Hack the RELRO program header table entry into a PT_LOAD entry that loads our desired
for header in program_headers:
	if header["p_type"] == PT_RELRO:
		print green + "Found program header to mangle:" + normal
		pprint.pprint(header)
		header["p_align"] = 2**3
		header["p_flags"] = 6 # rw-
		header["p_type"] = PT_LOAD
		header["p_memsz"] = 0
		header["p_offset"] = len(data)
		header["p_vaddr"] = header["p_paddr"] = javascript_load_vma
		header["p_filesz"] = 0
		relocation_addresses.append(header["OFFSET"]+32) # 
		relocation_addresses.append(header["OFFSET"]+40)
		print green + "Newly mangled:" + normal
		pprint.pprint(header)
		write_back(program_header_format, header)

# Patch-up the binary.

print
print green + "Binary patches:" + normal
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

print
print green + "Binary relocations:" + normal

fd = open("../quick_links/elf64_relocs", "w")
for loc in relocation_addresses:
	print "\t[%08x:%08x] += fs_size" % (loc, loc+8)
	fd.write("add,%s,8,fs_size\n" % loc)
#fd.write("%s,8,js_size\n" % (add_length,))
fd.close()

