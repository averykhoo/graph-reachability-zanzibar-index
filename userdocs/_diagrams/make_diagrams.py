"""Generate the explanation pages' diagrams as plain SVG files (TK151).

Run from the repo root::

    python userdocs/_diagrams/make_diagrams.py

Each figure is written twice into ``userdocs/explanation/img/``, ``<name>.svg`` for furo's
light theme and ``<name>-dark.svg`` for its dark one; a page shows the pair with the
``only-light`` / ``only-dark`` image classes. Plain SVG keeps the docs build free of a
diagram extension, a JavaScript renderer and a ``dot`` binary.

``tests/test_userdocs_diagrams.py`` fails when a committed SVG differs from what this
script generates, so edit a figure HERE and regenerate; never hand-edit the SVG.

The numbers drawn are the library's real answers, not illustrations: the path counts are
the ones the page's executed example prints, and the cascade figure's rounds and outbox
rows are what a ``Store`` writes for that schema (each figure's docstring says how they
were observed).
"""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).resolve().parent.parent / "explanation" / "img"

PALETTES = {
    "light": {
        "bg": "#fbfcfd", "frame": "#d0d7de", "ink": "#1f2328", "muted": "#59636e",
        "node": "#ffffff", "nodeline": "#8c959f",
        "blue": "#0969da", "orange": "#bc4c00", "green": "#1a7f37", "red": "#cf222e",
        "purple": "#8250df",
        "leaf": "#fff8c5", "derived": "#ddf4ff", "wild": "#fbefff", "band": "#f2f4f6",
        "badge": "#ffffff", "bad": "#ffebe9",
    },
    "dark": {
        "bg": "#1a1c1e", "frame": "#3d444d", "ink": "#e6edf3", "muted": "#9198a1",
        "node": "#22272e", "nodeline": "#768390",
        "blue": "#4493f8", "orange": "#f0883e", "green": "#3fb950", "red": "#f85149",
        "purple": "#ab7df8",
        "leaf": "#3b3418", "derived": "#13304f", "wild": "#38254d", "band": "#212529",
        "badge": "#22272e", "bad": "#4c1d1f",
    },
}
COLOURS = ("ink", "muted", "blue", "orange", "green", "red", "purple")
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
CHAR_W = 7.4  # monospace advance at 12.5px, for sizing boxes


class Box:
    """A labelled rectangle centred on (cx, cy)."""

    def __init__(self, cx, cy, lines, kind="node", w=None, h=None):
        self.lines = [lines] if isinstance(lines, str) else list(lines)
        self.cx, self.cy, self.kind = cx, cy, kind
        self.w = w or max(len(s) for s in self.lines) * CHAR_W + 22
        self.h = h or 16 * len(self.lines) + 14

    @property
    def left(self):
        return (self.cx - self.w / 2, self.cy)

    @property
    def right(self):
        return (self.cx + self.w / 2, self.cy)

    @property
    def top(self):
        return (self.cx, self.cy - self.h / 2)

    @property
    def bottom(self):
        return (self.cx, self.cy + self.h / 2)

    def at(self, fx, fy):
        """A point on or in the box: fx, fy in [-1, 1] from the centre."""
        return (self.cx + fx * self.w / 2, self.cy + fy * self.h / 2)


