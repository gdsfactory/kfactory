from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from ruamel.yaml import YAML

import kfactory as kf

if TYPE_CHECKING:
    from collections.abc import Callable

gf = pytest.importorskip("gdsfactory")
jinja2 = pytest.importorskip("jinja2")
gf_factories = pytest.importorskip("gdsfactory.routing.factories")
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
yaml = YAML(typ=["string", "safe"])

yaml_samples = [
    """
    name: sample_all_angle
    placements:
      s0:
        x: 0
        y: 0
    instances:
      s0:
        component: straight
        settings:
            length: 10
      b1:
        component: bend_euler_all_angle
        settings:
          radius: 10
          angle: 30
        virtual: True
      s1:
        component: straight
        settings:
          length: 10
        virtual: true
    connections:
      s1,o1: b1,o2
      s0,o2: b1,o1
    """,
    """
    name: sample_mmis
    info:
        polarization: te
        wavelength: 1.55
        description: just a demo on adding metadata
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
        mmi_long:
            rotation: 180
            x: 100
            y: 100
    routes:
        route_name1:
            links:
                mmi_short,o2: mmi_long,o1
            settings:
                cross_section: strip
    ports:
        o1: mmi_short,o1
        o2: mmi_long,o2
        o3: mmi_long,o3
    """,
    """
    name: mask_compact
    instances:
        mmi1x2_sweep_pack:
           component: pack_doe
           settings:
             doe: mmi1x2
             settings:
                 length_mmi: [2, 100]
                 width_mmi: [4, 10]
             do_permutations: True
             spacing: 100
             function: add_fiber_array
        mzi_sweep:
           component: pack_doe
           settings:
             doe: mzi
             settings:
                delta_length: [10, 100]
             do_permutations: True
             spacing: 100
             function: add_fiber_array
    placements:
        mmi1x2_sweep_pack:
            xmin: -10
        mzi_sweep:
            x: mmi1x2_sweep_pack,east
            dx: 10
            y: {instance: mmi1x2_sweep_pack, y: top}
            anchor: {x: "left", y: "top"}
    """,
    """
    instances:
      t:
        component: pad_array
        settings:
          port_orientation: 270
          columns: 3
      b:
        component: pad_array
        settings:
          port_orientation: 90
          columns: 3
    placements:
      t:
        x: 200
        y: 400
    routes:
      route1:
        settings:
          bend: wire_corner
          # start_straight_length: 150
          # end_straight_length: 150
          cross_section: metal_routing
          allow_width_mismatch: True
          sort_ports: True
        links:
          t,e11: b,e11
          t,e13: b,e13
    """,
]


def _get_path_stem(p: Path) -> str:
    return p.with_suffix("").stem


@pytest.mark.parametrize(
    "path",
    [
        pytest.param(
            file, marks=pytest.mark.skip(reason="Incompatible gdsfactory schematic")
        )
        if file.with_suffix("").stem in skip_files
        else pytest.param(
            file,
            marks=pytest.mark.xfail(
                raises=(ValueError, TypeError, KeyError),
                reason="old gdsfactory yaml",
            ),
        )
        for file in yaml_files
    ],
    ids=_get_path_stem,
)
def test_gdsfactory_yaml_build(path: Path) -> None:
    pdk = gf.get_active_pdk()
    factories = pdk.cells
    with path.open(encoding="utf-8") as f:
        fstr = jinja2.Template(f.read()).render()
    schematic = kf.DSchematic.model_validate(yaml.load(fstr))
    schematic.create_cell(
        output_type=gf.Component,
        factories=factories,
        routing_strategies=pdk.routing_strategies or gf_factories.routing_strategies,
        place_unknown=True,
    ).show()
    print(schematic.code_str())  # noqa: T201


@pytest.mark.parametrize("sample", yaml_samples)
def test_gdsfactory_yaml_samples(sample: str) -> None:
    pdk = gf.get_active_pdk()
    factories: dict[str, Callable[..., kf.DKCell] | Callable[..., kf.VKCell]] = {}
    factories.update(pdk.containers)
    factories.update(pdk.cells)
    schematic = kf.DSchematic.model_validate(yaml.load(sample))
    schematic.create_cell(
        output_type=gf.Component,
        factories=factories,
        routing_strategies=pdk.routing_strategies or gf_factories.routing_strategies,
        place_unknown=True,
    )
