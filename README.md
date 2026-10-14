# PolyOS

**PolyOS** is a custom operating system project written in Python, featuring an emulated CPU, memory management, and a custom filesystem.

## Features

- **Custom CPU:** An emulated processor with registers, memory access, arithmetic, logic, branching, and data-transfer instructions.
- **Memory management:** A simulated memory system with ownership checks and configurable word sizes.
- **PolyFS:** A custom filesystem with inode-based storage, file and directory markers, permission flags, and continuation inodes.
- **Custom instruction set:** Includes arithmetic, bitwise operations, jumps, conditional branching, loading, storing, and halting.
- **Filesystem permissions:** Supports read, write, execute, system, and hidden flags.
- **Persistent filesystem:** Supports saving and loading filesystem images using the `.pimg` format.
- **Python implementation:** Built in Python, making the underlying system components accessible for experimentation and development.

## Components

### CPU

The CPU emulator provides a custom instruction set and a configurable architecture.

Supported instruction categories include:

- Arithmetic: `ADD`, `SUB`, `MUL`, `DIV`
- Bitwise operations: `AND`, `OR`, `XOR`
- Control flow: `JMP`, `JZ`, `JNZ`, `HALT`
- Memory operations: `LOAD`, `STORE`
- Register and memory assignment: `SETR`, `SETM`

### Memory

PolyOS includes a simulated memory system designed to work with its CPU emulator. Its architecture uses configurable system bit widths and word sizes.

### PolyFS

PolyFS is PolyOS's custom filesystem implementation.

Its design includes:

- Inode-based file storage
- File, directory, and symbolic-link markers
- Inode allocation and reuse
- Continuation inodes for larger file contents
- Read, write, execute, system, and hidden permission flags
- Filesystem image persistence

Filesystem images use the `.pimg` extension.

## Project Structure

The project includes core configuration, utility functions, and internal system components.

```text
PolyOS/
├── main.py
└── internals/
    ├── cpu.py
    ├── fs.py
    ├── config.py
    ├── utils.py
    └── ram.py
```

*The structure above shows the main components; additional files may exist.*

## Goals

PolyOS explores operating-system concepts through a custom Python implementation, including:

- CPU instruction execution
- Register and memory interaction
- Filesystem structures and storage
- Binary serialization
- Resource allocation and permissions

## Project Status

PolyOS is an experimental operating-system project under active development. Its architecture, instruction set, and filesystem format may change over time.

## License

See the repository for licensing information.

## Repository

[github.com/arlorolypoly67/PolyOS](https://github.com/arlorolypoly67/PolyOS)