class Fig:
    def __init__(self, name, w, h):
        self.name, self.w, self.h = name, w, h
        self.parts: list[str] = []

    # -- primitives ----------------------------------------------------------
    def box(self, b: Box, dashed=False):
        cls = {"node": "n", "leaf": "lf", "derived": "dv", "wild": "wd", "ghost": "gh"}[b.kind]
        x, y = b.cx - b.w / 2, b.cy - b.h / 2
        dash = ' stroke-dasharray="5 4"' if dashed or b.kind == "ghost" else ""
        self.parts.append(f'<rect class="{cls}" x="{x:.1f}" y="{y:.1f}" width="{b.w:.1f}" '
                          f'height="{b.h:.1f}" rx="6"{dash}/>')
        top = b.cy - 8 * (len(b.lines) - 1)
        for i, line in enumerate(b.lines):
            self.text(b.cx, top + 16 * i + 4.5, line, mono=True, anchor="middle",
                      colour="muted" if b.kind == "ghost" or i > 0 else "ink",
                      size=12.5 if i == 0 else 11.5)
        return b

    def rect(self, x, y, w, h, cls="band", rx=8):
        self.parts.append(f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}"/>')

    def text(self, x, y, s, mono=False, anchor="start", colour="ink", size=12.5, bold=False,
             italic=False):
        fam = "m" if mono else "s"
        extra = (' font-weight="600"' if bold else "") + (' font-style="italic"' if italic else "")
        self.parts.append(f'<text class="{fam} c-{colour}" x="{x:.1f}" y="{y:.1f}" '
                          f'font-size="{size}" text-anchor="{anchor}"{extra}>{escape(s)}</text>')

    def arrow(self, p, q, colour="ink", dashed=False, bend=0.0, width=1.6, label=None,
              label_at=0.5, label_dx=0, label_dy=-7, label_colour=None, head=True, mono=False):
        (x1, y1), (x2, y2) = p, q
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        dx, dy = x2 - x1, y2 - y1
        length = max((dx * dx + dy * dy) ** 0.5, 1)
        cx, cy = mx - dy / length * bend, my + dx / length * bend
        d = f"M{x1:.1f},{y1:.1f} Q{cx:.1f},{cy:.1f} {x2:.1f},{y2:.1f}"
        dash = ' stroke-dasharray="6 4"' if dashed is True else (
            f' stroke-dasharray="{dashed}"' if dashed else "")
        mark = f' marker-end="url(#h-{colour})"' if head else ""
        self.parts.append(f'<path class="ln s-{colour}" d="{d}" stroke-width="{width}"{dash}{mark}/>')
        if label:
            t = label_at
            lx = (1 - t) ** 2 * x1 + 2 * (1 - t) * t * cx + t * t * x2
            ly = (1 - t) ** 2 * y1 + 2 * (1 - t) * t * cy + t * t * y2
            self.text(lx + label_dx, ly + label_dy, label, anchor="middle",
                      colour=label_colour or colour, size=11.5, mono=mono)

    def badge(self, x, y, n, colour="ink"):
        self.parts.append(f'<circle class="bdg s-{colour}" cx="{x:.1f}" cy="{y:.1f}" r="9"/>')
        self.text(x, y + 4, str(n), anchor="middle", colour=colour, size=11, bold=True)

    def cross(self, x, y, colour="red", r=6):
        self.parts.append(f'<path class="ln s-{colour}" stroke-width="2.4" '
                          f'd="M{x - r},{y - r} L{x + r},{y + r} M{x - r},{y + r} L{x + r},{y - r}"/>')

    # -- output --------------------------------------------------------------
    def render(self, pal: dict) -> str:
        css = [
            f".s{{font-family:{SANS}}} .m{{font-family:{MONO}}}",
            f".bgr{{fill:{pal['bg']};stroke:{pal['frame']}}}",
            f".band{{fill:{pal['band']};stroke:none}}",
            f".n{{fill:{pal['node']};stroke:{pal['nodeline']};stroke-width:1.3}}",
            f".gh{{fill:none;stroke:{pal['nodeline']};stroke-width:1.3}}",
            f".lf{{fill:{pal['leaf']};stroke:{pal['nodeline']};stroke-width:1.3}}",
            f".dv{{fill:{pal['derived']};stroke:{pal['blue']};stroke-width:1.5}}",
            f".wd{{fill:{pal['wild']};stroke:{pal['purple']};stroke-width:1.5}}",
            f".cell{{fill:{pal['node']};stroke:{pal['frame']}}}",
            f".hl{{fill:{pal['derived']};stroke:{pal['blue']}}}",
            f".lf2{{fill:{pal['leaf']};stroke:{pal['frame']}}}",
            f".bad{{fill:{pal['bad']};stroke:{pal['red']}}}",
            f".bdg{{fill:{pal['badge']};stroke-width:1.4}}",
            ".ln{fill:none;stroke-linecap:round}",
        ]
        for c in COLOURS:
            css.append(f".s-{c}{{stroke:{pal[c]}}} .c-{c}{{fill:{pal[c]}}}")
        markers = "".join(
            f'<marker id="h-{c}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
            f'markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" '
            f'fill="{pal[c]}"/></marker>' for c in COLOURS)
        body = "\n".join(self.parts)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" '
                f'width="{self.w}" height="{self.h}" role="img">\n'
                f'<style>{" ".join(css)}</style>\n<defs>{markers}</defs>\n'
                f'<rect class="bgr" x="0.5" y="0.5" width="{self.w - 1}" height="{self.h - 1}" rx="10"/>\n'
                f'{body}\n</svg>\n')


def table(f: Fig, x, y, cols, rows, col_w, row_h=26, highlight=()):
    """A small grid. ``cols`` are header strings; ``rows`` lists of cell strings."""
    xs = [x]
    for w in col_w:
        xs.append(xs[-1] + w)
    for j, head in enumerate(cols):
        for k, part in enumerate(head.split("\n")):
            f.text(xs[j] + 8, y - 8 - 14 * (len(head.split("\n")) - 1 - k), part, colour="muted",
                   size=11.5, bold=True)
    for i, row in enumerate(rows):
        ry = y + i * row_h
        f.rect(x, ry, sum(col_w), row_h, cls="hl" if i in highlight else "cell", rx=0)
        for j, cell in enumerate(row):
            f.text(xs[j] + 8, ry + row_h / 2 + 4.5, cell, mono=True, size=12)


# ---------------------------------------------------------------------------
# How the graph index works (explanation/graph-index.md)
# ---------------------------------------------------------------------------

