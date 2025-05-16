from pathlib import Path
from tempfile import NamedTemporaryFile

import kfactory as kf
from tests.conftest import Layers

pdk = kf.KCLayout("YAML", infos=Layers)

taper = kf.factories.taper.taper_factory(kcl=pdk)
bend = kf.factories.euler.bend_euler_factory(kcl=pdk)
straight = kf.factories.straight.straight_dbu_factory(kcl=pdk)

b90 = bend(width=0.5, radius=10, layer=Layers().WG)


@pdk.cell
def mmi_body() -> kf.KCell:
    c = pdk.kcell()

    c.shapes(pdk.layer(1, 0)).insert(kf.kdb.Box(10_000, 5000))

    c.create_port(
        name="o1",
        trans=kf.kdb.Trans(2, False, -5000, 0),
        layer=pdk.layer(1, 0),
        width=1000,
    )
    c.create_port(
        name="o2",
        trans=kf.kdb.Trans(5000, 1500),
        layer=pdk.layer(1, 0),
        width=1000,
    )
    c.create_port(
        name="o3",
        trans=kf.kdb.Trans(5000, -1500),
        layer=pdk.layer(1, 0),
        width=1000,
    )

    return c


@pdk.cell
def mmi() -> kf.KCell:
    c = pdk.kcell()

    body = c << mmi_body()
    t = [
        c << taper(width1=500, width2=1000, length=15000, layer=Layers().WG)
        for _ in range(3)
    ]
    t[0].connect("o2", body, "o1")
    t[1].connect("o2", body, "o2")
    t[2].connect("o2", body, "o3")

    c.add_ports([_t.ports["o1"] for _t in t])
    c.auto_rename_ports()

    return c


@pdk.cell
def mzi() -> kf.KCell:
    c = pdk.kcell()

    mmi1 = c << mmi()
    mmi2 = c << mmi()

    # top arm
    b_top = [c << b90 for _ in range(4)]
    b_top[0].connect("o1", mmi1, "o2")
    b_top[1].connect("o2", b_top[0], "o2")
    b_top[2].connect("o2", b_top[1], "o1")
    b_top[3].connect("o1", b_top[2], "o1")
    mmi2.connect("o3", b_top[3], "o2")
    # bot arm
    s = straight(width=500, length=10_000, layer=Layers().WG)
    s_bot = [c << s for _ in range(2)]
    b_bot = [c << b90 for _ in range(4)]
    b_bot[0].connect("o1", mmi1, "o3", mirror=True)
    s_bot[0].connect("o1", b_bot[0], "o2")
    b_bot[1].connect("o2", s_bot[0], "o2")
    b_bot[2].connect("o2", b_bot[1], "o1")
    s_bot[1].connect("o1", b_bot[2], "o1")
    b_bot[3].connect("o1", s_bot[1], "o2")

    return c


def test_yaml() -> None:
    mzi()
    with NamedTemporaryFile(suffix=".yml", delete=False) as _tf:
        tf = _tf.name
    kf.placer.cells_to_yaml(Path(tf), cells=list(pdk.kcells.values()))
    pdk2 = kf.KCLayout("YAML_READ")
    kf.placer.cells_from_yaml(Path(tf), kcl=pdk2)
    str(pdk2.kcells)
    Path(tf).unlink()
