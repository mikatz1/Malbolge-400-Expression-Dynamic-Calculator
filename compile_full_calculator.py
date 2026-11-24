#!/usr/bin/env python3
"""
Full 400-Expression Malbolge Calculator Compiler & Verifier.
Generates a standalone Malbolge program (`calculator_400.mal`) that:
1. Reads a 3-character arithmetic expression `X OP Y` (e.g. "7*8", "3-9", "8+5", "9/2", "5/0")
   at runtime via three `in a` instructions.
2. Computes the 10-trit dynamic handler address via `crz [d]` and `rotr [d]` across
   self-rewinding slots (67, 78, 81, 96, 125).
3. Branches dynamically via `jmp [d]` first to one of 4 operator routines (972, 1134, 1215, 1296)
   and then to one of 400 disjoint 27-byte-stride handler addresses (1539..58968).
4. Synthesizes and outputs the exact 2-character result (" 0".."81", "-1".."-9", "ER")
   using Pool 1 (D=128..134) and Pool 2 (D=136..142) and halts.
"""

from typing import Dict, List, Tuple
from malbolge_vm import MalbolgeVM, crz, rotr, to_trits, OPCODES


def char_for_op(addr: int, op: int) -> int:
    for v in range(33, 127):
        if (v + addr) % 94 == op:
            return v
    raise ValueError(f"Cannot encode op {op} at addr {addr}")


def allowed_vals(addr: int) -> List[int]:
    return [v for v in range(33, 127) if (v + addr) % 94 in OPCODES]


# =====================================================================
# 1. Python Reference Hash Functions (Exact match with Malbolge VM)
# =====================================================================
T1_MASK = rotr(crz(0, 53))  # 49205 (2111111122_3), stored at mem[78]
T2_MASK = crz(0, 53)        # 29522 (1111111222_3), stored at mem[84]

# Operator parameters: (nx, r_pre_plus_1, mask_val, r2)
OP_PARAMS = {
    "+": (3, 3, T1_MASK, 3),
    "-": (3, 4, T2_MASK, 3),
    "*": (4, 3, T1_MASK, 4),
    "/": (4, 3, T2_MASK, 3),
}


def compute_op_branch_addr(op: str) -> int:
    """Address stored in [D=96] at the first jmp [d] (operator branch)."""
    v = crz(crz(ord(op), 61), 97)
    for _ in range(6):
        v = rotr(v)
    return v


def compute_handler_addr(x: int, op: str, y: int) -> int:
    """Address stored in [D=125] at the second jmp [d] (400 expression handlers)."""
    nx, r_rot, mask_val, r2 = OP_PARAMS[op]
    mx = crz(crz(crz(ord(str(x)), 94), 67), 67)
    if nx == 4:
        mx = crz(mx, 94)
    for _ in range(r_rot):
        mx = rotr(mx)
    mx2 = crz(mx, mask_val)
    my = crz(crz(crz(ord(str(y)), 94), 67), 67)
    comb = crz(mx2, my)
    for _ in range(r2):
        comb = rotr(comb)
    return comb


def expected_output_str(x: int, op: str, y: int) -> str:
    """Expected 2-char output for (x, op, y)."""
    if op == "+":
        val = x + y
    elif op == "-":
        val = x - y
    elif op == "*":
        val = x * y
    elif op == "/":
        if y == 0:
            return "ER"
        val = x // y
    else:
        raise ValueError(op)
    return f"{val:2d}"


# =====================================================================
# 2. Pool 1 (D=128..134) & Pool 2 (D=136..142) Instruction Sequences
# =====================================================================
POOL1_VALS = [99, 33, 63, 80, 79, 59, 94]
POOL2_VALS = [114, 90, 37, 89, 87, 86, 108]


def build_pool_recipes(vals: List[int], target_chars: str) -> Dict[str, List[int]]:
    """
    For each target character in `target_chars`, return a 7-element list of
    Malbolge opcodes (68=nop, 39=rotr, 62=crz) that synthesizes `ord(ch)` mod 256.
    """
    targets = {ord(c): c for c in target_chars}
    recipes: Dict[str, List[int]] = {}
    K = len(vals)

    def record(a_val: int, indices: Tuple[int, ...]):
        ch_code = a_val % 256
        if ch_code in targets and targets[ch_code] not in recipes:
            ops = [68] * K
            ops[indices[0]] = 39  # first active cell uses rotr [d] (ignores prior A)
            for idx in indices[1:]:
                ops[idx] = 62     # subsequent active cells use crz [d]
            recipes[targets[ch_code]] = ops

    for i in range(K):
        ai = rotr(vals[i])
        record(ai, (i,))
        for j in range(i + 1, K):
            aj = crz(ai, vals[j])
            record(aj, (i, j))
            for k in range(j + 1, K):
                ak = crz(aj, vals[k])
                record(ak, (i, j, k))
                for l in range(k + 1, K):
                    al = crz(ak, vals[l])
                    record(al, (i, j, k, l))

    assert len(recipes) == len(target_chars), f"Missing recipes: {set(target_chars) - set(recipes)}"
    return recipes