def graph_tuples() -> Fig:
    """The page's counting example: four tuples, four edges."""
    f = Fig("graph-index-tuples", 860, 250)
    f.text(24, 38, "tuples", bold=True)
    tuples = ["user:alice member group:eng", "group:eng#member member group:staff",
              "group:eng#member viewer doc:1", "group:staff#member viewer doc:1"]
    for i, t in enumerate(tuples):
        f.badge(36, 66 + 30 * i - 4, i + 1)
        f.text(54, 66 + 30 * i, t, mono=True)
    f.text(320, 38, "graph: each tuple is one edge, user → object#relation", bold=True)
    alice = f.box(Box(380, 150, "user:alice"))
    eng = f.box(Box(550, 150, "group:eng#member"))
    staff = f.box(Box(705, 82, "group:staff#member"))
    doc = f.box(Box(770, 190, "doc:1#viewer"))
    f.arrow(alice.right, eng.left)
    f.badge(449, 150 - 16, 1)
    f.arrow(eng.at(0.55, -1), staff.at(-0.7, 1))
    f.badge(600, 108, 2)
    f.arrow(eng.at(0.6, 1), doc.left, bend=-12)
    f.badge(660, 192, 3)
    f.arrow(staff.at(0.6, 1), doc.at(0.3, -1))
    f.badge(766, 132, 4)
    f.text(320, 232, "“does alice have viewer on doc:1?” = is there a path from "
                     "user:alice to doc:1#viewer?", colour="muted", italic=True)
    return f


def graph_two_paths() -> Fig:
    """The closure rows of the same example. Counts observed 2026-10-23 by reading the
    ``Edge`` table after the page's four ``add_tuple`` calls, then again after removing
    tuple 3 (``indirect_edge_count``)."""
    f = Fig("graph-index-paths", 920, 330)
    f.text(24, 34, "two paths from alice to doc:1#viewer", bold=True)
    alice = f.box(Box(78, 140, "user:alice"))
    eng = f.box(Box(232, 140, "group:eng#member"))
    staff = f.box(Box(375, 78, "group:staff#member"))
    doc = f.box(Box(395, 220, "doc:1#viewer"))
    (ax, ay), (ex, ey) = alice.right, eng.left
    f.arrow((ax, ay - 3), (ex, ey - 3), colour="blue", width=2.2)
    f.arrow((ax, ay + 3), (ex, ey + 3), colour="orange", width=2.2)
    f.badge(142, 116, 1)
    f.arrow(eng.at(0.45, -1), staff.at(-0.75, 1), colour="orange", width=2.2)
    f.badge(268, 96, 2)
    f.arrow(eng.at(0.3, 1), doc.at(-0.5, -1), colour="blue", width=2.2)
    f.badge(300, 196, 3)
    f.arrow(staff.at(0.2, 1), doc.at(0.3, -1), colour="orange", width=2.2)
    f.badge(424, 146, 4)
    f.text(24, 282, "path 1:  1 then 3", colour="blue", bold=True)
    f.text(24, 304, "path 2:  1, 2, then 4", colour="orange", bold=True)
    f.text(490, 34, "the closure table: one row per connected pair", bold=True)
    table(f, 490, 72,
          ["from", "to", "paths", "after\nremoving 3"],
          [["user:alice", "group:eng#member", "1", "1"],
           ["user:alice", "group:staff#member", "1", "1"],
           ["user:alice", "doc:1#viewer", "2", "1"],
           ["group:eng#member", "group:staff#member", "1", "1"],
           ["group:eng#member", "doc:1#viewer", "2", "1"],
           ["group:staff#member", "doc:1#viewer", "1", "1"]],
          col_w=[140, 150, 52, 72], highlight={2})
    f.text(490, 254, "Removing a tuple subtracts paths; a row is deleted only when", colour="muted")
    f.text(490, 272, "its count reaches 0. Alice keeps access through path 2.", colour="muted")
    return f


