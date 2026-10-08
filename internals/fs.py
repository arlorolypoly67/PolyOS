import struct
from pathlib import Path

MAGIC = b'POLYOS_FS'
VERSION = 1
FS_FORMAT = struct.Struct(f'<{len(MAGIC)}s H')

INODE_FORMAT = struct.Struct(f'<I Q H H')

INODE_COUNT = 2 << 11
INODE_SIZE = 2 << 12

class Filesystem:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.inodes = {}

    def create(self):
        if not self.path.exists():
            with self.path.open('wb') as f:
                f.write(FS_FORMAT.pack(MAGIC, VERSION))
                f.write(b'\x00'*(INODE_SIZE*INODE_COUNT))

    def load(self):
        if not self.path.exists():
            self.create()
            self.inodes.clear()
            return

        with self.path.open('rb') as f:
            magic, version = FS_FORMAT.unpack(f.read(FS_FORMAT.size))

            if magic != MAGIC:
                raise ValueError(f'Invalid magic number: {magic!r}')

            if version != VERSION:
                raise ValueError(f'Version mismatch: {version!r}')

            while chunk := f.read(INODE_SIZE):
                if len(chunk) != INODE_SIZE:
                    raise ValueError('Truncated PolyFS file')

