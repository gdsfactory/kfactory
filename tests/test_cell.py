import kfactory as kf


def test_enclosure_name(straight_factory):
    wg = straight_factory(width=1000, length=10000)
    assert wg.name == "straight_W1000_L10000_LWG_EWGSTD"
    wg.show()
