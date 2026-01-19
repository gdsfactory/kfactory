from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

import kfactory as kf
from tests.conftest import Layers

# Find all YAML files
yaml_dir = Path(__file__).parent / "gdsfactory-yaml-pics" / "notebooks" / "yaml_pics"
yaml_files = sorted(yaml_dir.glob("**/*.pic.yml"))
skip_files = [
    "aar_bundles02",
    "aar_bundles01",
    "aar_bundles03",
    "mzi_lattice_filter",
    "mirror_demo",
]


def _get_path_stem(p: Path) -> str | None:
    # If it's a tuple, grab the first item
    if isinstance(p, tuple) and p:
        p = p[0]

    # Handle str/Path inputs
    if isinstance(p, str | Path):
        return Path(p).with_suffix("").stem

    # Let pytest fall back to default ID
    return None


def test_schematic() -> None:
    yaml = YAML(typ=["rt", "safe", "string"])
    schema_yaml = """
instances:
  mmi_long:
    component: mmi1x2
    settings:
      width_mmi: 4.5
      length_mmi: 10
  mmi_short:
    component: mmi1x2
    settings:
      width_mmi: 4.5
      length_mmi: 5

placements:
  mmi_short:
    rotation: 180
  mmi_long:
    rotation: 90
    x: mmi_short,o1
    y: mmi_short,o1
    dx: 20
    dy: 20

routes:
  optical:
    routing_strategy: route_bundle_all_angle
    settings:
      end_connector: wonky  # using our new, wonky connector for the final segment
      end_cross_section:  # and for that final segment, also tip the connector to use this cross-section
        cross_section: strip
        settings:
          width: 2.0
    links:
      mmi_short,o1: mmi_long,o1

ports:
  o1: mmi_short,o2
  o2: mmi_short,o3
"""  # noqa: E501
    schematic = kf.DSchematic.model_validate(yaml.load(schema_yaml))
    for inst in schematic.instances.values():
        _ = inst.parent_schematic.name

    schema_str = schematic.code_str()
    assert schema_str is not None


def test_schematic_create(
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None], kcl: kf.KCLayout
) -> None:
    pdk = kcl
    layers = Layers()

    @pdk.cell
    def straight(length: int) -> kf.KCell:
        c = pdk.kcell()
        c.shapes(layers.WG).insert(kf.kdb.Box(0, -250, length, 250))
        c.create_port(
            name="o1",
            width=500,
            trans=kf.kdb.Trans(rot=2, mirrx=False, x=0, y=0),
            layer_info=layers.WG,
        )
        c.create_port(
            name="o2",
            width=500,
            trans=kf.kdb.Trans(x=length, y=0),
            layer_info=layers.WG,
        )

        return c

    schematic = kf.Schematic(kcl=pdk)

    s1 = schematic.create_inst(
        name="s1", component="straight", settings={"length": 5000}
    )
    s2 = schematic.create_inst(
        name="s2", component="straight", settings={"length": 5000}
    )
    s3 = schematic.create_inst(
        name="s3", component="straight", settings={"length": 10_000}
    )

    s3.connect("o1", s1["o2"])
    s2.connect("o1", s3["o2"])

    s1.place(x=1000, y=10_000)

    c = schematic.create_cell(kf.KCell)
    c.name = "test_schematic_create"
    gds_regression(c)


def test_schematic_create_cell(
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None], kcl: kf.KCLayout
) -> None:
    layers = Layers()
    pdk = kcl

    @pdk.cell
    def straight(length: int) -> kf.KCell:
        c = pdk.kcell()
        c.shapes(layers.WG).insert(kf.kdb.Box(0, -250, length, 250))
        c.create_port(
            name="o1",
            width=500,
            trans=kf.kdb.Trans(rot=2, mirrx=False, x=0, y=0),
            layer_info=layers.WG,
        )
        c.create_port(
            name="o2",
            width=500,
            trans=kf.kdb.Trans(x=length, y=0),
            layer_info=layers.WG,
        )

        return c

    @pdk.schematic_cell(output_type=kf.DKCell)
    def long_straight(n: int) -> kf.schematic.TSchematic[int]:
        schematic = kf.Schematic(kcl=pdk)

        s1 = schematic.create_inst(
            name="s1", component="straight", settings={"length": 5000}
        )
        s2 = schematic.create_inst(
            name="s2", component="straight", settings={"length": 5000}
        )
        s3 = schematic.create_inst(
            name="s3", component="straight", settings={"length": n}
        )

        s3.connect("o1", s1["o2"])
        s2.connect("o1", s3["o2"])

        s1.place(x=1000, y=10_000)

        return schematic

    assert pdk.factories["long_straight"].schematic_driven()

    gds_regression(long_straight(2))


