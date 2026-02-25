# 🧠 IMPLEMENTATION_PLAN.md: MatMul-Free Streaming Neuron

## 1. System Context & Objective
You are an Expert ASIC RTL Architect and Verification Engineer. We are designing a digital microchip for the SkyWater 130nm node using the TinyTapeout flow.
Your goal is to implement the core hardware primitive from the paper "Scalable MatMul-free Language Modeling" (Zhu et al.) — specifically **Section 6.1: MatMul-free Dense Layers with Ternary Weights**, where dense multipliers are replaced with pure ternary addition/subtraction.

Due to the strict 8-pin I/O limitation of the TinyTapeout wrapper, we are implementing a **Sequential / Streaming Architecture**. Over $N$ clock cycles, we will stream 8-bit signed activations and 2-bit ternary weights into an internal 16-bit accumulator.

## 2. STRICT ENGINEERING RULES (CRITICAL)
1. **Hardware is not Software:** Write strictly synthesizable Verilog-2001. NO SystemVerilog (`logic`, `always_comb`, `always_ff`). Use standard `wire`, `reg`, `always @*`, and `always @(posedge clk)`. No `initial` blocks or `#` delays in RTL.
2. **Synchronous Active-Low Reset:** The reset `rst_n` is ACTIVE-LOW. All sequential blocks must strictly use: `always @(posedge clk) begin if (!rst_n) ...`
3. **Explicit Sign Extension:** Do NOT rely on `$signed()` casting for bit-extension. It is notoriously buggy in open-source synthesis tools. Use explicit concatenation. Example: `wire [15:0] act_ext = {{8{ui_in[7]}}, ui_in};`.
4. **No Inferred Latches:** All combinatorial `always @*` blocks must have default assignments for every variable at the top of the block before any `if/case` statements.
5. **Exact I/O Match:** The top-level module `tt_um_matmul_free` MUST strictly use the 8 standard TinyTapeout ports: `input  wire [7:0] ui_in`, `output wire [7:0] uo_out`, `input  wire [7:0] uio_in`, `output wire [7:0] uio_out`, `output wire [7:0] uio_oe`, `input  wire ena`, `input  wire clk`, `input  wire rst_n`. Tie off unused outputs: `assign uio_out = 8'b0; assign uio_oe = 8'b0;`.
6. **Execution Environment:** When asked to run tests, use non-interactive commands. Do NOT use the `-it` flag. 
   - If executing from the host machine via Docker, use: `docker run --rm -v "$(pwd):/workspace" jeshragh/ece183-293-win bash -c "cd /workspace/test && make -B"` (drop `-win` if on ARM/Mac).
   - If executing directly inside the Devcontainer shell, simply run: `cd test && make -B`.

## 3. PHASE 1: Template Patching
The provided class template has known compatibility issues with newer Cocotb versions. Apply these fixes to the files in the `test/` directory:
1. Open `test/test.py`. Change line 13 from `unit="us"` to `units="us"`.
2. Open `test/Makefile`. Around line 43, immediately under the `COCOTB_TEST_MODULES` definition, add: `MODULE ?= $(COCOTB_TEST_MODULES)`.
3. **Action:** Run the `make -B` execution command to ensure the dummy template passes the smoke test before writing any RTL.

## 4. PHASE 2: OpenLane Physical Configuration (The Virtual Tapeout Space Cheat)
Since this is a virtual tapeout, we have permission to use a larger physical silicon footprint to guarantee OpenLane physical synthesis passes without density/congestion errors.
1. Open `info.yaml`.
2. Set `top_module: tt_um_matmul_free`.
3. Change `source_files` to `- src/tt_um_matmul_free.v` (You will create this file in Phase 3).
4. **CRITICAL:** Change the `tiles` parameter to `2x2` (gives us 4x the standard logic gates and routing space).
5. Update the `pinout` section to logically match our architecture:
   - `ui_in[7:0]`: "activation_in"
   - `uo_out[7:0]`: "activation_out"
   - `uio_in[0]`: "weight_bit_0"
   - `uio_in[1]`: "weight_bit_1"
   - `uio_in[2]`: "valid"
   - `uio_in[3]`: "clear_acc"

## 5. PHASE 3: RTL Architecture (`src/tt_um_matmul_free.v`)
Create the main Verilog module at `src/tt_um_matmul_free.v`. Delete the placeholder `src/project.v` if present.
**Logic Specification:**
1. **State:** Declare a 16-bit signed accumulator: `reg signed [15:0] accumulator;`.
2. **Sequential Logic (`always @(posedge clk)`):**
   - If `!rst_n` OR `uio_in[3]` (clear_acc) is high, `accumulator <= 16'sd0;`.
   - Else if `ena` AND `uio_in[2]` (valid) are high, perform the ternary MAC:
     - Explicitly sign-extend `ui_in` to 16 bits.
     - Weight Encoding (`uio_in[1:0]`):
       - `2'b01` (Weight +1): `accumulator <= accumulator + sign_extended_ui_in;`
       - `2'b10` (Weight -1): `accumulator <= accumulator - sign_extended_ui_in;`
       - `2'b00` or `2'b11` (Weight 0): Do nothing (accumulator holds its value).
3. **Combinatorial Saturation (`always @*` or `assign`):**
   - Clamp the 16-bit signed `accumulator` to an 8-bit signed output `uo_out` ([-128, 127]) to act as the activation function and fit the output bus.
   - If the 16-bit `accumulator > 127`, `uo_out = 8'sd127` (or `8'h7F`).
   - If the 16-bit `accumulator < -128`, `uo_out = -8'sd128` (or `8'h80`).
   - Else, `uo_out = accumulator[7:0]`.

## 6. PHASE 4: Cocotb Verification (`test/tb.v` & `test/test.py`)
1. Update `test/tb.v` to instantiate `tt_um_matmul_free` instead of the dummy project. Make sure the instance name remains whatever `test.py` expects (usually `uut` or `user_project`), and connect all standard TT ports properly.
2. In `test/test.py`, delete the existing dummy test logic and write a comprehensive validation suite:
   - Initialize clock (`units="us"`).
   - Assert `rst_n` low, then high.
   - Pulse `uio_in[3]` (clear_acc) to ensure a clean state.
   - Maintain a Python-side golden accumulator (`python_acc = 0`).
   - **Main Loop (100 cycles):**
     - Generate a random 8-bit signed integer `x` `[-128, 127]` for activation.
     - Generate a random ternary weight `w` mapped to `uio_in[1:0]` (`1` for add, `2` for sub, `0` for ignore).
     - Set `valid` high (`uio_in[2] = 1`). Drive the pins.
     - In Python: if `w == 1`, `python_acc += x`. If `w == 2`, `python_acc -= x`.
     - Calculate Python expected output: `expected = max(-128, min(127, python_acc))`.
     - `await RisingEdge(dut.clk)` to advance time.
     - Wait for `FallingEdge(dut.clk)` before reading the output to avoid delta-cycle race conditions.
     - `assert dut.uo_out.value.signed_integer == expected`.
   - **Edge Cases:** Inject specific test vectors designed to intentionally drive the internal accumulator sequentially above +127 and below -128 (e.g., streaming `x = 127` with weight `1` multiple times) to mathematically prove the hardware saturation clamp works correctly.

## 7. PHASE 5: Autonomous Execution & Debug Loop
Execute the test command. If the Cocotb assertion fails or synthesis throws warnings, read the terminal output, analyze where your Verilog logic or Python golden model misaligned, fix the code, and rerun. Pay special attention to Python's handling of Two's Complement math vs Verilog's. Loop this autonomously until tests pass 100%.