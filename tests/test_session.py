from session import session1, session2, session3

import kfactory as kf


def test_session_cache() -> None:
    c = session3.my_cell(a=5)

    assert session1.cell_created
    assert session2.cell_created
    assert session3.cell_created

    kf.save_session(c=c)

    session1.cell_created = False
    session2.cell_created = False
    session3.cell_created = False

    session1.test.prune()
    session2.my_other_cell.prune()

    kf.load_session()

    session3.my_cell(a=5)

    assert not session1.cell_created
    assert not session2.cell_created
    assert not session3.cell_created

    session2.my_other_cell.prune()

    session1.cell_created = False
    session2.cell_created = False
    session3.cell_created = False

    session3.my_cell(a=5)

    assert not session1.cell_created
    assert session2.cell_created
    assert session3.cell_created

    kf.save_session(session1.test())

    session1.test.prune()
    session2.my_other_cell.prune()

    session1.cell_created = False
    session2.cell_created = False
    session3.cell_created = False

    kf.load_session()

    session3.my_cell(a=5)

    assert not session1.cell_created
    assert session2.cell_created
    assert session3.cell_created

    session2.kcl2.delete()
    session1.kcl1.delete()
