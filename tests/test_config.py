import kfactory as kf
from pathlib import Path


def test_custom_show() -> None:
    showed = False

    def show(
        layout: kf.KCLayout | kf.KCell | Path | str,
        lyrdb: kf.rdb.ReportDatabase | Path | str | None = None,
        l2n: kf.kdb.LayoutToNetlist | Path | str | None = None,
        keep_position: bool = True,
        save_options: kf.kdb.SaveLayoutOptions = kf.save_layout_options(),
        use_libraries: bool = True,
        library_save_options: kf.kdb.SaveLayoutOptions = kf.save_layout_options(),
    ) -> None:
        nonlocal showed
        showed = True

    c = kf.kcl.kcell("CustomShow")
    _show = kf.config.show_function
    kf.config.show_function = show
    c.show()
    assert showed
    kf.config.show_function = _show


def test_custom_show_string() -> None:
    c = kf.kcl.kcell("CustomShowString")
    _show = kf.config.show_function
    kf.config.show_function = "custom.show.show"  # type: ignore[assignment]
    c.show()
    kf.config.show_function = _show
