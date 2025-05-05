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

    LAYER = Layers()
    pdk = kf.KCLayout("SCHEMA_PDK", infos=Layers)

    @pdk.cell
    def straight(length: int) -> kf.KCell:
        c = pdk.kcell()
        c.shapes(LAYER.WG).insert(kf.kdb.Box(0, -250, length, 250))
        c.create_port(
            name="o1",
            width=500,
            trans=kf.kdb.Trans(rot=2, mirrx=False, x=0, y=0),
            layer_info=LAYER.WG,
        )
        c.create_port(
            name="o2",
            width=500,
            trans=kf.kdb.Trans(x=length, y=0),
            layer_info=LAYER.WG,
        )

        return c

    schema = kf.schema.TSchema[int](kcl=pdk)

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

    LAYER = Layers()
    pdk = kf.KCLayout("SCHEMA_PDK_DECORATOR", infos=Layers)

    @pdk.cell
    def straight(length: int) -> kf.KCell:
        c = pdk.kcell()
        c.shapes(LAYER.WG).insert(kf.kdb.Box(0, -250, length, 250))
        c.create_port(
            name="o1",
            width=500,
            trans=kf.kdb.Trans(rot=2, mirrx=False, x=0, y=0),
            layer_info=LAYER.WG,
        )
        c.create_port(
            name="o2",
            width=500,
            trans=kf.kdb.Trans(x=length, y=0),
            layer_info=LAYER.WG,
        )

        return c

    @pdk.schematic_cell
    def long_straight(n: int) -> kf.schema.TSchema[int]:
        schema = kf.schema.TSchema[int](kcl=pdk)

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