# =====================================================================
# 3. Assemble Full 59,000-byte Malbolge Source Code
# =====================================================================
def compile_malbolge_calculator() -> str:
    max_size = 59000
    mem = [char_for_op(i, 68) for i in range(max_size)]

    # --- Fixed Data Cells (D = 49..142) ---
    mem[49] = 49   # slot 49 initial value (rotr 8 times -> 441)
    mem[50] = 48   # slot 49 rewind pointer (48 + 1 = 49)

    mem[62] = 94   # crz 1 for X
    mem[66] = 67   # crz 2 for X
    mem[67] = 67   # slot 67: crz 3 for X (stores nx=3)
    mem[68] = 66   # slot 67 rewind pointer (66 + 1 = 67)
    mem[69] = 124  # forward D-jump pointer (124 + 1 = 125)

    mem[75] = 42   # t1 synthesis cell 1 (rotr)
    mem[76] = 80   # t1 synthesis cell 2 (crz)
    mem[77] = 98   # t1 synthesis cell 3 (crz)
    mem[78] = 97   # slot 78: t1 synthesis cell 4 (crz -> t2, then 1 rotr -> t1)
    mem[79] = 77   # slot 78 rewind pointer (77 + 1 = 78)

    mem[81] = 94   # slot 81: crz 4 for X (stores nx=4)
    mem[82] = 80   # slot 81 rewind pointer (80 + 1 = 81)
    mem[83] = 51   # t2 synthesis cell 1 (rotr)
    mem[84] = 49   # t2 synthesis cell 2 (crz -> stores t2)

    mem[87] = 124  # forward D-jump pointer (124 + 1 = 125)
    mem[88] = 74   # backward D-jump pointer (74 + 1 = 75)

    mem[95] = 61   # OP crz 1
    mem[96] = 97   # slot 96: OP crz 2 & rotate 6 times
    mem[97] = 95   # slot 96 rewind pointer (95 + 1 = 96)

    mem[98] = 94   # crz 1 for Y
    mem[108] = 67  # crz 2 for Y
    mem[125] = 67  # slot 125: crz 3 for Y (stores my, then comb)
    mem[126] = 124 # slot 125 rewind pointer (124 + 1 = 125)
    mem[127] = 66  # backward D-jump pointer (66 + 1 = 67)

    # Pool 1 at D = 128..134 (note: mem[131] = 80, which also serves as jump pointer -> 81!)
    for i, v in enumerate(POOL1_VALS):
        mem[128 + i] = v
    # Pool 2 at D = 136..142
    for i, v in enumerate(POOL2_VALS):
        mem[136 + i] = v

    # --- Entry Code (C = 0..25 -> jumps C to 442) ---
    c = 0
    def emit(op: int):
        nonlocal c
        mem[c] = char_for_op(c, op)
        c += 1

    emit(40)  # C=0, D=0: mov d, [0] (mem[0]=40 -> D=41)
    for _ in range(49 - 41):
        emit(68)  # walk D from 41 to 49
    # At D=49: rotate 8 times so mem[49] becomes 441, then jmp [49]
    for _ in range(8):
        emit(39)  # rotr [49] -> D=50
        emit(40)  # mov d, [50] -> D=49
    emit(4)       # jmp [49] -> C becomes 442, D becomes 50!

    # --- Main Preamble & X / OP Input (C = 442.., D = 50..96) ---
    c = 442
    # Walk D from 50 to 61 (11 nops)
    for _ in range(61 - 50):
        emit(68)
    emit(23)  # D=61: in a (read X) -> D=62
    emit(62)  # D=62: crz [62] (94) -> D=63
    for _ in range(66 - 63):
        emit(68)
    emit(62)  # D=66: crz [66] (67) -> D=67
    emit(62)  # D=67: crz [67] (67) -> mem[67] = nx=3! D=68
    for _ in range(81 - 68):
        emit(68)
    emit(62)  # D=81: crz [81] (94) -> mem[81] = nx=4! D=82
    for _ in range(88 - 82):
        emit(68)
    emit(40)  # D=88: mov d, [88] (mem[88]=74) -> D jumps to 75!

    # Synthesize t1 at slot 78 (D = 75..78)
    emit(39)  # D=75: rotr [75] -> D=76
    emit(62)  # D=76: crz [76] -> D=77
    emit(62)  # D=77: crz [77] -> D=78
    emit(62)  # D=78: crz [78] (mem[78] = t2) -> D=79
    emit(40)  # D=79: mov d, [79] (rewinds D to 78)
    emit(39)  # D=78: rotr [78] (mem[78] = t1!) -> D=79

    # Walk D from 79 to 83 (4 nops)
    for _ in range(83 - 79):
        emit(68)
    # Synthesize t2 at cell 84 (D = 83..84)
    emit(39)  # D=83: rotr [83] -> D=84
    emit(62)  # D=84: crz [84] (mem[84] = t2!) -> D=85

    # Walk D from 85 to 94 (9 nops)
    for _ in range(94 - 85):
        emit(68)
    emit(23)  # D=94: in a (read OP) -> D=95
    emit(62)  # D=95: crz [95] (61) -> D=96
    emit(62)  # D=96: crz [96] (97) -> D=97
    for _ in range(6):
        emit(40)  # D=97: mov d, [97] -> D=96
        emit(39)  # D=96: rotr [96] -> D=97
    emit(40)  # D=97: mov d, [97] -> D=96
    emit(4)   # D=96: jmp [96] -> jumps to operator routine + 1, with D=97!

    # --- 4 Operator Routines (start at compute_op_branch_addr(op) + 1, with D = 97) ---
    for op in "+-*/":
        c = compute_op_branch_addr(op) + 1
        nx, r_rot, _, r2 = OP_PARAMS[op]

        # Step 1: Read Y at D=97 and store `my` into slot 125 (D = 97..126)
        emit(23)  # D=97: in a (read Y) -> D=98
        emit(62)  # D=98: crz [98] (94) -> D=99
        for _ in range(108 - 99):
            emit(68)
        emit(62)  # D=108: crz [108] (67) -> D=109
        for _ in range(125 - 109):
            emit(68)
        emit(62)  # D=125: crz [125] (67) -> mem[125] = my! D=126
        emit(68)  # D=126: nop -> D=127

        if op == "+":
            # Jump D=127 -> 67, rotate slot 67 by 3, crz [78] (t1), jump D=87 -> 125
            emit(40)  # D=127: mov d, [127] -> D=67
            for i in range(3):
                emit(39)  # D=67: rotr [67] -> D=68
                if i < 2:
                    emit(40)  # D=68: mov d, [68] -> D=67
            # Now D=68, A = rotated mx! Walk D from 68 to 78 (10 nops)
            for _ in range(78 - 68):
                emit(68)
            emit(62)  # D=78: crz [78] (t1) -> A = mx2! D=79
            for _ in range(87 - 79):
                emit(68)
            emit(40)  # D=87: mov d, [87] (124) -> D=125!

        elif op == "-":
            # Jump D=127 -> 67, rotate slot 67 by 4, crz [84] (t2), jump D=87 -> 125
            emit(40)  # D=127: mov d, [127] -> D=67
            for i in range(4):
                emit(39)  # D=67: rotr [67] -> D=68
                if i < 3:
                    emit(40)  # D=68: mov d, [68] -> D=67
            # Walk D from 68 to 84 (16 nops)
            for _ in range(84 - 68):
                emit(68)
            emit(62)  # D=84: crz [84] (t2) -> A = mx2! D=85
            for _ in range(87 - 85):
                emit(68)
            emit(40)  # D=87: mov d, [87] (124) -> D=125!

        elif op == "*":
            # Walk D=127..130 (4 nops), jump D=131 -> 81, rotate slot 81 by 3,
            # jump D=85 -> 78, crz [78] (t1), jump D=87 -> 125
            for _ in range(131 - 127):
                emit(68)
            emit(40)  # D=131: mov d, [131] (80) -> D=81
            for i in range(3):
                emit(39)  # D=81: rotr [81] -> D=82
                if i < 2:
                    emit(40)  # D=82: mov d, [82] -> D=81
            # Now D=82, A = rotated mx! Walk D=82..87 (6 nops) to D=88 (jumps to 75)
            for _ in range(88 - 82):
                emit(68)
            emit(40)  # D=88: mov d, [88] (74) -> D=75
            for _ in range(78 - 75):
                emit(68)
            emit(62)  # D=78: crz [78] (t1) -> A = mx2! D=79
            for _ in range(87 - 79):
                emit(68)
            emit(40)  # D=87: mov d, [87] (124) -> D=125!

        elif op == "/":
            # Walk D=127..130 (4 nops), jump D=131 -> 81, rotate slot 81 by 3,
            # walk D=82..83 (2 nops), crz [84] (t2), jump D=87 -> 125
            for _ in range(131 - 127):
                emit(68)
            emit(40)  # D=131: mov d, [131] (80) -> D=81
            for i in range(3):
                emit(39)  # D=81: rotr [81] -> D=82
                if i < 2:
                    emit(40)  # D=82: mov d, [82] -> D=81
            for _ in range(84 - 82):
                emit(68)
            emit(62)  # D=84: crz [84] (t2) -> A = mx2! D=85
            for _ in range(87 - 85):
                emit(68)
            emit(40)  # D=87: mov d, [87] (124) -> D=125!

        # Combine A (mx2) with mem[125] (my), rotate r2 times, and jmp [125]!
        emit(62)  # D=125: crz [125] (mem[125] = comb!) -> D=126
        for _ in range(r2):
            emit(40)  # D=126: mov d, [126] -> D=125
            emit(39)  # D=125: rotr [125] -> D=126
        emit(40)  # D=126: mov d, [126] -> D=125
        emit(4)   # D=125: jmp [125] -> jumps to handler + 1, with D=126!

    # --- 400 Expression Result Handlers (at compute_handler_addr(x, op, y) + 1, D = 126) ---
    pool1_recipes = build_pool_recipes(POOL1_VALS, " -12345678E")
    pool2_recipes = build_pool_recipes(POOL2_VALS, "0123456789R")

    for op in "+-*/":
        for x in range(10):
            for y in range(10):
                h_addr = compute_handler_addr(x, op, y)
                out_str = expected_output_str(x, op, y)
                ch1, ch2 = out_str[0], out_str[1]

                c = h_addr + 1
                emit(68)  # D=126: nop -> D=127
                emit(68)  # D=127: nop -> D=128
                for op_code in pool1_recipes[ch1]:
                    emit(op_code)  # D=128..134 (Pool 1)
                emit(5)   # D=135: out a (prints ch1!) -> D=136
                for op_code in pool2_recipes[ch2]:
                    emit(op_code)  # D=136..142 (Pool 2)
                emit(5)   # D=143: out a (prints ch2!) -> D=144
                emit(81)  # D=144: halt!

    return "".join(chr(v) for v in mem)


