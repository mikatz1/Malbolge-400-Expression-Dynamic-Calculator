# Malbolge 400-Expression Dynamic Calculator (`calculator_400.mal`)

1998년 Ben Olmstead가 설계한 난해한 프로그래밍 언어 **말레볼제(Malbolge)**로 구현한 **사칙연산 계산기(`.mal`) 및 3진법 완전 해싱(Ternary Perfect Hashing) 컴파일러**입니다.

말레볼제는 덧셈/뺄셈 같은 산술 연산자와 조건문(`if`)이 전혀 존재하지 않고, 명령어가 실행될 때마다 암호화 테이블(`XLAT2`)에 의해 자폭(Self-modifying)하는 3진법 가상 머신($3^{10} = 59,049$ 워드)입니다. 본 프로젝트는 말레볼제의 유일한 연산 명령어인 **`crz` (Crazy 연산)**와 **`rotr` (10-trit 우측 순환 시프트)**, 그리고 **간접 점프(`jmp [d]`, `mov d, [d]`)**만을 조합하여 런타임 입력 `X OP Y` (`0~9`, `+, -, *, /`, `0~9` 총 400가지 수식)를 동적 해싱하고 정확한 계산 결과를 출력합니다.

---

## 주요 특징 (Key Features)

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

---

## 프로젝트 구조 (Repository Structure)

```text
.
├── calculator_400.mal         # 컴파일된 59,000바이트 순수 말레볼제 계산기 프로그램
├── compile_full_calculator.py # .mal 컴파일러 및 400개 입력 전수 검증 스크립트
├── run_calculator.py          # 대화형 CLI 실행기 및 VM 점프 트레이서
├── malbolge_vm.py             # 1998년 공식 명세 100% 호환 말bolge VM 인터프리터
├── test_minimal.py            # 단일 숫자 동적 해시-점프 최소 기능 검증 스크립트
├── test_mask_synthesis.py     # 데이터 포인터 순환 링(D=78..85) 10-trit 마스크 합성 검증
└── verification_report_400.txt# 400개 전체 수식의 Python 주소 vs VM 점프 주소 및 실행 로그
```

---

## 실행 방법 (Quick Start)

Python 3.8 이상이 설치되어 있으면 외부 라이브러리 없이 즉시 실행할 수 있습니다.

### 1. 대화형 모드로 계산기 실행
```bash
python run_calculator.py
```
프롬프트에 `[0-9][+-*/][0-9]` 형식의 수식(예: `7*8`, `3-9`, `8+5`, `9/2`, `5/0`)을 입력하면 말레볼제 VM이 `calculator_400.mal`을 실행하여 결과를 출력합니다.

### 2. 단일 수식 실행 및 VM 내부 점프 트레이스 확인 (`-t`)
```bash
python run_calculator.py "7*8" -t
```

**실행 출력 예시:**
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

### 3. `.mal` 재컴파일 및 400개 수식 전수 검증
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

---

## 메모리 맵 (Memory Layout)

| 주소 구간 | 용도 | 설명 |
| :---: | :--- | :--- |
| `0 .. 25` | **Entry Stub** | `D`를 `49`번지로 이동시키고 `slot 49`를 8회 회전시켜 `C = 442`번지로 점프 |
| `49 .. 142` | **Data Slots & Constant Pools** | 자기 되감기 슬롯(`49, 67, 78, 81, 96, 125`), 점프 포인터, `Pool 1`(`128..134`), `Pool 2`(`136..142`) |
| `442 .. 519` | **Main Preamble & Hash** | 첫 번째 숫자 `X` 정규화, 10-trit 마스크 `t1`/`t2` 합성, 연산자 `OP` 입력 및 1차 `jmp [96]` |
| `973 .. 1353` | **4 Operator Routines** | `-`(`973`), `/`(`1135`), `*`(`1216`), `+`(`1297`)별 `Y` 입력 및 `(X, Y)` 합성 후 2차 `jmp [125]` |
| `1539 .. 58987` | **400 Expression Handlers** | 27바이트 간격으로 배치된 400개의 19바이트 결과 출력 및 `halt` 핸들러 |