def graph_add_edge() -> Fig:
    """The update rule for one new edge, on made-up counts."""
    f = Fig("graph-index-add-edge", 900, 262)
    f.text(24, 32, "adding the edge u → v", bold=True)

    def dot(x, y, label, kind="node"):
        return f.box(Box(x, y, label, kind=kind, w=40, h=30))

    a1, a2, u = dot(60, 80, "a1"), dot(60, 180, "a2"), dot(220, 130, "u")
    v, b1, b2 = dot(390, 130, "v"), dot(550, 80, "b1"), dot(550, 180, "b2")
    f.arrow(a1.right, u.at(-1, -0.4), colour="muted", dashed="2 4", label="2 paths",
            label_dy=-9)
    f.arrow(a2.right, u.at(-1, 0.4), colour="muted", dashed="2 4", label="1 path",
            label_dy=18)
    f.arrow(u.right, v.left, colour="green", width=2.6, label="new edge", label_dy=-10)
    f.arrow(v.at(1, -0.4), b1.left, colour="muted", dashed="2 4", label="1 path",
            label_dy=-9)
    f.arrow(v.at(1, 0.4), b2.left, colour="muted", dashed="2 4", label="3 paths",
            label_dy=18)
    f.text(60, 226, "reach u", anchor="middle", colour="muted")
    f.text(550, 226, "reached from v", anchor="middle", colour="muted")
    f.text(640, 52, "paths added to row (a, b)", bold=True)
    gx, gy, cw, rh = 700, 92, 54, 30
    for j, (name, n) in enumerate([("v", 1), ("b1", 1), ("b2", 3)]):
        f.text(gx + cw * j + cw / 2, gy - 12, f"{name} ×{n}", anchor="middle", mono=True, size=12)
    for i, (name, n) in enumerate([("a1", 2), ("a2", 1), ("u", 1)]):
        f.text(gx - 10, gy + rh * i + 20, f"{name} ×{n}", anchor="end", mono=True, size=12)
        for j, m in enumerate([1, 1, 3]):
            f.rect(gx + cw * j, gy + rh * i, cw, rh, cls="cell", rx=0)
            f.text(gx + cw * j + cw / 2, gy + rh * i + 20, f"+{n * m}", anchor="middle",
                   mono=True, colour="green", bold=True)
    f.text(24, 250, "paths(a, b)  +=  paths(a, u) × paths(v, b)      with paths(x, x) = 1 "
                    "(the empty path).   Removing the edge subtracts the same grid.",
           mono=True, size=11.5, colour="muted")
    return f


def graph_wildcard() -> Fig:
    """A ``user:*`` grant is one edge from one node; a check makes two probes."""
    f = Fig("graph-index-wildcard", 900, 262)
    f.text(24, 34, "tuples", bold=True)
    for i, t in enumerate(["user:* viewer folder:p", "folder:p parent doc:1"]):
        f.badge(36, 62 + 30 * i - 4, i + 1)
        f.text(54, 62 + 30 * i, t, mono=True)
    f.text(24, 150, "viewer on doc includes", colour="muted", size=11.5)
    f.text(24, 166, "viewer from parent", colour="muted", size=11.5, mono=True)
    star = f.box(Box(370, 92, "user:*", kind="wild"))
    folder = f.box(Box(560, 92, "folder:p#viewer"))
    doc = f.box(Box(780, 92, "doc:1#viewer"))
    f.arrow(star.right, folder.left)
    f.badge(452, 76, 1)
    f.arrow(folder.right, doc.left)
    f.badge(668, 76, 2)
    f.arrow(star.top, doc.top, colour="green", dashed="2 4", bend=-46, width=2,
            label="probe 2: a closure row from user:*?  yes", label_dy=-8)
    ghost = f.box(Box(370, 200, ["user:someone-new", "(no node)"], kind="ghost"))
    f.arrow(ghost.right, doc.at(-0.2, 1), colour="red", dashed=True, bend=8,
            label="probe 1: a closure row from the user?  no", label_at=0.5, label_dx=30,
            label_dy=26)
    f.cross(doc.cx + 30, doc.cy + 34)
    f.text(24, 222, "check(user:someone-new,", mono=True, size=12)
    f.text(24, 240, "      viewer, doc:1) = True", mono=True, size=12)
    return f


def graph_any_all() -> Fig:
    """The two kinds of wildcard node and their bridges."""
    f = Fig("graph-index-any-all", 960, 330)
    f.rect(12, 12, 460, 262)
    f.rect(488, 12, 460, 262)
    f.text(28, 38, "an any node: “some group”", bold=True)
    f.text(28, 56, "[group:*#member]", mono=True, colour="muted", size=11.5)
    alice = f.box(Box(70, 100, "user:alice"))
    eng = f.box(Box(205, 100, "group:eng#member"))
    ops = f.box(Box(205, 200, "group:ops#member"))
    anyn = f.box(Box(395, 150, ["group:*#member", "any"], kind="wild"))
    doc = f.box(Box(395, 245, "doc:1#viewer"))
    f.arrow(alice.right, eng.left)
    f.arrow(eng.right, anyn.at(-1, -0.3), colour="purple", dashed=True, label="bridge",
            label_dy=-8)
    f.arrow(ops.right, anyn.at(-1, 0.3), colour="purple", dashed=True, label="bridge",
            label_dy=18)
    f.arrow(anyn.bottom, doc.top, label="grant", label_dx=24, label_dy=4)
    f.text(28, 262, "group:*#member viewer doc:1", mono=True, size=11, colour="muted")
    f.text(504, 38, "an all node: “every folder”", bold=True)
    f.text(504, 56, "object wildcard folder:*", mono=True, colour="muted", size=11.5)
    bob = f.box(Box(545, 150, "user:bob"))
    alln = f.box(Box(690, 150, ["folder:*#viewer", "all"], kind="wild"))
    fp = f.box(Box(872, 90, "folder:p#viewer"))
    fq = f.box(Box(872, 210, "folder:q#viewer"))
    f.arrow(bob.right, alln.left, label="grant", label_dy=-8)
    f.arrow(alln.at(1, -0.3), fp.left, colour="purple", dashed=True, label="bridge",
            label_dx=-12, label_dy=-8)
    f.arrow(alln.at(1, 0.3), fq.left, colour="purple", dashed=True, label="bridge",
            label_dx=-12, label_dy=18)
    f.text(504, 262, "user:bob viewer folder:*", mono=True, size=11, colour="muted")
    a = f.box(Box(110, 304, "T:*  any", kind="wild"))
    b = f.box(Box(280, 304, "T:*  all", kind="wild"))
    f.arrow(a.right, b.left, colour="red", dashed=True)
    f.cross(195, 304)
    f.text(345, 309, "never an edge from any to all: being one instance would then grant "
                     "what was given to every instance", colour="muted", size=11.5)
    return f


