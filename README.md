# Malbolge 400-Expression Dynamic Calculator (`calculator_400.mal`)

[**English**](#english) | [**한국어 (Korean)**](#한국어-korean)

---

<a id="english"></a>

## English

A **400-expression dynamic arithmetic calculator (`.mal`)** and **Ternary Perfect Hashing compiler** written for **Malbolge**, the notoriously difficult esoteric programming language designed by Ben Olmstead in 1998.

Malbolge operates on a ternary virtual machine ($3^{10} = 59,049$ memory words) with no arithmetic instructions (`+`, `-`, `*`, `/`), no conditional jump (`if`), and mandatory self-modification (`XLAT2` encryption) after every executed instruction. This project overcomes these constraints by combining only **`crz` (ternary crazy operation)**, **`rotr` (10-trit rotate right)**, and **indirect jumps (`jmp [d]`, `mov d, [d]`)** to hash any runtime 3-character input `X OP Y` (`0~9`, `+, -, *, /`, `0~9` — 400 expressions in total) into a collision-free memory address and synthesize the exact 2-character output.

### Key Features

1. **Runtime Ternary Perfect Hashing**
   - Reads `X`, `OP`, and `Y` at runtime via `in a` and packs the operands into a single 10-trit memory word without information loss using the digit-wise homomorphism of `rotr` and `crz` ($\text{rotr}(\text{crz}(A, B)) \equiv \text{crz}(\text{rotr}(A), \text{rotr}(B))$).
   - Maps all 400 expressions to **400 completely disjoint handler addresses with a minimum stride of 27 bytes (`Min Stride = 27`, address range `1539 .. 58968`, zero collisions)**.

2. **Self-Rewinding Slots**
   - Because Malbolge increments the data pointer `D` after every instruction, performing repeated in-place rotations on a single memory cell is normally impossible.
   - By selecting memory addresses `slot` (`49, 67, 78, 81, 96, 125`) where `(2 * slot) % 94` is a valid Malbolge opcode and placing `mem[slot + 1] = slot - 1`, executing `mov d, [d]` at `D = slot + 1` rewinds `D` back to `slot` indefinitely without altering `mem[slot + 1]`.

3. **2-Stage Computed Jump Architecture (`jmp [d]`)**
   - **Stage 1 (Operator Branch)**: Hashes the operator `OP` (`+`, `-`, `*`, `/`) at `slot 96` and jumps via `jmp [96]` to one of 4 operator routines (`972`, `1134`, `1215`, `1296`, spaced at least 81 bytes apart).
   - **Stage 2 (Expression Handler Branch)**: Combines normalized `X` and `Y` with synthesized 10-trit masks (`t1 = 49205`, `t2 = 29522`) at `slot 125` and jumps via `jmp [125]` to one of 400 disjoint 27-byte-stride handler addresses.

4. **19-Byte Fixed-Pool Result Handlers (`Pool 1` & `Pool 2`)**
   - Each of the 400 handlers walks across two shared 7-byte constant pools (`Pool 1` at `D = 128..134` and `Pool 2` at `D = 136..142`), selecting `{nop, rotr, crz}` instructions to synthesize and print the 2-character result (`" 0"` to `"81"`, `"-1"` to `"-9"`, or `"ER"` on division by zero) before halting.

### Repository Structure

```text
.
├── calculator_400.mal         # Compiled 59,000-byte standalone Malbolge calculator
├── compile_full_calculator.py # .mal compiler and full 400-input verification suite
├── run_calculator.py          # Interactive CLI runner and VM jump tracer
├── malbolge_vm.py             # 1998 official specification compliant Malbolge VM
├── test_minimal.py            # Minimal single-digit dynamic hash-and-jump verifier
├── test_mask_synthesis.py     # Data-pointer ring (D=78..85) 10-trit mask synthesis verifier
└── verification_report_400.txt# Full 400-expression log (Python addr vs VM addr & outputs)
```

### Quick Start

Requires Python 3.8+ (zero external dependencies).

#### 1. Interactive Mode
```bash
python run_calculator.py
```
Enter any 3-character expression matching `[0-9][+-*/][0-9]` (e.g., `7*8`, `3-9`, `8+5`, `9/2`, `5/0`).

#### 2. Single Expression with VM Execution Trace (`-t`)
```bash
python run_calculator.py "7*8" -t
```

**Sample Output:**
```text
--- [Malbolge VM Execution Trace] ---
  Step   25 | C=   25 D=   49 A=  441 (0000121100) | [D]=  441 | jmp [d]
  Step   37 | C=  453 D=   61 A=  441 (0000121100) | [D]=  101 | in a
  Step   86 | C=  502 D=   94 A=29537 (1111111222) | [D]=   68 | in a
  Step  102 | C=  518 D=   96 A= 1215 (0001200000) | [D]= 1215 | jmp [d]
  Step  103 | C= 1216 D=   97 A= 1215 (0001200000) | [D]=   95 | in a
  Step  173 | C= 1286 D=  125 A= 5616 (0021201000) | [D]= 5616 | jmp [d]
  Step  183 | C= 5626 D=  135 A=   53 (0000001222) | [D]=  121 | out a
  Step  191 | C= 5634 D=  143 A=29494 (1111110101) | [D]=  113 | out a
  Step  192 | C= 5635 D=  144 A=29494 (1111110101) | [D]=  112 | halt
-------------------------------------
[Malbolge VM 실행 결과]
  입력 수식       : 7*8
  연산자 분기 주소: 1215번지
  최종 핸들러 주소: 5616번지
  총 실행 스텝 수 : 193 스텝
  출력 결과       : '56'  (값: 56)
```

#### 3. Recompile `.mal` & Run Full 400-Expression Verification
```bash
python compile_full_calculator.py
```
```text
Compiling 400-expression Malbolge calculator...
Saved 59000 bytes to calculator_400.mal

=== FULL 400-INPUT VERIFICATION SUMMARY ===
Address Match (VM vs Python) : 400 / 400
Output Match  (VM vs Python) : 400 / 400
```

### Memory Layout

| Address Range | Role | Description |
| :---: | :--- | :--- |
| `0 .. 25` | **Entry Stub** | Advances `D` to `49`, rotates `slot 49` 8 times, and jumps `C` to `442` |
| `49 .. 142` | **Data Slots & Constant Pools** | Self-rewinding slots (`49, 67, 78, 81, 96, 125`), jump pointers, `Pool 1` (`128..134`), `Pool 2` (`136..142`) |
| `442 .. 519` | **Main Preamble & Hash** | Normalizes first digit `X`, synthesizes 10-trit masks `t1`/`t2`, reads operator `OP`, executes 1st `jmp [96]` |
| `973 .. 1353` | **4 Operator Routines** | Routines for `-` (`973`), `/` (`1135`), `*` (`1216`), `+` (`1297`); reads `Y`, combines `(X, Y)`, executes 2nd `jmp [125]` |
| `1539 .. 58987` | **400 Expression Handlers** | 400 disjoint 19-byte handlers (minimum 27-byte stride) that synthesize and output the 2-char result and `halt` |

---

<a id="한국어-korean"></a>

## 한국어 (Korean)

1998년 Ben Olmstead가 설계한 난해한 프로그래밍 언어 **말레볼제(Malbolge)**로 구현한 **사칙연산 계산기(`.mal`) 및 3진법 완전 해싱(Ternary Perfect Hashing) 컴파일러**입니다.

말레볼제는 덧셈/뺄셈 같은 산술 연산자와 조건문(`if`)이 전혀 존재하지 않고, 명령어가 실행될 때마다 암호화 테이블(`XLAT2`)에 의해 자폭(Self-modifying)하는 3진법 가상 머신($3^{10} = 59,049$ 워드)입니다. 본 프로젝트는 말레볼제의 유일한 연산 명령어인 **`crz` (Crazy 연산)**와 **`rotr` (10-trit 우측 순환 시프트)**, 그리고 **간접 점프(`jmp [d]`, `mov d, [d]`)**만을 조합하여 런타임 입력 `X OP Y` (`0~9`, `+, -, *, /`, `0~9` 총 400가지 수식)를 동적 해싱하고 정확한 계산 결과를 출력합니다.

### 주요 특징

1. **런타임 3진법 완전 해싱 (Ternary Perfect Hashing)**
   - 사용자 입력 문자 `X`, `OP`, `Y`를 `in a`로 읽어들인 뒤, `crz`와 `rotr`의 자리별 동형 사상($\text{rotr}(\text{crz}(A, B)) \equiv \text{crz}(\text{rotr}(A), \text{rotr}(B))$) 성질을 이용해 하나의 10-trit 메모리 주소로 무손실 패킹합니다.
   - 400개의 모든 수식이 **단 하나의 주소 충돌도 없이 최소 27바이트 간격(`Min Stride = 27`, 주소 범위 `1539 ~ 58968`)**으로 완벽히 분리됩니다.

2. **자기 되감기 슬롯 (Self-Rewinding Slots)**
   - 매 스텝마다 데이터 포인터 `D`가 1씩 자동 증가하는 말레볼제의 제약을 극복하기 위해, `(2 * slot) % 94`가 유효한 명령어 번호가 되는 주소(`slot = 49, 67, 78, 81, 96, 125`) 바로 다음 칸에 `mem[slot + 1] = slot - 1`을 배치하여 `mov d, [d]`만으로 `D`를 제자리로 무한 되감는 구조를 구현했습니다.

3. **2단계 동적 점프 아키텍처 (2-Stage Computed `jmp [d]`)**
   - **1차 분기**: 연산자 `OP` (`+`, `-`, `*`, `/`)를 해싱하여 81바이트 간격의 4개 연산자 전용 루틴(`972`, `1134`, `1215`, `1296`번지)으로 분기합니다.
   - **2차 분기**: 정규화된 두 피연산자 `X`, `Y`와 연산자별 마스크(`t1 = 49205`, `t2 = 29522`)를 결합해 400개의 27바이트 간격 핸들러 주소로 분기합니다.

4. **고정 상수 풀(`Pool 1`, `Pool 2`) 기반 19바이트 결과 합성 핸들러**
   - 400개 핸들러는 각각 고정된 14바이트 상수 풀(`Pool 1`: `128..134`번지, `Pool 2`: `136..142`번지) 위를 지나가며 `{nop, rotr, crz}` 명령어 조합만으로 두 자리 결과 문자열(`" 0"` ~ `"81"`, `"-1"` ~ `"-9"`, 0으로 나눌 때 `"ER"`)을 합성해 출력합니다.

### 실행 방법

1. **대화형 모드**: `python run_calculator.py`
2. **단일 수식 및 VM 점프 트레이스 확인**: `python run_calculator.py "7*8" -t`
3. **`.mal` 재컴파일 및 400개 수식 전수 검증**: `python compile_full_calculator.py`
