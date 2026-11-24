#!/usr/bin/env python3
"""
Exact synthesis and reuse of M_X1 = 59008 (2222220111_3) in a real .mal program
executed on MalbolgeVM.
"""

from malbolge_vm import MalbolgeVM, crz, rotr, to_trits, from_trits, OPCODES


def char_for_op(addr: int, op: int) -> int:
    for v in range(33, 127):
        if (v + addr) % 94 == op:
            return v
    raise ValueError(f"Cannot encode op {op} at addr {addr}")


def allowed_vals(addr: int):
    return [v for v in range(33, 127) if (v + addr) % 94 in OPCODES]


def find_ring_synthesis_for_59008():
    M_X1 = from_trits("2222220111")  # 59008
    # Let's check using slot 78 (allowed_vals(78)), cell 80 (allowed_vals(80)),
    # slot 81 (allowed_vals(81)), cells 83, 84, and rewind cell 85 (mem[85]=77 -> jumps D to 78)!
    # Trace:
    # Pass 1:
    #   At D=81: we start with A=0 (or A from crz at 78/80), do crz [81], and rotate slot 81 by r1 times.
    #   At D=83, 84: optional crz to reset/modify A.
    #   At D=85: mov d, [d] (mem[85]=77 -> D becomes 78!).
    # Pass 2:
    #   At D=78: crz [78] (or rotr [78]) and rotate slot 78 by r2 times -> sets A!
    #   At D=80: optional crz [80].
    #   At D=81: crz [81] (combines A with mem[81] from Pass 1!) and rotate slot 81 by r3 times!
    # Let's search over allowed initial ASCII values at 78, 80, 81, 83, 84!
    v78s = allowed_vals(78)
    v80s = allowed_vals(80)
    v81s = allowed_vals(81)
    v83s = allowed_vals(83)

    # All cyclic shifts of M_X1 = 59008:
    shifts = {}
    cur = M_X1
    for r in range(10):
        shifts[cur] = (10 - r) % 10
        cur = rotr(cur)

    for v81 in v81s:
        # Pass 1 at D=81 with A=0:
        m81_0 = crz(0, v81)
        for r1 in range(10):
            m81_rot = m81_0
            for _ in range(r1):
                m81_rot = rotr(m81_rot)
            # Now A = m81_rot, mem[81] = m81_rot.
            # Walk to D=85 via D=83 (where we can either nop or crz with v83):
            for use_83 in [False, True]:
                for v83 in (v83s if use_83 else [0]):
                    a_after_83 = crz(m81_rot, v83) if use_83 else m81_rot
                    # Jump D=85 -> D=78. At D=78, we can either rotr [78] (ignores A!) or crz [78]:
                    for op78 in ["rotr", "crz"]:
                        for v78 in v78s:
                            m78 = rotr(v78) if op78 == "rotr" else crz(a_after_83, v78)
                            for r2 in range(10):
                                a_from_78 = m78
                                for _ in range(r2):
                                    a_from_78 = rotr(a_from_78)
                                # Optional crz at D=80:
                                for use_80 in [False, True]:
                                    for v80 in (v80s if use_80 else [0]):
                                        a_into_81 = crz(a_from_78, v80) if use_80 else a_from_78
                                        comb81 = crz(a_into_81, m81_rot)
                                        if comb81 in shifts:
                                            r3 = shifts[comb81]
                                            return {
                                                "v81": v81, "r1": r1,
                                                "use_83": use_83, "v83": v83,
                                                "op78": op78, "v78": v78, "r2": r2,
                                                "use_80": use_80, "v80": v80,
                                                "r3": r3,
                                            }
    return None


