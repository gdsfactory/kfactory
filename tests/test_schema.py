from collections.abc import Sequence
from typing import Any

from ruamel.yaml import YAML

import kfactory as kf


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
    class Layers(kf.LayerInfos):
        WG: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)
        WGCLAD: kf.kdb.LayerInfo = kf.kdb.LayerInfo(111, 0)
        WGEXCLUDE: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 1)
        WGCLADEXCLUDE: kf.kdb.LayerInfo = kf.kdb.LayerInfo(111, 1)
        FILL1: kf.kdb.LayerInfo = kf.kdb.LayerInfo(2, 0)
        FILL2: kf.kdb.LayerInfo = kf.kdb.LayerInfo(3, 0)
        FILL3: kf.kdb.LayerInfo = kf.kdb.LayerInfo(10, 0)

    layers = Layers()
    pdk = kf.KCLayout("SCHEMA_PDK", infos=Layers)

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
    class Layers(kf.LayerInfos):
        WG: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)
        WGCLAD: kf.kdb.LayerInfo = kf.kdb.LayerInfo(111, 0)
        WGEXCLUDE: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 1)
        WGCLADEXCLUDE: kf.kdb.LayerInfo = kf.kdb.LayerInfo(111, 1)
        FILL1: kf.kdb.LayerInfo = kf.kdb.LayerInfo(2, 0)
        FILL2: kf.kdb.LayerInfo = kf.kdb.LayerInfo(3, 0)
        FILL3: kf.kdb.LayerInfo = kf.kdb.LayerInfo(10, 0)

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

    long_straight(50_000).show()


def test_schema_route() -> None:
    class Layers(kf.LayerInfos):
        WG: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)
        WGCLAD: kf.kdb.LayerInfo = kf.kdb.LayerInfo(111, 0)
        WGEXCLUDE: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 1)
        WGCLADEXCLUDE: kf.kdb.LayerInfo = kf.kdb.LayerInfo(111, 1)
        FILL1: kf.kdb.LayerInfo = kf.kdb.LayerInfo(2, 0)
        FILL2: kf.kdb.LayerInfo = kf.kdb.LayerInfo(3, 0)
        FILL3: kf.kdb.LayerInfo = kf.kdb.LayerInfo(10, 0)

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

        schema.add_route("s1-s2", [s1["o2"]], [s2["o2"]], separation=20_000)

        return schema

    route_example().show()


def test_netlist() -> None:
    class Layers(kf.LayerInfos):
        WG: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)
        WGCLAD: kf.kdb.LayerInfo = kf.kdb.LayerInfo(111, 0)
        WGEXCLUDE: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 1)
        WGCLADEXCLUDE: kf.kdb.LayerInfo = kf.kdb.LayerInfo(111, 1)
        FILL1: kf.kdb.LayerInfo = kf.kdb.LayerInfo(2, 0)
        FILL2: kf.kdb.LayerInfo = kf.kdb.LayerInfo(3, 0)
        FILL3: kf.kdb.LayerInfo = kf.kdb.LayerInfo(10, 0)

    layers = Layers()
    pdk = kf.KCLayout("SCHEMA_PDK_NETLIST", infos=Layers)

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

    schema = kf.Schema(kcl=pdk)

    s1 = schema.create_inst(
        name="s1", component="straight", settings={"length": 5000, "width": 500}
    )
    s2 = schema.create_inst(
        name="s2", component="straight", settings={"length": 5000, "width": 500}
    )

    s1.place(x=1000, y=10_000)
    s2.place(x=1000, y=-210_000)

    schema.add_route("s1-s2", [s1["o2"]], [s2["o2"]], separation=20_000)
    schema.add_port("o1", port=s1["o1"])
    schema.add_port("o2", port=s2["o1"])

    nl = schema.netlist()
    c = schema.create_cell(kf.KCell)
    nl2 = c.netlist(ignore_unnamed=True)
    assert nl == nl2[c.name]
