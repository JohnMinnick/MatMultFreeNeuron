"""
Manim animations for the MatMul-Free Streaming Neuron README.
Generates three GIF figures:
  1. ArchitectureDatapath - shows the streaming MAC datapath
  2. TimingDiagram - shows clock-cycle-level signal timing
  3. SaturationClamp - shows the output saturation behavior

Render command (low quality, 8fps for small GIF):
  python -m manim render -ql -r 640,360 --fps 8 --format=gif docs/manim_figures.py <SceneName>
"""

from manim import *
import numpy as np


# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------
BG_COLOR = "#1a1a2e"
ACCENT_BLUE = "#4fc3f7"
ACCENT_GREEN = "#66bb6a"
ACCENT_RED = "#ef5350"
ACCENT_YELLOW = "#ffd54f"
ACCENT_PURPLE = "#ab47bc"
ACCENT_ORANGE = "#ffa726"
TEXT_COLOR = "#e0e0e0"
BOX_COLOR = "#16213e"
WIRE_COLOR = "#546e7a"


# =====================================================================
# Scene 1: Architecture Datapath
# =====================================================================
class ArchitectureDatapath(Scene):
    """Animated block diagram of the streaming ternary MAC unit."""

    def construct(self):
        self.camera.background_color = BG_COLOR

        # Title
        title = Text("Streaming Ternary MAC - Datapath", font_size=28,
                      color=ACCENT_BLUE, weight=BOLD)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title), run_time=0.6)

        # -- Build blocks --
        def make_block(label, width=2.0, height=0.8, color=ACCENT_BLUE):
            rect = RoundedRectangle(
                width=width, height=height, corner_radius=0.12,
                stroke_color=color, stroke_width=2, fill_color=BOX_COLOR,
                fill_opacity=0.8
            )
            txt = Text(label, font_size=14, color=color)
            return VGroup(rect, txt)

        # Input block
        inp = make_block("ui_in[7:0]\nActivation", width=2.0, height=0.8,
                         color=ACCENT_GREEN)
        inp.move_to(LEFT * 4.8)

        # Sign extension block
        sext = make_block("Sign Ext\n8b->16b", width=1.6, height=0.8,
                          color=ACCENT_YELLOW)
        sext.move_to(LEFT * 2.5)

        # Ternary MUX block
        mux = make_block("Ternary\nMUX", width=1.4, height=0.8,
                         color=ACCENT_ORANGE)
        mux.move_to(LEFT * 0.4)

        # Accumulator block
        acc = make_block("Accumulator\n16-bit", width=1.8, height=0.8,
                         color=ACCENT_PURPLE)
        acc.move_to(RIGHT * 1.8)

        # Saturate block
        sat = make_block("Saturate\n[-128,127]", width=1.6, height=0.8,
                         color=ACCENT_RED)
        sat.move_to(RIGHT * 4.0)

        # Output label
        out_label = Text("uo_out\n[7:0]", font_size=12,
                         color=ACCENT_GREEN)
        out_label.next_to(sat, RIGHT, buff=0.4)

        # Weight input (below MUX, offset to avoid overlap)
        weight_label = Text("uio_in[1:0]\nWeight", font_size=12,
                            color=ACCENT_YELLOW)
        weight_label.next_to(mux, DOWN, buff=1.0)

        # Control signals (below accumulator, offset to avoid overlap)
        ctrl_valid = Text("valid", font_size=11, color=ACCENT_GREEN)
        ctrl_clear = Text("clear_acc", font_size=11, color=ACCENT_RED)
        ctrls = VGroup(ctrl_valid, ctrl_clear).arrange(DOWN, buff=0.1)
        ctrls.next_to(acc, DOWN, buff=1.0)

        # -- Arrows --
        arr1 = Arrow(inp.get_right(), sext.get_left(), buff=0.08,
                     stroke_color=WIRE_COLOR, stroke_width=2.5, max_tip_length_to_length_ratio=0.15)
        arr2 = Arrow(sext.get_right(), mux.get_left(), buff=0.08,
                     stroke_color=WIRE_COLOR, stroke_width=2.5, max_tip_length_to_length_ratio=0.15)
        arr3 = Arrow(mux.get_right(), acc.get_left(), buff=0.08,
                     stroke_color=WIRE_COLOR, stroke_width=2.5, max_tip_length_to_length_ratio=0.15)
        arr4 = Arrow(acc.get_right(), sat.get_left(), buff=0.08,
                     stroke_color=WIRE_COLOR, stroke_width=2.5, max_tip_length_to_length_ratio=0.15)
        arr5 = Arrow(sat.get_right(), out_label.get_left(), buff=0.08,
                     stroke_color=WIRE_COLOR, stroke_width=2.5, max_tip_length_to_length_ratio=0.15)
        arr_w = Arrow(weight_label.get_top(), mux.get_bottom(), buff=0.08,
                      stroke_color=ACCENT_YELLOW, stroke_width=2, max_tip_length_to_length_ratio=0.2)
        arr_c = Arrow(ctrls.get_top(), acc.get_bottom(), buff=0.08,
                      stroke_color=ACCENT_RED, stroke_width=2, max_tip_length_to_length_ratio=0.2)

        # Feedback arrow from accumulator back to mux (arcs OVER the top)
        feedback = CurvedArrow(acc.get_top(), mux.get_top(),
                               angle=TAU/4, stroke_color=ACCENT_PURPLE,
                               stroke_width=2, tip_length=0.12)
        fb_label = Text("feedback", font_size=10, color=ACCENT_PURPLE)
        fb_label.next_to(feedback, UP, buff=0.05)

        # -- Animate: blocks appear left to right --
        self.play(FadeIn(inp), run_time=0.6)
        self.play(GrowArrow(arr1), FadeIn(sext), run_time=0.6)
        self.play(GrowArrow(arr2), FadeIn(mux), run_time=0.6)
        self.play(GrowArrow(arr3), FadeIn(acc), run_time=0.6)
        self.play(GrowArrow(arr4), FadeIn(sat), run_time=0.6)
        self.play(GrowArrow(arr5), FadeIn(out_label), run_time=0.6)
        self.play(FadeIn(weight_label), GrowArrow(arr_w), run_time=0.6)
        self.play(FadeIn(ctrls), GrowArrow(arr_c), run_time=0.6)
        self.play(Create(feedback), FadeIn(fb_label), run_time=0.8)

        # Data flow pulse animation
        self.wait(0.5)
        dot = Dot(color=ACCENT_GREEN, radius=0.1).move_to(inp.get_right())
        glow = dot.copy().set_opacity(0.3).scale(2)
        pulse = VGroup(glow, dot)
        self.play(FadeIn(pulse), run_time=0.3)
        for pt in [sext.get_center(), mux.get_center(),
                   acc.get_center(), sat.get_center(), out_label.get_left()]:
            self.play(pulse.animate.move_to(pt), run_time=0.5)
        self.play(FadeOut(pulse), run_time=0.3)
        self.wait(1.0)