def build_and_run_M_X1_verification():
    cfg = find_ring_synthesis_for_59008()
    print("Found synthesis config for M_X1 = 59008:", cfg)
    if not cfg:
        return

    # Now build a real .mal program that:
    # 1. Executes this exact synthesis so mem[81] == 59008 (2222220111_3)
    # 2. Rewinds D to 81 (via mem[82]=80)
    # 3. Executes `in a` to read input digit X ('0'..'9')
    # 4. Executes `crz [d]` at D=81 (reusing the synthesized mem[81] == 59008!)
    # 5. Halts!
    mem = [char_for_op(i, 68) for i in range(500)]
    c = 0

    def emit(op: int):
        nonlocal c
        mem[c] = char_for_op(c, op)
        c += 1

    # Step 0: C=0, D=0 -> mov d, [d] (sets D=41, C=1)
    emit(40)
    # Step 1: C=1, D=41 -> jmp [d] with mem[41]=122 (sets C=123, D=42!)
    # Notice: (122 + 41) % 94 = 163 % 94 = 69 (not in OPCODES). What allowed_val at 41 is >= 95?
    j_target = max(allowed_vals(41))
    mem[41] = j_target
    emit(4)  # jmp [41] -> C becomes j_target + 1 (>= 115), D becomes 42!
    c = j_target + 1

    # Walk D from 42 to 53 (11 nops)
    for _ in range(53 - 42):
        emit(68)
    # At D=53: mem[53]=80 -> mov d, [d] jumps D directly to 81!
    mem[53] = 80
    emit(40)

    # Now D = 81!
    # Pass 1: at D=81, crz [81], rewind D=82->81, rotate r1 times
    emit(62)  # crz [81] -> D=82
    for _ in range(cfg["r1"]):
        emit(40)  # mov d, [82] -> D=81
        emit(39)  # rotr [81] -> D=82
    # Step out of slot 81: nop at D=82 -> D=83
    emit(68)
    # At D=83:
    if cfg["use_83"]:
        mem[83] = cfg["v83"]
        emit(62)  # crz [83] -> D=84
    else:
        emit(68)  # nop -> D=84
    # At D=84: nop -> D=85
    emit(68)
    # At D=85: mem[85]=77 -> mov d, [85] jumps D back to 78!
    mem[85] = 77
    emit(40)

    # Pass 2: now D = 78!
    mem[78] = cfg["v78"]
    mem[79] = 77
    if cfg["op78"] == "rotr":
        emit(39)  # rotr [78] -> D=79
    else:
        emit(62)  # crz [78] -> D=79
    for _ in range(cfg["r2"]):
        emit(40)  # mov d, [79] -> D=78
        emit(39)  # rotr [78] -> D=79
    # Step out of slot 78: nop at D=79 -> D=80
    emit(68)
    # At D=80:
    if cfg["use_80"]:
        mem[80] = cfg["v80"]
        emit(62)  # crz [80] -> D=81
    else:
        emit(68)  # nop -> D=81

    # Now D = 81! Combine A with mem[81] and rotate r3 times:
    emit(62)  # crz [81] -> D=82
    for _ in range(cfg["r3"]):
        emit(40)  # mov d, [82] -> D=81
        emit(39)  # rotr [81] -> D=82

    # Rewind D=82 -> D=81 so D points at mem[81] (which now holds 59008!)
    emit(40)  # mov d, [82] -> D=81

    # NOW READ INPUT DIGIT via `in a` and REUSE mem[81] (59008) in `crz [81]`!
    # Wait: `in a` advances D from 81 to 82!
    # So we should do `in a` BEFORE rewinding at D=82, OR rewind after!
    # Let's check: if D=82 when we do `in a`? No, if we do `in a` at D=81, D becomes 82, then `mov d, [82]` rewinds D to 81, then `crz [81]`!
    # Wait: let's replace the last `emit(40)` above with:
    c -= 1
    # Currently D=82! If we do `mov d, [82]` -> D=81.
    # Instead, let's see: if we do `in a` while D=81, D becomes 82, then `mov d, [82]` sets D=81, then `crz [81]`!
    emit(40)  # at D=82: mov d, [82] -> D=81
    step_check_59008 = c
    emit(23)  # at D=81: `in a` (reads input into A!) -> D=82
    emit(40)  # at D=82: `mov d, [82]` (rewinds D to 81!) -> D=81
    emit(62)  # at D=81: `crz [81]` (computes crz(input, 59008)!) -> D=82
    emit(81)  # halt!

    mem[81] = cfg["v81"]
    mem[82] = 80

    print(f"Total code length: C ended at {c} (must be < 53 so code never touches data 53..85!)")
    mal_source = "".join(chr(v) for v in mem)

    M_X1 = from_trits("2222220111")  # 58981
    for digit in "0123456789":
        vm = MalbolgeVM(mal_source)
        _, steps, trace = vm.run(input_data=digit, trace=True)
        # Find the trace line right at `in a` (where D=81 and [D] is the synthesized mask!)
        in_line = [l for l in trace if "in a" in l][0]
        crz_line = [l for l in trace if "crz [d]" in l][-1]
        synthesized_mask = int(in_line.split("[D]=")[1].split()[0])
        expected_crz = crz(ord(digit), M_X1)
        actual_crz = vm.a
        print(
            f"Input '{digit}': Synthesized [D=81]={synthesized_mask} ({to_trits(synthesized_mask)}) | "
            f"After crz(input, [D=81]): VM A={actual_crz} ({to_trits(actual_crz)}) vs Python={expected_crz} | "
            f"Match={synthesized_mask == M_X1 and actual_crz == expected_crz}"
        )


if __name__ == "__main__":
    build_and_run_M_X1_verification()
