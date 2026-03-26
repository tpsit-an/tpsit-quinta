#!/usr/bin/env python3
"""
Generate a Gantt chart SVG from a JSON file using TikZ.

Usage:
    python gantt.py input.json [-o output.svg]

JSON format:
{
    "title": "CPU del client — send()",
    "ticks": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    "tick_labels": ["0s", "", "", "", "", "5s", "", "", "", "", "10s"],
    "sections": [
        {
            "name": "send()",
            "bars": [
                {"label": "send()", "start": 0, "end": 10, "style": "active"}
            ]
        },
        {
            "name": "CPU",
            "bars": [
                {"label": "invio dati", "start": 0, "end": 1, "style": "crit"},
                {"label": "attesa ACK (IDLE)", "start": 1, "end": 9, "style": "idle"},
                {"label": "fine", "start": 9, "end": 10, "style": "crit"}
            ]
        }
    ],
    "markers": [
        {"at": 1, "label": "arrivo dati", "color": "yellow"}
    ]
}

Styles: "active", "crit", "idle", "done"
Markers: vertical dashed lines with a label. Color defaults to "yellow".
If tick_labels is omitted, ticks values are used as labels.
Labels: "label": "text" for single line, "label": ["line1", "line2"] for two lines.
Durations: "duration": "~5ms" on a bar to show custom text below it.
Ticks: "show_ticks": false to hide vertical tick lines.
Nowrap: "nowrap": true globally or per-bar/marker to disable text wrapping.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile

STYLES = {
    "crit":   ("red!85",  "red!50",  "CPU attiva"),
    "active": ("teal!90", "teal!50", "Linea di esecuzione bloccata"),
    "idle":   ("gray!55", "gray!60", "CPU inattiva (IDLE)"),
    "done":   ("gray!70", "gray!40", "Completato"),
}

BAR_HEIGHT = 0.6
SECTION_GAP = 0.2
GROUP_GAP = 0.05
GROUP_PAD = 0.
ROW_GAP = 0.


def tex_escape(s):
    """Escape LaTeX special characters in user text."""
    # Backslash first, then braces, then everything else
    s = s.replace("\\", r"\textbackslash ")
    s = s.replace("{", r"\{")
    s = s.replace("}", r"\}")
    s = s.replace("&", r"\&")
    s = s.replace("%", r"\%")
    s = s.replace("$", r"\$")
    s = s.replace("#", r"\#")
    s = s.replace("_", r"\_")
    s = s.replace("~", r"$\sim$")
    s = s.replace("^", r"\^{}")
    return s


def generate_tikz(data):
    title = tex_escape(data.get("title", ""))
    ticks = data["ticks"]
    tick_labels = [tex_escape(s) for s in data.get("tick_labels", [str(t) for t in ticks])]
    show_ticks = data.get("show_ticks", True)

    # Deep-escape all user text in sections and groups
    sections = data["sections"]
    for section in sections:
        for bar in section["bars"]:
            if isinstance(bar["label"], list):
                bar["label"] = [tex_escape(l) for l in bar["label"]]
            else:
                bar["label"] = tex_escape(bar["label"])
            if "duration" in bar:
                bar["duration"] = tex_escape(bar["duration"])
    groups = data.get("groups", [])
    for group in groups:
        group["name"] = tex_escape(group["name"])
    markers = data.get("markers", [])
    for marker in markers:
        if "label" in marker:
            marker["label"] = tex_escape(marker["label"])

    t_min = min(ticks)
    t_max = max(ticks)
    width = 12
    scale = width / (t_max - t_min)

    def tx(val):
        return (val - t_min) * scale

    nowrap = data.get("nowrap", False)

    # --- First pass: compute y positions for each section ---
    section_y_start = {}  # section index -> y start
    section_y_end = {}    # section index -> y end
    group_y_ranges = []   # (group_name, y_start, y_end)

    y = 0
    if groups:
        for gi, group in enumerate(groups):
            if gi > 0:
                y += GROUP_GAP
            group_y_top = y
            group_sections = group["sections"]
            for si, sec_idx in enumerate(group_sections):
                y += SECTION_GAP
                section_y_start[sec_idx] = y
                num_bars = len(sections[sec_idx]["bars"])
                section_height = num_bars * BAR_HEIGHT
                section_y_end[sec_idx] = y + section_height
                y = section_y_end[sec_idx]
            # Extra padding if last section's last bar has a duration label
            last_sec = sections[group_sections[-1]]
            has_last_duration = any(b.get("duration") for b in last_sec["bars"])
            extra_pad = 0.35 if has_last_duration else 0
            group_color = group.get("color", None)
            group_y_ranges.append((group["name"], group_y_top, y + GROUP_PAD + extra_pad, group_color))
            y += GROUP_PAD + extra_pad
    else:
        for si, section in enumerate(sections):
            y += SECTION_GAP
            section_y_start[si] = y
            num_bars = len(section["bars"])
            section_height = num_bars * BAR_HEIGHT
            section_y_end[si] = y + section_height
            y = section_y_end[si]

    total_height = y

    # Collect which styles are actually used for the legend
    used_styles = set()
    for section in sections:
        for bar in section["bars"]:
            used_styles.add(bar.get("style", "active"))

    # Compute vertical offsets: legend on top, then title, then markers, then chart
    legend_items = [(k, v) for k, v in STYLES.items() if k in used_styles]
    box_h = 0.3
    row_spacing = 0.15
    cols = len(legend_items) if legend_items else 1
    legend_height = box_h + row_spacing
    title_height = 1.0 if title else 0
    marker_labels = [m for m in data.get("markers", []) if m.get("label")]
    marker_header = 0.8 if marker_labels else 0

    top_offset = legend_height + title_height + marker_header

    lines = []
    lines.append(r"\documentclass[border=8pt]{standalone}")
    lines.append(r"\usepackage[T1]{fontenc}")
    lines.append(r"\usepackage{inconsolata}")
    lines.append(r"\renewcommand{\familydefault}{\ttdefault}")
    lines.append(r"\usepackage{tikz}")
    lines.append(r"\begin{document}")
    lines.append(r"\begin{tikzpicture}[y=-1cm]")

    # Legend at top (single row, no "Legenda:" label)
    box_w = 0.5
    col_width = width / cols
    legend_row_y = -top_offset

    for i, (style_key, (fill, border, desc)) in enumerate(legend_items):
        lx = i * col_width
        ly = legend_row_y
        lines.append(f"  \\fill[{fill}, rounded corners=1pt] ({lx:.2f}, {ly:.2f}) rectangle ({lx + box_w:.2f}, {ly + box_h:.2f});")
        lines.append(f"  \\draw[{border}, rounded corners=1pt] ({lx:.2f}, {ly:.2f}) rectangle ({lx + box_w:.2f}, {ly + box_h:.2f});")
        # Use text width for wrapping long descriptions
        text_w = col_width - box_w - 0.3
        lines.append(f"  \\node[anchor=west, font=\\scriptsize, gray, text width={text_w:.2f}cm] at ({lx + box_w + 0.15:.2f}, {ly + box_h/2:.2f}) {{{desc}}};")

    # Title
    if title:
        title_y = legend_row_y + box_h + 0.3
        lines.append(f"  \\node[anchor=south, font=\\large\\bfseries] at ({width/2}, {title_y:.2f}) {{{title}}};")

    # Tick lines and labels
    if show_ticks:
        for i, t in enumerate(ticks):
            x = tx(t)
            label = tick_labels[i] if i < len(tick_labels) else str(t)
            lines.append(f"  \\draw[gray!30, very thin] ({x:.2f}, 0) -- ({x:.2f}, {total_height:.2f});")
            if label:
                lines.append(f"  \\node[anchor=north, font=\\small, gray] at ({x:.2f}, {total_height + 0.1:.2f}) {{{label}}};")

    # Group backgrounds and vertical left labels
    default_group_colors = ["blue!3", "orange!4"]
    bbox_x0 = -0.2
    bbox_x1 = width + 0.2
    label_x = bbox_x0 - 0.3
    for gi, (group_name, gy_top, gy_bot, group_color) in enumerate(group_y_ranges):
        bg = group_color if group_color else default_group_colors[gi % len(default_group_colors)]
        lines.append(f"  \\fill[{bg}, fill opacity=0.15, rounded corners=0pt] ({bbox_x0:.2f}, {gy_top:.2f}) rectangle ({bbox_x1:.2f}, {gy_bot:.2f});")
        mid_y = (gy_top + gy_bot) / 2
        lines.append(f"  \\node[rotate=90, anchor=south, font=\\normalsize\\bfseries, gray] at ({label_x:.2f}, {mid_y:.2f}) {{{group_name}}};")

    # Draw sections and bars
    for si, section in enumerate(sections):
        y = section_y_start[si]

        for bar in section["bars"]:
            label = bar["label"]
            start = bar["start"]
            end = bar["end"]
            style = bar.get("style", "active")
            fill, border, _ = STYLES.get(style, STYLES["active"])

            x1 = tx(start)
            x2 = tx(end)

            bar_width = x2 - x1
            lines.append(f"  \\fill[{fill}, rounded corners=2pt] ({x1:.2f}, {y:.2f}) rectangle ({x2:.2f}, {y + BAR_HEIGHT:.2f});")
            lines.append(f"  \\draw[{border}, rounded corners=2pt] ({x1:.2f}, {y:.2f}) rectangle ({x2:.2f}, {y + BAR_HEIGHT:.2f});")
            cx = (x1 + x2) / 2
            cy = y + BAR_HEIGHT / 2
            if isinstance(label, list) and len(label) == 2:
                line_offset = BAR_HEIGHT * 0.2
                lines.append(f"  \\node[font=\\small\\bfseries, white] at ({cx:.2f}, {cy - line_offset:.2f}) {{{label[0]}}};")
                lines.append(f"  \\node[font=\\small\\bfseries, white] at ({cx:.2f}, {cy + line_offset:.2f}) {{{label[1]}}};")
            elif nowrap or bar.get("nowrap", False):
                lines.append(f"  \\node[font=\\small\\bfseries, white] at ({cx:.2f}, {cy:.2f}) {{{label}}};")
            else:
                lines.append(f"  \\node[font=\\small\\bfseries, white, text width={bar_width - 0.2:.2f}cm, align=center] at ({cx:.2f}, {cy:.2f}) {{{label}}};")

            # Duration label below the bar (manual only)
            duration = bar.get("duration")
            if duration:
                lines.append(f"  \\node[font=\\small, black] at ({cx:.2f}, {y + BAR_HEIGHT + 0.13:.2f}) {{{duration}}};")

            y += BAR_HEIGHT

    # Markers (vertical dashed lines) — label just above the chart area
    markers = data.get("markers", [])
    for marker in markers:
        mx = tx(marker["at"])
        color = marker.get("color", "yellow")
        mlabel = marker.get("label", "")
        lines.append(f"  \\draw[{color}, dashed, thick] ({mx:.2f}, -0.1) -- ({mx:.2f}, {total_height + 0.1:.2f});")
        if mlabel:
            marker_y = -0.2
            if nowrap or marker.get("nowrap", False):
                lines.append(f"  \\node[anchor=south, font=\\small\\bfseries, {color}] at ({mx:.2f}, {marker_y:.2f}) {{{mlabel}}};")
            else:
                lines.append(f"  \\node[anchor=south, font=\\small\\bfseries, {color}, text width=3cm, align=center] at ({mx:.2f}, {marker_y:.2f}) {{{mlabel}}};")

    lines.append(r"\end{tikzpicture}")
    lines.append(r"\end{document}")
    return "\n".join(lines)


def compile_to_svg(tikz_source, output_path):
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = os.path.join(tmpdir, "gantt.tex")
        pdf_path = os.path.join(tmpdir, "gantt.pdf")

        with open(tex_path, "w") as f:
            f.write(tikz_source)

        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-output-directory", tmpdir, tex_path],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print("pdflatex failed:", file=sys.stderr)
            print(result.stdout, file=sys.stderr)
            sys.exit(1)

        result = subprocess.run(
            ["pdf2svg", pdf_path, output_path],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print("pdf2svg failed:", file=sys.stderr)
            print(result.stderr, file=sys.stderr)
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Generate Gantt chart SVG from JSON using TikZ")
    parser.add_argument("input", help="JSON input file")
    parser.add_argument("-o", "--output", help="Output SVG path (default: same name as input with .svg)")
    args = parser.parse_args()

    with open(args.input) as f:
        data = json.load(f)

    output = args.output or os.path.splitext(args.input)[0] + ".svg"

    tikz_source = generate_tikz(data)
    compile_to_svg(tikz_source, output)
    print(f"Generated: {output}")


if __name__ == "__main__":
    main()
