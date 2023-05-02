import kfactory as kf


def test_shapes(LAYER):
    kc = kf.Cell()

    kc.shapes(LAYER.WG).insert(kf.kdb.Text())


if __name__ == "__main__":
    test_shapes()
