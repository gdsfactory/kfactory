from collections.abc import Sequence
from typing import Any

from ruamel.yaml import YAML

import kfactory as kf
from tests.conftest import Layers


def test_schema() -> None:
    yaml = YAML(typ=["rt", "safe", "string"])
    schema_yaml = """
instances:
  bl:
    component: pad
  tl:
    component: pad
  br:
    component: pad
  tr:
    component: pad

placements:
  tl:
    x: -200
    y: 500

  br:
    x: 400
    y: 400

  tr:
    x: 400
    y: 600

routes:
  electrical:
    settings:
      separation: 20
      cross_section: metal_routing
      allow_width_mismatch: True
    links:
      tl,e3: tr,e1
      bl,e3: br,e1
"""
    schema = kf.DSchema.model_validate(yaml.load(schema_yaml))
    for inst in schema.instances.values():
        _ = inst.parent_schema.name


def test_schema_create() -> None:
    pdk = kf.KCLayout("SCHEMA_PDK", infos=Layers)
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

    schema = kf.Schema(kcl=pdk)

    s1 = schema.create_inst(name="s1", component="straight", settings={"length": 5000})
    s2 = schema.create_inst(name="s2", component="straight", settings={"length": 5000})
    s3 = schema.create_inst(
        name="s3", component="straight", settings={"length": 10_000}
    )

    s3.connect("o1", s1["o2"])
    s2.connect("o1", s3["o2"])

    s1.place(x=1000, y=10_000)

    schema.create_cell(kf.KCell)


def test_schema_create_cell() -> None:
    layers = Layers()
    pdk = kf.KCLayout("SCHEMA_PDK_DECORATOR", infos=Layers)

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
    def long_straight(n: int) -> kf.schema.TSchema[int]:
        schema = kf.Schema(kcl=pdk)

        s1 = schema.create_inst(
            name="s1", component="straight", settings={"length": 5000}
        )
        s2 = schema.create_inst(
            name="s2", component="straight", settings={"length": 5000}
        )
        s3 = schema.create_inst(name="s3", component="straight", settings={"length": n})

        s3.connect("o1", s1["o2"])
        s2.connect("o1", s3["o2"])

        s1.place(x=1000, y=10_000)

        return schema


def test_schema_route() -> None:
    layers = Layers()
    pdk = kf.KCLayout("SCHEMA_PDK_ROUTING", infos=Layers)

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
    def route_example() -> kf.schema.TSchema[int]:
        schema = kf.Schema(kcl=pdk)

        s1 = schema.create_inst(
            name="s1", component="straight", settings={"length": 5000, "width": 500}
        )
        s2 = schema.create_inst(
            name="s2", component="straight", settings={"length": 5000, "width": 500}
        )

        s1.place(x=1000, y=10_000)
        s2.place(x=1000, y=210_000)

        schema.add_route(
            "s1-s2", [s1["o2"]], [s2["o2"]], "route_bundle", separation=20_000
        )

        return schema


def test_netlist() -> None:
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
        "SCHEMA_PDK_NETLIST",
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

    schema = kf.Schema(kcl=pdk)

    s1 = schema.create_inst(
        name="s1", component="straight", settings={"length": 5000, "width": 500}
    )
    s2 = schema.create_inst(
        name="s2", component="straight", settings={"length": 5000, "width": 500}
    )

    padm1_1 = schema.create_inst(name="padm1_1", component="pad_m1")
    padm1_2 = schema.create_inst(name="padm1_2", component="pad_m1")
    padm2_1 = schema.create_inst(name="padm2_1", component="pad_m2")
    padm2_2 = schema.create_inst(name="padm2_2", component="pad_m2")

    s1.place(x=1000, y=10_000)
    s2.place(x=1000, y=-210_000)

    padm1_1.place(x=-500_000, y=0)
    padm1_2.place(x=500_000, y=0, orientation=180)
    padm2_1.place(x=0, y=100_000, orientation=270)
    padm2_2.place(x=0, y=-100_000, orientation=90)

    schema.add_route("s1-s2", [s1["o2"]], [s2["o2"]], "route_bundle", separation=20_000)
    schema.add_route(
        "pm1_1-pm1_2",
        [padm1_1["e1"]],
        [padm1_2["e1"]],
        "route_bundle_elec",
        separation=20_000,
    )
    schema.add_route(
        "pm2_1-pm2_2",
        [padm2_1["e1"]],
        [padm2_2["e1"]],
        "route_bundle_elec",
        separation=20_000,
    )
    schema.add_port("o1", port=s1["o1"])
    schema.add_port("o2", port=s2["o1"])

    c = schema.create_cell(kf.KCell)
    nl = schema.netlist()
    nl2 = c.netlist(
        ignore_unnamed=True,
        connectivity=[(layers.METAL1, layers.VIA1, layers.METAL2)],
    )
    assert nl == nl2[c.name]


def test_netlist_equivalent() -> None:
    layers = Layers()
    pdk = kf.KCLayout(
        "SCHEMA_PDK_NETLIST_EQUIVALENT",
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

    schema = kf.Schema(kcl=pdk)

    padm1_1 = schema.create_inst(name="padm1_1", component="pad_m1")
    padm1_2 = schema.create_inst(name="padm1_2", component="pad_m1")
    padm1_3 = schema.create_inst(name="padm1_3", component="pad_m1")
    padm1_4 = schema.create_inst(name="padm1_4", component="pad_m1")

    padm1_1.place(x=-400_000, y=0)
    padm1_2.place(x=400_000, y=0)
    padm1_3.place(x=-400_000, y=-400_000)
    padm1_4.place(
        x=400_000,
        y=-400_000,
    )

    schema.add_route(
        "pm1_1-pm1_2",
        [padm1_1["e3"]],
        [padm1_2["e1"]],
        "route_bundle_elec",
        separation=20_000,
    )
    schema.add_route(
        "pm1_2-pm1_4",
        [padm1_2["e4"]],
        [padm1_4["e2"]],
        "route_bundle_elec",
        separation=20_000,
    )
    schema.add_route(
        "pm1_3-pm1_4",
        [padm1_1["e4"]],
        [padm1_3["e2"]],
        "route_bundle_elec",
        separation=20_000,
    )
    schema.add_route(
        "pm1_4-pm1_1",
        [padm1_4["e1"]],
        [padm1_3["e3"]],
        "route_bundle_elec",
        separation=20_000,
    )

    nl = schema.netlist()
    c = schema.create_cell(kf.KCell)
    nl2 = c.netlist(
        ignore_unnamed=True, connectivity=[(layers.METAL1, layers.VIA1, layers.METAL2)]
    )
    assert (
        nl.lvs_equivalent(
            cell_name=c.name, equivalent_ports={"pad_m1": [["e1", "e2", "e3", "e4"]]}
        )
        == nl2[c.name]
    )
