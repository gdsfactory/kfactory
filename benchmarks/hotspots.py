"""Small hotspot probes for local performance triage.

Run with:

    uv run python benchmarks/hotspots.py
"""

from __future__ import annotations

import argparse
import gc
import statistics
import sys
import time
from typing import TYPE_CHECKING

import kfactory as kf

if TYPE_CHECKING:
    from collections.abc import Callable


class Layers(kf.LayerInfos):
    WG: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)
    WGCLAD: kf.kdb.LayerInfo = kf.kdb.LayerInfo(111, 0)


def timed(
    name: str,
    func: Callable[[], int],
    repeat: int,
) -> tuple[str, list[float], int]:
    gc.collect()
    gc.disable()
    values: list[float] = []
    result = 0
    try:
        for _ in range(repeat):
            t0 = time.perf_counter()
            result = func()
            values.append(time.perf_counter() - t0)
    finally:
        gc.enable()
    return name, values, result


def port_lookup(port_count: int, loops: int) -> int:
    kcl = kf.KCLayout(name="BENCH_PORT_LOOKUP", infos=Layers)
    c = kcl.kcell("PORT_LOOKUP")
    layer = Layers().WG
    for i in range(port_count):
        c.create_port(
            name=f"o{i}",
            width=500,
            layer_info=layer,
            trans=kf.kdb.Trans(i % 4, False, i * 1000, 0),
        )

    total = 0
    for _ in range(loops):
        for i in range(port_count):
            total += c.ports[f"o{i}"].x
    return total


def port_lookup_via_mapping(port_count: int, loops: int) -> int:
    kcl = kf.KCLayout(name="BENCH_PORT_MAPPING", infos=Layers)
    c = kcl.kcell("PORT_MAPPING")
    layer = Layers().WG
    for i in range(port_count):
        c.create_port(
            name=f"o{i}",
            width=500,
            layer_info=layer,
            trans=kf.kdb.Trans(i % 4, False, i * 1000, 0),
        )

    ports_by_name = c.ports.get_all_named()
    total = 0
    for _ in range(loops):
        for i in range(port_count):
            total += ports_by_name[f"o{i}"].x
    return total


def port_filter(port_count: int, loops: int) -> int:
    kcl = kf.KCLayout(name="BENCH_PORT_FILTER", infos=Layers)
    c = kcl.kcell("PORT_FILTER")
    layer = Layers().WG
    for i in range(port_count):
        c.create_port(
            name=f"o{i}",
            width=500,
            layer_info=layer,
            trans=kf.kdb.Trans(i % 4, False, i * 1000, 0),
            port_type="optical" if i % 2 else "electrical",
        )

    total = 0
    for _ in range(loops):
        total += len(c.ports.filter(angle=1, port_type="optical"))
    return total


def extrude_static(point_count: int, loops: int) -> int:
    kcl = kf.KCLayout(name="BENCH_EXTRUDE_STATIC", infos=Layers)
    c = kcl.kcell("EXTRUDE_STATIC")
    layers = Layers()
    enclosure = kf.LayerEnclosure(sections=[(layers.WGCLAD, 0, 2000)])
    path = [kf.kdb.DPoint(i, 0 if i % 2 == 0 else 10) for i in range(point_count)]
    for _ in range(loops):
        kf.enclosure.extrude_path(
            c,
            layers.WG,
            path,
            width=0.5,
            enclosure=enclosure,
        )
    return c.shapes(kcl.layer(layers.WG)).size()


def extrude_dynamic(point_count: int, loops: int) -> int:
    kcl = kf.KCLayout(name="BENCH_EXTRUDE_DYNAMIC", infos=Layers)
    c = kcl.kcell("EXTRUDE_DYNAMIC")
    layers = Layers()
    enclosure = kf.LayerEnclosure(sections=[(layers.WGCLAD, 0, 2000)])
    path = [kf.kdb.DPoint(i, 0 if i % 2 == 0 else 10) for i in range(point_count)]
    widths = [0.5 + 0.001 * (i % 10) for i in range(point_count)]
    for _ in range(loops):
        kf.enclosure.extrude_path_dynamic(
            c,
            layers.WG,
            path,
            widths=widths,
            enclosure=enclosure,
        )
    return c.shapes(kcl.layer(layers.WG)).size()


def cell_cache(loops: int) -> int:
    kcl = kf.KCLayout(name="BENCH_CELL_CACHE", infos=Layers)
    layers = Layers()
    enclosure = kcl.get_enclosure(
        kf.LayerEnclosure(name="WGSTD", sections=[(layers.WGCLAD, 0, 2000)])
    )
    straight = kf.factories.straight.straight_dbu_factory(kcl=kcl)
    total = 0
    for i in range(loops):
        total += straight(
            width=500,
            length=10_000 + (i % 8),
            layer=layers.WG,
            enclosure=enclosure,
        ).cell_index()
    return total


def stats(values: list[float]) -> str:
    return (
        f"min={min(values) * 1e3:.2f}ms "
        f"median={statistics.median(values) * 1e3:.2f}ms "
        f"mean={statistics.fmean(values) * 1e3:.2f}ms"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument("--ports", type=int, default=1000)
    parser.add_argument("--port-loops", type=int, default=10)
    parser.add_argument("--points", type=int, default=500)
    parser.add_argument("--extrude-loops", type=int, default=10)
    parser.add_argument("--cell-loops", type=int, default=1000)
    args = parser.parse_args()

    cases = [
        (
            "ports[name]",
            lambda: port_lookup(args.ports, args.port_loops),
        ),
        (
            "ports.get_all_named()[name]",
            lambda: port_lookup_via_mapping(args.ports, args.port_loops),
        ),
        (
            "ports.filter(angle,type)",
            lambda: port_filter(args.ports, args.port_loops),
        ),
        (
            "extrude_path",
            lambda: extrude_static(args.points, args.extrude_loops),
        ),
        (
            "extrude_path_dynamic",
            lambda: extrude_dynamic(args.points, args.extrude_loops),
        ),
        (
            "cell_factory_cache",
            lambda: cell_cache(args.cell_loops),
        ),
    ]

    for name, func in cases:
        case_name, values, result = timed(name, func, args.repeat)
        sys.stdout.write(f"{case_name:28} {stats(values)} result={result}\n")


if __name__ == "__main__":
    main()
