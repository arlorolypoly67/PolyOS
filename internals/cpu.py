from .config import SYSTEM_BITS, OPCODE_SIZE
from .ram import VirtualRAM

INSTRUCTIONS = {
    0x00: 'HALT',
    0x01: 'SETM',
    0x02: 'SETR',
    0x03: 'ADD',
    0x04: 'SUB',
    0x05: 'MUL',
    0x06: 'DIV',
    0x07: 'JMP',
    0x08: 'JZ',
    0x09: 'JNZ',
    0x0a: 'LOAD',
    0x0b: 'STORE',
    0x0c: 'AND',
    0x0d: 'XOR',
    0x0e: 'OR',
}


INSTRUCTIONS_INVERTED = {
    name: opcode
    for opcode, name in INSTRUCTIONS.items()
}


MAX_OPERANDS = 3
WORD_SIZE = SYSTEM_BITS // 8

OPERAND_BITS = (
    SYSTEM_BITS - OPCODE_SIZE
) // MAX_OPERANDS

UNUSED_BITS = (
    SYSTEM_BITS
    - OPCODE_SIZE
    - (OPERAND_BITS * MAX_OPERANDS)
)

OPCODE_MASK = (1 << OPCODE_SIZE) - 1
OPERAND_MASK = (1 << OPERAND_BITS) - 1

class CPUHalted(Exception): ...

def pack(instruction: str) -> int:
    parts = instruction.upper().split()

    if not parts:
        raise ValueError('Empty instruction')

    name = parts[0]

    try:
        opcode = INSTRUCTIONS_INVERTED[name]
    except KeyError:
        raise ValueError(f'Unknown instruction: {name!r}')

    if len(parts) > MAX_OPERANDS + 1:
        raise ValueError(
            f'{name} takes at most {MAX_OPERANDS} operands'
        )

    operands = [
        int(value, 0)
        for value in parts[1:]
    ]

    operands += [0] * (MAX_OPERANDS - len(operands))

    for operand in operands:
        if not 0 <= operand <= OPERAND_MASK:
            raise ValueError(
                f'Operand {operand} does not fit in '
                f'{OPERAND_BITS} bits'
            )

    result = opcode

    for operand in operands:
        result <<= OPERAND_BITS
        result |= operand

    result <<= UNUSED_BITS

    return result


def unpack(instruction: int) -> tuple[int, list[int]]:
    if not isinstance(instruction, int):
        raise TypeError('Instruction must be an int')

    if not 0 <= instruction < (1 << SYSTEM_BITS):
        raise ValueError(
            f'Instruction does not fit in {SYSTEM_BITS} bits'
        )

    instruction >>= UNUSED_BITS

    operands = []

    for _ in range(MAX_OPERANDS):
        operands.append(instruction & OPERAND_MASK)
        instruction >>= OPERAND_BITS

    opcode = instruction & OPCODE_MASK

    operands.reverse()

    return opcode, operands

