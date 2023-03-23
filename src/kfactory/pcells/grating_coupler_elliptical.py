from enum import IntEnum
from typing import Callable, Literal, Optional

import numpy as np

import kfactory as kf
from kfactory.generic_tech import LAYER


@kf.autocell
def grating_coupler_elliptical(
    polarization: Literal["te"] | Literal["tm"] = "te",
    taper_length: int = 16600,
    taper_angle: float = 40.0,
    trenches_extra_angle: float = 10.0,
    lambda_c: float = 1.554,
    fiber_angle: float = 15.0,
    grating_line_width: int = 343,
    wg_width: int = 500,
    neff: float = 2.638,  # tooth effective index
    layer_taper: Optional[IntEnum] = LAYER.WG,
    layer_trench: IntEnum = LAYER.UNDERCUT,
    p_start: int = 26,
    n_periods: int = 30,
    taper_offset: int = 0,
    taper_extent_n_periods: float | Literal["first"] | Literal["last"] = "last",
    period: Optional[int] = None,
    x_fiber_launch: Optional[int] = None,
) -> kf.KCell:
    
    DEG2RAD = np.pi / 180

    # Define some constants
    nc = 1.443  # cladding index
    # Compute some ellipse parameters
    sthc = np.sin(fiber_angle * DEG2RAD)

    if period is not None:
        neff = lambda_c / period + nc * sthc

    d = neff**2 - nc**2 * sthc**2
    a1 = lambda_c * neff / d
    b1 = lambda_c / np.sqrt(d)
    x1 = lambda_c * nc * sthc / d

    a1 = round(a1 * 1e3)
    b1 = round(b1 * 1e3)
    x1 = round(x1 * 1e3)

    _period = a1 + x1

    trench_line_width = _period - grating_line_width

    c = kf.KCell()
    c.settings["polarization"] = polarization
    c.settings["wavelength"] = lambda_c * 1e3

    # Make each grating line

    for p in range(p_start, p_start + n_periods + 2):
        tooth = grating_tooth(
            (p - 0.5) * a1,
            (p - 0.5) * b1,
            (p - 0.5) * x1,
            trench_line_width,
            taper_angle + trenches_extra_angle,
        )
        c.shapes(layer_trench).insert(tooth)
    tooth_region = kf.kdb.Region(c.shapes(layer_trench))

    # Make the taper
    if taper_extent_n_periods == "last":
        n_periods_over_grating: float = n_periods + 1
    elif taper_extent_n_periods == "first":
        n_periods_over_grating = -1.5
    else:
        n_periods_over_grating = taper_extent_n_periods

    def _get_taper_pts(
        n_periods_over_grating: float,
    ) -> tuple[list[kf.kdb.Point], float]:
        p_taper = p_start + n_periods_over_grating
        _taper_length = taper_length + (n_periods_over_grating - 1) * _period

        a_taper = a1 * p_taper
        b_taper = b1 * p_taper
        x_taper = x1 * p_taper

        x_output = a_taper + x_taper - _taper_length + grating_line_width / 2
        taper_pts = grating_taper_points(
            a_taper,
            b_taper,
            x_output,
            x_taper + _period,
            taper_angle,
            wg_width=wg_width,
        )
        return taper_pts, x_output

    taper_pts, x_output = _get_taper_pts(n_periods_over_grating=n_periods_over_grating)
    if layer_taper is not None:
        c.shapes(layer_taper).insert(
            kf.kdb.Polygon(taper_pts).transformed(kf.kdb.Trans(taper_offset, 0))
        )
        c.create_port(
            name="W0", trans=kf.kdb.Trans.R180, width=wg_width, layer=layer_taper
        )
    #     _taper = c.add_polygon(taper_pts, layer_taper)
    #     _taper.movex(taper_offset)

    #     add_tile_excl(c, taper_pts, layers=[LAYER.RXEXCLUD])

    c.transform(kf.kdb.Trans(int(-x_output - taper_offset), 0))

    # c.move((-x_output - taper_offset, 0))

    # Add port
    c.settings["period"] = _period
    # setattr(c.ports["W0"], "polarization", polarization)

    # Add GC Fibre launch reference port, we are putting it at the same place
    # as the other I/O port for now
    x0 = p_start * a1 - grating_line_width + 9

    x_fiber_launch = x0 if x_fiber_launch is None else x_fiber_launch
    c.create_port(
        name="FL",
        trans=kf.kdb.Trans(x_fiber_launch, 0),
        layer=LAYER.WG,
        width=100,
        port_type="fibre_launch",
    )
    # setattr(c.ports["FL"], "polarization", polarization)

    y0 = 0
    setattr(c, "p0_overclad", (x0, y0))

    return c


def grating_tooth(
    ap: float,
    bp: float,
    xp: int,
    width: int,
    taper_angle: float,
    spiked: bool = True,
    angle_step: float = 1.0,
) -> kf.kdb.Region:
    theta_min = -taper_angle / 2
    theta_max = taper_angle / 2

    backbone_points = ellipse_arc(ap, bp, xp, theta_min, theta_max, angle_step)
    if spiked:
        spike_length = width // 3
        path = kf.kdb.Path(backbone_points, width).polygon()
        edges = kf.kdb.Edges([path])
        bb_edges = kf.kdb.Edges(
            [
                kf.kdb.Edge(backbone_points[0], backbone_points[1]),
                kf.kdb.Edge(backbone_points[-1], backbone_points[-2]),
            ]
        )
        border_edges = edges.interacting(bb_edges)
        reg = kf.kdb.Region([path])
        for edge in border_edges.each():
            shifted = edge.shifted(spike_length)
            shifted_center = (shifted.p1 + shifted.p2.to_v()) / 2
            reg.insert(kf.kdb.Polygon([edge.p1, shifted_center, edge.p2]))
        reg.merge()

    else:
        reg = kf.kdb.Region(kf.kdb.Path(backbone_points, width))

    # points = extrude_path(
    #     backbone_points,
    #     width,
    #     with_manhattan_facing_angles=False,
    #     spike_length=spike_length,
    # )

    return reg


def grating_taper_points(
    a: float,
    b: float,
    x0: int,
    taper_length: int,
    taper_angle: float,
    wg_width: int,
    angle_step: float = 1.0,
) -> list[kf.kdb.Point]:
    taper_arc = ellipse_arc(a, b, taper_length, -taper_angle / 2, taper_angle / 2)

    p0 = kf.kdb.Point(x0, wg_width // 2)
    p1 = kf.kdb.Point(x0, -wg_width // 2)

    # port_position = np.array((x0, 0))
    # p0 = port_position + (0, wg_width / 2)
    # p1 = port_position + (0, -wg_width / 2)
    # points = np.vstack([p0, p1, taper_arc])
    return [p0, p1] + taper_arc


def ellipse_arc(
    a: float,
    b: float,
    x0: int,
    theta_min: float,
    theta_max: float,
    angle_step: float = 0.5,
) -> list[kf.kdb.Point]:
    theta = np.arange(theta_min, theta_max + angle_step, angle_step) * np.pi / 180
    xs = a * np.cos(theta) + x0
    ys = b * np.sin(theta)
    return [kf.kdb.Point(x, y) for x, y in zip(xs, ys)]  # np.column_stack([xs, ys])
