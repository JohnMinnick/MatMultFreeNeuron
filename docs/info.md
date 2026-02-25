<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

This design implements a **MatMul-Free Streaming Neuron** based on Section 6.1 of "Scalable MatMul-free Language Modeling" (Zhu et al.). It replaces traditional dense matrix multipliers with pure ternary addition/subtraction.

**Architecture:** Over N clock cycles, 8-bit signed activations (`ui_in[7:0]`) and 2-bit ternary weights (`uio_in[1:0]`) are streamed into a 16-bit internal accumulator. The output (`uo_out[7:0]`) is the accumulator value saturated (clamped) to the signed 8-bit range [-128, +127], acting as a built-in activation function.

**Weight encoding (`uio_in[1:0]`):**
- `2'b01` → Weight = +1 (accumulate + activation)
- `2'b10` → Weight = -1 (accumulate - activation)
- `2'b00` → Weight =  0 (hold / no-op)
- `2'b11` → Weight =  0 (hold / no-op, reserved)

**Control signals:**
- `uio_in[2]` → **valid**: gates accumulation (must be high for MAC to execute)
- `uio_in[3]` → **clear_acc**: synchronous accumulator clear (resets to zero)

## How to test

1. Assert `rst_n` low for several clock cycles, then release high.
2. Pulse `uio_in[3]` (clear_acc) high for one cycle to zero the accumulator.
3. On each cycle, drive an 8-bit signed activation on `ui_in[7:0]` and a 2-bit ternary weight on `uio_in[1:0]`. Set `uio_in[2]` (valid) high to enable accumulation.
4. Read the saturated 8-bit signed result from `uo_out[7:0]` on the following clock edge.
5. The Cocotb test suite (`test/test.py`) provides a 100-cycle random stress test and targeted saturation edge cases. Run with: `cd test && make -B`.

## External hardware

No external hardware required. All I/O uses the standard TinyTapeout dedicated input/output pins.
