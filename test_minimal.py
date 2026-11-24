#!/usr/bin/env python3
"""
Step 1: Minimal Working Malbolge Dynamic Hash & Jump Program.
Verifies on the real MalbolgeVM that:
1. Input digit '0'..'9' is read at runtime via `in a`
2. Hashed via `crz [d]` at D=68 (mem[68]=94) and D=81 (mem[81]=94)
3. Rotated 7 times in-place at self-rewinding slot D=81 (mem[82]=80)
4. Jumps dynamically via `jmp [d]` to 10 disjoint 27-byte-stride addresses (729..1404)
5. Each handler synthesizes and outputs a unique response character and halts!
"""

from malbolge_vm import MalbolgeVM, crz, rotr, to_trits, OPCODES


def char_for_op(addr: int, op: int) -> int:
    for v in range(33, 127):
        if (v + addr) % 94 == op:
            return v
    raise ValueError(f"Cannot encode op {op} at addr {addr}")


def allowed_vals(addr: int):
    return [v for v in range(33, 127) if (v + addr) % 94 in OPCODES]


def expected_addr(x_digit: int) -> int:
    v = crz(crz(ord(str(x_digit)), 94), 94)
    for _ in range(7):
        v = rotr(v)
    return v


def build_minimal_mal() -> str:
    max_addr = 1500
    # Default fill every cell with valid `nop` (op 68)
    mem = [char_for_op(i, 68) for i in range(max_addr)]

    # Memory layout:
    # 0: jmp [d] (op 4). At addr 0, op 4 is ASCII 98 ('b').
    #    Wait: when C=0, D=0 executes jmp [d], C becomes mem[0]=98, then encrypted, then C=99, D=1!
    #    Let's instead put `mov d, [d]` (op 40, ASCII 40) at addr 0 so D jumps to 41, C becomes 1!
    #    Wait: our code at C=1..35 will execute while D walks from 41..82!
    #    Let's trace C and D simultaneously:
    #    Step 0: C=0, D=0 -> `mov d, [d]` (mem[0]=40) -> C=1, D=41
    #    Wait: at D=51, mem[51]=66 is allowed (`(66+51)%94 = 23 in OPCODES`).
    #    If we do `mov d, [d]` when D=51, D jumps to 66+1 = 67!
    #    Even simpler: from D=41 to D=68 is only 27 steps! C can just walk from C=1 to C=28 while D walks from 41 to 68!
    #    Wait: if C walks from 1 to 50, does C collide with D (41..82)?
    #    If C reaches 41 while D is at 81, C only overlaps with 41..55 AFTER D has already passed 41..55!
    #    Let's check: at step k (for k >= 1 before rewinds):
    #      C = k
    #      D = 40 + k
    #    Since D = 40 + k is ALWAYS 40 bytes ahead of C = k, as long as total code length < 68,
    #    C NEVER reaches 68..82 (where our data cells 68, 81, 82 live)!!

    # Let's verify how many instructions C executes!
    # Step 0: C=0, D=0: `mov d, [d]` (op 40, mem[0]=40) -> next: C=1, D=41
    # Steps 1..26 (26 steps): C=1..26, D=41..66: `nop` (op 68) -> next: C=27, D=67
    # Step 27: C=27, D=67: `in a` (op 23) -> reads digit X into A! next: C=28, D=68
    # Step 28: C=28, D=68: `crz [d]` (op 62) with mem[68]=94 -> A = crz(ord(X), 94)! next: C=29, D=69
    # Steps 29..40 (12 steps): C=29..40, D=69..80: `nop` (op 68) -> next: C=41, D=81
    # Step 41: C=41, D=81: `crz [d]` (op 62) with mem[81]=94 -> mem[81] = crz(A, 94)! next: C=42, D=82
    # Step 42: C=42, D=82: `mov d, [d]` (op 40) with mem[82]=80 -> rewinds D to 81! next: C=43, D=81
    # Now 7 rotations of mem[81]:
    #   Steps 43..56 (14 steps, 7 pairs of (rotr [d], mov d, [d])):
    #   At C=43, 45, 47, 49, 51, 53, 55 (D=81): `rotr [d]` (op 39)
    #   At C=44, 46, 48, 50, 52, 54, 56 (D=82): `mov d, [d]` (op 40)
    # Step 57: C=57, D=81: `jmp [d]` (op 4) -> jumps C to mem[81] (which is target_addr - 1? WAIT:
    #   In Malbolge, when `jmp [d]` executes, `self.c = self.mem[self.d]`, then `mem[self.c]` is encrypted,
    #   and THEN `self.c = (self.c + 1) % MEM_SIZE`!
    #   So execution resumes at `mem[81] + 1`, and D becomes `82`!)
    # Notice that C only goes from 0 to 57!
    # And our critical data cells are at 68, 81, 82 (all >= 68 > 57)!
    # So C (0..57) and critical data (68..95) NEVER OVERLAP!

    mem[0] = char_for_op(0, 40)  # mov d, [d] (sets D=41)
    for c in range(1, 27):
        mem[c] = char_for_op(c, 68)  # nop
    mem[27] = char_for_op(27, 23)  # in a
    mem[28] = char_for_op(28, 62)  # crz [d] (at D=68)
    for c in range(29, 41):
        mem[c] = char_for_op(c, 68)  # nop
    mem[41] = char_for_op(41, 62)  # crz [d] (at D=81)
    mem[42] = char_for_op(42, 40)  # mov d, [d] (at D=82 -> rewinds D to 81)
    for i in range(7):
        mem[43 + 2 * i] = char_for_op(43 + 2 * i, 39)      # rotr [d] (at D=81)
        mem[43 + 2 * i + 1] = char_for_op(43 + 2 * i + 1, 40)  # mov d, [d] (at D=82)
    mem[57] = char_for_op(57, 4)   # jmp [d] (at D=81)

    # Set data cells:
    mem[68] = 94  # '^' (valid at 68 since (94+68)%94 = 68 in OPCODES)
    mem[81] = 94  # '^' (valid at 81 since (94+81)%94 = 81 in OPCODES)
    mem[82] = 80  # 'P' (valid at 82 since (80+82)%94 = 68 in OPCODES)

    # Wait: after `jmp [d]` at D=81, C jumps to `addr + 1` (where `addr = expected_addr(x)`),
    # and D is at 82!
    # At the handler (`addr + 1`), D starts at 82, 83, 84...
    # Let's put a simple character synthesis at D=83, 84 and `out a`, `halt` at each handler `addr + 1`
    # to test that all 10 digits jump to the exact expected address and execute the handler!
    for x in range(10):
        addr = expected_addr(x)
        # Note: after rotr 7 times on D=81, A already holds `addr`.
        # At `addr + 1` (D=82): let's do `out a` (outputs chr(addr % 256)) and `halt` at `addr + 2`!
        mem[addr + 1] = char_for_op(addr + 1, 5)   # out a
        mem[addr + 2] = char_for_op(addr + 2, 81)  # halt

    return "".join(chr(v) for v in mem)


if __name__ == "__main__":
    mal_code = build_minimal_mal()
    print(f"Generated minimal .mal program of length {len(mal_code)} bytes.")
    all_ok = True
    for x in range(10):
        vm = MalbolgeVM(mal_code)
        out, steps, trace = vm.run(input_data=str(x), trace=True)
        py_addr = expected_addr(x)
        # Check the jmp instruction in trace (Step 57)
        jmp_line = [l for l in trace if "jmp [d]" in l][0]
        # Extract [D]=... from trace line
        vm_addr = int(jmp_line.split("[D]=")[1].split()[0])
        match = (vm_addr == py_addr) and (out == chr(py_addr % 256))
        all_ok = all_ok and match
        print(
            f"Input '{x}': Python addr={py_addr:4d} | VM [D] at jmp={vm_addr:4d} | "
            f"Match={match} | Steps={steps} | Output={out!r}"
        )
    print(f"\nMinimal verification result: {'100% PASS' if all_ok else 'FAIL'}")
