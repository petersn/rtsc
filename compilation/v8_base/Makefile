
V8_HOME = /home/peter/local/v8
LINKING = $(V8_HOME)/out/native/obj.target/tools/gyp

CPPFLAGS = -O3 -Wall -I$(V8_HOME)/include

all: Main

Main: launch.o javascript.o Makefile
	g++ -o $@ launch.o javascript.o $(LINKING)/libv8_base.a $(LINKING)/libv8_snapshot.a -lpthread

javascript.o: code.js Makefile
	objcopy --input binary --output elf64-x86-64 --binary-architecture i386:x86-64 code.js javascript.o

clean:
	rm -f *.o Test

