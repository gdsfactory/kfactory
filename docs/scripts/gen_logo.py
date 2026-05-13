"""Generate the kfactory κ logo as a real GDS, then export to SVG.

The κ is constructed in a `kf.KCLayout` using two layers (WG core and
STUB markers); each shape is a `kdb.DPolygon` produced from a centerline
+ width offset (cubic-Bezier centerlines stand in for true clothoids —
they're indistinguishable at favicon size and avoid pulling in the full
Euler-bend factory just to draw four shapes).

The cell is written to `<out_dir>/logo.gds`, then walked shape-by-shape
to produce `<out_dir>/logo.svg` with one `<polygon>` per shape and a
per-layer fill (turquoise core, deeper teal stubs).

Called as a build stage from `build_docs_source.py` (writes into
`docs/source-built/_static/`); can also run standalone to refresh
the assets:

    uv run -p 3.14 --extra docs --with . python docs/scripts/gen_logo.py
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import kfactory as kf
from kfactory import kdb

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "docs/source-built/_static"


class LogoLayers(kf.LayerInfos):
    WG: kdb.LayerInfo = kdb.LayerInfo(1, 0)
    STUB: kdb.LayerInfo = kdb.LayerInfo(2, 0)


# Per-layer SVG fill. Turquoise reads well on both light and dark
# palettes; the stubs use a slightly deeper teal so the port markers
# show through against the lighter waveguide core.
LAYER_FILL: dict[str, str] = {
    "WG": "#14B8A6",  # tailwind teal-500 — main waveguide
    "STUB": "#0F766E",  # tailwind teal-700 — port-stub accents
}


def cubic_bezier(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    n: int = 48,
) -> list[tuple[float, float]]:
    pts: list[tuple[float, float]] = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        x = u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0]
        y = u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1]
        pts.append((x, y))
    return pts


def ribbon(centerline: list[tuple[float, float]], width: float) -> kdb.DPolygon:
    """Offset a centerline ±width/2 to produce a closed ribbon polygon."""
    half = width / 2
    n = len(centerline)
    left: list[tuple[float, float]] = []
    right: list[tuple[float, float]] = []
    for i, (x, y) in enumerate(centerline):
        if i == 0:
            tx, ty = centerline[1][0] - x, centerline[1][1] - y
        elif i == n - 1:
            tx, ty = x - centerline[i - 1][0], y - centerline[i - 1][1]
        else:
            tx = centerline[i + 1][0] - centerline[i - 1][0]
            ty = centerline[i + 1][1] - centerline[i - 1][1]
        m = math.hypot(tx, ty) or 1
        nx, ny = -ty / m, tx / m
        left.append((x + nx * half, y + ny * half))
        right.append((x - nx * half, y - ny * half))
    pts = left + list(reversed(right))
    return kdb.DPolygon([kdb.DPoint(x, y) for x, y in pts])


def build_logo() -> tuple[kf.KCLayout, kf.KCell]:
    """Build the κ as a real KCell. Coordinates are in µm with y-up
    (klayout convention). The SVG exporter flips y for SVG y-down."""
    kcl = kf.KCLayout("KFACTORY_LOGO", infos=LogoLayers)
    layers = LogoLayers()
    c = kcl.kcell("kappa_logo")
    wg = kcl.find_layer(layers.WG)
    stub = kcl.find_layer(layers.STUB)

    W = 5  # waveguide width µm

    # Stem — vertical waveguide at x=14, y=[8, 56]
    c.shapes(wg).insert(kdb.DBox(14 - W / 2, 8, 14 + W / 2, 56))

    # Upper arm — clothoid-like sweep from stem mid (14,32) up to (50,52)
    upper = cubic_bezier((14, 32), (14, 40), (28, 50), (50, 52), n=48)
    c.shapes(wg).insert(ribbon(upper, W))

    # Lower arm — mirror across y=32, ending at (50,12)
    lower = cubic_bezier((14, 32), (14, 24), (28, 14), (50, 12), n=48)
    c.shapes(wg).insert(ribbon(lower, W))

    # Port stubs — small filled squares at all four open ends
    stub_size = 6
    for sx, sy in [(14, 59), (14, 5), (50, 55), (50, 9)]:
        half = stub_size / 2
        c.shapes(stub).insert(kdb.DBox(sx - half, sy - half, sx + half, sy + half))

    return kcl, c


def export_svg(
    kcl: kf.KCLayout,
    cell: kf.KCell,
    viewbox: tuple[int, int, int, int] = (0, 0, 64, 64),
) -> str:
    """Walk every shape per layer, emit one `<polygon>` per shape with the
    per-layer fill from LAYER_FILL. Flip y to match SVG's y-down axis."""
    _, _, _, vb_h = viewbox
    layers = LogoLayers()
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="{viewbox[0]} {viewbox[1]} {viewbox[2]} {viewbox[3]}" '
        f'role="img" aria-label="kfactory">',
        "  <title>kfactory</title>",
    ]
    for layer_name, fill in LAYER_FILL.items():
        layer_info = getattr(layers, layer_name)
        idx = kcl.find_layer(layer_info)
        for shape in cell.shapes(idx).each():
            poly = shape.dpolygon
            pts = " ".join(f"{p.x:g},{vb_h - p.y:g}" for p in poly.each_point_hull())
            parts.append(
                f'  <polygon points="{pts}" fill="{fill}" data-layer="{layer_name}"/>'
            )
    parts.append("</svg>")
    return "\n".join(parts)


def generate(out_dir: Path) -> tuple[Path, Path]:
    """Build the logo, write `<out_dir>/logo.{gds,svg}`, return both paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    out_gds = out_dir / "logo.gds"
    out_svg = out_dir / "logo.svg"
    kcl, c = build_logo()
    c.write(str(out_gds))
    out_svg.write_text(export_svg(kcl, c) + "\n")
    return out_gds, out_svg


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_OUT_DIR),
        help=f"Directory for logo.gds + logo.svg (default: {DEFAULT_OUT_DIR})",
    )
    args = parser.parse_args(argv)
    gds, svg = generate(Path(args.out_dir).resolve())
    print(f"Wrote {gds}")
    print(f"Wrote {svg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
