import struct
from pathlib import Path

MAGIC = b'POLYOS_FS'
VERSION = 1
FS_FORMAT = struct.Struct(f'<{len(MAGIC)}s H')

INODE_FORMAT = struct.Struct(f'<I Q H H I')

INODE_COUNT = 2 << 11
INODE_SIZE = 2 << 12

EMPTY_CHUNK = b'\x00' * INODE_SIZE

FILE_MARKER = b'FILE\x00'
DIR_MARKER = b'DIR\x00'
LINK_MARKER = b'LNK\x00'

PERM_R = 1 << 0
PERM_W = 1 << 1
PERM_X = 1 << 2
PERM_SYSTEM = 1 << 3
PERM_HIDDEN = 1 << 4

class Filesystem:
    def __init__(self, path: str | Path):
        self.path = Path(path).with_suffix('.pimg')
        self.inodes = {}

    def create(self):
        if not self.path.exists():
            with self.path.open('wb') as f:
                f.write(FS_FORMAT.pack(MAGIC, VERSION))
                f.write(EMPTY_CHUNK*INODE_COUNT)

    def load(self):
        self.inodes.clear()

        if not self.path.exists():
            self.create()
            return

        with self.path.open('rb') as f:
            try:
                magic, version = FS_FORMAT.unpack(f.read(FS_FORMAT.size))
            except struct.error:
                raise ValueError('Corrupted PolyFS file')

            if magic != MAGIC:
                raise ValueError(f'Invalid magic number: {magic!r}')

            if version != VERSION:
                raise ValueError(f'Version mismatch: {version!r}')

            while chunk := f.read(INODE_SIZE):
                if len(chunk) != INODE_SIZE:
                    raise ValueError('Truncated PolyFS file')

                if chunk == EMPTY_CHUNK:
                    continue

                header = chunk[:INODE_FORMAT.size]

                try:
                    id_, datalen, fpsize, contsize, permissions = INODE_FORMAT.unpack(header)
                except struct.error:
                    raise ValueError('Corrupted inode header')

                if not 0 <= id_ < INODE_COUNT:
                    raise ValueError('Corrupted inode')

                if INODE_FORMAT.size + contsize + fpsize + datalen > INODE_SIZE:
                    raise ValueError('Corrupted inode')

                offset = INODE_FORMAT.size

                cont_nodes = chunk[offset:offset+contsize]
                offset += contsize
                fp = chunk[offset:offset+fpsize]
                offset += fpsize
                data = chunk[offset:offset+datalen]

                cont_ids = (
                    [int(node_id) for node_id in cont_nodes.split(b':')]
                    if cont_nodes
                    else []
                )

                if any(not 0 <= node_id < INODE_COUNT for node_id in cont_ids):
                    raise ValueError('Corrupted inode')

                type_, data = data.split(b'\x00', 1)

                entry = {
                    'id': id_,
                    'data': data,
                    'cont_nodes': cont_ids,
                    'filepath': fp,
                    'perms': permissions,
                    'type': type_
                }

                self.inodes[id_] = entry

    def save(self):
        data = bytearray()

        data.extend(FS_FORMAT.pack(MAGIC, VERSION))

        for info in self.inodes.values():
            cont_nodes = ':'.join(map(str, info['cont_nodes'])).encode()

            length = INODE_SIZE - (
                    INODE_FORMAT.size
                    + len(cont_nodes)
                    + len(info['filepath'])
                    + len(info['type'])
                    + 1
            )

            pack_data = (
                    info['type']
                    + b'\x00'
                    + info['data'].ljust(length, b'\x00')
            )

            hdr = INODE_FORMAT.pack(
                info['id'],
                len(info['data']) + len(info['type']) + 1,
                len(info['filepath']),
                len(cont_nodes),
                info['perms']
            )

            data.extend(hdr)
            data.extend(cont_nodes)
            data.extend(info['filepath'])
            data.extend(pack_data)

        data = data.ljust(
            FS_FORMAT.size + INODE_SIZE * INODE_COUNT,
            b'\x00',
        )

        with self.path.open('wb') as f:
            f.write(data)