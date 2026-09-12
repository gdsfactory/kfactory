from pathlib import Path

import pytest

import kfactory as kf
from kfactory.settings import Info


@pytest.mark.parametrize("kind", ["integer", "double", "virtual"])
def test_instance_info_requires_name(kcl: kf.KCLayout, kind: str) -> None:
    child = kcl.kcell("child")
    parent = kcl.kcell("parent")
    inst = (
        kf.VInstance(child)
        if kind == "virtual"
        else (parent << child).to_dtype()
        if kind == "double"
        else parent << child
    )
    with pytest.raises(ValueError, match="Unnamed instances"):
        _ = inst.info
    with pytest.raises(ValueError, match="Unnamed instances"):
        inst.info = Info(measure="spectrum")
    assert parent.instance_infos == {}

    inst.name = ""
    inst.info["measure"] = "spectrum"
    inst.info.wavelength_nm = 1550
    assert inst.info.model_dump() == {"measure": "spectrum", "wavelength_nm": 1550}
    source = Info(nested={"values": [1, 2]})
    inst.info = source
    source.nested["values"].append(3)
    assert inst.info.nested == {"values": [1, 2]}
    with pytest.raises(ValueError, match="Values of the info dict"):
        inst.info["invalid"] = object()  # ty:ignore[invalid-assignment]
    assert "invalid" not in inst.info


@pytest.mark.parametrize("dtype", [False, True])
def test_instance_info_identity_and_rename(kcl: kf.KCLayout, dtype: bool) -> None:
    parent = kcl.dkcell("parent") if dtype else kcl.kcell("parent")
    child = kcl.kcell("child")
    child.info["component"] = "mzi"
    first = parent << child
    second = parent << child
    first.name = "first"
    second.name = "second"
    first.info["measure"] = "spectrum"
    second.info["measure"] = "power"
    info = first.info
    first.dmove((10, 30)).drotate(90)
    assert parent.insts["first"].info is info
    assert first.to_itype().info is first.to_dtype().info
    assert second.info.measure == "power"
    assert child.info.model_dump() == {"component": "mzi"}

    first.name = "renamed"
    first.name = "renamed"
    assert "first" not in parent.instance_infos
    assert parent.insts["renamed"].info is info
    assert first.name == "renamed"
    assert first.info is info
    assert second.info.measure == "power"

    other_parent = kcl.kcell("other_parent")
    other = other_parent << child
    other.name = "renamed"
    assert other.info.model_dump() == {}


@pytest.mark.parametrize("suffix", [".gds", ".oas"])
def test_instance_info_roundtrip(kcl: kf.KCLayout, tmp_path: Path, suffix: str) -> None:
    parent = kcl.kcell("parent")
    child = kcl.kcell("child")
    child.shapes(kcl.layer(1, 0)).insert(kf.kdb.Box(500))
    child.info["component"] = "mzi"
    first = parent << child
    second = parent << child
    first.name = "first"
    second.name = "second"
    first.info["abc"] = kf.kdb.Box(500)
    first.info["really_long_thing"] = "a" * 100_000
    first.info["nested"] = {"box": kf.kdb.DBox(5), "values": [1, "two", None]}
    second.info["measure"] = "power"
    first.name = "renamed"
    first.dmovey(30)
    path = tmp_path / f"instance_info{suffix}"
    parent.write(path)
    restored = kf.KCLayout(f"{kcl.name}_read")
    restored.read(path)
    top = restored["parent"]
    assert top.insts["renamed"].info.model_dump() == first.info.model_dump()
    assert top.insts["second"].info.model_dump() == second.info.model_dump()
    assert top.insts["renamed"].cell_index == top.insts["second"].cell_index
    assert restored["child"].info.model_dump() == child.info.model_dump()
    assert set(top.instance_infos) == {"renamed", "second"}
    assert len(list(restored.each_cell())) == 2


