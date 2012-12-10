# Makefile for RTSC quick-links binaries.

CPPFLAGS = -g -O3 -Wall -Iinclude `sdl-config --cflags`

# To cross-compile for Windows, set MINGW_CXX to your MinGW g++.
# Or set the environment variable appropriately.
WIN32_CXX = i586-mingw32msvc-g++
WIN32_CPPFLAGS = -Iinclude/win32

# Under Linux this seems to be needed to prevent the .unicorn section from being completely emptied.
STRIP_ARGS = --keep-symbol=fs_image_vma_pointer

OBJECTS = launch.o rtscfs.o os.o opengl.o

help:
	@echo RTSC quick-links makefile.
	@echo
	@echo Valid targets: clean, elf32, elf64, win32
	@echo
	@echo When building for win32:
	@echo Make sure to change CXX in the Makefile to point to MinGW\'s g++.
	@echo
	@echo Before switching build targets, make sure to clean!
	@echo Otherwise, g++ will try to reuse the previosu incompatible .o files.

.PHONY: clean
clean:
	rm -f *.o elf{32,64}_base win{32,64}_base.exe

### Linux compilation.

# 64 bits

ELF64_LIBS = lib/elf64/libv8_base.a lib/elf64/libv8_snapshot.a lib/elf64/libbz2.a -lpthread -lGLU -lSDL

elf64_base: $(OBJECTS) Makefile
	$(CXX) -o $@ $(OBJECTS) $(ELF64_LIBS)

.PHONY: elf64
elf64: elf64_base Makefile
	python scripts/elf64_fixup.py
	#strip $(STRIP_ARGS) ../quick_links/elf64_data

# 32 bits

ELF32_LIBS = lib/elf32/libv8_base.a lib/elf32/libv8_snapshot.a lib/elf32/libbz2.a -lpthread -lGLU -lSDL

elf32_base: $(OBJECTS) Makefile
	$(CXX) -m32 -o $@ $(OBJECTS) $(ELF32_LIBS)

.PHONY: elf32_vars
elf32_vars:
	$(eval CPPFLAGS += -m32 -DWRAP_WORKAROUND)

.PHONY: elf32
elf32: elf32_vars elf32_base Makefile
	python scripts/elf32_fixup.py

### Windows compilation.

WIN32_LIBS = lib/win32/libbz2.a lib/win32/libv8_base.a lib/win32/libv8_snapshot.a lib/win32/winmm.lib lib/win32/ws2_32.lib lib/win32/libSDL.dll.a lib/win32/opengl32.lib lib/win32/glu32.lib

win32_base.exe: $(OBJECTS) Makefile
	$(CXX) -o $@ $(OBJECTS) $(WIN32_LIBS)

.PHONY: win32_vars
win32_vars:
	$(eval CXX := $(WIN32_CXX))
	$(eval CPPFLAGS += $(WIN32_CPPFLAGS))

.PHONY: win32
win32: win32_vars win32_base.exe Makefile
	python scripts/win32_fixup.py
	#strip $(STRIP_ARGS) ../quick_links/win32_data
