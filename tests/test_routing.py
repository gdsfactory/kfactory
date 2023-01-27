import kfactory as kf
import pytest
import warnings


def test_connect_straight(bend90, waveguide_factory, LAYER):
    c = kf.KCell()
    c.create_port(
        name="o1",
        trans=kf.kdb.Trans.R0,
        layer=LAYER.WG,
        width=1000,
        port_type="optical",
    )
    c.create_port(
        name="o2",
        trans=kf.kdb.Trans(2, False, 10000, 0),
        layer=LAYER.WG,
        width=1000,
        port_type="optical",
    )
    kf.routing.optical.connect(
        c,
        c.ports["o1"],
        c.ports["o2"],
        straight_factory=waveguide_factory,
        bend90_cell=bend90,
    )
