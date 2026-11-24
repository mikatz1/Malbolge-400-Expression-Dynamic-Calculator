#!/usr/bin/env python3
"""
Malbolge Virtual Machine (Interpreter), Debugger, and Ternary Arithmetic Solver.
Implements the official 1998 Ben Olmstead Malbolge specification.
"""

from typing import List, Tuple, Optional, Dict

# Official Malbolge translation tables
XLAT1 = (
    "+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA\"lI"
    ".v%{gJh4G\\-=O@5`_3i<?Z';FNQuY]szf$!BS/|t:Pn6^Ha"
)

XLAT2 = (
    "5z]&gqtyfr$(we4{WP)H-Zn,[%\\3dL+Q;>U!pJS72FhOA1C"
    "B6v^=I_0/8|jsb9m<.TVac`uY*MK'X~xDl}REokN:#?G\"i@"
)

# Crazy operation truth table: CRZ_TABLE[A_trit][D_trit]
CRZ_TABLE = (
    (1, 0, 0),
    (1, 0, 2),
    (2, 2, 1),
)

MEM_SIZE = 59049  # 3^10

OPCODES = {
    4: "jmp [d]",
    5: "out a",
    23: "in a",
    39: "rotr [d]",
    40: "mov d, [d]",
    62: "crz [d]",
    68: "nop",
    81: "halt",
}


def crz(a: int, d: int) -> int:
    """Perform Malbolge ternary crazy operation crz(a, d)."""
    result = 0
    mul = 1
    for _ in range(10):
        a_trit = a % 3
        d_trit = d % 3
        result += CRZ_TABLE[d_trit][a_trit] * mul
        a //= 3
        d //= 3
        mul *= 3
    return result


def rotr(val: int) -> int:
    """Perform ternary rotate right by 1 trit on a 10-trit number."""
    return (val // 3) + (val % 3) * 19683  # 3^9 = 19683


def to_trits(val: int) -> str:
    """Convert integer to 10-trit string (MSB first)."""
    trits = []
    for _ in range(10):
        trits.append(str(val % 3))
        val //= 3
    return "".join(reversed(trits))


def from_trits(trit_str: str) -> int:
    """Convert 10-trit string (MSB first) to integer."""
    val = 0
    for ch in trit_str:
        val = val * 3 + int(ch)
    return val


class MalbolgeVM:
    """Full Malbolge Virtual Machine with instruction tracing and debugging."""

    def __init__(self, source: str):
        self.mem = [0] * MEM_SIZE
        self.c = 0
        self.d = 0
        self.a = 0
        self.steps = 0
        self.load_program(source)

    def load_program(self, source: str) -> None:
        idx = 0
        for ch in source:
            if ch.isspace():
                continue
            code = ord(ch)
            if 33 <= code <= 126:
                op = (code + idx) % 94
                if op not in OPCODES:
                    raise ValueError(
                        f"Invalid instruction '{ch}' at address {idx} (opcode {op})"
                    )
                self.mem[idx] = code
                idx += 1
                if idx > MEM_SIZE:
                    raise ValueError("Program exceeds 59049 words")
        if idx == 0:
            raise ValueError("Empty program")
        while idx < MEM_SIZE:
            self.mem[idx] = crz(self.mem[idx - 1], self.mem[idx - 2])
            idx += 1

    def run(
        self,
        input_data: str = "",
        max_steps: int = 1_000_000,
        trace: bool = False,
    ) -> Tuple[str, int, List[str]]:
        inp_idx = 0
        output = []
        trace_log = []

        while self.steps < max_steps:
            instr = self.mem[self.c]
            if not (33 <= instr <= 126):
                # In Malbolge specification, values outside 33..126 act as nop or invalid
                break

            op = (instr + self.c) % 94
            if trace:
                op_name = OPCODES.get(op, f"nop({op})")
                trace_log.append(
                    f"Step {self.steps:4d} | C={self.c:5d} D={self.d:5d} "
                    f"A={self.a:5d} ({to_trits(self.a)}) | [D]={self.mem[self.d]:5d} | {op_name}"
                )

            if op == 4:  # jmp [d]
                self.c = self.mem[self.d]
            elif op == 5:  # out a
                output.append(chr(self.a % 256))
            elif op == 23:  # in a
                if inp_idx < len(input_data):
                    self.a = ord(input_data[inp_idx])
                    inp_idx += 1
                else:
                    self.a = MEM_SIZE - 1  # EOF = 59048 (all 2s)
            elif op == 39:  # rotr [d]
                self.mem[self.d] = rotr(self.mem[self.d])
                self.a = self.mem[self.d]
            elif op == 40:  # mov d, [d]
                self.d = self.mem[self.d]
            elif op == 62:  # crz [d]
                self.mem[self.d] = crz(self.a, self.mem[self.d])
                self.a = self.mem[self.d]
            elif op == 81:  # halt
                self.steps += 1
                break
            # op == 68 or anything else is nop

            # Encrypt instruction at [C] if in printable ASCII range
            if 33 <= self.mem[self.c] <= 126:
                self.mem[self.c] = ord(XLAT2[self.mem[self.c] - 33])

            self.c = (self.c + 1) % MEM_SIZE
            self.d = (self.d + 1) % MEM_SIZE
            self.steps += 1

        return "".join(output), self.steps, trace_log


if __name__ == "__main__":
    # Quick sanity check with the classic Hello World in Malbolge
    hello_world = (
        "(=<`#9]~6ZY32Vx/4Rs+0No-&Jk)\"Fh}|Bcy?`=*z]Kw%oG4UUS0/@-ejc(:'8dc"
    )
    vm = MalbolgeVM(hello_world)
    out, steps, _ = vm.run()
    print(f"Sanity check output: {out!r} in {steps} steps")
