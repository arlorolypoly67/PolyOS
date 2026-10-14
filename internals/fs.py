import struct
from pathlib import Path
import uuid
from types import TracebackType

MAGIC = b'POLYOS_FS'
VERSION = 1
FS_FORMAT = struct.Struct(f'<{len(MAGIC)}s H')

INODE_FORMAT = struct.Struct(f'<I Q H H I')

INODE_COUNT = 2 << 12
INODE_SIZE = 2 << 13

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
                    id_, datalen, fpsize, contsize, permissions = (
                        INODE_FORMAT.unpack(header)
                    )
                except struct.error:
                    raise ValueError('Corrupted inode header')

                if not 0 <= id_ < INODE_COUNT:
                    raise ValueError('Corrupted inode')

                if (
                        INODE_FORMAT.size + contsize + fpsize + datalen
                        > INODE_SIZE
                ):
                    raise ValueError('Corrupted inode')

                offset = INODE_FORMAT.size

                cont_nodes = chunk[offset:offset + contsize]
                offset += contsize

                fp = chunk[offset:offset + fpsize]
                offset += fpsize

                data = chunk[offset:offset + datalen]

                try:
                    cont_ids = (
                        [int(node_id) for node_id in cont_nodes.split(b':')]
                        if cont_nodes else []
                    )
                except ValueError:
                    raise ValueError('Corrupted inode continuation list')

                if any(not 0 <= node_id < INODE_COUNT for node_id in cont_ids):
                    raise ValueError('Corrupted inode')

                try:
                    type_, data = data.split(b'\x00', 1)
                except ValueError:
                    raise ValueError('Corrupted inode type marker')

                if type_ not in (b'FILE', b'DIR', b'LNK'):
                    raise ValueError('Unknown inode type')

                self._make_inode(
                    id_, type_, data, cont_ids, fp, permissions
                )

        if 0 not in self.inodes:
            self._make_inode(
                0, DIR_MARKER[:-1], b'', [], b'/', PERM_R | PERM_W | PERM_X
            )
            self.save()

        root = self.inodes[0]

        if root['type'] != DIR_MARKER[:-1] or root['filepath'] != b'/':
            raise ValueError('Invalid root directory')

    def _get_free_id(self):
        for id_ in range(INODE_COUNT):
            if id_ not in self.inodes:
                return id_

        raise OSError('No free inodes')

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

    def __enter__(self):
        self.load()
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None):
        if exc_type is None:
            self.save()

        return False

    def _make_inode(self, id_, type_, data, continue_nodes, fp, perms):
        inode = {
            'id': id_,
            'type': type_,
            'data': data,
            'cont_nodes': continue_nodes,
            'filepath': fp,
            'perms': perms,
        }

        self.inodes[id_] = inode
        return inode

    def path2id(self, path: bytes | str):
        if isinstance(path, str):
            path = path.encode()

        for node in self.inodes.values():
            if node['filepath'] == path:
                return node['id']

        return None

    def mkdir(self, path, perms):
        if isinstance(path, str):
            path = path.encode()

        if self.path2id(path) is not None:
            raise FileExistsError(path)

        id_ = self._get_free_id()
        self._make_inode(id_, DIR_MARKER[:-1], b'', [], path, perms)

    md = mkdir

    def _remove_conts(self, id_):
        cont_nodes = self.inodes[id_]['cont_nodes']

        for node in cont_nodes:
            self.inodes.pop(node, None)

        cont_nodes.clear()

    def remove(self, path):
        if isinstance(path, str):
            path = path.encode()

        id_ = self.path2id(path)

        if id_ is None:
            raise FileNotFoundError(path)

        self._remove_conts(id_)

        del self.inodes[id_]

    rm = remove

    def touch(self, path, perms):
        if isinstance(path, str):
            path = path.encode()

        id_ = self._get_free_id()
        self._make_inode(id_, FILE_MARKER[:-1], b'', [], path, perms)
        return id_

    def write(self, path, data, perms=None):
        if isinstance(path, str):
            path = path.encode()

        if isinstance(data, str):
            data = data.encode()

        id_ = self.path2id(path)

        if id_ is None:
            if perms is None:
                raise ValueError('Permissions required if file does not exist')
            id_ = self.touch(path, perms)

        inode = self.inodes[id_]

        header_size = (
            len(':'.join(map(str, inode['cont_nodes'])).encode())
            + len(FILE_MARKER)
            + INODE_FORMAT.size
            + len(inode['filepath'])
        )

        if len(data) >= (INODE_SIZE - header_size):
            capacity = INODE_SIZE - header_size

            cont_inodes = []
            self._remove_conts(id_)

            orig_id = id_

            self.inodes[id_]['data'] = data[:capacity]
            data = data[capacity:]

            while data:
                chunk = data[:capacity]
                data = data[capacity:]

                fp = f'/.cont_inode_{uuid.uuid4().hex}'

                id_ = self.touch(fp, PERM_SYSTEM | PERM_HIDDEN | PERM_R)

                self.inodes[id_]['data'] = chunk
                cont_inodes.append(id_)

            self.inodes[orig_id]['cont_nodes'] = cont_inodes
        else:
            self.inodes[id_]['data'] = data