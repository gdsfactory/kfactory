from __future__ import annotations

import pytest

import kfactory as kf


def test_layout_metadata_decorators(kcl: kf.KCLayout) -> None:
    @kcl.cell
    def mmi1x2(n: int = 2) -> kf.KCell:
        c = kcl.kcell()
        c.create_port(name="o1", trans=kf.kdb.Trans.R180, layer=1, width=1000)
        for idx in range(n):
            c.create_port(
                name=f"o{idx + 2}", trans=kf.kdb.Trans.R0, layer=1, width=1000
            )
        return c

    @kcl.device_type_for("mmi1x2")
    def device_type() -> str:
        return "mmi-1x2"

    @kcl.ports_for("mmi1x2")
    def ports(n: int = 2) -> list[kf.PortSpec]:
        return [
            kf.PortSpec(name="o1", kind="optical", side="left"),
            *[
                kf.PortSpec(name=f"o{idx + 2}", kind="optical", side="right")
                for idx in range(n)
            ],
        ]

    @kcl.model_for("mmi1x2")
    def base_model() -> dict:
        return {
            "language": "sax",
            "name": "mmi",
            "module": "base_models",
            "qualname": "mmi",
            "port_order": ("o1", "o2", "o3"),
        }

    factory = kcl.factories["mmi1x2"]
    metadata = factory.get_metadata(n=3)

    assert factory.has_metadata()
    assert metadata.device_type == "mmi-1x2"
    assert [p["name"] for p in metadata.ports] == ["o1", "o2", "o3", "o4"]
    assert [p["side"] for p in metadata.ports] == ["left", "right", "right", "right"]
    assert len(metadata.models) == 1
    assert metadata.models[0]["module"] == "base_models"


def test_fqn_providers_and_prepend(kcl: kf.KCLayout) -> None:
    @kcl.cell
    def straight() -> kf.KCell:
        return kcl.kcell()

    factory = kcl.factories["straight"]

    @kcl.model_for("straight")
    def base_model() -> dict:
        return {
            "language": "sax",
            "name": "straight",
            "module": "base_models",
            "qualname": "straight",
        }

    @kcl.model_for(factory.qualified_name, position="prepend")
    def preferred_model() -> dict:
        return {
            "language": "sax",
            "name": "straight_preferred",
            "module": "preferred_models",
            "qualname": "straight",
        }

    @kcl.tags_for(factory.qualified_name)
    def tags() -> tuple[str, ...]:
        return ("fqn",)

    metadata = factory.get_metadata()

    assert kcl.factories.get_by_qualified_name(factory.qualified_name) is factory
    assert metadata.models[0]["module"] == "preferred_models"
    assert metadata.models[1]["module"] == "base_models"
    assert metadata.tags == ("fqn",)


def test_target_resolution_errors(kcl: kf.KCLayout) -> None:
    @kcl.cell(basename="dup")
    def real_dup() -> kf.KCell:
        return kcl.kcell()

    @kcl.vcell(basename="dup")
    def virtual_dup() -> kf.VKCell:
        return kcl.vkcell()

    with pytest.raises(ValueError, match="Ambiguous factory name"):
        kcl.device_type_for("dup", lambda: "ckt")

    with pytest.raises(KeyError, match="Unknown factory name"):
        kcl.device_type_for("missing", lambda: "ckt")

    real_factory = kcl.factories.get_all_by_name("dup")[0]

    kcl.device_type_for(real_factory.qualified_name, lambda: "ckt")
    assert real_factory.get_metadata().device_type == "ckt"


def test_provider_parameter_errors(kcl: kf.KCLayout) -> None:
    @kcl.cell
    def straight(length: int = 10) -> kf.KCell:
        return kcl.kcell()

    @kcl.device_type_for("straight")
    def device_type(missing: int) -> str:
        return f"missing-{missing}"

    with pytest.raises(TypeError, match="requires parameters unavailable"):
        kcl.factories["straight"].get_metadata(length=20)


def test_vcell_metadata(kcl: kf.KCLayout) -> None:
    @kcl.vcell
    def virtual() -> kf.VKCell:
        return kcl.vkcell()

    @kcl.device_type_for("virtual")
    def device_type() -> str:
        return "ckt"

    factory = kcl.virtual_factories["virtual"]

    assert factory.get_metadata().device_type == "ckt"
    assert [f.name for f in kcl.virtual_factories.with_metadata()] == ["virtual"]


def test_schematic_function_is_separate(kcl: kf.KCLayout) -> None:
    def schematic() -> kf.DSchematic:
        return kf.DSchematic()

    @kcl.cell(schematic_function=schematic)
    def schematic_cell() -> kf.KCell:
        return kcl.kcell()

    factory = kcl.factories["schematic_cell"]

    assert factory.schematic_driven()
    assert not factory.has_metadata()
    assert factory.get_metadata() == kf.FactoryMetadata()
    assert isinstance(factory.get_schematic(), kf.DSchematic)


def test_schematic_for_decorator(kcl: kf.KCLayout) -> None:
    @kcl.cell
    def my_cell() -> kf.KCell:
        return kcl.kcell()

    factory = kcl.factories["my_cell"]
    assert not factory.schematic_driven()

    @kcl.schematic_for("my_cell")
    def my_schematic() -> kf.DSchematic:
        s = kf.DSchematic()
        s.info["symbol"] = "ckt"
        return s

    assert factory.schematic_driven()
    schematic = factory.get_schematic()
    assert isinstance(schematic, kf.DSchematic)
    assert schematic.info["symbol"] == "ckt"


def test_schematic_for_with_fqn(kcl: kf.KCLayout) -> None:
    @kcl.cell
    def another_cell() -> kf.KCell:
        return kcl.kcell()

    factory = kcl.factories["another_cell"]

    @kcl.schematic_for(factory.qualified_name)
    def schematic() -> kf.DSchematic:
        return kf.DSchematic()

    assert factory.schematic_driven()


def test_schematic_for_with_object(kcl: kf.KCLayout) -> None:
    @kcl.cell
    def obj_cell() -> kf.KCell:
        return kcl.kcell()

    factory = kcl.factories["obj_cell"]

    @kcl.schematic_for(factory)
    def schematic() -> kf.DSchematic:
        return kf.DSchematic()

    assert factory.schematic_driven()


def test_display_as_dict(kcl: kf.KCLayout) -> None:
    @kcl.cell
    def comp() -> kf.KCell:
        return kcl.kcell()

    @kcl.display_for("comp")
    def display() -> dict:
        return {"kind": "svg", "path": "/icons/comp.svg"}

    metadata = kcl.factories["comp"].get_metadata()
    assert metadata.display == {"kind": "svg", "path": "/icons/comp.svg"}


def test_models_are_plain_lists(kcl: kf.KCLayout) -> None:
    @kcl.cell
    def dev() -> kf.KCell:
        return kcl.kcell()

    @kcl.model_for("dev")
    def models() -> list:
        return [
            {"language": "sax", "name": "dev_sax"},
            {"language": "spice", "name": "dev_spice"},
        ]

    metadata = kcl.factories["dev"].get_metadata()
    assert len(metadata.models) == 2
    assert metadata.models[0]["language"] == "sax"
    assert metadata.models[1]["language"] == "spice"
