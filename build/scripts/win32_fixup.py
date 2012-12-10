#! /usr/bin/python
# Operates on win32_base.exe.

from collections import OrderedDict
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
pe_header_format = [
	("Machine", half),
	("NumberOfSections", half),
	("TimeDateStamp", word),
	("PointerToSymbolTable", word),
	("NumberOfSymbols", word),
	("SizeOfOptionalHeader", half),
	("Characteristics", half),
	# Begin optional header.
	("Magic", half),
	("MajorLinkerVersion", "B"),
	("MinorLinkerVersion", "B"),
	("SizeOfCode", word),
	("SizeOfInitializedData", word),
	("SizeOfUninitializedData", word),
	("AddressOfEntryPoint", word),
	("BaseOfCode", word),
	("BaseOfData", word),
	("ImageBase", word),
	("SectionAlignment", word),
	("FileAlignment", word),
	("MajorOperatingSystemVersion", half),
	("MinorOperatingSystemVersion", half),
	("MajorImageVersion", half),
	("MinorImageVersion", half),
	("MajorSubsystemVersion", half),
	("MinorSubsystemVersion", half),
	("Reserved", word),
	("SizeOfImage", word),
	("SizeOfHeaders", word),
	("CheckSum", word),
	("Subsystem", half),
	("DLLCharacteristics", half),
	("SizeOfStackReserve", word),
	("SizeOfStackCommit", word),
	("SizeOfHeapReserve", word),
	("SizeOfHeapCommit", word),
	("LoaderFlags", word),
	("NumberOfRvaAndSizes", word),
]

pe_section_header_format = [
	("Name", "8s"),
	("VirtualSize", word),
	("VirtualAddress", word),
	("SizeOfRawData", word),
	("PointerToRawData", word),
	("PointerToRelocations", word),
	("PointerToLinenumbers", word),
	("NumberOfRelocations", half),
	("NumberOfLinenumbers", half),
	("Characteristics", word),
]

def format_size(fields):
	format = "<" + "".join(i[1] for i in fields)
	return struct.calcsize(format)

def parse(fields, data):
	format = "<" + "".join(i[1] for i in fields)
	header = struct.unpack(format, data[:struct.calcsize(format)])
	return OrderedDict(zip((i[0] for i in fields), header))

patches = []
relocation_addresses = []

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

# Read in our PE binary.
data = open("win32_base.exe").read()

padding = -len(data)%4096
print green + "Padding binary out to multiple of 4096 with null bytes:" + normal, padding
data += "\0" * padding

# Read the main PE header.
header_start = data.index("PE\0\0")+4
print green + "PE section header + optional header:" + normal, hex(header_start)
header = parse(pe_header_format, data[header_start:])
header["OFFSET"] = header_start
pprint.pprint(header.items())

main_pe_load_offset = header["ImageBase"]
javascript_load_vma = main_pe_load_offset + header["SizeOfImage"] # Load after everything else.
relocation_addresses.append(header_start+8+20) # Add fs length into SizeOfInitializedData.
relocation_addresses.append(header_start+56+20) # Add fs length into SizeOfImage.

# Relink the .ponies section.

header_start = data.index(".ponies")
print green + "PE section header (.ponies):" + normal, hex(header_start)
header = parse(pe_section_header_format, data[header_start:])
header["OFFSET"] = header_start
pprint.pprint(header.items())
# For some reason the Characteristics entry is set to 0xc0300040, which is READ, WRITE, INITIALIZED, and ALIGN4.
# The spec from microsoft says that you can only set ALIGN4 on object files. Oh well.

header["VirtualSize"] = 0; relocation_addresses.append(header["OFFSET"]+8)
header["VirtualAddress"] = javascript_load_vma - main_pe_load_offset
header["SizeOfRawData"] = 0; relocation_addresses.append(header["OFFSET"]+16)
header["PointerToRawData"] = len(data)
write_back(pe_section_header_format, header)

#write_back(pe_section_header_format, header)

# Relink the .unicorns section data.

header_start = data.index(".unicorn")
print green + "PE section header (.unicorn):" + normal, hex(header_start)
header = parse(pe_section_header_format, data[header_start:])
pprint.pprint(header.items())
file_offset = header["PointerToRawData"]
patches.append( (file_offset, file_offset+8, struct.pack("<Q", javascript_load_vma)) )
patches.append( (file_offset+8, file_offset+16, "\0"*8) )
relocation_addresses.append(file_offset+8)

print
print green + "Binary patches:" + normal
data = list(data)
for start, stop, new in patches:
	previous = "".join(data[start:stop])
	print "\t[%08x:%08x] (%r) = %r" % (start, stop, previous.encode("hex"), new.encode("hex"))
	assert len(new) == stop - start
	data[start:stop] = list(new)
data = "".join(data)

fd = open("../quick_links/win32_data", "w")
fd.write(data)
fd.close()

print
print green + "Binary relocations:" + normal

fd = open("../quick_links/win32_relocs", "w")
fd.write("nullpad,4096\n")
for loc in relocation_addresses:
	print "\t[%08x:%08x] += fs_size" % (loc, loc+4)
	fd.write("add,%s,4,fs_size\n" % loc)
fd.close()

