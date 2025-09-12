from pathlib import Path

import pytest
from ruamel.yaml import YAML

import kfactory as kf

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


def _get_path_stem(p: Path) -> str:
    return p.with_suffix("").stem


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
