
V8_HOME = /home/peter/local/v8
LINKING = $(V8_HOME)/out/native/obj.target/tools/gyp

CPPFLAGS = -O3 -Wall -I$(V8_HOME)/include

all: launch.o

clean:
	rm -f *.o Test

# Examples of what it would look like to build using launch$ARCH.o:

javascript.o: code.js Makefile
	objcopy --input binary --output elf64-x86-64 --binary-architecture i386:x86-64 code.js javascript.o

Main: launch.o javascript.o Makefile
	g++ -o $@ launch.o javascript.o $(LINKING)/libv8_base.a $(LINKING)/libv8_snapshot.a -lpthread

