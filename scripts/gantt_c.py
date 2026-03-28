#!/usr/bin/env python3
"""
Generate a Gantt chart SVG from a JSON file using TikZ (class-based).

Usage:
    python gantt_c.py input.json [-o output.svg]

JSON format: see gantt.py docstring for full reference.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field


STYLES = {
    "crit":   ("red!85",  "red!50",  "CPU attiva"),
    "active": ("teal!90", "teal!50", "Linea di esecuzione bloccata"),
    "idle":   ("gray!90", "gray!90", "CPU inattiva (IDLE)"),
    "done":   ("gray!70", "gray!40", "Completato"),
}

DEFAULT_GROUP_COLORS = ["blue!3", "orange!4"]

def tex_escape(s: str) -> str:
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


def escape_label(label):
    if isinstance(label, list):
        return [tex_escape(l) for l in label]
    return tex_escape(label)


# --- TikZ node base ---

@dataclass
class TikzNode:
    name: str
    x: float = 0
    y: float = 0
    options: str = ""
    content: str = ""

    def render(self) -> str:
        name_str = f"({self.name}) " if self.name else ""
        return f"  \\node[{self.options}] {name_str}at ({self.x:.2f}, {self.y:.2f}) {{{self.content}}};"


# --- Data classes ---

@dataclass
class Bar:
    label: str | list
    start: float
    end: float
    style: str = "active"
    duration: str = ""
    row: str = ""
    id: str = ""
    nowrap: bool = False

    # Set after layout
    x1: float = 0
    x2: float = 0
    y: float = 0

    # Set after assign_names
    node_name: str = ""
    dur_node_name: str = ""

    @classmethod
    def from_dict(cls, d: dict, prev_end: float | None = None) -> "Bar":
        start = d.get("start", prev_end)
        return cls(
            label=escape_label(d["label"]),
            start=start,
            end=d["end"],
            style=d.get("style", "active"),
            duration=tex_escape(d["duration"]) if "duration" in d else "",
            row=d.get("row", ""),
            id=d.get("id", ""),
            nowrap=d.get("nowrap", False),
        )


@dataclass
class Marker:
    at: float | str
    label: str = ""
    color: str = "yellow"
    position: str = "top"
    nowrap: bool = False

    # Set after layout
    mx: float = 0

    # Set after assign_names
    node_name: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "Marker":
        return cls(
            at=d["at"],
            label=tex_escape(d["label"]) if "label" in d else "",
            color=d.get("color", "yellow"),
            position=d.get("position", "top"),
            nowrap=d.get("nowrap", False),
        )


@dataclass
class Section:
    name: str
    bars: list[Bar]
    markers: list[Marker] = field(default_factory=list)
    id: str = ""

    # Set after layout
    y_start: float = 0
    y_end: float = 0

    @classmethod
    def from_dict(cls, d: dict) -> "Section":
        bars = []
        prev_end = None
        for bd in d["bars"]:
            bar = Bar.from_dict(bd, prev_end)
            prev_end = bar.end
            bars.append(bar)
        markers = [Marker.from_dict(m) for m in d.get("markers", [])]
        return cls(
            name=tex_escape(d.get("name", "")),
            bars=bars,
            markers=markers,
            id=d.get("id", ""),
        )

    def count_rows(self) -> int:
        rows_seen = set()
        for bi, bar in enumerate(self.bars):
            row_id = bar.row or f"_auto_{bi}"
            rows_seen.add(row_id)
        return len(rows_seen)


@dataclass
class Group:
    name: str
    section_indices: list[int]
    color: str = ""
    markers: list[Marker] = field(default_factory=list)

    # Set after layout
    y_top: float = 0
    y_bot: float = 0


    @classmethod
    def from_dict(cls, d: dict) -> "Group":
        return cls(
            name=tex_escape(d["name"]),
            section_indices=d["sections"],
            color=d.get("color", ""),
            markers=[Marker.from_dict(m) for m in d.get("markers", [])],
        )


@dataclass
class GanttChart:
    ticks: list[float]
    sections: list[Section]
    groups: list[Group] = field(default_factory=list)
    markers: list[Marker] = field(default_factory=list)
    title: str = ""
    tick_labels: list[str] = field(default_factory=list)
    show_ticks: bool = True
    nowrap: bool = False
    width: float = 12
    bar_height: float = 0.9
    section_gap: float = 0.3
    group_gap: float = 0.1
    group_pad: float = 0.0

    # Computed
    total_height: float = 0
    bar_positions: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "GanttChart":
        ticks = data["ticks"]
        tick_labels = [tex_escape(s) for s in data.get("tick_labels", [str(t) for t in ticks])]
        sections = [Section.from_dict(s) for s in data["sections"]]
        groups = [Group.from_dict(g) for g in data.get("groups", [])]
        markers = [Marker.from_dict(m) for m in data.get("markers", [])]
        return cls(
            ticks=ticks,
            sections=sections,
            groups=groups,
            markers=markers,
            title=tex_escape(data.get("title", "")),
            tick_labels=tick_labels,
            show_ticks=data.get("show_ticks", True),
            nowrap=data.get("nowrap", False),
            width=data.get("width", 12),
        )

    @property
    def t_min(self):
        return min(self.ticks)

    @property
    def t_max(self):
        return max(self.ticks)

    @property
    def scale(self):
        return self.width / (self.t_max - self.t_min)

    def tx(self, val: float) -> float:
        return (val - self.t_min) * self.scale

    def _marker_padding(self, markers: list[Marker], position: str) -> float:
        if any(m.position == position and m.label for m in markers):
            return 0.6
        return 0.0

    def layout(self):
        """Compute y positions for all sections, groups, and bars."""
        y = 0.0
        if self.groups:
            for gi, group in enumerate(self.groups):
                if gi > 0:
                    y += self.group_gap
                    y += self._marker_padding(self.groups[gi - 1].markers, "bottom")
                    y += self._marker_padding(group.markers, "top")
                group.y_top = y
                for sec_idx in group.section_indices:
                    y += self.section_gap
                    y += self._marker_padding(self.sections[sec_idx].markers, "top")
                    self._layout_section(sec_idx, y)
                    y = self.sections[sec_idx].y_end
                    y += self._marker_padding(self.sections[sec_idx].markers, "bottom")
                last_sec = self.sections[group.section_indices[-1]]
                extra = 0.35 if any(b.duration for b in last_sec.bars) else 0
                group.y_bot = y + self.group_pad + extra
                y = group.y_bot
        else:
            for si in range(len(self.sections)):
                y += self.section_gap
                y += self._marker_padding(self.sections[si].markers, "top")
                self._layout_section(si, y)
                y = self.sections[si].y_end
                y += self._marker_padding(self.sections[si].markers, "bottom")

        self.total_height = y
        self._layout_bars()
        self._resolve_markers()
        self._assign_names()

    def _layout_section(self, si: int, y_start: float):
        section = self.sections[si]
        section.y_start = y_start
        num_rows = section.count_rows()
        section.y_end = y_start + num_rows * self.bar_height

    def _layout_bars(self):
        for si, section in enumerate(self.sections):
            y = section.y_start
            rows_seen = {}
            for bi, bar in enumerate(section.bars):
                row_id = bar.row or f"_auto_{bi}"
                if row_id in rows_seen:
                    bar.y = rows_seen[row_id]
                else:
                    bar.y = y
                    rows_seen[row_id] = y
                    y += self.bar_height
                bar.x1 = self.tx(bar.start)
                bar.x2 = self.tx(bar.end)
                pos = {"west": bar.x1, "east": bar.x2, "y": bar.y, "h": self.bar_height}
                if bar.id:
                    self.bar_positions[bar.id] = pos
                if section.id:
                    self.bar_positions[f"{section.id}-{bi}"] = pos

    def _resolve_markers(self):
        all_markers = list(self.markers)
        for section in self.sections:
            all_markers.extend(section.markers)
        for group in self.groups:
            all_markers.extend(group.markers)
        for marker in all_markers:
            at = marker.at
            if isinstance(at, str) and "." in at:
                bar_ref, anchor = at.rsplit(".", 1)
                marker.mx = self.bar_positions[bar_ref][anchor]
            else:
                marker.mx = self.tx(at)

    def _assign_names(self):
        """Assign TikZ node names to all elements."""
        for si, section in enumerate(self.sections):
            for bi, bar in enumerate(section.bars):
                bar.node_name = f"bar_s{si}_b{bi}"
                if bar.duration:
                    bar.dur_node_name = f"dur_s{si}_b{bi}"

        for gi, group in enumerate(self.groups):
            for mi, marker in enumerate(group.markers):
                if marker.label:
                    marker.node_name = f"mkr_g{gi}_m{mi}"

    def used_styles(self) -> set[str]:
        styles = set()
        for section in self.sections:
            for bar in section.bars:
                styles.add(bar.style)
        return styles


# --- TikZ component classes ---

@dataclass
class TikzTick:
    x: float
    label: str
    total_height: float

    def render(self) -> list[str]:
        lines = []
        lines.append(f"  \\draw[gray!30, very thin] ({self.x:.2f}, 0) -- ({self.x:.2f}, {self.total_height:.2f});")
        if self.label:
            lines.append(f"  \\node[anchor=north, font=\\normalsize, gray] at ({self.x:.2f}, {self.total_height + 0.1:.2f}) {{{self.label}}};")
        return lines


@dataclass
class TikzLegendItem:
    fill: str
    border: str
    desc: str
    x: float
    y: float
    box_w: float
    box_h: float
    text_w: float

    def render(self) -> list[str]:
        lx, ly = self.x, self.y
        return [
            f"  \\fill[{self.fill}, rounded corners=1pt] ({lx:.2f}, {ly:.2f}) rectangle ({lx + self.box_w:.2f}, {ly + self.box_h:.2f});",
            f"  \\draw[{self.border}, rounded corners=1pt] ({lx:.2f}, {ly:.2f}) rectangle ({lx + self.box_w:.2f}, {ly + self.box_h:.2f});",
            f"  \\node[anchor=west, font=\\normalsize, gray, text width={self.text_w:.2f}cm] at ({lx + self.box_w + 0.15:.2f}, {ly + self.box_h/2:.2f}) {{{self.desc}}};",
        ]


@dataclass
class TikzBar:
    bar: Bar
    bar_height: float
    nowrap: bool

    def render(self) -> list[str]:
        b = self.bar
        fill, border, _ = STYLES.get(b.style, STYLES["active"])
        bw = b.x2 - b.x1
        cx = (b.x1 + b.x2) / 2
        cy = b.y + self.bar_height / 2
        lines = []

        lines.append(f"  \\node[inner sep=0pt, minimum width={bw:.2f}cm, minimum height={self.bar_height:.2f}cm, fill={fill}, draw={border}, rounded corners=2pt] ({b.node_name}) at ({cx:.2f}, {cy:.2f}) {{}};")

        label = b.label
        if isinstance(label, list) and len(label) == 2:
            off = self.bar_height * 0.2
            lines.append(f"  \\node[font=\\normalsize\\bfseries, white] at ({cx:.2f}, {cy - off:.2f}) {{{label[0]}}};")
            lines.append(f"  \\node[font=\\normalsize\\bfseries, white] at ({cx:.2f}, {cy + off:.2f}) {{{label[1]}}};")
        elif self.nowrap or b.nowrap:
            lines.append(f"  \\node[font=\\normalsize\\bfseries, white] at ({cx:.2f}, {cy:.2f}) {{{label}}};")
        else:
            lines.append(f"  \\node[font=\\normalsize\\bfseries, white, text width={bw - 0.2:.2f}cm, align=center] at ({cx:.2f}, {cy:.2f}) {{{label}}};")

        if b.duration:
            lines.append(f"  \\node[font=\\normalsize, gray!70] ({b.dur_node_name}) at ({cx:.2f}, {b.y + self.bar_height + 0.13:.2f}) {{{b.duration}}};")

        return lines


@dataclass
class TikzMarkerLabel:
    marker: Marker
    y_top: float
    y_bot: float
    nowrap: bool

    def render(self) -> list[str]:
        m = self.marker
        if m.position == "bottom":
            my, anchor = self.y_bot + 0.1, "north"
        else:
            my, anchor = self.y_top - 0.1, "south"
        name_str = f"({m.node_name}) " if m.node_name else ""
        if self.nowrap or m.nowrap:
            return [f"  \\node[anchor={anchor}, font=\\normalsize\\bfseries, {m.color}] {name_str}at ({m.mx:.2f}, {my:.2f}) {{{m.label}}};"]
        else:
            return [f"  \\node[anchor={anchor}, font=\\normalsize\\bfseries, {m.color}, text width=3cm, align=center] {name_str}at ({m.mx:.2f}, {my:.2f}) {{{m.label}}};"]


@dataclass
class TikzMarkerLine:
    marker: Marker
    y_top: float = 0
    y_bot: float = 0

    def render(self) -> list[str]:
        m = self.marker
        lw = "very thick" if m.position == "bottom" else "thick"
        return [f"  \\draw[{m.color}, dashed, {lw}] ({m.mx:.2f}, {self.y_top:.2f}) -- ({m.mx:.2f}, {self.y_bot:.2f});"]


@dataclass
class TikzGroupBackground:
    group: Group
    chart_width: float
    bg_color: str

    def render(self) -> list[str]:
        g = self.group
        bbox_x0, bbox_x1 = -0.2, self.chart_width + 0.2
        label_x = bbox_x0 - 0.3
        bg = self.bg_color
        mid_y = (g.y_top + g.y_bot) / 2
        lines = [
            f"  \\fill[{bg}, fill opacity=0.15, rounded corners=0pt] ({bbox_x0:.2f}, {g.y_top:.2f}) rectangle ({bbox_x1:.2f}, {g.y_bot:.2f});",
            f"  \\node[rotate=90, anchor=south, font=\\large\\bfseries, gray] at ({label_x:.2f}, {mid_y:.2f}) {{{g.name}}};",
        ]
        return lines


# --- TikZ Renderer ---

class TikzRenderer:
    def __init__(self, chart: GanttChart):
        self.chart = chart
        self.lines: list[str] = []

    def render(self) -> str:
        c = self.chart
        c.layout()

        legend_items = [(k, v) for k, v in STYLES.items() if k in c.used_styles()]
        top_offset = self._compute_top_offset(legend_items)

        self._preamble()
        self._legend(legend_items, top_offset)
        self._title(top_offset)
        self._ticks()
        self._bars()
        self._marker_labels()
        self._group_backgrounds()
        self._marker_lines()
        self.lines.append(r"\end{tikzpicture}")
        self.lines.append(r"\end{document}")
        return "\n".join(self.lines)

    def _compute_top_offset(self, legend_items) -> float:
        c = self.chart
        box_h = 0.5
        legend_height = box_h + 1.0
        title_height = 1.0 if c.title else 0
        has_top_markers = any(
            m.label and m.position == "top" for m in c.markers
        )
        marker_header = 0.8 if has_top_markers else 0
        return legend_height + title_height + marker_header

    def _preamble(self):
        self.lines.extend([
            r"\documentclass[border=8pt]{standalone}",
            r"\usepackage[T1]{fontenc}",
            r"\usepackage{inconsolata}",
            r"\renewcommand{\familydefault}{\ttdefault}",
            r"\usepackage{tikz}",
            r"\usetikzlibrary{backgrounds}",
            r"\begin{document}",
            r"\begin{tikzpicture}[y=-1cm]",
        ])

    def _legend(self, legend_items, top_offset):
        c = self.chart
        box_h, box_w = 0.5, 0.5
        cols = len(legend_items) if legend_items else 1
        col_width = c.width / cols
        legend_row_y = -top_offset
        for i, (_, (fill, border, desc)) in enumerate(legend_items):
            item = TikzLegendItem(
                fill=fill, border=border, desc=desc,
                x=i * col_width, y=legend_row_y,
                box_w=box_w, box_h=box_h,
                text_w=col_width - box_w - 0.3,
            )
            self.lines.extend(item.render())

    def _title(self, top_offset):
        c = self.chart
        if not c.title:
            return
        box_h = 0.5
        legend_row_y = -top_offset
        title_y = legend_row_y + box_h + 0.3
        self.lines.append(f"  \\node[anchor=south, font=\\Large\\bfseries] at ({c.width/2}, {title_y:.2f}) {{{c.title}}};")

    def _ticks(self):
        c = self.chart
        if not c.show_ticks:
            return
        for i, t in enumerate(c.ticks):
            x = c.tx(t)
            label = c.tick_labels[i] if i < len(c.tick_labels) else str(t)
            self.lines.extend(TikzTick(x=x, label=label, total_height=c.total_height).render())

    def _bars(self):
        c = self.chart
        for section in c.sections:
            for bar in section.bars:
                self.lines.extend(TikzBar(bar=bar, bar_height=c.bar_height, nowrap=c.nowrap).render())

    def _marker_labels(self):
        c = self.chart
        for marker in c.markers:
            if marker.label:
                self.lines.extend(TikzMarkerLabel(marker=marker, y_top=-0.1, y_bot=c.total_height + 0.1, nowrap=c.nowrap).render())
        for section in c.sections:
            for marker in section.markers:
                if marker.label:
                    self.lines.extend(TikzMarkerLabel(marker=marker, y_top=section.y_start - 0.05, y_bot=section.y_end + 0.05, nowrap=c.nowrap).render())
        for group in c.groups:
            for marker in group.markers:
                if marker.label:
                    self.lines.extend(TikzMarkerLabel(marker=marker, y_top=group.y_top, y_bot=group.y_bot, nowrap=c.nowrap).render())

    def _group_backgrounds(self):
        c = self.chart
        if not c.groups:
            return
        for gi, group in enumerate(c.groups):
            bg_color = group.color or DEFAULT_GROUP_COLORS[gi % len(DEFAULT_GROUP_COLORS)]
            self.lines.extend(TikzGroupBackground(group=group, chart_width=c.width, bg_color=bg_color).render())

    def _marker_lines(self):
        c = self.chart
        for marker in c.markers:
            self.lines.extend(TikzMarkerLine(marker=marker, y_top=-0.1, y_bot=c.total_height + 0.1).render())
        for section in c.sections:
            for marker in section.markers:
                self.lines.extend(TikzMarkerLine(marker=marker, y_top=section.y_start - 0.05, y_bot=section.y_end + 0.05).render())
        for group in c.groups:
            for marker in group.markers:
                self.lines.extend(TikzMarkerLine(marker=marker, y_top=group.y_top - 0.1, y_bot=group.y_bot + 0.1).render())


# --- Compiler ---

def compile_to_svg(tikz_source: str, output_path: str):
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

    chart = GanttChart.from_dict(data)
    renderer = TikzRenderer(chart)
    tikz_source = renderer.render()
    compile_to_svg(tikz_source, output)
    print(f"Generated: {output}")


if __name__ == "__main__":
    main()
