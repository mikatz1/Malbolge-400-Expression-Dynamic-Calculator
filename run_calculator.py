#!/usr/bin/env python3
"""
Interactive CLI runner for the Malbolge Calculator (`calculator_400.mal`).
Usage:
  python run_calculator.py          # Interactive prompt
  python run_calculator.py 7*8      # Direct single expression evaluation
  python run_calculator.py 7*8 -t   # Direct evaluation with full VM step-by-step trace
"""

import os
import sys
from malbolge_vm import MalbolgeVM

MAL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calculator_400.mal")


def evaluate_in_malbolge(expr: str, show_trace: bool = False) -> None:
    expr = expr.strip().replace(" ", "")
    if len(expr) != 3 or expr[0] not in "0123456789" or expr[1] not in "+-*/" or expr[2] not in "0123456789":
        print("입력 형식: [0-9][+-*/][0-9] (예: 7*8, 3-9, 8+5, 9/2, 5/0)")
        return

    with open(MAL_PATH, "r", encoding="ascii") as f:
        mal_source = f.read()

    vm = MalbolgeVM(mal_source)
    out, steps, trace = vm.run(input_data=expr, trace=True)

    if show_trace:
        print("\n--- [Malbolge VM Execution Trace] ---")
        for line in trace:
            if any(k in line for k in ("in a", "jmp [d]", "out a", "halt")):
                print(" ", line)
        print("-------------------------------------")

    jmp_lines = [l for l in trace if "jmp [d]" in l]
    op_branch = jmp_lines[1].split("[D]=")[1].split()[0]
    handler_addr = jmp_lines[2].split("[D]=")[1].split()[0]

    print(f"[Malbolge VM 실행 결과]")
    print(f"  입력 수식       : {expr}")
    print(f"  연산자 분기 주소: {op_branch}번지")
    print(f"  최종 핸들러 주소: {handler_addr}번지")
    print(f"  총 실행 스텝 수 : {steps} 스텝")
    print(f"  출력 결과       : {out!r}  (값: {out.strip()})")


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        trace_flag = "-t" in sys.argv or "--trace" in sys.argv
        evaluate_in_malbolge(sys.argv[1], show_trace=trace_flag)
    else:
        print("=== Malbolge 사칙연산 계산기 (calculator_400.mal) ===")
        print("수식을 입력하세요 (예: 7*8, 3-9, 8+5, 9/2, 5/0). 종료하려면 q 입력.\n")
        while True:
            try:
                user_in = input("수식 입력 > ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if user_in.lower() in ("q", "quit", "exit"):
                break
            if not user_in:
                continue
            evaluate_in_malbolge(user_in, show_trace=True)
            print()