class CPUEmulator:
    def __init__(self, instructions: list[int], ident, mem: VirtualRAM):
        self.instructions = instructions
        self.ident = ident
        self.mem = mem
        self.pc = 0
        self.running = True
        self.registers = {i: 0 for i in range(16)}

    def step(self):
        if not self.running:
            return

        if not 0 <= self.pc < len(self.instructions):
            self.running = False
            return

        old_pc = self.pc
        instruction = self.instructions[self.pc]

        try:
            self.execute(instruction)
        except CPUHalted:
            self.running = False

        if old_pc == self.pc:
            self.pc += 1

    def execute(self, instruction):
        opcode, operands = unpack(instruction)

        match opcode:
            case 0:
                raise CPUHalted()

            case 1:
                addr, data, *_ = operands
                data = data.to_bytes(WORD_SIZE, 'little')

                self.mem.write(addr, data, self.ident)

            case 2:
                reg, value, *_ = operands

                if not 0 <= reg <= 15:
                    raise ValueError('Register out of bounds')

                self.registers[reg] = value

            case 3:
                dest, a, b, *_ = operands

                for n in (dest, a, b):
                    if not 0 <= n <= 15:
                        raise ValueError('Register out of bounds')

                a_val, b_val = self.registers[a], self.registers[b]

                self.registers[dest] = a_val + b_val

            case 4:
                dest, a, b, *_ = operands

                for n in (dest, a, b):
                    if not 0 <= n <= 15:
                        raise ValueError('Register out of bounds')

                a_val, b_val = self.registers[a], self.registers[b]

                self.registers[dest] = a_val - b_val

            case 5:
                dest, a, b, *_ = operands

                for n in (dest, a, b):
                    if not 0 <= n <= 15:
                        raise ValueError('Register out of bounds')

                a_val, b_val = self.registers[a], self.registers[b]

                self.registers[dest] = a_val * b_val

            case 6:
                dest, a, b, *_ = operands

                for n in (dest, a, b):
                    if not 0 <= n <= 15:
                        raise ValueError('Register out of bounds')

                a_val, b_val = self.registers[a], self.registers[b]

                if b_val == 0:
                    raise ValueError('Division by zero')

                self.registers[dest] = a_val // b_val

            case 7:
                target, *_ = operands

                if not 0 <= target < len(self.instructions):
                    raise ValueError('Jump target out of range')

                self.pc = target

            case 8:
                reg, target, *_ = operands

                if not 0 <= target < len(self.instructions):
                    raise ValueError('Jump target out of range')

                if not 0 <= reg <= 15:
                    raise ValueError('Register out of bounds')

                if self.registers[reg] == 0:
                    self.pc = target

            case 9:
                reg, target, *_ = operands

                if not 0 <= target < len(self.instructions):
                    raise ValueError('Jump target out of range')

                if not 0 <= reg <= 15:
                    raise ValueError('Register out of bounds')

                if self.registers[reg] != 0:
                    self.pc = target

            case 10:
                addr, reg, *_ = operands

                if not 0 <= reg <= 15:
                    raise ValueError('Register out of bounds')

                data = self.mem.read(addr, WORD_SIZE, self.ident)

                data = int.from_bytes(data, 'little')

                self.registers[reg] = data

            case 11:
                reg, addr, *_ = operands

                if not 0 <= reg <= 15:
                    raise ValueError('Register out of bounds')


                val = self.registers[reg]

                val = val.to_bytes(WORD_SIZE, 'little')

                self.mem.write(addr, val, self.ident)

            case 12:
                dest, a, b, *_ = operands

                for n in (dest, a, b):
                    if not 0 <= n <= 15:
                        raise ValueError('Register out of bounds')

                a_val, b_val = self.registers[a], self.registers[b]

                self.registers[dest] = a_val & b_val

            case 13:
                dest, a, b, *_ = operands

                for n in (dest, a, b):
                    if not 0 <= n <= 15:
                        raise ValueError('Register out of bounds')

                a_val, b_val = self.registers[a], self.registers[b]

                self.registers[dest] = a_val ^ b_val

            case 14:
                dest, a, b, *_ = operands

                for n in (dest, a, b):
                    if not 0 <= n <= 15:
                        raise ValueError('Register out of bounds')

                a_val, b_val = self.registers[a], self.registers[b]

                self.registers[dest] = a_val | b_val

            case _:
                raise ValueError(f'Invalid instruction: {instruction!r}')


    def run(self):
        while self.running:
            self.step()

    def dump(self, ram_end=None):
        print(f'PC: {self.pc}')

        print('Registers:')
        for reg, val in self.registers.items():
            print(f'\tR{reg}: {val:#0{(WORD_SIZE*2)+2}x}')

        print('Instructions:')
        for i, ins in enumerate(self.instructions):
            op, operands = unpack(ins)
            width = (SYSTEM_BITS // 4) + 2

            print(
                f'\t{i}: {ins:#0{width}x} '
                f'({INSTRUCTIONS.get(op, "???")} {" ".join(map(str, operands))})'
            )

        self.mem.stat(ram_end)