def test_schematic_mirror_connection(
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None], kcl: kf.KCLayout
) -> None:
    layers = Layers()
    pdk = kcl

    @pdk.cell
    def straight(length: int) -> kf.KCell:
        c = pdk.kcell()
        c.shapes(layers.WG).insert(kf.kdb.Box(0, -250, length, 250))
        c.create_port(
            name="o1",
            width=500,
            trans=kf.kdb.Trans(rot=2, mirrx=False, x=0, y=0),
            layer_info=layers.WG,
        )
        c.create_port(
            name="o2",
            width=500,
            trans=kf.kdb.Trans(x=length, y=0),
            layer_info=layers.WG,
        )

        return c

    @pdk.cell
    def bend_s_euler(
        offset: int,
        radius: int = 10_000,
        resolution: float = 150,
    ) -> kf.KCell:
        c = pdk.kcell()

        width = 500

        backbone = kf.factories.euler.euler_sbend_points(
            offset=pdk.to_um(offset),
            radius=pdk.to_um(radius),
            resolution=resolution,
        )
        center_path = kf.enclosure.extrude_path(
            target=c,
            layer=pdk.infos["WG"],
            path=backbone,
            width=pdk.to_um(width),
            start_angle=0,
            end_angle=0,
        )

        v = backbone[-1] - backbone[0]
        if v.x < 0:
            p1 = c.kcl.to_dbu(backbone[-1])
            p2 = c.kcl.to_dbu(backbone[0])
        else:
            p1 = c.kcl.to_dbu(backbone[0])
            p2 = c.kcl.to_dbu(backbone[-1])
        li = c.kcl.layer(pdk.infos["WG"])
        c.create_port(
            trans=kf.kdb.Trans(2, False, p1.to_v()),
            width=width,
            port_type="optical",
            layer=li,
        )
        c.create_port(
            trans=kf.kdb.Trans(0, False, p2.to_v()),
            width=width,
            port_type="optical",
            layer=li,
        )
        c.boundary = center_path

        c.auto_rename_ports()
        return c

    @pdk.schematic_cell()
    def straight_sbend(length: int, offset: int) -> kf.schematic.TSchematic[int]:
        schematic = kf.Schematic(kcl=pdk, name="Mirror Test")

        s1 = schematic.create_inst(
            name="s1", component="straight", settings={"length": length}
        )
        s2 = schematic.create_inst(
            name="s2", component="bend_s_euler", settings={"offset": offset}
        )
        s3 = schematic.create_inst(
            name="s3", component="straight", settings={"length": length}
        )
        s4 = schematic.create_inst(
            name="s4", component="bend_s_euler", settings={"offset": offset}
        )

        s2.connect("o1", s1["o2"])
        s2.mirror = True
        s4.connect("o1", s3["o2"])

        s1.place(x=0, y=0)
        s3.place(x=0, y=10_000)

        return schematic

    assert pdk.factories["straight_sbend"].schematic_driven()

    gds_regression(straight_sbend(length=10_000, offset=20_000))


def test_schematic_kcl_mix_netlist(
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None], layers: Layers
) -> None:
    layers = Layers()
    pdk = kf.KCLayout("schematic_pdk_decorator", infos=layers.__class__)
    pdk2 = kf.KCLayout("schematic_pdk_decorator_2", infos=layers.__class__)

    @pdk.cell
    def straight(length: int) -> kf.KCell:
        c = pdk.kcell()
        c.shapes(layers.WG).insert(kf.kdb.Box(0, -250, length, 250))
        c.create_port(
            name="o1",
            width=500,
            trans=kf.kdb.Trans(rot=2, mirrx=False, x=0, y=0),
            layer_info=layers.WG,
        )
        c.create_port(
            name="o2",
            width=500,
            trans=kf.kdb.Trans(x=length, y=0),
            layer_info=layers.WG,
        )

        return c

    @pdk2.schematic_cell
    def long_straight(n: int) -> kf.schematic.TSchematic[int]:
        schematic = kf.Schematic(kcl=pdk2)

        s1 = schematic.create_inst(
            name="s1",
            component="straight",
            settings={"length": 5000},
            kcl=pdk,
        )
        s2 = schematic.create_inst(
            name="s2",
            component="straight",
            settings={"length": 5000},
            kcl=pdk,
        )
        s3 = schematic.create_inst(
            name="s3", component="straight", settings={"length": n}, kcl=pdk
        )

        s3.connect("o1", s1["o2"])
        s2.connect("o1", s3["o2"])

        s1.place(x=1000, y=10_000)

        return schematic

    c = long_straight(n=2000)
    c.netlist()
    gds_regression(c)


