import kfactory as kf


def test_layerstack_instance(pdk: kf.pdk.Pdk):
    assert isinstance(pdk.layer_stack, kf.pdk.LayerStack)


def test_layerstack_layer_thickness(pdk: kf.pdk.Pdk):
    assert isinstance(pdk.layer_stack.get_layer_to_thickness()[(1,0)], float)


def test_layerstack_layer_zmin(pdk: kf.pdk.Pdk):
    assert isinstance(pdk.layer_stack.get_layer_to_zmin()[(1,0)], float)


def test_layerstack_layer_material(pdk: kf.pdk.Pdk):
    assert isinstance(pdk.layer_stack.get_layer_to_material()[(1,0)], str)


def test_layerstack_layer_info(pdk: kf.pdk.Pdk):
    print(pdk.layer_stack.get_layer_to_info())
    assert isinstance(pdk.layer_stack.get_layer_to_info()[(1,0)], kf.kcell.Info)


def test_layerstack_layer_sidewall_angle(pdk: kf.pdk.Pdk):
    assert isinstance(pdk.layer_stack.get_layer_to_sidewall_angle()[(1,0)], float)
