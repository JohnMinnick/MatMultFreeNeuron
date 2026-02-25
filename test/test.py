# SPDX-FileCopyrightText: © 2025 John Minnick
# SPDX-License-Identifier: Apache-2.0

"""
Cocotb verification suite for tt_um_matmul_free -- MatMul-Free Streaming Neuron.

Implements two test cases:
  1. test_ternary_mac:      100-cycle random stress test with Python golden model.
  2. test_saturation_clamp: Targeted edge cases proving the 8-bit output saturation
                            clamp works correctly for both positive and negative overflow.
"""

import cocotb
import random
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, ClockCycles


# ---------------------------------------------------------------------------
# Helper: Convert unsigned Python int to signed 8-bit (Two's Complement)
# ---------------------------------------------------------------------------
def to_signed_8(val):
    """Convert an unsigned 8-bit value [0..255] to signed [-128..+127]."""
    val = val & 0xFF
    if val >= 128:
        return val - 256
    return val


# ---------------------------------------------------------------------------
# Helper: Drive one ternary MAC cycle
# ---------------------------------------------------------------------------
async def drive_mac_cycle(dut, activation, weight_code, valid=1):
    """
    Drive a single MAC cycle on the DUT.

    Args:
        dut:         Cocotb DUT handle.
        activation:  Signed 8-bit integer [-128..+127] to drive on ui_in.
        weight_code: 2-bit ternary weight encoding (0=nop, 1=add, 2=sub).
        valid:       Whether to assert the valid strobe (default=1).
    """
    # Convert signed activation to unsigned 8-bit representation for the bus
    act_unsigned = activation & 0xFF

    # Build uio_in: [3]=0 (no clear), [2]=valid, [1:0]=weight_code
    uio_val = (valid << 2) | (weight_code & 0x03)

    dut.ui_in.value = act_unsigned
    dut.uio_in.value = uio_val

    # Advance one clock cycle -- rising edge latches the data
    await RisingEdge(dut.clk)


# ---------------------------------------------------------------------------
# Helper: Read the saturated output after a falling edge
# ---------------------------------------------------------------------------
async def read_output(dut):
    """
    Wait for falling edge (avoids delta-cycle race) and return the signed
    8-bit output value from uo_out.
    """
    await FallingEdge(dut.clk)
    return dut.uo_out.value.signed_integer


# ---------------------------------------------------------------------------
# Test 1: 100-cycle random ternary MAC stress test
# ---------------------------------------------------------------------------
@cocotb.test()
async def test_ternary_mac(dut):
    """
    Random stress test: stream 100 random activations with random ternary
    weights and verify the saturated output matches a Python golden model.
    """
    dut._log.info("=== Test 1: 100-cycle random ternary MAC ===")

    # Start the 10us period clock (100 KHz)
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())

    # ── Reset sequence ──
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1

    # ── Clear accumulator pulse ──
    # Set clear_acc (uio_in[3]) high for one cycle to guarantee clean state
    dut.uio_in.value = 0x08  # bit 3 = clear_acc
    await RisingEdge(dut.clk)
    dut.uio_in.value = 0x00
    await RisingEdge(dut.clk)

    # ── Python golden accumulator (unbounded) ──
    python_acc = 0

    # Seed the random module for reproducibility within Cocotb's seed
    NUM_CYCLES = 100

    for i in range(NUM_CYCLES):
        # Generate random signed 8-bit activation [-128, +127]
        x = random.randint(-128, 127)

        # Generate random ternary weight code: 0=nop, 1=add, 2=sub
        w = random.choice([0, 1, 2])

        # Drive the DUT
        await drive_mac_cycle(dut, x, w, valid=1)

        # Update Python golden model
        if w == 1:
            python_acc += x
        elif w == 2:
            python_acc -= x
        # w == 0: no-op

        # Expected saturated 8-bit output
        expected = max(-128, min(127, python_acc))

        # Read DUT output (wait for falling edge to avoid race)
        actual = await read_output(dut)

        dut._log.info(
            f"Cycle {i:3d}: x={x:4d}, w={w}, acc={python_acc:6d}, "
            f"expected={expected:4d}, actual={actual:4d}"
        )
        assert actual == expected, (
            f"MISMATCH at cycle {i}: x={x}, w={w}, python_acc={python_acc}, "
            f"expected={expected}, actual={actual}"
        )

    dut._log.info(f"=== PASSED: {NUM_CYCLES} random MAC cycles ===")