# ---------------------------------------------------------------------------
# How `and` and `but not` work (explanation/boolean-operators.md)
# ---------------------------------------------------------------------------

BOOL_SCHEMA = ["define banned: [user]", "define verified: [user]",
               "define viewer: [user] but not banned", "define commenter: viewer and verified"]


def boolean_layers() -> Fig:
    """Strata and leaves for ``BOOL_SCHEMA``. Observed 2026-10-23 on a ``Store``'s
    ``CompiledBooleans``: ``strata == [[('doc', 'viewer')], [('doc', 'commenter')]]``;
    leaves ``viewer.0`` (stored ``viewer`` tuples), ``viewer.1`` (the subtracted side),
    ``commenter.0`` (``verified``); ``commenter`` reads ``viewer`` as a derived relation."""
    f = Fig("boolean-layers", 920, 470)
    f.text(24, 34, "schema", bold=True)
    for i, line in enumerate(BOOL_SCHEMA):
        f.text(24, 58 + 19 * i, line, mono=True)
    f.text(420, 52, "Each layer is computed only from layers below it,", colour="muted")
    f.text(420, 71, "and is complete before the next layer reads it.", colour="muted")
    bands = [(130, "layer 2", "derived: commenter"), (232, "layer 1", "derived: viewer"),
             (334, "layer 0", "the closure (path counting)")]
    for y, name, what in bands:
        f.rect(12, y, 896, 88)
        f.text(28, y + 26, name, bold=True)
        f.text(28, y + 44, what, colour="muted", size=11.5)
    com = f.box(Box(560, 174, ["doc:1#commenter", "viewer and commenter.0"], kind="derived"))
    view = f.box(Box(380, 276, ["doc:1#viewer", "viewer.0 but not viewer.1"], kind="derived"))
    v0 = f.box(Box(270, 378, ["doc:1#viewer.0", "viewer tuples"], kind="leaf"))
    v1 = f.box(Box(480, 378, ["doc:1#viewer.1", "banned tuples"], kind="leaf"))
    c0 = f.box(Box(700, 378, ["doc:1#commenter.0", "verified tuples"], kind="leaf"))
    f.arrow(v0.top, view.at(-0.45, 1), colour="blue", label="keep", label_dx=-20, label_dy=4)
    f.arrow(v1.top, view.at(0.45, 1), colour="red", label="but not", label_dx=28, label_dy=4)
    f.arrow(view.top, com.at(-0.45, 1), colour="blue", label="and", label_dx=-18, label_dy=4)
    f.arrow(c0.top, com.at(0.45, 1), colour="blue", label="and", label_dx=18, label_dy=4)
    f.text(760, 166, "derived edges", colour="muted", size=11.5)
    f.text(760, 182, "+ residue", colour="muted", size=11.5)
    f.text(760, 268, "derived edges", colour="muted", size=11.5)
    f.text(760, 284, "+ residue", colour="muted", size=11.5)
    f.text(24, 450, "Leaves (yellow) are internal relations with ordinary closure rows. "
                    "Derived relations (blue) are written by the delta processor.",
           colour="muted", size=11.5)
    return f


