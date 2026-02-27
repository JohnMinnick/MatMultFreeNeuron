![](../../workflows/gds/badge.svg) ![](../../workflows/docs/badge.svg) ![](../../workflows/test/badge.svg) ![](../../workflows/fpga/badge.svg)

# MatMul-Free Streaming Neuron

A hardware implementation of the ternary-weight dense layer from [**"Scalable MatMul-free Language Modeling"**](https://arxiv.org/abs/2406.02528) (Zhu et al., 2024), built for the [TinyTapeout](https://tinytapeout.com) SkyWater 130nm shuttle.

> **Key idea:** Replace expensive matrix multipliers with pure ternary addition/subtraction. Each weight is encoded as {-1, 0, +1}, so a "multiply-accumulate" becomes just add, subtract, or skip — no DSP required.

📄 [Full project documentation](docs/info.md)

---

## Architecture

The design implements a **sequential streaming datapath** where activations and weights are fed one pair per clock cycle into a central accumulator. Figure 1 animates the full datapath from input to saturated output.

<p align="center">
  <img src="docs/architecture_datapath.gif" alt="Figure 1: Animated block diagram of the streaming ternary MAC unit datapath" width="700"/>
</p>
<p align="center"><em>Figure 1: Streaming ternary MAC datapath. Data flows left-to-right: 8-bit activation is sign-extended
to 16 bits, passed through a ternary weight MUX (+1/add, -1/subtract, 0/hold), accumulated in a 16-bit
register, and saturated to 8-bit signed output. The accumulator feeds back into the MUX for iterative accumulation.</em></p>

### Weight Encoding (`uio_in[1:0]`)

| Code | Weight | Operation |
|------|--------|-----------|
| `2'b01` | +1 | `acc += activation` |
| `2'b10` | -1 | `acc -= activation` |
| `2'b00` | 0 | Hold (no-op) |
| `2'b11` | 0 | Hold (reserved) |

### Pin Mapping

| Pin | Direction | Signal |
|-----|-----------|--------|
| `ui_in[7:0]` | Input | 8-bit signed activation |
| `uo_out[7:0]` | Output | 8-bit signed saturated result |
| `uio_in[0]` | Input | weight_bit_0 |
| `uio_in[1]` | Input | weight_bit_1 |
| `uio_in[2]` | Input | valid (gates accumulation) |
| `uio_in[3]` | Input | clear_acc (synchronous reset) |

---

## Timing Diagram

Figure 2 shows a 5-cycle MAC operation demonstrating the accumulator building up across cycles, including a saturation event in cycle 5 where the internal 16-bit value (130) exceeds the 8-bit signed maximum (+127).

<p align="center">
  <img src="docs/timing_diagram.gif" alt="Figure 2: Timing diagram showing 5 clock cycles of MAC operation with saturation" width="700"/>
</p>
<p align="center"><em>Figure 2: Timing diagram of a 5-cycle MAC sequence. Signals shown: clock, valid strobe,
activation values, ternary weight codes (color-coded: green=+1, red=-1, gray=0), 16-bit accumulator
state, and 8-bit saturated output. Cycle 5 triggers output saturation (130 → 127, shown in red).</em></p>

**Cycle-by-cycle trace:**

| Cycle | Activation | Weight | Accumulator | Output (8-bit) |
|-------|-----------|--------|-------------|----------------|
| 1 | +50 | +1 | 50 | 50 |
| 2 | +30 | +1 | 80 | 80 |
| 3 | +20 | -1 | 60 | 60 |
| 4 | +100 | 0 | 60 | 60 |
| 5 | +70 | +1 | 130 | **127 (saturated)** |

---

## Output Saturation

The 16-bit accumulator is clamped to the 8-bit signed range [-128, +127] before driving the output bus. This saturation acts as a hardware **hard-clipping activation function**, similar to `hardtanh` in PyTorch. Figure 3 shows the transfer characteristic.

<p align="center">
  <img src="docs/saturation_clamp.gif" alt="Figure 3: Output saturation transfer function from 16-bit accumulator to 8-bit output" width="700"/>
</p>
<p align="center"><em>Figure 3: Saturation clamp transfer function. The green linear region passes accumulator
values directly as output. Beyond +127 or below -128, the output is clamped (red flat regions),
preventing overflow and providing a bounded nonlinearity.</em></p>

---

## Design Decisions & Technical Justification

### Why Ternary Weights?
Standard neural network accelerators require costly hardware multipliers (DSPs) for weight×activation products. By constraining weights to {-1, 0, +1}, each "multiplication" reduces to a simple **add, subtract, or skip** — eliminating multipliers entirely. This is the core insight from Zhu et al., enabling dramatically smaller silicon area on resource-constrained nodes like SkyWater 130nm.

### Why Explicit Sign-Extension?
Open-source synthesis tools (Yosys, used in the TinyTapeout OpenLane flow) handle Verilog's `$signed()` casting inconsistently, sometimes producing incorrect bit-extension during elaboration. We use explicit concatenation (`{{8{ui_in[7]}}, ui_in}`) which is guaranteed correct regardless of tool version — a critical reliability decision for a physical tapeout.

### Why a 16-bit Accumulator?
An 8-bit activation added up to 256 times (the maximum reasonable layer width) could reach ±32,768 — exactly the 16-bit signed range. The 16-bit accumulator provides sufficient dynamic range for realistic layer sizes while keeping register cost minimal (16 flip-flops).

### Why Saturation Instead of Truncation?
Truncating the lower bits would produce **wrap-around artifacts** (e.g., a large positive value suddenly becoming negative), which is catastrophic for neural network inference. Saturation clamp preserves the **sign and magnitude intent** of the computation, and is the standard approach in quantized inference hardware (see NVIDIA's INT8 tensor cores).

---

## Verification

The [Cocotb test suite](test/test.py) provides comprehensive functional verification:

| Test | Vectors | Description |
|------|---------|-------------|
| `test_ternary_mac` | 100 | Random stress test with Python golden model |
| `test_saturation_clamp` | 15+ | Positive/negative overflow, clear, weight hold, valid gating |

### Verification Metrics

| Metric | Result |
|--------|--------|
| Total test cases | 2 |
| Total assertion points | 115+ |
| Random MAC vectors | 100 |
| Saturation edge cases | 5 sub-tests (overflow+, overflow-, clear, weight hold, valid gate) |
| Pass rate | **100% (PASS=2, FAIL=0)** |
| Icarus Verilog warnings | 0 |

### Run locally via Docker

```bash
docker run --rm -v "$(pwd):/workspace" jeshragh/ece183-293-win \
  bash -c "cd /workspace/test && make -B"
```

### Expected output

```
TESTS=2 PASS=2 FAIL=0 SKIP=0
```

---

## Design Constraints

This is strictly **synthesizable Verilog-2001** adhering to the following rules:
- **No SystemVerilog** — only `wire`, `reg`, `always @*`, `always @(posedge clk)`
- **Explicit sign-extension** — concatenation only, no `$signed()` casting
- **No inferred latches** — default assignments in all combinational blocks
- **Synchronous active-low reset** — `rst_n` with priority over all other control
- **Standard TinyTapeout I/O** — 8 ports, unused bidirectional pins tied off

---

## References

- Zhu, R., Zhang, Y., Sifferman, E., et al. (2024). *Scalable MatMul-free Language Modeling.* [arXiv:2406.02528](https://arxiv.org/abs/2406.02528)
- [TinyTapeout](https://tinytapeout.com) — educational ASIC shuttle program
- Animations generated with [Manim Community Edition](https://www.manim.community/)
