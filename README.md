![](../../workflows/gds/badge.svg) ![](../../workflows/docs/badge.svg) ![](../../workflows/test/badge.svg) ![](../../workflows/fpga/badge.svg)

# MatMul-Free Streaming Neuron

A hardware implementation of the ternary-weight dense layer from [**"Scalable MatMul-free Language Modeling"**](https://arxiv.org/abs/2406.02528) (Zhu et al., 2024), built for the [TinyTapeout](https://tinytapeout.com) SkyWater 130nm shuttle.

> **Key idea:** Replace expensive matrix multipliers with pure ternary addition/subtraction. Each weight is encoded as {-1, 0, +1}, so a "multiply-accumulate" becomes just add, subtract, or skip — no DSP required.

📄 [Full project documentation →](docs/info.md)

## Architecture

```
ui_in[7:0] ──► sign-extend to 16b ──► ternary MUX ──► accumulator[15:0] ──► saturate ──► uo_out[7:0]
                                        ▲
uio_in[1:0] (weight encoding) ─────────┘
uio_in[2]   (valid strobe)
uio_in[3]   (clear_acc)
```

Over *N* clock cycles, 8-bit signed activations and 2-bit ternary weights are streamed into a **16-bit internal accumulator**. The output is the accumulator value **saturated to the 8-bit signed range** [-128, +127], acting as a built-in activation function.

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

## Design Constraints

This is strictly **synthesizable Verilog-2001** following these rules:
- No SystemVerilog constructs (`logic`, `always_comb`, `always_ff`)
- Explicit sign-extension via concatenation (no `$signed()`)
- Default assignments in all combinational blocks (no inferred latches)
- Synchronous active-low reset (`rst_n`)

## Verification

The [Cocotb test suite](test/test.py) includes:

| Test | Description |
|------|-------------|
| `test_ternary_mac` | 100-cycle random stress test with Python golden model |
| `test_saturation_clamp` | Positive/negative overflow, clear, weight hold, valid gating |

### Run locally via Docker

```bash
docker run --rm -v "$(pwd):/workspace" jeshragh/ece183-293-win \
  bash -c "cd /workspace/test && make -B"
```

### Expected output

```
TESTS=2 PASS=2 FAIL=0 SKIP=0
```

## References

- Zhu, R., Zhang, Y., Sifferman, E., et al. (2024). *Scalable MatMul-free Language Modeling.* [arXiv:2406.02528](https://arxiv.org/abs/2406.02528)
- [TinyTapeout](https://tinytapeout.com) — educational ASIC shuttle program
