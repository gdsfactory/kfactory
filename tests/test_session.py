import kfactory as kf
from tests.session import session1, session2, session3


def test_session_cache() -> None:
    c = session3.my_cell(a=5)

    f2 = session2.kcl2.factories["my_other_cell"]
    f1 = session1.kcl1.factories["test"]

    assert session1.cell_created
    assert session2.cell_created
    assert session3.cell_created

    kf.save_session(c=c)

    session1.cell_created = False
    session2.cell_created = False
    session3.cell_created = False

    f1.prune()
    f2.prune()

    kf.load_session()

    session3.my_cell(a=5)

    assert not session1.cell_created
    assert not session2.cell_created
    assert not session3.cell_created

    f2.prune()

    session1.cell_created = False
    session2.cell_created = False
    session3.cell_created = False

    session3.my_cell(a=5)

    assert not session1.cell_created
    assert session2.cell_created
    assert session3.cell_created

    kf.save_session(session1.test())

    f1.prune()
    f2.prune()

    session1.cell_created = False
    session2.cell_created = False
    session3.cell_created = False

    kf.load_session()

    session3.my_cell(a=5)

    assert not session1.cell_created
    assert session2.cell_created
    assert session3.cell_created
