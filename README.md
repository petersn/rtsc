# What is RTSC?

RTSC is a game creation tool for programmers of a wide experience level (novice to expert).

# Compiling

The main RTSC compiler and GUI don't need any compilation.
RTSC uses a simple trick to allow end users to compile binaries for their native platform without a compiler/linker.
The details are described in `docs/main_docs.tex`, but the gist is that a valid binary for each platform is distributed with RTSC,
with minimal "relinking" instructions specifying how to add more data into the binary.
This process is referred to here as "quick-linking".
You may wish to compile your own quick-linking binaries if you modify the source.
Each OS that follows will make a pair of files in `quick_links/`, namely `TARGET_data` and `TARGET_relocs`.
All paths that follow are relative to `build/`.

## Dependencies

* `libbz2`
* `v8`
* `SDL`
* `OpenGL`, `GLU`

OS specific instructions are detailed:

## Linux (elf64)

Somehow compile/download `libbz2.a`, `libv8_base.a`, and `libv8_snapshot.a`, then place them into `lib/elf64/`.
Under `build/`, `make elf64`.

## Windows (win32)

I did it, but it was really nasty.
To document later.

