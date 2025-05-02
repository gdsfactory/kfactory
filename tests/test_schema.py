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
    kf.DSchema.model_validate(yaml.load(schema_yaml))
