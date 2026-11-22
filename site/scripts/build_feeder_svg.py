"""Build a simplified line drawing of the IEEE European LV Test Feeder for the site hero.

Reads (read only) the git-ignored feeder files in data/feeders/LVTestCase and writes
ONE simplified SVG to site/src/assets/feeder.svg.

What goes into the SVG: line geometry only (rescaled, rounded to integer user units),
one dot per load bus, and the 4c_70 trunk drawn as a separate <path id="trunk">.
What does NOT go in: impedances, linecode data, bus names, ratings, lengths, loads.

Degree-2 bus chains are merged into single polylines and collinear points dropped
after rounding, so the file stays small while the full topology is kept.

Run from anywhere:  python site/scripts/build_feeder_svg.py
"""
from __future__ import annotations

import re
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "feeders" / "LVTestCase"
OUT = ROOT / "site" / "src" / "assets" / "feeder.svg"

WIDTH = 1000  # viewBox width in user units; height follows the aspect ratio
PAD = 16
TRUNK_CODE = "4c_70"
SOURCE_BUS = "1"  # LV side of the transformer (Transformers.txt: Buses=[SourceBus 1])


def read_inputs():
    coords = {}
    for row in (SRC / "Buscoords.txt").read_text().split("\n"):
        p = row.split()
        if len(p) >= 3:
            coords[p[0]] = (float(p[1]), float(p[2]))
    line_re = re.compile(r"Bus1=(\S+)\s+Bus2=(\S+).*?Linecode=(\S+)", re.I)
    lines = []
    for row in (SRC / "Lines.txt").read_text().split("\n"):
        m = line_re.search(row)
        if m:
            b1, b2, code = (m.group(1).split(".")[0], m.group(2).split(".")[0], m.group(3))
            lines.append((b1, b2, code))
    loads = set()
    for row in (SRC / "Loads.txt").read_text().split("\n"):
        m = re.search(r"Bus1=(\S+)", row, re.I)
        if m:
            loads.add(m.group(1).split(".")[0])
    return coords, lines, loads


