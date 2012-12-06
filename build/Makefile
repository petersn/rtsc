
CPPFLAGS = -g -Wall -Iinclude `sdl-config --cflags`

all: elf64

.PHONY: clean
clean:
	rm -f *.o elf64_base

# Linux compilation.

elf64_base: launch.o opengl.o os.o rtscfs.o Makefile
	$(CXX) -o $@ launch.o opengl.o os.o rtscfs.o lib/elf64/libv8_base.a lib/elf64/libv8_snapshot.a lib/elf64/libbz2.a -lpthread -lGLU -lSDL

.PHONY: elf64_data
elf64: elf64_base Makefile
	python scripts/elf64_fixup.py

