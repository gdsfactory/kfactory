from pathlib import Path

import kfactory as kf


def test_custom_show() -> None:
    from kfactory.kcell import AnyKCell

    showed = False
    _layout_options = kf.save_layout_options()

    def show(
        layout: kf.KCLayout | AnyKCell | Path | str,
        lyrdb: kf.rdb.ReportDatabase | Path | str | None = None,
        l2n: kf.kdb.LayoutToNetlist | Path | str | None = None,
        keep_position: bool = True,
        save_options: kf.kdb.SaveLayoutOptions = _layout_options,
        use_libraries: bool = True,
        library_save_options: kf.kdb.SaveLayoutOptions = _layout_options,
    ) -> None:
        nonlocal showed
        showed = True

    kcl = kf.KCLayout("TEST_CUSTOM_SHOW")
    c = kcl.kcell("CustomShow")
    _show = kf.config.show_function
    kf.config.show_function = show
    c.show()
    assert showed
    kf.config.show_function = _show


def test_custom_show_string() -> None:
    kcl = kf.KCLayout("TEST_CUSTOM_SHOW_STRING")
    c = kcl.kcell("CustomShowString")
    _show = kf.config.show_function
    kf.config.show_function = "tests.custom.show.show"  # type: ignore[assignment]
    c.show()
    kf.config.show_function = _show