if __name__ == "__main__":
    print("Compiling 400-expression Malbolge calculator...")
    mal_source = compile_malbolge_calculator()
    mal_path = r"C:\Users\USER\.gemini\antigravity\scratch\malbolge_ultimate\calculator_400.mal"
    with open(mal_path, "w", encoding="ascii") as f:
        f.write(mal_source)
    print(f"Saved {len(mal_source)} bytes to {mal_path}")

    # Verify all 400 input combinations on the real MalbolgeVM
    pass_count = 0
    addr_match_count = 0
    results_log = []

    for op in "+-*/":
        for x in range(10):
            for y in range(10):
                expr = f"{x}{op}{y}"
                expected_out = expected_output_str(x, op, y)
                expected_addr = compute_handler_addr(x, op, y)

                vm = MalbolgeVM(mal_source)
                actual_out, steps, trace = vm.run(input_data=expr, trace=True)

                # Extract the actual jump address from the second `jmp [d]` instruction in the VM trace
                jmp_lines = [l for l in trace if "jmp [d]" in l]
                vm_jmp_addr = int(jmp_lines[-1].split("[D]=")[1].split()[0])

                addr_ok = (vm_jmp_addr == expected_addr)
                out_ok = (actual_out == expected_out)
                if addr_ok:
                    addr_match_count += 1
                if addr_ok and out_ok:
                    pass_count += 1
                else:
                    print(f"FAIL on {expr}: expected ({expected_addr}, {expected_out!r}), got ({vm_jmp_addr}, {actual_out!r})")
                results_log.append((expr, expected_addr, vm_jmp_addr, addr_ok, expected_out, actual_out, out_ok, steps))

    print(f"\n=== FULL 400-INPUT VERIFICATION SUMMARY ===")
    print(f"Address Match (VM vs Python) : {addr_match_count} / 400")
    print(f"Output Match  (VM vs Python) : {pass_count} / 400")