# =====================================================================
# Scene 2: Timing Diagram
# =====================================================================
class TimingDiagram(Scene):
    """Timing diagram showing 5 MAC cycles with accumulator state."""

    def construct(self):
        self.camera.background_color = BG_COLOR

        title = Text("Timing Diagram - 5-Cycle MAC Operation", font_size=24,
                      color=ACCENT_BLUE, weight=BOLD)
        title.to_edge(UP, buff=0.25)
        self.play(Write(title), run_time=0.8)

        # Simulation data: (activation, weight_code, weight_label, acc_after)
        cycles = [
            (50,  1, "+1",  50),
            (30,  1, "+1",  80),
            (20,  2, "-1",  60),
            (100, 0, " 0",  60),
            (70,  1, "+1", 130),
        ]

        # Layout parameters
        x_start = -5.0
        x_step = 2.0
        y_base = 1.8
        row_gap = 0.6

        # Signal labels (positioned well to the left)
        labels = ["clk", "valid", "act[7:0]", "wt[1:0]", "acc[15:0]", "out[7:0]"]
        label_x = x_start - 0.6

        label_objs = []
        for i, lbl in enumerate(labels):
            y = y_base - i * row_gap
            t = Text(lbl, font_size=13, color=TEXT_COLOR)
            t.move_to([label_x, y, 0]).align_to([label_x, y, 0], RIGHT)
            label_objs.append(t)

        self.play(*[FadeIn(l) for l in label_objs], run_time=0.6)

        # Draw timing waveforms cycle by cycle
        for cyc_i, (act, wt, wt_lbl, acc_val) in enumerate(cycles):
            x = x_start + cyc_i * x_step
            x_end = x + x_step
            cyc_elements = VGroup()

            # Cycle number label
            cyc_num = Text(f"C{cyc_i+1}", font_size=11, color=ACCENT_BLUE)
            cyc_num.move_to([(x + x_end) / 2, y_base + 0.35, 0])
            cyc_elements.add(cyc_num)

            # Row 0: Clock square wave
            y_clk = y_base
            clk_hi, clk_lo = y_clk + 0.15, y_clk - 0.15
            clk_wave = VGroup(
                Line([x, clk_lo, 0], [x, clk_hi, 0], stroke_color=ACCENT_GREEN, stroke_width=2),
                Line([x, clk_hi, 0], [x + x_step/2, clk_hi, 0], stroke_color=ACCENT_GREEN, stroke_width=2),
                Line([x + x_step/2, clk_hi, 0], [x + x_step/2, clk_lo, 0], stroke_color=ACCENT_GREEN, stroke_width=2),
                Line([x + x_step/2, clk_lo, 0], [x_end, clk_lo, 0], stroke_color=ACCENT_GREEN, stroke_width=2),
            )
            cyc_elements.add(clk_wave)

            # Row 1: Valid line (stays high)
            y_valid = y_base - row_gap
            valid_line = Line([x, y_valid + 0.1, 0], [x_end, y_valid + 0.1, 0],
                              stroke_color=ACCENT_GREEN, stroke_width=2)
            cyc_elements.add(valid_line)

            # Row 2: Activation value
            y_act = y_base - 2 * row_gap
            act_box = Rectangle(width=x_step - 0.15, height=0.3,
                                stroke_color=ACCENT_YELLOW, stroke_width=1.5,
                                fill_color=ACCENT_YELLOW, fill_opacity=0.12)
            act_box.move_to([(x + x_end) / 2, y_act, 0])
            act_text = Text(f"{act}", font_size=12, color=ACCENT_YELLOW)
            act_text.move_to(act_box.get_center())
            cyc_elements.add(act_box, act_text)

            # Row 3: Weight value (color-coded)
            y_wt = y_base - 3 * row_gap
            wt_color = ACCENT_GREEN if wt == 1 else (ACCENT_RED if wt == 2 else WIRE_COLOR)
            wt_box = Rectangle(width=x_step - 0.15, height=0.3,
                                stroke_color=wt_color, stroke_width=1.5,
                                fill_color=wt_color, fill_opacity=0.12)
            wt_box.move_to([(x + x_end) / 2, y_wt, 0])
            wt_text = Text(f"w={wt_lbl}", font_size=12, color=wt_color)
            wt_text.move_to(wt_box.get_center())
            cyc_elements.add(wt_box, wt_text)

            # Row 4: Accumulator value
            y_acc = y_base - 4 * row_gap
            acc_box = Rectangle(width=x_step - 0.15, height=0.3,
                                stroke_color=ACCENT_PURPLE, stroke_width=1.5,
                                fill_color=ACCENT_PURPLE, fill_opacity=0.12)
            acc_box.move_to([(x + x_end) / 2, y_acc, 0])
            acc_text = Text(f"{acc_val}", font_size=12, color=ACCENT_PURPLE)
            acc_text.move_to(acc_box.get_center())
            cyc_elements.add(acc_box, acc_text)

            # Row 5: Output (saturated)
            y_out = y_base - 5 * row_gap
            out_val = max(-128, min(127, acc_val))
            is_saturated = out_val != acc_val
            out_color = ACCENT_RED if is_saturated else ACCENT_GREEN
            out_box = Rectangle(width=x_step - 0.15, height=0.3,
                                stroke_color=out_color, stroke_width=1.5 if not is_saturated else 2.5,
                                fill_color=out_color, fill_opacity=0.12 if not is_saturated else 0.25)
            out_box.move_to([(x + x_end) / 2, y_out, 0])
            sat_marker = " SAT!" if is_saturated else ""
            out_text = Text(f"{out_val}{sat_marker}", font_size=12, color=out_color,
                            weight=BOLD if is_saturated else NORMAL)
            out_text.move_to(out_box.get_center())
            cyc_elements.add(out_box, out_text)

            # Vertical dashed separator between cycles
            if cyc_i > 0:
                sep = DashedLine([x, y_base + 0.4, 0], [x, y_out - 0.25, 0],
                                 stroke_color=WIRE_COLOR, stroke_width=1,
                                 stroke_opacity=0.3)
                cyc_elements.add(sep)

            self.play(FadeIn(cyc_elements), run_time=0.8)

        # Annotation for saturation event
        self.wait(0.6)
        sat_note = Text("Accumulator 130 > 127 -> output clamped!", font_size=13,
                        color=ACCENT_RED, weight=BOLD)
        sat_note.to_edge(DOWN, buff=0.4)
        self.play(FadeIn(sat_note), run_time=0.6)
        self.wait(1.5)