def boolean_cascade() -> Fig:
    """One write, settled layer by layer. Observed 2026-10-23 with ``BOOL_SCHEMA`` after
    ``user:alice`` was given ``viewer`` and ``verified`` on ``doc:1``: writing ``user:alice
    banned doc:1`` appended outbox rows ADDED ``banned``, ADDED ``viewer.1``, then REMOVED
    ``viewer``, then REMOVED ``commenter``, and ``check`` on ``commenter`` returned False."""
    f = Fig("boolean-cascade", 940, 380)
    f.text(24, 32, "store.add_tuple(\"user:alice\", \"banned\", \"doc:1\")", mono=True, bold=True)
    f.text(24, 52, "alice already has viewer and verified on doc:1; everything below is one "
                   "transaction", colour="muted", size=11.5)
    lanes = [(76, "layer 0", "closure"), (170, "layer 1", "viewer"), (264, "layer 2", "commenter")]
    for y, name, what in lanes:
        f.rect(12, y, 916, 84)
        f.text(28, y + 36, name, bold=True)
        f.text(28, y + 54, what, colour="muted", size=11.5, mono=True)
    s0 = f.box(Box(255, 118, ["add edges alice → doc:1#banned", "and alice → doc:1#viewer.1"]))
    s1 = f.box(Box(485, 212, ["recompute viewer for alice:", "viewer.0 yes, but viewer.1 yes",
                              "→ remove derived edge"], kind="derived"))
    s2 = f.box(Box(735, 306, ["recompute commenter for alice:", "viewer no, commenter.0 yes",
                              "→ remove derived edge"], kind="derived"))
    f.arrow(s0.at(0.75, 1), s1.at(-1, -0.25), colour="orange", bend=-18,
            label="outbox: +banned, +viewer.1", label_at=0.45, label_dx=-128, label_dy=12,
            mono=True)
    f.arrow(s1.at(0.6, 1), s2.at(-1, -0.25), colour="orange", bend=-18,
            label="outbox: −viewer", label_at=0.45, label_dx=-92, label_dy=14, mono=True)
    f.text(700, 120, "round 1 reads only rows the", colour="muted", size=11.5)
    f.text(700, 136, "write added; round 2 only rows", colour="muted", size=11.5)
    f.text(700, 152, "round 1 added", colour="muted", size=11.5)
    f.text(24, 370, "outbox: −commenter.  No derived relation left to recompute, "
                    "so the write commits; check(alice, commenter, doc:1) is False.",
           colour="muted", size=11.5)
    return f


def boolean_residue() -> Fig:
    """``[user, user:*] but not banned``: no edge per user, one residue record."""
    f = Fig("boolean-residue", 920, 300)
    f.text(24, 32, "define viewer: [user, user:*] but not banned", mono=True, bold=True)
    for i, t in enumerate(["user:* viewer doc:1", "user:mallory banned doc:1"]):
        f.text(24, 62 + 20 * i, t, mono=True, colour="muted", size=12)
    star = f.box(Box(90, 140, "user:*", kind="wild"))
    mal = f.box(Box(90, 210, "user:mallory"))
    v0 = f.box(Box(300, 140, "doc:1#viewer.0", kind="leaf"))
    v1 = f.box(Box(300, 210, "doc:1#viewer.1", kind="leaf"))
    f.arrow(star.right, v0.left)
    f.arrow(mal.right, v1.left)
    f.text(300, 108, "layer 0: closure", anchor="middle", colour="muted", size=11.5)
    view = f.box(Box(620, 120, "doc:1#viewer", kind="derived"))
    f.arrow((v0.right[0] + 6, 175), (500, 175), colour="orange", width=2.2,
            label="delta processor", label_dy=-8)
    f.arrow(view.bottom, (view.cx, 148), colour="muted", head=False)
    f.rect(500, 148, 270, 80, cls="cell")
    f.text(512, 170, "residue for doc:1#viewer", bold=True, size=11.5)
    f.text(512, 192, "covered by:  user:*", mono=True, size=12)
    f.text(512, 212, "except:      user:mallory", mono=True, size=12)
    f.text(790, 124, "no derived edges", colour="muted", size=11.5)
    for y, q, why, ans in [(262, "check(user:bob, viewer, doc:1)", "no derived edge; residue covers user:*, "
                                "and bob is not excepted", "True"),
                           (282, "check(user:mallory, viewer, doc:1)", "no derived edge; residue "
                                "excepts mallory", "False")]:
        f.text(24, y, q, mono=True, size=11.5)
        f.text(300, y, why, colour="muted", size=11.5)
        f.text(640, y, "→ " + ans, mono=True, size=11.5, bold=True)
    return f


# ---------------------------------------------------------------------------
# The two backends (explanation/two-backends.md)
# ---------------------------------------------------------------------------

CHAIN = ["user:alice", "group:eng#member", "group:staff#member", "folder:root#viewer",
         "folder:projects#viewer", "doc:roadmap#viewer"]


def backends_work() -> Fig:
    """The page's example chain, evaluated at read time or stored at write time."""
    f = Fig("backends-work", 920, 372)
    for px, title, sub in [(12, "set engine", "does the work when you read"),
                           (466, "graph index", "does the work when you write")]:
        f.rect(px, 12, 442, 348)
        f.text(px + 16, 38, title, bold=True)
        f.text(px + 16, 56, sub, colour="muted", size=11.5)
    stacks = []
    for cx in (124, 578):
        boxes = [f.box(Box(cx, 92 + 40 * i, name, w=186)) for i, name in enumerate(CHAIN)]
        for a, b in zip(boxes, boxes[1:], strict=False):  # adjacent pairs: truncation intended
            f.arrow(a.bottom, b.top, colour="muted")
        stacks.append(boxes)
    left, right = stacks
    f.arrow(left[-1].right, left[0].right, colour="orange", width=2.2, bend=70)
    f.text(272, 186, "check walks the chain:", colour="orange", size=11.5)
    f.text(272, 204, "5 hops, on every check", colour="orange", size=11.5)
    f.arrow(right[0].right, right[-1].right, colour="green", width=2.2, dashed="2 4",
            bend=-70)
    f.text(726, 186, "one stored row, written when", colour="green", size=11.5)
    f.text(726, 204, "the chain was connected;", colour="green", size=11.5)
    f.text(726, 222, "check reads it: 1 lookup", colour="green", size=11.5)
    f.text(28, 336, "write: record 1 tuple.  read: grows with depth and fan-out.",
           colour="muted", size=11.5)
    f.text(482, 336, "write: a row per newly connected pair.  read: a few lookups.",
           colour="muted", size=11.5)
    return f