def main() -> None:
    coords, lines, loads = read_inputs()

    # Map metres to a viewBox; flip y (map north up).
    xs = [c[0] for c in coords.values()]
    ys = [c[1] for c in coords.values()]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    s = (WIDTH - 2 * PAD) / (x1 - x0)
    height = round((y1 - y0) * s + 2 * PAD)

    def pt(bus):
        x, y = coords[bus]
        return (round((x - x0) * s + PAD), round((y1 - y) * s + PAD))

    # Trunk = 4c_70 segments connected to the transformer LV bus.
    trunk_adj = defaultdict(list)
    for b1, b2, code in lines:
        if code.lower() == TRUNK_CODE.lower():
            trunk_adj[b1].append(b2)
            trunk_adj[b2].append(b1)
    trunk_bus = {SOURCE_BUS}
    q = deque([SOURCE_BUS])
    while q:
        b = q.popleft()
        for n in trunk_adj[b]:
            if n not in trunk_bus:
                trunk_bus.add(n)
                q.append(n)
    is_trunk = lambda b1, b2, code: code.lower() == TRUNK_CODE.lower() and b1 in trunk_bus and b2 in trunk_bus

    # Tree adjacency for the non-trunk network, with BFS depth from the source.
    adj = defaultdict(list)
    for b1, b2, code in lines:
        if not is_trunk(b1, b2, code):
            adj[b1].append(b2)
            adj[b2].append(b1)
    full_adj = defaultdict(list)
    for b1, b2, _ in lines:
        full_adj[b1].append(b2)
        full_adj[b2].append(b1)
    dist = {SOURCE_BUS: 0}
    q = deque([SOURCE_BUS])
    while q:
        b = q.popleft()
        for n in full_adj[b]:
            if n not in dist:
                dist[n] = dist[b] + 1
                q.append(n)
    maxd = max(dist.values())

    def chains(adjacency, keep):
        """Split the graph into polylines between junction/end buses (degree != 2)."""
        seen = set()
        out = []
        nodes = sorted(adjacency, key=lambda b: dist.get(b, 0))
        for start in nodes:
            if len(adjacency[start]) == 2 and start not in keep:
                continue
            for n in adjacency[start]:
                e = frozenset((start, n))
                if e in seen:
                    continue
                seen.add(e)
                chain = [start, n]
                prev, cur = start, n
                while len(adjacency[cur]) == 2 and cur not in keep:
                    nxt = adjacency[cur][0] if adjacency[cur][1] == prev else adjacency[cur][1]
                    e = frozenset((cur, nxt))
                    if e in seen:
                        break
                    seen.add(e)
                    chain.append(nxt)
                    prev, cur = cur, nxt
                if dist.get(chain[0], 0) > dist.get(chain[-1], 0):
                    chain.reverse()
                out.append(chain)
        return out

    def simplify(points):
        """Drop repeated and exactly collinear points after integer rounding."""
        pts = []
        for p in points:
            if not pts or pts[-1] != p:
                pts.append(p)
        if len(pts) < 3:
            return pts
        res = [pts[0]]
        for i in range(1, len(pts) - 1):
            a, b, c = res[-1], pts[i], pts[i + 1]
            if (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) != 0:
                res.append(b)
        res.append(pts[-1])
        return res

    def d_attr(pts):
        out = f"M{pts[0][0]} {pts[0][1]}"
        for (px, py), (x, y) in zip(pts, pts[1:]):
            out += f"l{x - px} {y - py}"
        return out

    # Trunk: one path (all trunk chains joined as subpaths).
    # Trunk: ONE subpath (a depth-first walk that retraces short branches), so a single
    # dash animation draws it cleanly in every browser.
    t_adj = trunk_adj_only(trunk_adj, trunk_bus)
    walk, seen_t = [], set()

    def dfs(b):
        seen_t.add(b)
        walk.append(b)
        kids = sorted((n for n in t_adj[b] if n not in seen_t), key=lambda n: subtree(n, b))
        for n in kids:
            dfs(n)
            walk.append(b)

    def subtree(n, parent):
        size, stack, vis = 0, [n], {parent}
        while stack:
            x = stack.pop()
            if x in vis:
                continue
            vis.add(x)
            size += 1
            stack.extend(t_adj[x])
        return size

    dfs(SOURCE_BUS)
    # Visit the longest branch last so the walk ends at the far end, then trim the tail return.
    while len(walk) > 1 and walk[-1] in walk[:-1] and len(t_adj[walk[-1]]) > 1:
        walk.pop()
    trunk_d = d_attr(simplify([pt(b) for b in walk]))

    net_paths = []
    for c in chains(adj, loads | {SOURCE_BUS}):
        pts = simplify([pt(b) for b in c])
        if len(pts) < 2:
            continue
        delay = round(dist.get(c[0], 0) / maxd, 2)  # 0..1, used as a CSS animation delay fraction
        net_paths.append((delay, d_attr(pts)))
    net_paths.sort()

    load_pts = sorted(pt(b) for b in loads)  # keep all 55, even if two round to one point
    sx, sy = pt(SOURCE_BUS)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {height}" class="feeder-svg" fill="none">',
        '<g class="net" stroke-linecap="round" stroke-linejoin="round">',
    ]
    parts += [f'<path pathLength="1" style="--d:{dl}" d="{d}"/>' for dl, d in net_paths]
    parts.append("</g>")
    parts.append(f'<path id="trunk" class="trunk" pathLength="1" stroke-linecap="round" stroke-linejoin="round" d="{trunk_d}"/>')
    parts.append('<g class="loads">' + "".join(f'<circle cx="{x}" cy="{y}" r="2.5"/>' for x, y in load_pts) + "</g>")
    parts.append(f'<rect class="tx" x="{sx - 6}" y="{sy - 6}" width="12" height="12"/>')
    parts.append("</svg>")
    svg = "\n".join(parts) + "\n"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(svg, encoding="utf-8")
    print(f"buses with coords: {len(coords)}, lines: {len(lines)}, loads: {len(loads)}")
    print(f"trunk ({TRUNK_CODE}) buses connected to source: {len(trunk_bus)}")
    print(f"paths: {len(net_paths)} + trunk, viewBox {WIDTH}x{height}, size {OUT.stat().st_size} bytes -> {OUT}")


def trunk_adj_only(trunk_adj, trunk_bus):
    return {b: [n for n in ns if n in trunk_bus] for b, ns in trunk_adj.items() if b in trunk_bus}


if __name__ == "__main__":
    main()
