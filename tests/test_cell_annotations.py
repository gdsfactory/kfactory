from __future__ import annotations

import pytest

import kfactory as kf


def test_layout_annotation_decorators(kcl: kf.KCLayout) -> None:
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
    def ports(n: int = 2) -> list[kf.AnnotationPort]:
        return [
            kf.AnnotationPort(name="o1", kind="optical", side="left"),
            *[
                kf.AnnotationPort(name=f"o{idx + 2}", kind="optical", side="right")
                for idx in range(n)
            ],
        ]

    @kcl.model_for("mmi1x2")
    def base_model() -> kf.SaxModelSpec:
        return kf.SaxModelSpec(
            name="mmi",
            module="base_models",
            qualname="mmi",
            port_order=("o1", "o2", "o3"),
        )

    factory = kcl.factories["mmi1x2"]
    annotation = factory.get_annotation(n=3)

    assert factory.has_annotation()
    assert annotation.device_type == "mmi-1x2"
    assert [p.name for p in annotation.ports] == ["o1", "o2", "o3", "o4"]
    assert [p.side for p in annotation.ports] == ["left", "right", "right", "right"]
    assert annotation.models.select(simulator="sax")[0].module == "base_models"


def test_fqn_providers_and_prepend(kcl: kf.KCLayout) -> None:
    @kcl.cell
    def straight() -> kf.KCell:
        return kcl.kcell()

    factory = kcl.factories["straight"]

    @kcl.model_for("straight")
    def base_model() -> kf.SaxModelSpec:
        return kf.SaxModelSpec(
            name="straight",
            module="base_models",
            qualname="straight",
        )

    @kcl.model_for(factory.qualified_name, position="prepend")
    def preferred_model() -> kf.SaxModelSpec:
        return kf.SaxModelSpec(
            name="straight",
            module="preferred_models",
            qualname="straight",
        )

    @kcl.tags_for(factory.qualified_name)
    def tags() -> tuple[str, ...]:
        return ("fqn",)

    annotation = factory.get_annotation()

    assert kcl.factories.get_by_qualified_name(factory.qualified_name) is factory
    assert [model.module for model in annotation.models] == ["preferred_models"]
    assert annotation.tags == ("fqn",)


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
    assert real_factory.get_annotation().device_type == "ckt"


def test_provider_parameter_errors(kcl: kf.KCLayout) -> None:
    @kcl.cell
    def straight(length: int = 10) -> kf.KCell:
        return kcl.kcell()

    @kcl.device_type_for("straight")
    def device_type(missing: int) -> str:
        return f"missing-{missing}"

    with pytest.raises(TypeError, match="requires parameters unavailable"):
        kcl.factories["straight"].get_annotation(length=20)


def test_vcell_annotations(kcl: kf.KCLayout) -> None:
    @kcl.vcell
    def virtual() -> kf.VKCell:
        return kcl.vkcell()

    @kcl.device_type_for("virtual")
    def device_type() -> str:
        return "ckt"

    factory = kcl.virtual_factories["virtual"]

    assert factory.get_annotation().device_type == "ckt"
    assert [f.name for f in kcl.virtual_factories.annotated()] == ["virtual"]


def test_schematic_function_is_separate(kcl: kf.KCLayout) -> None:
    def schematic() -> kf.DSchematic:
        return kf.DSchematic()

    @kcl.cell(schematic_function=schematic)
    def schematic_cell() -> kf.KCell:
        return kcl.kcell()

    factory = kcl.factories["schematic_cell"]

    assert factory.schematic_driven()
    assert not factory.has_annotation()
    assert factory.get_annotation() == kf.CellAnnotation()
    assert isinstance(factory.get_schematic(), kf.DSchematic)
