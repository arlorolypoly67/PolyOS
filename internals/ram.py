from collections import defaultdict

class Pointer:
    def __init__(self, address, owner, ram: 'VirtualRAM'):
        self.address = address
        self.owner = owner
        self.ram = ram

    def read(self, length):
        return self.ram.read(self.address, length, self.owner)

    def write(self, data):
        self.ram.write(self.address, data, self.owner)

    def __add__(self, offset):
        return Pointer(self.address + offset, self.owner, self.ram)

    def __sub__(self, offset):
        return Pointer(self.address - offset, self.owner, self.ram)

    def __iadd__(self, offset):
        self.address += offset
        return self

    def __isub__(self, offset):
        self.address -= offset
        return self

    def __repr__(self):
        return f"Pointer(address={self.address}, owner={self.owner})"

class VirtualRAM:
    def __init__(self, size):
        self.size = size
        self.memory = bytearray(size)
        self.allocations = defaultdict(list)

    def _validate_address(self, address, length):
        if address < 0 or address + length > self.size:
            raise ValueError("Address out of bounds")

    def _validate_ownership(self, address, length, owner, noalloc_err=True):
        end = address + length

        for owner2, ranges in self.allocations.items():
            for start, end2 in ranges:
                if start <= address and end <= end2:
                    if owner2 != owner:
                        raise ValueError(
                            'Memory range is already allocated to another owner'
                        )

                    return

        if noalloc_err:
            raise ValueError('Memory range is not allocated')
                    
    def _find_free_range(self, size):
        sorted_allocations = sorted(
            (start, end)
            for ranges in self.allocations.values()
            for start, end in ranges
        )

        if not sorted_allocations:
            return 0

        if sorted_allocations[0][0] >= size:
            return 0

        for i in range(len(sorted_allocations) - 1):
            _, end1 = sorted_allocations[i]
            start2, _ = sorted_allocations[i + 1]

            if start2 - end1 >= size:
                return end1

        last_end = sorted_allocations[-1][1]

        if self.size - last_end >= size:
            return last_end

        raise MemoryError('Not enough free memory available')

    def malloc(self, size, to):
        if size <= 0:
            raise ValueError("Size must be positive")

        pos = self._find_free_range(size)

        self._validate_address(pos, size)
        self._validate_ownership(pos, size, to, noalloc_err=False)

        self.allocations[to].append((pos, pos + size))

        return Pointer(pos, to, self)

    def manual_malloc(self, pos, size, to):
        if size <= 0:
            raise ValueError("Size must be positive")

        self._validate_address(pos, size)
        self._validate_ownership(pos, size, to, noalloc_err=False)

        self.allocations[to].append((pos, pos + size))

        return Pointer(pos, to, self)

    def free(self, pointer, zero=False):
        if pointer.ram is not self:
            raise ValueError('Pointer does not belong to this memory')

        if pointer.owner not in self.allocations:
            raise ValueError('Pointer owner has no allocations')

        for i, (start, end) in enumerate(self.allocations[pointer.owner]):
            if start == pointer.address:
                del self.allocations[pointer.owner][i]

                if zero:
                    self.memory[start:end] = b'\x00' * (end - start)

                return

        raise ValueError('Pointer does not match any allocated range')

    def read(self, address, length, owner):
        self._validate_address(address, length)
        self._validate_ownership(address, length, owner)

        return self.memory[address:address + length]

    def write(self, address, data, owner):
        length = len(data)
        self._validate_address(address, length)
        self._validate_ownership(address, length, owner)

        self.memory[address:address + length] = data

    def stat(self, hdump_end=None):
        if hdump_end is None:
            hdump_end = self.size
        print('----HEXDUMP----')
        for i in range(0, hdump_end, 16):
            chunk = self.memory[i:i + 16]
            hex_chunk = ' '.join(f'{byte:02x}' for byte in chunk)
            ascii_chunk = ''.join(chr(byte) if 32 <= byte <= 126 else '.' for byte in chunk)
            print(f'{i:08x}  {hex_chunk:<48}  {ascii_chunk}')
        print('----ALLOCATIONS----')
        for owner, ranges in self.allocations.items():
            for start, end in ranges:
                print(f'Owner: {owner}, Range: {start:#08x}-{end:#08x}')
        print('----USAGE----')
        total_allocated = sum(end - start for ranges in self.allocations.values() for start, end in ranges)
        print(f'Total allocated: {total_allocated} bytes')
        print(f'Total free: {self.size - total_allocated} bytes')
        print(f'Total size: {self.size} bytes')
        print('-----------------')