@pytest.mark.parametrize("virtual_child", [False, True])
@pytest.mark.parametrize("angle", [0, 30])
def test_virtual_instance_info_materialization(
    kcl: kf.KCLayout, virtual_child: bool, angle: int
) -> None:
    child = kcl.vkcell("child") if virtual_child else kcl.kcell("child")
    child.shapes(kcl.layer(1, 0)).insert(kf.kdb.DBox(5))
    parent = kcl.kcell("parent")
    inst = kf.VInstance(
        child, trans=kf.kdb.DCplxTrans(1, angle, False, 0, 0), name="ref"
    )
    inst.info["nested"] = {"values": [1]}
    copy = inst.dup()
    copy.info.nested["values"].append(2)
    assert inst.info.nested == {"values": [1]}
    inserted = inst.insert_into(parent)
    assert inserted.info.model_dump() == inst.info.model_dump()
    inserted.info.nested["values"].append(3)
    assert inst.info.nested == {"values": [1]}


def test_instance_info_cell_copy(kcl: kf.KCLayout) -> None:
    parent = kcl.kcell("parent")
    inst = parent << kcl.kcell("child")
    inst.name = "ref"
    inst.info["nested"] = {"values": [1]}
    copy = parent.dup()
    assert copy.insts["ref"].info.model_dump() == inst.info.model_dump()
    copy.insts["ref"].info.nested["values"].append(2)
    assert inst.info.nested == {"values": [1]}


@pytest.mark.parametrize("virtual", [False, True])
def test_instance_info_remove_name(kcl: kf.KCLayout, virtual: bool) -> None:
    parent = kcl.kcell("parent")
    child = kcl.kcell("child")
    inst = kf.VInstance(child) if virtual else parent << child
    inst.name = "ref"
    inst.info["measure"] = "power"
    with pytest.raises(ValueError, match="Cannot remove the name"):
        inst.name = None
    assert inst.name == "ref"
    assert inst.info.measure == "power"
    inst.info = Info()
    inst.name = None
    assert parent.instance_infos == {}
    with pytest.raises(ValueError, match="Unnamed instances"):
        _ = inst.info


@pytest.mark.parametrize(
    "method", ["delete", "remove", "index", "clear", "flatten", "flatten_parent"]
)
def test_instance_info_removal(kcl: kf.KCLayout, method: str) -> None:
    parent = kcl.kcell("parent")
    child = kcl.kcell("child")
    inst = parent << child
    inst.name = "ref"
    inst.info["measure"] = "power"
    match method:
        case "delete":
            inst.delete()
        case "remove":
            parent.insts.remove(inst)
        case "index":
            del parent.insts[0]
        case "clear":
            parent.insts.clear()
        case "flatten":
            inst.flatten()
        case "flatten_parent":
            parent.flatten()
    assert parent.instance_infos == {}
    replacement = parent << child
    replacement.name = "ref"
    assert replacement.info.model_dump() == {}


@pytest.mark.parametrize("append", [False, True])
def test_instance_info_insert(kcl: kf.KCLayout, append: bool) -> None:
    parent = kcl.kcell("parent")
    target = kcl.kcell("target")
    inst = parent << kcl.kcell("child")
    inst.name = "ref"
    inst.info["nested"] = {"values": [1]}
    if append:
        target.insts.append(inst)
    else:
        target.insert(inst)
    assert target.insts["ref"].info.model_dump() == inst.info.model_dump()
    target.insts["ref"].info.nested["values"].append(2)
    assert inst.info.nested == {"values": [1]}
    assert len(target.insts) == 1


@pytest.mark.parametrize("target_dtype", [False, True])
def test_dinstance_info_append(kcl: kf.KCLayout, target_dtype: bool) -> None:
    parent = kcl.dkcell("parent")
    target = kcl.dkcell("target") if target_dtype else kcl.kcell("target")
    inst = parent << kcl.kcell("child")
    inst.name = "ref"
    inst.dcplx_trans = kf.kdb.DCplxTrans(1.25, 30, True, 1.234, 5.678)
    inst.info["nested"] = {"values": [1]}
    trans = inst.dcplx_trans

    target.insts.append(inst)

    inserted = target.insts["ref"]
    assert inserted.cell_index == inst.cell_index
    assert inserted.dcplx_trans == trans
    assert inserted.info.model_dump() == inst.info.model_dump()
    inserted.info.nested["values"].append(2)
    assert inst.info.nested == {"values": [1]}
    assert inst.dcplx_trans == trans
    assert parent.insts["ref"].instance == inst.instance
    assert len(parent.insts) == 1
    assert len(target.insts) == 1