def test_schematic_route(
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
) -> None:
    layers = Layers()
    pdk = kf.KCLayout("schematic_pdk_routing", infos=Layers)

    @pdk.cell
    def straight(width: int, length: int) -> kf.KCell:
        c = pdk.kcell()
        c.shapes(layers.WG).insert(kf.kdb.Box(0, -width // 2, length, width // 2))
        c.create_port(
            name="o1",
            width=width,
            trans=kf.kdb.Trans(rot=2, mirrx=False, x=0, y=0),
            layer_info=layers.WG,
        )
        c.create_port(
            name="o2",
            width=width,
            trans=kf.kdb.Trans(x=length, y=0),
            layer_info=layers.WG,
        )

        return c

    bend90_function = kf.factories.euler.bend_euler_factory(kcl=pdk)
    bend90 = bend90_function(width=0.500, radius=10, layer=layers.WG)

    @pdk.routing_strategy
    def route_bundle(
        c: kf.ProtoTKCell[Any],
        start_ports: Sequence[kf.ProtoPort[Any]],
        end_ports: Sequence[kf.ProtoPort[Any]],
        separation: int = 5000,
    ) -> list[kf.routing.generic.ManhattanRoute]:
        return kf.routing.optical.route_bundle(
            c=kf.KCell(base=c._base),
            start_ports=[kf.Port(base=sp.base) for sp in start_ports],
            end_ports=[kf.Port(base=ep.base) for ep in end_ports],
            separation=separation,
            straight_factory=straight,
            bend90_cell=bend90,
        )

    @pdk.schematic_cell(output_type=kf.KCell)
    def route_example() -> kf.schematic.TSchematic[int]:
        schematic = kf.Schematic(kcl=pdk)

        s1 = schematic.create_inst(
            name="s1", component="straight", settings={"length": 5000, "width": 500}
        )
        s2 = schematic.create_inst(
            name="s2", component="straight", settings={"length": 5000, "width": 500}
        )

        s1.place(x=1000, y=10_000)
        s2.place(x=1000, y=210_000)

        schematic.add_route(
            "s1-s2", [s1["o2"]], [s2["o2"]], "route_bundle", separation=20_000
        )

        return schematic

    assert pdk.factories["route_example"]._f_orig is route_example.__wrapped__  # type: ignore[attr-defined]

    gds_regression(route_example())


def test_netlist(
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
) -> None:
    class Layers(kf.LayerInfos):
        WG: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)
        WGCLAD: kf.kdb.LayerInfo = kf.kdb.LayerInfo(111, 0)
        WGEXCLUDE: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 1)
        WGCLADEXCLUDE: kf.kdb.LayerInfo = kf.kdb.LayerInfo(111, 1)
        FILL1: kf.kdb.LayerInfo = kf.kdb.LayerInfo(2, 0)
        FILL2: kf.kdb.LayerInfo = kf.kdb.LayerInfo(3, 0)
        FILL3: kf.kdb.LayerInfo = kf.kdb.LayerInfo(10, 0)
        METAL1: kf.kdb.LayerInfo = kf.kdb.LayerInfo(2, 0)
        METAL1EX: kf.kdb.LayerInfo = kf.kdb.LayerInfo(2, 1)
        VIA1: kf.kdb.LayerInfo = kf.kdb.LayerInfo(3, 0)
        METAL2: kf.kdb.LayerInfo = kf.kdb.LayerInfo(4, 0)
        METAL2EX: kf.kdb.LayerInfo = kf.kdb.LayerInfo(4, 1)

    layers = Layers()
    pdk = kf.KCLayout(
        "schematic_pdk_netlist",
        infos=Layers,
        connectivity=[(layers.METAL1, layers.VIA1, layers.METAL2)],
    )

    @pdk.cell
    def straight(width: int, length: int) -> kf.KCell:
        c = pdk.kcell()
        c.shapes(layers.WG).insert(kf.kdb.Box(0, -width // 2, length, width // 2))
        c.create_port(
            name="o1",
            width=width,
            trans=kf.kdb.Trans(rot=2, mirrx=False, x=0, y=0),
            layer_info=layers.WG,
        )
        c.create_port(
            name="o2",
            width=width,
            trans=kf.kdb.Trans(x=length, y=0),
            layer_info=layers.WG,
        )

        return c

    @pdk.cell
    def pad_m1() -> kf.KCell:
        c = pdk.kcell()
        c.shapes(layers.METAL1).insert(kf.kdb.Box(100_000))
        c.create_port(
            name="e1",
            trans=kf.kdb.Trans(50_000, 0),
            width=50_000,
            layer_info=layers.METAL1,
            port_type="electrical",
        )
        return c

    @pdk.cell
    def pad_m2() -> kf.KCell:
        c = pdk.kcell()
        c.shapes(layers.METAL2).insert(kf.kdb.Box(100_000))
        c.create_port(
            name="e1",
            trans=kf.kdb.Trans(50_000, 0),
            width=50_000,
            layer_info=layers.METAL2,
            port_type="electrical",
        )
        return c

    bend90_function = kf.factories.euler.bend_euler_factory(kcl=pdk)
    bend90 = bend90_function(width=0.500, radius=10, layer=layers.WG)

    @pdk.routing_strategy
    def route_bundle(
        c: kf.ProtoTKCell[Any],
        start_ports: Sequence[kf.ProtoPort[Any]],
        end_ports: Sequence[kf.ProtoPort[Any]],
        separation: int = 5000,
    ) -> list[kf.routing.generic.ManhattanRoute]:
        return kf.routing.optical.route_bundle(
            c=kf.KCell(base=c._base),
            start_ports=[kf.Port(base=sp.base) for sp in start_ports],
            end_ports=[kf.Port(base=ep.base) for ep in end_ports],
            separation=separation,
            straight_factory=straight,
            bend90_cell=bend90,
        )

    @pdk.routing_strategy
    def route_bundle_elec(
        c: kf.ProtoTKCell[Any],
        start_ports: Sequence[kf.ProtoPort[Any]],
        end_ports: Sequence[kf.ProtoPort[Any]],
        separation: int = 5000,
        start_straight: int = 0,
        end_straight: int = 0,
    ) -> list[kf.routing.generic.ManhattanRoute]:
        return kf.routing.electrical.route_bundle(
            c=kf.KCell(base=c._base),
            start_ports=[kf.Port(base=sp.base) for sp in start_ports],
            end_ports=[kf.Port(base=ep.base) for ep in end_ports],
            separation=separation,
            starts=start_straight,
            ends=end_straight,
        )

    schematic = kf.Schematic(kcl=pdk)

    s1 = schematic.create_inst(
        name="s1", component="straight", settings={"length": 5000, "width": 500}
    )
    s2 = schematic.create_inst(
        name="s2", component="straight", settings={"length": 5000, "width": 500}
    )

    padm1_1 = schematic.create_inst(name="padm1_1", component="pad_m1")
    padm1_2 = schematic.create_inst(name="padm1_2", component="pad_m1")
    padm2_1 = schematic.create_inst(name="padm2_1", component="pad_m2")
    padm2_2 = schematic.create_inst(name="padm2_2", component="pad_m2")

    s1.place(x=1000, y=10_000)
    s2.place(x=1000, y=-210_000)

    padm1_1.place(x=-500_000, y=0)
    padm1_2.place(x=500_000, y=0, orientation=180)
    padm2_1.place(x=0, y=100_000, orientation=270)
    padm2_2.place(x=0, y=-100_000, orientation=90)

    schematic.add_route(
        "s1-s2", [s1["o2"]], [s2["o2"]], "route_bundle", separation=20_000
    )
    schematic.add_route(
        "pm1_1-pm1_2",
        [padm1_1["e1"]],
        [padm1_2["e1"]],
        "route_bundle_elec",
        separation=20_000,
    )
    schematic.add_route(
        "pm2_1-pm2_2",
        [padm2_1["e1"]],
        [padm2_2["e1"]],
        "route_bundle_elec",
        separation=20_000,
    )
    schematic.add_port("o1", port=s1["o1"])
    schematic.add_port("o2", port=s2["o1"])

    c = schematic.create_cell(kf.KCell)
    c.name = "test_schematic_anchor"
    nl = schematic.netlist()
    nl2 = c.netlist(
        ignore_unnamed=True,
        connectivity=[(layers.METAL1, layers.VIA1, layers.METAL2)],
    )
    assert nl == nl2[c.name]
    gds_regression(c)


def test_netlist_equivalent(
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
) -> None:
    layers = Layers()
    pdk = kf.KCLayout(
        "schematic_pdk_netlist_equivalent",
        infos=Layers,
        connectivity=[(layers.METAL1, layers.VIA1, layers.METAL2)],
    )

    @pdk.cell
    def straight(width: int, length: int) -> kf.KCell:
        c = pdk.kcell()
        c.shapes(layers.WG).insert(kf.kdb.Box(0, -width // 2, length, width // 2))
        c.create_port(
            name="o1",
            width=width,
            trans=kf.kdb.Trans(rot=2, mirrx=False, x=0, y=0),
            layer_info=layers.WG,
        )
        c.create_port(
            name="o2",
            width=width,
            trans=kf.kdb.Trans(x=length, y=0),
            layer_info=layers.WG,
        )

        return c

    @pdk.cell(lvs_equivalent_ports=[["e1", "e2", "e3", "e4"]])
    def pad_m1() -> kf.KCell:
        c = pdk.kcell()
        c.shapes(layers.METAL1).insert(kf.kdb.Box(100_000))
        c.create_port(
            name="e1",
            trans=kf.kdb.Trans(2, False, -50_000, 0),
            width=50_000,
            layer_info=layers.METAL1,
            port_type="electrical",
        )
        c.create_port(
            name="e2",
            trans=kf.kdb.Trans(1, False, 0, 50_000),
            width=50_000,
            layer_info=layers.METAL1,
            port_type="electrical",
        )
        c.create_port(
            name="e3",
            trans=kf.kdb.Trans(50_000, 0),
            width=50_000,
            layer_info=layers.METAL1,
            port_type="electrical",
        )
        c.create_port(
            name="e4",
            trans=kf.kdb.Trans(3, False, 0, -50_000),
            width=50_000,
            layer_info=layers.METAL1,
            port_type="electrical",
        )
        return c

    bend90_function = kf.factories.euler.bend_euler_factory(kcl=pdk)
    bend90 = bend90_function(width=0.500, radius=10, layer=layers.WG)

    @pdk.routing_strategy
    def route_bundle(
        c: kf.ProtoTKCell[Any],
        start_ports: Sequence[kf.ProtoPort[Any]],
        end_ports: Sequence[kf.ProtoPort[Any]],
        separation: int = 5000,
    ) -> list[kf.routing.generic.ManhattanRoute]:
        return kf.routing.optical.route_bundle(
            c=kf.KCell(base=c._base),
            start_ports=[kf.Port(base=sp.base) for sp in start_ports],
            end_ports=[kf.Port(base=ep.base) for ep in end_ports],
            separation=separation,
            straight_factory=straight,
            bend90_cell=bend90,
        )

    @pdk.routing_strategy
    def route_bundle_elec(
        c: kf.ProtoTKCell[Any],
        start_ports: Sequence[kf.ProtoPort[Any]],
        end_ports: Sequence[kf.ProtoPort[Any]],
        separation: int = 5000,
        start_straight: int = 0,
        end_straight: int = 0,
    ) -> list[kf.routing.generic.ManhattanRoute]:
        return kf.routing.electrical.route_bundle(
            c=kf.KCell(base=c._base),
            start_ports=[kf.Port(base=sp.base) for sp in start_ports],
            end_ports=[kf.Port(base=ep.base) for ep in end_ports],
            separation=separation,
            starts=start_straight,
            ends=end_straight,
        )

    schematic = kf.Schematic(kcl=pdk)
    schematic.name = "test_schematic"

    padm1_1 = schematic.create_inst(name="padm1_1", component="pad_m1")
    padm1_2 = schematic.create_inst(name="padm1_2", component="pad_m1")
    padm1_3 = schematic.create_inst(name="padm1_3", component="pad_m1")
    padm1_4 = schematic.create_inst(name="padm1_4", component="pad_m1")

    padm1_1.place(x=-400_000, y=0)
    padm1_2.place(x=400_000, y=0)
    padm1_3.place(x=-400_000, y=-400_000)
    padm1_4.place(
        x=400_000,
        y=-400_000,
    )

    schematic.add_route(
        "pm1_1-pm1_2",
        [padm1_1["e3"]],
        [padm1_2["e1"]],
        "route_bundle_elec",
        separation=20_000,
    )
    schematic.add_route(
        "pm1_2-pm1_4",
        [padm1_2["e4"]],
        [padm1_4["e2"]],
        "route_bundle_elec",
        separation=20_000,
    )
    schematic.add_route(
        "pm1_3-pm1_4",
        [padm1_1["e4"]],
        [padm1_3["e2"]],
        "route_bundle_elec",
        separation=20_000,
    )
    schematic.add_route(
        "pm1_4-pm1_1",
        [padm1_4["e1"]],
        [padm1_3["e3"]],
        "route_bundle_elec",
        separation=20_000,
    )

    nl = schematic.netlist()
    c = schematic.create_cell(kf.KCell)
    nl2 = c.netlist(
        ignore_unnamed=True, connectivity=[(layers.METAL1, layers.VIA1, layers.METAL2)]
    )
    assert (
        nl.lvs_equivalent(
            cell_name=c.name, equivalent_ports={"pad_m1": [["e1", "e2", "e3", "e4"]]}
        )
        == nl2[c.name]
    )

    schema_str = schematic.code_str()

    assert schema_str is not None
    c.name = "test_schematic_anchor"
    gds_regression(c)


def test_schematic_anchor(
    gds_regression: Callable[[kf.ProtoTKCell[Any]], None],
) -> None:
    pdk = kf.KCLayout("schematic_pdk_anchor_port", infos=Layers)
    layers = Layers()

    @pdk.cell
    def straight(length: int) -> kf.KCell:
        c = pdk.kcell()
        c.shapes(layers.WG).insert(kf.kdb.Box(0, -250, length, 250))
        c.create_port(
            name="o1",
            width=500,
            trans=kf.kdb.Trans(rot=2, mirrx=False, x=0, y=0),
            layer_info=layers.WG,
        )
        c.create_port(
            name="o2",
            width=500,
            trans=kf.kdb.Trans(x=length, y=0),
            layer_info=layers.WG,
        )

        return c

    schematic = kf.Schematic(kcl=pdk)

    s1 = schematic.create_inst(
        name="s1", component="straight", settings={"length": 5000}
    )
    s2 = schematic.create_inst(
        name="s2", component="straight", settings={"length": 5000}
    )
    s3 = schematic.create_inst(
        name="s3", component="straight", settings={"length": 10_000}
    )

    s1.place()
    s2.place(x=1000, y=10_000, anchor={"x": "left", "y": "top"})
    s3.place(
        x=s1.ports["o2"],
        y=s1.ports["o2"],
        orientation=90,
        dx=10_000,
        anchor={"port": "o1"},
    )

    c = schematic.create_cell(kf.KCell)
    c.name = "test_schematic_anchor"
    gds_regression(c)


def test_schematic_function_get_port_positions(
    kcl: kf.KCLayout, layers: Layers
) -> None:
    xs = kcl.get_icross_section(
        kf.SymmetricalCrossSection(
            width=500,
            enclosure=kcl.get_enclosure(
                kf.LayerEnclosure(
                    [(layers.WGEX, 3000)], name="WGENC", main_layer=layers.WG
                )
            ),
            name="WG500",
            radius=20_000,
        )
    )

    @kcl.cell
    def bend_euler(
        cross_section: str,
        angle: kf.typings.deg = 90,
        resolution: float = 150,
    ) -> kf.KCell:
        """Create a euler bend.

        Args:
            width: Width of the core. [um]
            radius: Radius off the backbone. [um]
            layer: Layer index / LayerEnum of the core.
            enclosure: Slab/exclude definition. [dbu]
            angle: Angle of the bend.
            resolution: Angle resolution for the backbone.
        """
        c = kcl.kcell()

        xs = c.kcl.get_icross_section(cross_section)
        width = c.kcl.to_um(xs.width)
        radius = c.kcl.to_um(xs.radius)
        assert radius is not None, "Radius of cross section must not be None"
        layer = xs.layer
        enclosure = xs.enclosure
        if angle < 0:
            kf.logger.critical(
                f"Negative lengths are not allowed {angle} as ports"
                " will be inverted. Please use a positive number. Forcing positive"
                " lengths."
            )
            angle = -angle
        if width < 0:
            kf.logger.critical(
                f"Negative widths are not allowed {width} as ports"
                " will be inverted. Please use a positive number. Forcing positive"
                " lengths."
            )
            width = -width
        backbone = kf.factories.euler.euler_bend_points(
            angle, radius=radius, resolution=resolution
        )

        center_path = kf.enclosure.extrude_path(
            target=c,
            layer=layer,
            path=backbone,
            width=width,
            enclosure=enclosure,
            start_angle=0,
            end_angle=angle,
        )
        li = c.kcl.layer(layer)
        c.create_port(
            layer=li,
            width=c.kcl.to_dbu(width),
            trans=kf.kdb.Trans(2, False, c.kcl.to_dbu(backbone[0]).to_v()),
        )

        if abs(angle % 90) < 0.001:
            _ang = round(angle)
            c.create_port(
                trans=kf.kdb.Trans(
                    _ang // 90, False, c.kcl.to_dbu(backbone[-1]).to_v()
                ),
                width=round(width / c.kcl.dbu),
                layer=li,
            )
        else:
            c.create_port(
                dcplx_trans=kf.kdb.DCplxTrans(1, angle, False, backbone[-1].to_v()),
                width=c.kcl.to_dbu(width),
                layer=li,
            )
        c.boundary = center_path

        c.auto_rename_ports()
        return c

    @kcl.cell
    def bend_s_euler(
        offset: kf.typings.um,
        cross_section: str,
        resolution: float = 150,
    ) -> kf.KCell:
        """Create a euler s-bend.

        Args:
            offset: Offset between left/right. [um]
            width: Width of the core. [um]
            radius: Radius off the backbone. [um]
            layer: Layer index / LayerEnum of the core.
            enclosure: Slab/exclude definition. [dbu]
            resolution: Angle resolution for the backbone.
        """
        c = kcl.kcell()
        xs = c.kcl.get_icross_section(cross_section)

        width = c.kcl.to_um(xs.width)
        radius = c.kcl.to_um(xs.radius)
        if radius is None:
            raise ValueError(
                f"Radius of cross section must be defined cross_section={xs}"
            )

        backbone = kf.factories.euler.euler_sbend_points(
            offset=offset,
            radius=radius,
            resolution=resolution,
        )
        center_path = kf.enclosure.extrude_path(
            target=c,
            layer=xs.layer,
            path=backbone,
            width=width,
            enclosure=xs.enclosure,
            start_angle=0,
            end_angle=0,
        )

        v = backbone[-1] - backbone[0]
        if v.x < 0:
            p1 = c.kcl.to_dbu(backbone[-1])
            p2 = c.kcl.to_dbu(backbone[0])
        else:
            p1 = c.kcl.to_dbu(backbone[0])
            p2 = c.kcl.to_dbu(backbone[-1])
        li = c.kcl.layer(xs.layer)
        c.create_port(
            trans=kf.kdb.Trans(2, False, p1.to_v()),
            width=c.kcl.to_dbu(width),
            port_type="optical",
            layer=li,
        )
        c.create_port(
            trans=kf.kdb.Trans(0, False, p2.to_v()),
            width=c.kcl.to_dbu(width),
            port_type="optical",
            layer=li,
        )
        c.boundary = center_path
        c.auto_rename_ports()
        return c

    @kcl.cell
    def straight(length: kf.typings.um, cross_section: str) -> kf.KCell:
        """Waveguide defined in dbu.

            ┌──────────────────────────────┐
            │         Slab/Exclude         │
            ├──────────────────────────────┤
            │                              │
            │             Core             │
            │                              │
            ├──────────────────────────────┤
            │         Slab/Exclude         │
            └──────────────────────────────┘
        Args:
            width: Waveguide width. [dbu]
            length: Waveguide length. [dbu]
            layer: Main layer of the waveguide.
            enclosure: Definition of slab/excludes. [dbu]
        """
        c = kcl.kcell()
        xs = c.kcl.get_icross_section(cross_section)

        length_ = c.kcl.to_dbu(length)

        if length_ < 0:
            kf.logger.critical(
                f"Negative lengths are not allowed {length_} as ports"
                " will be inverted. Please use a positive number. Forcing positive"
                " lengths."
            )
            length_ = -length_

        li = c.kcl.layer(xs.layer)
        c.shapes(li).insert(kf.kdb.Box(0, -xs.width // 2, length_, xs.width // 2))
        c.create_port(trans=kf.kdb.Trans(2, False, 0, 0), layer=li, width=xs.width)
        c.create_port(
            trans=kf.kdb.Trans(0, False, length_, 0), layer=li, width=xs.width
        )

        xs.enclosure.apply_minkowski_y(c, xs.layer)

        c.boundary = c.dbbox()  # type: ignore[assignment]
        c.auto_rename_ports()
        return c

    @kcl.schematic_cell
    def dc(gap: int, length: int) -> kf.Schematic:
        length_ = kcl.to_um(length)
        s = kf.Schematic(kcl=kcl)

        s1 = s.create_inst(
            "s1",
            "straight",
            settings={"cross_section": xs.name, "length": length_},
        )

        s2 = s.create_inst(
            "s2", "straight", settings={"cross_section": xs.name, "length": length_}
        )

        s1.place(orientation=90)
        s2.place(x=-(gap + xs.width), orientation=90)

        b1 = s.create_inst(
            "b1",
            "bend_s_euler",
            settings={
                "offset": 10,
                "cross_section": xs.name,
            },
        )
        b2 = s.create_inst(
            "b2",
            "bend_s_euler",
            settings={
                "offset": 10,
                "cross_section": xs.name,
            },
        )
        b3 = s.create_inst(
            "b3",
            "bend_s_euler",
            settings={
                "offset": 10,
                "cross_section": xs.name,
            },
        )
        b4 = s.create_inst(
            "b4",
            "bend_s_euler",
            settings={
                "offset": 10,
                "cross_section": xs.name,
            },
        )

        b1.connect("o1", s1.ports["o1"])
        b2.connect("o1", s1.ports["o2"])
        b3.connect("o1", s2.ports["o1"])
        b4.connect("o1", s2.ports["o2"])

        b2.mirror = True
        b3.mirror = True

        s.add_port("o1", port=b1.ports["o2"])
        s.add_port("o4", port=b2.ports["o2"])
        s.add_port("o2", port=b3.ports["o2"])
        s.add_port("o3", port=b4.ports["o2"])

        return s

    @kcl.schematic_cell
    def tree(n: int) -> kf.Schematic:
        s = kf.Schematic(kcl=kcl)

        dc1 = s.create_inst(
            "dc1", component="dc", settings={"gap": 240, "length": 10_000}
        )
        dc2 = s.create_inst(
            "dc2", component="dc", settings={"gap": 240, "length": 10_000}
        )
        dc3 = s.create_inst(
            "dc3", component="dc", settings={"gap": 240, "length": 10_000}
        )

        dc1.place()
        dc3.connect("o2", dc1.ports["o4"])
        dc2.mirror = True
        dc2.connect("o4", dc3.ports["o1"])

        b1 = s.create_inst(
            "b1", component="bend_euler", settings={"cross_section": xs.name}
        )
        b2 = s.create_inst(
            "b2", component="bend_euler", settings={"cross_section": xs.name}
        )
        b3 = s.create_inst(
            "b3", component="bend_euler", settings={"cross_section": xs.name}
        )
        b4 = s.create_inst(
            "b4", component="bend_euler", settings={"cross_section": xs.name}
        )

        b1.mirror = True
        b4.mirror = True
        b1.connect("o1", dc1.ports["o2"])
        b2.connect("o1", dc1.ports["o3"])
        b3.connect("o1", dc2.ports["o2"])
        b4.connect("o1", dc2.ports["o3"])
        s.add_port("o1", port=b1.ports["o2"])
        s.add_port("o2", port=b2.ports["o2"])
        s.add_port(f"o{4 * n + 1}", port=b3.ports["o2"])
        s.add_port(f"o{4 * n + 2}", port=b4.ports["o2"])
        s.add_port(f"o{4 * n + 3}", port=dc2.ports["o1"])
        s.add_port(f"o{4 * n + 4}", port=dc1.ports["o1"])

        for i in range(1, n):
            dc_i1 = s.create_inst(
                f"dc{i * 3 + 1}",
                component="dc",
                settings={"gap": 240, "length": 10_000},
            )
            dc_i2 = s.create_inst(
                f"dc{i * 3 + 2}",
                component="dc",
                settings={"gap": 240, "length": 10_000},
            )
            dc_i3 = s.create_inst(
                f"dc{i * 3 + 3}",
                component="dc",
                settings={"gap": 240, "length": 10_000},
            )

            dc_i2.mirror = True
            dc_i1.connect("o1", dc3.ports["o3"])
            dc_i2.connect("o1", dc3.ports["o4"])
            dc_i3.connect("o1", dc_i2.ports["o4"])
            dc_i3.connect("o2", dc_i1.ports["o4"])

            b_i1 = s.create_inst(
                f"b{i * 4 + 1}",
                component="bend_euler",
                settings={"cross_section": xs.name},
            )
            b_i2 = s.create_inst(
                f"b{i * 4 + 2}",
                component="bend_euler",
                settings={"cross_section": xs.name},
            )
            b_i3 = s.create_inst(
                f"b{i * 4 + 3}",
                component="bend_euler",
                settings={"cross_section": xs.name},
            )
            b_i4 = s.create_inst(
                f"b{i * 4 + 4}",
                component="bend_euler",
                settings={"cross_section": xs.name},
            )

            b_i1.mirror = True
            b_i4.mirror = True
            b_i1.connect("o1", dc_i1.ports["o2"])
            b_i2.connect("o1", dc_i1.ports["o3"])
            b_i3.connect("o1", dc_i2.ports["o2"])
            b_i4.connect("o1", dc_i2.ports["o3"])
            s.add_port(f"o{2 * i + 1}", port=b_i1.ports["o2"])
            s.add_port(f"o{2 * i + 2}", port=b_i2.ports["o2"])
            s.add_port(f"o{4 * n - 2 * i + 1}", port=b_i4.ports["o2"])
            s.add_port(f"o{4 * n - 2 * i + 2}", port=b_i3.ports["o2"])

            dc1 = dc_i1
            dc2 = dc_i2
            dc3 = dc_i3

        s.add_port(f"o{2 * n + 1}", port=dc3.ports["o3"])
        s.add_port(f"o{2 * n + 2}", port=dc3.ports["o4"])

        return s

    factories: dict[
        str,
        kf.decorators.WrappedKCellFunc[Any, kf.ProtoTKCell[Any]]
        | kf.decorators.WrappedVKCellFunc[Any, kf.VKCell],
    ] = {}
    factories.update(kcl.virtual_factories.as_dict())
    factories.update(kcl.factories.as_dict())
    assert kcl.factories["dc"].get_schematic(gap=240, length=10_000).get_port_positions(
        factories
    ) == {"right": [], "top": ["o3", "o4"], "left": [], "bottom": ["o1", "o2"]}
    assert kcl.factories["tree"].get_schematic(n=3).get_port_positions(factories) == {
        "right": ["o10", "o11", "o12", "o13", "o14", "o9"],
        "top": ["o7", "o8"],
        "left": ["o1", "o2", "o3", "o4", "o5", "o6"],
        "bottom": ["o15", "o16"],
    }


@pytest.mark.parametrize(
    "path",
    [
        pytest.param(
            file, marks=pytest.mark.skip(reason="Incompatible gdsfactory schematic")
        )
        if file.with_suffix("").stem in skip_files
        else pytest.param(file)
        for file in yaml_files
    ],
    ids=_get_path_stem,
)
def test_gdsfactory_yaml(path: Path) -> None:
    with path.open(encoding="utf-8") as f:
        fstr = f.read()
        pytest.mark.skipif("%" in fstr)
    schematic = kf.read_schematic(path)
    for inst in schematic.instances.values():
        _ = inst.parent_schematic.name