# ---------------------------------------------------------------------------
# Test 2: Targeted saturation clamp edge cases
# ---------------------------------------------------------------------------
@cocotb.test()
async def test_saturation_clamp(dut):
    """
    Inject specific test vectors to intentionally overflow and underflow the
    16-bit accumulator, proving the 8-bit output saturation clamp works.
    """
    dut._log.info("=== Test 2: Saturation clamp edge cases ===")

    # Start the 10us period clock (100 KHz)
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())

    # ── Reset sequence ──
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1

    # ── Clear accumulator ──
    dut.uio_in.value = 0x08
    await RisingEdge(dut.clk)
    dut.uio_in.value = 0x00
    await RisingEdge(dut.clk)

    python_acc = 0

    # ── Part A: Drive accumulator positive past +127 ──
    dut._log.info("Part A: Positive overflow -- streaming x=127, w=+1")
    for i in range(5):
        await drive_mac_cycle(dut, 127, 1, valid=1)  # +127 each cycle
        python_acc += 127
        expected = max(-128, min(127, python_acc))
        actual = await read_output(dut)

        dut._log.info(
            f"  +OVF cycle {i}: acc={python_acc:6d}, "
            f"expected={expected:4d}, actual={actual:4d}"
        )
        assert actual == expected, (
            f"Positive overflow mismatch at cycle {i}: "
            f"acc={python_acc}, expected={expected}, actual={actual}"
        )

    # Verify we are indeed clamped at +127
    assert python_acc > 127, f"Accumulator should exceed +127, got {python_acc}"
    actual = dut.uo_out.value.signed_integer
    assert actual == 127, f"Output should be clamped to +127, got {actual}"
    dut._log.info(f"  Confirmed: acc={python_acc}, output clamped to +127 [OK]")

    # ── Part B: Clear and drive accumulator negative past -128 ──
    dut._log.info("Part B: Negative overflow -- clear then stream x=127, w=-1")
    dut.uio_in.value = 0x08  # clear_acc
    await RisingEdge(dut.clk)
    dut.uio_in.value = 0x00
    await RisingEdge(dut.clk)
    python_acc = 0

    for i in range(5):
        await drive_mac_cycle(dut, 127, 2, valid=1)  # -127 each cycle
        python_acc -= 127
        expected = max(-128, min(127, python_acc))
        actual = await read_output(dut)

        dut._log.info(
            f"  -OVF cycle {i}: acc={python_acc:6d}, "
            f"expected={expected:4d}, actual={actual:4d}"
        )
        assert actual == expected, (
            f"Negative overflow mismatch at cycle {i}: "
            f"acc={python_acc}, expected={expected}, actual={actual}"
        )

    # Verify we are indeed clamped at -128
    assert python_acc < -128, f"Accumulator should be below -128, got {python_acc}"
    actual = dut.uo_out.value.signed_integer
    assert actual == -128, f"Output should be clamped to -128, got {actual}"
    dut._log.info(f"  Confirmed: acc={python_acc}, output clamped to -128 [OK]")

    # ── Part C: Clear and verify output returns to 0 ──
    dut._log.info("Part C: Clear after saturation -- verify output = 0")
    dut.uio_in.value = 0x08  # clear_acc
    await RisingEdge(dut.clk)
    dut.uio_in.value = 0x00
    actual = await read_output(dut)
    assert actual == 0, f"After clear, output should be 0, got {actual}"
    dut._log.info(f"  Confirmed: clear_acc resets output to 0 [OK]")

    # ── Part D: Verify weight=0 (no-op) holds accumulator ──
    dut._log.info("Part D: Weight=0 no-op -- accumulator should hold")
    # First, put a known value in the accumulator
    await drive_mac_cycle(dut, 42, 1, valid=1)  # acc = +42
    python_acc = 42
    actual = await read_output(dut)
    assert actual == 42, f"Expected 42, got {actual}"

    # Now stream with weight=0 -- should hold at 42
    for i in range(3):
        await drive_mac_cycle(dut, 100, 0, valid=1)  # weight=0, should be no-op
        actual = await read_output(dut)
        assert actual == 42, f"Weight=0 should hold, expected 42, got {actual}"

    # Also test weight=3 (2'b11) -- should also be no-op
    await drive_mac_cycle(dut, 100, 3, valid=1)  # weight=3, should be no-op
    actual = await read_output(dut)
    assert actual == 42, f"Weight=3 should hold, expected 42, got {actual}"
    dut._log.info(f"  Confirmed: weight=0 and weight=3 both hold accumulator [OK]")

    # ── Part E: Verify valid=0 gates accumulation ──
    dut._log.info("Part E: Valid=0 -- accumulation should be gated")
    await drive_mac_cycle(dut, 100, 1, valid=0)  # valid=0, should not accumulate
    actual = await read_output(dut)
    assert actual == 42, f"Valid=0 should gate, expected 42, got {actual}"
    dut._log.info(f"  Confirmed: valid=0 gates accumulation [OK]")

    dut._log.info("=== PASSED: All saturation and edge case tests ===")