def store_composition() -> Fig:
    """How a ``Store`` routes writes and reads (two-backends.md, "How a Store combines
    them"; consistency.md, "What can be stale")."""
    f = Fig("store-composition", 940, 372)
    f.text(24, 34, "writes", bold=True)
    f.text(470, 34, "inside a Store", bold=True, anchor="middle")
    f.text(916, 34, "reads", bold=True, anchor="end")
    eng = f.box(Box(470, 92, ["set engine", "in memory, bitmaps"]))
    log = f.box(Box(470, 196, ["tuples + tuple log", "the source of truth"], kind="leaf"))
    idx = f.box(Box(470, 300, ["graph index + cursor", "a view of the log"], kind="derived"))
    w = f.box(Box(104, 196, ["add_tuple", "remove_tuple"]))
    f.arrow(w.at(0.4, -1), eng.left, bend=-20, label="1  validate (else AdmissionRejected)",
            label_at=0.55, label_dx=-6, label_dy=-10)
    f.arrow(w.right, log.left, label="2  append a log row, return its id (the token)",
            label_dx=6, label_dy=-8)
    f.arrow(w.at(0.4, 1), idx.left, bend=20, dashed=True)
    f.text(24, 330, "3  apply: in the same transaction (sync),", size=11.5)
    f.text(24, 348, "    or later, in catch_up() (async)", size=11.5)
    f.arrow(log.at(-0.2, -1), eng.at(-0.2, 1), colour="green", label="new rows",
            label_dx=-34, label_dy=4)
    f.arrow(log.at(-0.2, 1), idx.at(-0.2, -1), colour="green", label="rows in order",
            label_dx=-44, label_dy=4)
    ex = f.box(Box(840, 92, "expand"))
    ck = f.box(Box(840, 196, "check"))
    lk = f.box(Box(840, 300, ["lookup", "lookup_reverse"]))
    f.arrow(ex.left, eng.right, colour="blue", label="always", label_dy=-8)
    f.arrow(ck.at(-1, 0.3), idx.at(1, -0.4), colour="blue", label="if fresh enough",
            label_at=0.45, label_dx=30, label_dy=-14)
    f.arrow(ck.at(-1, -0.3), eng.at(1, 0.4), colour="orange", label="otherwise",
            label_at=0.45, label_dx=8, label_dy=-6)
    f.arrow(lk.left, idx.right, colour="blue", label="only", label_dy=-8)
    f.text(700, 350, "not fresh: LookupNotFresh / IndexStalled", colour="red", size=11.5)
    return f


# ---------------------------------------------------------------------------
# Consistency (explanation/consistency.md)
# ---------------------------------------------------------------------------

def log_strip(f: Fig, x, y, n, cw=56, h=34, styles=None, labels=None):
    """``n`` log rows left to right."""
    styles, labels = styles or {}, labels or {}
    for i in range(n):
        f.rect(x + cw * i, y, cw, h, cls=styles.get(i + 1, "cell"), rx=0)
        f.text(x + cw * i + cw / 2, y + h / 2 + 4.5, labels.get(i + 1, f"row {i + 1}"),
               anchor="middle", mono=True, size=11.5)


def cursor(f: Fig, x, y, text="cursor", colour="blue"):
    f.parts.append(f'<path class="c-{colour}" d="M{x:.1f},{y:.1f} l-7,12 h14 z"/>')
    f.text(x, y + 28, text, anchor="middle", colour=colour, size=11.5, bold=True)


def consistency_sync_async() -> Fig:
    f = Fig("consistency-sync-async", 920, 262)
    f.text(24, 34, "the tuple log, and how far the graph index has applied it", bold=True)
    x0, cw = 190, 62
    for y, name, sub, applied, note in [
            (64, "sync=True", "the default", 6,
             ["lag() is 0: each write and its index", "update commit together"]),
            (160, "sync=False", "async", 4,
             ["lag() is 2: these rows wait for", "catch_up(), which applies them in batches"])]:
        f.text(24, y + 16, name, mono=True, bold=True)
        f.text(24, y + 34, sub, colour="muted", size=11.5)
        styles = {i: ("hl" if i <= applied else "lf2") for i in range(1, 7)}
        log_strip(f, x0, y, 6, cw=cw, styles=styles)
        cursor(f, x0 + cw * applied, y + 38)
        f.text(x0 + cw * 6 + 24, y + 12, note[0], colour="muted", size=11.5)
        f.text(x0 + cw * 6 + 24, y + 30, note[1], colour="muted", size=11.5)
    f.text(x0 + cw * 5.5, 56, "newest write: its id is the token", anchor="middle",
           colour="muted", size=11)
    f.text(24, 250, "blue: applied to the index", colour="muted", size=11.5)
    f.text(200, 250, "yellow: logged, not applied yet", colour="muted", size=11.5)
    return f