# =====================================================================
# Scene 3: Saturation Clamp Visualization
# =====================================================================
class SaturationClamp(Scene):
    """Visualize the 16-bit to 8-bit saturation clamp behavior."""

    def construct(self):
        self.camera.background_color = BG_COLOR

        title = Text("Output Saturation Clamp", font_size=26,
                      color=ACCENT_BLUE, weight=BOLD)
        title.to_edge(UP, buff=0.3)
        self.play(Write(title), run_time=0.8)

        # Create axes — compact and shifted right to leave room for y-label
        ax = Axes(
            x_range=[-400, 400, 200],
            y_range=[-200, 200, 100],
            x_length=6.5,
            y_length=3.5,
            axis_config={
                "include_numbers": True,
                "font_size": 13,
                "color": TEXT_COLOR,
                "tick_size": 0.04,
            },
            tips=False,
        ).shift(RIGHT * 0.4 + UP * 0.15)

        # Y-axis label — rotated, positioned near the axis but clear of tick numbers
        y_label = Text("Output (8-bit)", font_size=13, color=TEXT_COLOR)
        y_label.rotate(PI / 2)
        y_label.to_edge(LEFT, buff=0.15)

        # X-axis label at bottom edge of scene
        x_label = Text("Accumulator Value (16-bit)", font_size=13, color=TEXT_COLOR)
        x_label.to_edge(DOWN, buff=0.55)

        self.play(Create(ax), FadeIn(x_label), FadeIn(y_label), run_time=1.0)

        # Identity line (very faint reference)
        identity = ax.plot(lambda x: x, x_range=[-200, 200],
                           color=WIRE_COLOR, stroke_width=1, stroke_opacity=0.2)
        self.play(Create(identity), run_time=0.6)

        # Saturation function drawn as 3 segments
        seg_mid = ax.plot(lambda x: x, x_range=[-128, 127],
                         color=ACCENT_GREEN, stroke_width=3)
        seg_pos = ax.plot(lambda x: 127, x_range=[127, 400],
                         color=ACCENT_RED, stroke_width=3)
        seg_neg = ax.plot(lambda x: -128, x_range=[-400, -128],
                         color=ACCENT_RED, stroke_width=3)

        # Linear region label — upper-left, well clear of the line
        self.play(Create(seg_mid), run_time=0.8)
        lin_label = Text("Linear\nregion", font_size=12, color=ACCENT_GREEN)
        lin_label.move_to(ax.c2p(-280, 100))
        self.play(FadeIn(lin_label), run_time=0.4)

        # Upper saturation — label to the right, outside plot area
        self.play(Create(seg_pos), run_time=0.6)
        upper_line = DashedLine(
            ax.c2p(-400, 127), ax.c2p(400, 127),
            stroke_color=ACCENT_RED, stroke_width=1, stroke_opacity=0.35
        )
        upper_label = Text("+127 clamp", font_size=12, color=ACCENT_RED, weight=BOLD)
        upper_label.next_to(ax.c2p(400, 127), RIGHT, buff=0.1)
        self.play(Create(upper_line), FadeIn(upper_label), run_time=0.6)

        # Lower saturation — label to the right, outside plot area
        self.play(Create(seg_neg), run_time=0.6)
        lower_line = DashedLine(
            ax.c2p(-400, -128), ax.c2p(400, -128),
            stroke_color=ACCENT_RED, stroke_width=1, stroke_opacity=0.35
        )
        lower_label = Text("-128 clamp", font_size=12, color=ACCENT_RED, weight=BOLD)
        lower_label.next_to(ax.c2p(400, -128), RIGHT, buff=0.1)
        self.play(Create(lower_line), FadeIn(lower_label), run_time=0.6)

        # Subtitle at bottom (below x-label)
        subtitle = Text(
            "Hardware activation function (hard clipping)",
            font_size=13, color=ACCENT_YELLOW
        )
        subtitle.to_edge(DOWN, buff=0.15)
        self.play(FadeIn(subtitle), run_time=0.6)

        self.wait(1.5)
