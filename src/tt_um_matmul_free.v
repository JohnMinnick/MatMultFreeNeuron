/*
 * MatMul-Free Streaming Neuron — Ternary MAC Unit
 * Implements Section 6.1 of "Scalable MatMul-free Language Modeling" (Zhu et al.)
 *
 * Architecture: Sequential / streaming design for TinyTapeout (SkyWater 130nm).
 * Over N clock cycles, 8-bit signed activations and 2-bit ternary weights are
 * streamed into a 16-bit internal accumulator. The output is the accumulator
 * value saturated (clamped) to 8-bit signed range [-128, +127].
 *
 * Weight encoding (uio_in[1:0]):
 *   2'b01 → weight = +1 (accumulate + activation)
 *   2'b10 → weight = -1 (accumulate - activation)
 *   2'b00 → weight =  0 (hold / no-op)
 *   2'b11 → weight =  0 (hold / no-op, reserved)
 *
 * Control signals:
 *   uio_in[2] → valid   : gates accumulation
 *   uio_in[3] → clear_acc : synchronous accumulator clear
 *
 * Copyright (c) 2025 John Minnick
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tt_um_matmul_free (
    input  wire [7:0] ui_in,    // 8-bit signed activation input
    output wire [7:0] uo_out,   // 8-bit signed saturated output
    input  wire [7:0] uio_in,   // IOs: weight[1:0], valid, clear_acc
    output wire [7:0] uio_out,  // IOs: Output path (unused, directly tied off)
    output wire [7:0] uio_oe,   // IOs: Enable path (unused, tied low = input)
    input  wire       ena,      // TinyTapeout enable (high when design selected)
    input  wire       clk,      // System clock
    input  wire       rst_n     // Active-low synchronous reset
);

    // ─────────────────────────────────────────────────────────────────────
    // Tie off unused bidirectional outputs
    // ─────────────────────────────────────────────────────────────────────
    assign uio_out = 8'b0;
    assign uio_oe  = 8'b0;

    // ─────────────────────────────────────────────────────────────────────
    // Signal aliases for readability
    // ─────────────────────────────────────────────────────────────────────
    wire [1:0] weight    = uio_in[1:0];  // Ternary weight encoding
    wire       valid     = uio_in[2];    // Valid strobe — gates MAC
    wire       clear_acc = uio_in[3];    // Synchronous accumulator clear

    // ─────────────────────────────────────────────────────────────────────
    // Explicit sign-extension of 8-bit activation to 16 bits
    // NOTE: We do NOT use $signed() — open-source synthesis tools handle
    //       it inconsistently. Explicit concatenation is always correct.
    // ─────────────────────────────────────────────────────────────────────
    wire [15:0] act_ext = {{8{ui_in[7]}}, ui_in};

    // ─────────────────────────────────────────────────────────────────────
    // 16-bit signed accumulator (sequential state)
    // ─────────────────────────────────────────────────────────────────────
    reg [15:0] accumulator;

    always @(posedge clk) begin
        if (!rst_n || clear_acc) begin
            // Active-low reset OR explicit clear → zero the accumulator
            accumulator <= 16'd0;
        end else if (ena && valid) begin
            // Ternary MAC operation — only when enabled and valid
            case (weight)
                2'b01:   accumulator <= accumulator + act_ext;  // Weight +1
                2'b10:   accumulator <= accumulator - act_ext;  // Weight -1
                default: accumulator <= accumulator;            // Weight 0 (hold)
            endcase
        end
    end

    // ─────────────────────────────────────────────────────────────────────
    // Combinational saturation clamp: 16-bit accumulator → 8-bit output
    //
    // Strategy: Check the upper byte (accumulator[15:8]) to determine if
    // the value is within the signed 8-bit range [-128, +127].
    //
    // For a signed 16-bit number in range [-128, +127]:
    //   - Positive in-range: accumulator[15:7] == 9'b000000000
    //   - Negative in-range: accumulator[15:7] == 9'b111111111
    //   - Positive overflow:  accumulator[15] == 0 AND any of [14:7] != 0
    //   - Negative overflow:  accumulator[15] == 1 AND any of [14:7] != 1
    //
    // Simplified: if accumulator[15:7] is all-zeros or all-ones, the value
    // fits in 8 bits. Otherwise we saturate.
    // ─────────────────────────────────────────────────────────────────────
    reg [7:0] uo_out_reg;

    always @* begin
        // Default assignment — prevents latch inference
        uo_out_reg = accumulator[7:0];

        if (accumulator[15] == 1'b0 && accumulator[15:7] != 9'b000000000) begin
            // Positive overflow: accumulator > +127 → clamp to +127
            uo_out_reg = 8'h7F;
        end else if (accumulator[15] == 1'b1 && accumulator[15:7] != 9'b111111111) begin
            // Negative overflow: accumulator < -128 → clamp to -128
            uo_out_reg = 8'h80;
        end
        // else: value fits in 8-bit signed range → pass through lower byte
    end

    assign uo_out = uo_out_reg;

endmodule
