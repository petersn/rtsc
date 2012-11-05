
V8_HOME = /home/peter/local/v8
LINKING = $(V8_HOME)/out/native/obj.target/tools/gyp

CPPFLAGS = -g -Wall -I$(V8_HOME)/include `sdl-config --cflags`

all: launch.o opengl.o os.o

.PHONY: clean
clean:
	rm -f *.o Test

# Below are commands for making quick_links entries.

code.js: Makefile
	python -c 'open("code.js", "w").write("\0"*16)'

javascript.o: code.js Makefile
	objcopy --input binary --output elf64-x86-64 --binary-architecture i386:x86-64 --rename-section .data=.unicorns code.js javascript.o

prod: launch.o javascript.o opengl.o os.o rtscfs.o Makefile
	g++ -o prod launch.o opengl.o os.o rtscfs.o javascript.o libs64/libv8_base.a libs64/libv8_snapshot.a -lpthread -lGLU -lSDL

../quick_links/elf64_data: prod fixup.py Makefile
	python fixup.py