def consistency_revoke() -> Fig:
    """The page's executed example: async store, grant caught up, then revoked."""
    f = Fig("consistency-revoke", 980, 300)
    f.text(24, 34, "async: the grant was applied, the revoke not yet", bold=True)
    f.rect(24, 64, 250, 34, cls="hl", rx=0)
    f.text(34, 86, "t1  ADD alice viewer doc:1", mono=True, size=11.5)
    f.rect(24, 98, 250, 34, cls="lf2", rx=0)
    f.text(34, 120, "t2  REMOVE alice viewer doc:1", mono=True, size=11.5)
    f.text(150, 56, "tuple log", anchor="middle", colour="muted", size=11.5)
    f.parts.append('<path class="c-blue" d="M276,98 l12,-7 v14 z"/>')
    f.text(294, 102, "cursor", colour="blue", size=11.5, bold=True)
    idx = f.box(Box(480, 110, ["graph index", "applied up to t1: alice can view"], kind="derived"))
    eng = f.box(Box(480, 222, ["set engine", "has read t2: alice cannot"]))
    f.arrow((276, 124), eng.left, colour="green", bend=12, label="read through t2",
            label_at=0.55, label_dx=-56, label_dy=10)
    r1 = f.box(Box(840, 110, "check(alice, viewer, doc:1)"))
    r2 = f.box(Box(840, 222, ["check(alice, viewer, doc:1,", "      at_least=t2)"]))
    f.arrow(r1.left, idx.right, colour="red", label="no token: the index as it is", label_dx=34,
            label_dy=-14)
    f.text(840, 148, "True: a stale ALLOW", anchor="middle", colour="red", bold=True)
    f.arrow(r2.at(-0.6, -1), idx.at(0.7, 1), colour="muted", dashed=True)
    f.cross(668, 170, colour="muted")
    f.text(688, 174, "cursor is before t2", colour="muted", size=11.5)
    f.arrow(r2.left, eng.right, colour="green", label="falls back", label_dy=-8)
    f.text(840, 268, "False: correct", anchor="middle", colour="green", bold=True)
    return f


def consistency_stall() -> Fig:
    f = Fig("consistency-stall", 920, 232)
    f.text(24, 34, "a stall: one row cannot be applied, so nothing after it can be", bold=True)
    x0, cw = 24, 70
    styles = {1: "hl", 2: "hl", 3: "hl", 4: "bad", 5: "lf2", 6: "lf2", 7: "lf2"}
    log_strip(f, x0, 60, 7, cw=cw, styles=styles)
    cursor(f, x0 + cw * 3, 98)
    f.text(x0 + cw * 3.5, 140, "fails", anchor="middle", colour="red", bold=True)
    f.text(x0 + cw * 5.5, 120, "wait behind it, revokes too", anchor="middle", colour="muted",
           size=11.5)
    f.text(540, 74, "The stall is recorded on the cursor row, so every", colour="muted",
           size=11.5)
    f.text(540, 92, "instance sees it. While it lasts:", colour="muted", size=11.5)
    for i, (what, then) in enumerate([("check without a token", "set engine"),
                                      ("lookup without a token", "IndexStalled"),
                                      ("sync=True writes", "refused")]):
        f.text(540, 116 + 20 * i, what, mono=True, size=11.5)
        f.text(728, 116 + 20 * i, "\u2192 " + then, mono=True, size=11.5)
    f.text(24, 196, "It ends at the next catch_up() that applies a row; a row that can never be "
                    "applied (PathCountExceeded)", colour="muted", size=11.5)
    f.text(24, 214, "needs the tuple removed and the index rebuilt with rebuild_index().",
           colour="muted", size=11.5)
    return f


FIGURES = [graph_tuples, graph_two_paths, graph_add_edge, graph_wildcard, graph_any_all,
           boolean_layers, boolean_cascade, boolean_residue, backends_work, store_composition,
           consistency_sync_async, consistency_revoke, consistency_stall]


def generate() -> dict[str, str]:
    """{file name: SVG text} for every figure in both themes."""
    out = {}
    for make in FIGURES:
        fig = make()
        out[f"{fig.name}.svg"] = fig.render(PALETTES["light"])
        out[f"{fig.name}-dark.svg"] = fig.render(PALETTES["dark"])
    return out


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, svg in generate().items():
        (OUT / name).write_text(svg, encoding="utf-8", newline="\n")
        print("wrote", (OUT / name).relative_to(OUT.parent.parent.parent))
