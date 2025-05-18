import kfactory as kf
from tests.conftest import Layers


def test_layerstack_instance(pdk: kf.KCLayout) -> None:
    assert isinstance(pdk.layer_stack, kf.LayerStack)


def test_layerstack_layer_thickness(pdk: kf.KCLayout) -> None:
    assert isinstance(pdk.layer_stack.get_layer_to_thickness()[(1, 0)], float)


def test_layerstack_layer_zmin(pdk: kf.KCLayout) -> None:
    assert isinstance(pdk.layer_stack.get_layer_to_zmin()[(1, 0)], float)


def test_layerstack_layer_material(pdk: kf.KCLayout) -> None:
    assert isinstance(pdk.layer_stack.get_layer_to_material()[(1, 0)], str)


def test_layerstack_layer_info(pdk: kf.KCLayout) -> None:
    assert isinstance(pdk.layer_stack.get_layer_to_info()[(1, 0)], kf.Info)


def test_layerstack_layer_sidewall_angle(pdk: kf.KCLayout) -> None:
    assert isinstance(pdk.layer_stack.get_layer_to_sidewall_angle()[(1, 0)], float)


def test_layerstack_layer_getattr(pdk: kf.KCLayout, layers: Layers) -> None:
    assert pdk.layer_stack.wg == kf.layer.LayerLevel(
        layer=layers.WG,
        thickness=0.22,
        zmin=0,
        material="si",
        info=kf.Info(mesh_order=1),
    )


def test_layerstack_layer_getitem(pdk: kf.KCLayout, layers: Layers) -> None:
    assert pdk.layer_stack["wg"] == kf.layer.LayerLevel(
        layer=layers.WG,
        thickness=0.22,
        zmin=0,
        material="si",
        info=kf.Info(mesh_order=1),
    )
