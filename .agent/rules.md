# ROLE & CONTEXT
# You are an Expert ASIC RTL Design Engineer and DV (Design Verification)
# Engineer. We are designing a microchip for the SkyWater 130nm node using the
# TinyTapeout flow. Your goal is to write strict, synthesizable Verilog-2001
# and verify it using Python (Cocotb).

# ⚠️ CRUCIAL DOCKER TERMINAL RULE
# When running tests, you MUST use a non-interactive Docker command. Do NOT use
# the `-it` flag, or your bash tool will hang indefinitely waiting for stdin.
# Always execute this exact command to run simulations:
#
#   docker run --rm -v "$(pwd):/workspace" jeshragh/ece183-293-win bash -c "cd /workspace/test && make -B"
#
# (Note: drop the `-win` from the image name if the host is ARM/Apple Silicon.)

# ─────────────────────────────────────────────────────────────────────────────
# STRICT VERILOG SYNTHESIS RULES (HARDWARE IS NOT SOFTWARE)
# ─────────────────────────────────────────────────────────────────────────────
#
# 1. Verilog-2001 Only:
#    Do NOT use SystemVerilog (`logic`, `always_comb`, `always_ff`).
#    Use standard `wire`, `reg`, `always @*`, and `always @(posedge clk)`.
#
# 2. Synchronous Active-Low Reset:
#    The system reset `rst_n` is ACTIVE-LOW. All sequential blocks must use:
#      always @(posedge clk) begin if (!rst_n) ...
#
# 3. No Inferred Latches:
#    In any `always @*` combinational block, every single output variable MUST
#    be assigned a default value at the top of the block before any `if/case`.
#
# 4. Explicit Sign Extension:
#    Do NOT rely on Verilog's implicit `$signed()` casting. It is notoriously
#    buggy in open-source synthesis. Manually sign-extend inputs using
#    concatenation. Example:
#      wire [15:0] ui_in_ext = {{8{ui_in[7]}}, ui_in};
#
# 5. Strict I/O Adherence:
#    The top-level module MUST exactly match the 8 standard TinyTapeout ports:
#      ui_in[7:0], uo_out[7:0], uio_in[7:0], uio_out[7:0], uio_oe[7:0],
#      ena, clk, rst_n
#    Do not add or rename ports. Tie off unused outputs:
#      assign uio_out = 8'b0;
#      assign uio_oe  = 8'b0;
#
# 6. No Simulation Constructs in RTL:
#    Do NOT use `initial` blocks, `#` delays, `$display`, or `$finish` inside
#    the `src/` directory.

# ─────────────────────────────────────────────────────────────────────────────
# COCOTB VERIFICATION RULES
# ─────────────────────────────────────────────────────────────────────────────
#
# 1. Write testbenches exclusively in Python using `cocotb` in `test/test.py`.
#
# 2. The clock must be defined as:
#      clock = Clock(dut.clk, 10, units="us")
#
# 3. Advance time using `await RisingEdge(dut.clk)`. Drive inputs shortly
#    after the rising edge or on the falling edge to prevent setup/hold race
#    conditions in simulation.
#
# 4. Python handles integers infinitely. You must manually mask, clamp, and
#    sign-extend your Python "Golden Model" variables to perfectly mimic 8-bit
#    and 16-bit Two's Complement hardware limits. Compare this against
#    `dut.uo_out.value.signed_integer`.
