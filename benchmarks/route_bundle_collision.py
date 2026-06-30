"""Benchmark route_bundle collision-check overhead.

Run with:

    uv run python benchmarks/route_bundle_collision.py

The benchmark compares the current fast path (`on_collision=None`) with the
collision-checking path (`on_collision="error"`). It intentionally avoids
pytest-benchmark so it can run in the normal dev environment without extra tools.
"""

from __future__ import annotations

import argparse
import gc
import itertools
import statistics
import sys
import time
from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING, Literal

import kfactory as kf

if TYPE_CHECKING:
    from collections.abc import Callable


class Layers(kf.LayerInfos):
    WG: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)
    WGCLAD: kf.kdb.LayerInfo = kf.kdb.LayerInfo(111, 0)


@dataclass(frozen=True)
class BenchCase:
    kcl: kf.KCLayout
    straight_factory: Callable[..., kf.KCell]
    bend90: kf.KCell
    ports: int


cell_counter = itertools.count()


def build_case(ports: int) -> BenchCase:
    kcl = kf.KCLayout(name="BENCH_ROUTE_BUNDLE_COLLISION", infos=Layers)
    layers = Layers()
    enclosure = kcl.get_enclosure(
        kf.LayerEnclosure(name="WGSTD", sections=[(layers.WGCLAD, 0, 2000)])
    )
    straight_factory = partial(
        kf.factories.straight.straight_dbu_factory(kcl=kcl),
        layer=layers.WG,
        enclosure=enclosure,
    )
    bend90 = kf.factories.euler.bend_euler_factory(kcl=kcl)(
        width=0.5,
        radius=10,
        layer=layers.WG,
        enclosure=enclosure,
        angle=90,
    )
    return BenchCase(
        kcl=kcl,
        straight_factory=straight_factory,
        bend90=bend90,
        ports=ports,
    )


def build_ports(ports: int) -> tuple[list[kf.Port], list[kf.Port]]:
    layers = Layers()
    optical_port = kf.Port(
        name="o1",
        width=500,
        trans=kf.kdb.Trans.R0,
        layer_info=layers.WG,
    )
    start_ports = [
        optical_port.copy(
            kf.kdb.Trans(
                1,
                False,
                i * 200_000 - 50_000,
                (4 - i) * 6_000 if i < 5 else (i - 5) * 6_000,
            )
        )
        for i in range(ports)
    ]
    end_ports = [
        optical_port.copy(
            kf.kdb.Trans(3, False, i * 200_000 + i**2 * 19_000 + 500_000, 300_000)
        )
        for i in range(ports)
    ]
    return start_ports, end_ports


def route_once(case: BenchCase, on_collision: Literal["error"] | None) -> int:
    c = case.kcl.kcell(f"BENCH_ROUTE_{next(cell_counter)}")
    start_ports, end_ports = build_ports(case.ports)
    routes = kf.routing.optical.route_bundle(
        c,
        start_ports,
        end_ports,
        5_000,
        straight_factory=case.straight_factory,
        bend90_cell=case.bend90,
        on_collision=on_collision,
    )
    return len(routes)


def time_pair(
    case: BenchCase,
    *,
    repeat: int,
    warmups: int,
) -> tuple[list[float], list[float]]:
    for _ in range(warmups):
        route_once(case, None)
        route_once(case, "error")

    gc.collect()
    gc.disable()
    no_check: list[float] = []
    check: list[float] = []
    try:
        for i in range(repeat):
            if i % 2:
                t0 = time.perf_counter()
                route_once(case, "error")
                check.append(time.perf_counter() - t0)

                t0 = time.perf_counter()
                route_once(case, None)
                no_check.append(time.perf_counter() - t0)
            else:
                t0 = time.perf_counter()
                route_once(case, None)
                no_check.append(time.perf_counter() - t0)

                t0 = time.perf_counter()
                route_once(case, "error")
                check.append(time.perf_counter() - t0)
    finally:
        gc.enable()
    return no_check, check


def format_stats(values: list[float]) -> str:
    return (
        f"min={min(values) * 1e3:.2f}ms "
        f"median={statistics.median(values) * 1e3:.2f}ms "
        f"mean={statistics.fmean(values) * 1e3:.2f}ms"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ports", type=int, default=20)
    parser.add_argument("--repeat", type=int, default=10)
    parser.add_argument("--warmups", type=int, default=2)
    args = parser.parse_args()

    case = build_case(args.ports)
    no_check, check = time_pair(
        case,
        repeat=args.repeat,
        warmups=args.warmups,
    )
    overhead = (statistics.fmean(check) / statistics.fmean(no_check) - 1) * 100

    sys.stdout.write(
        f"ports={args.ports} repeat={args.repeat} warmups={args.warmups}\n"
    )
    sys.stdout.write(f"on_collision=None:    {format_stats(no_check)}\n")
    sys.stdout.write(f"on_collision='error': {format_stats(check)}\n")
    sys.stdout.write(f"mean overhead: {overhead:.1f}%\n")


if __name__ == "__main__":
    main()
