from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    import kfactory


def show(
    layout: kfactory.KCLayout | kfactory.KCell | Path | str,
    *,
    lyrdb: kfactory.rdb.ReportDatabase | Path | str | None = None,
    l2n: kfactory.kdb.LayoutToNetlist | Path | str | None = None,
    keep_position: bool = True,
    save_options: kfactory.kdb.SaveLayoutOptions | None = None,
    use_libraries: bool = True,
    library_save_options: kfactory.kdb.SaveLayoutOptions | None = None,
    technology: str | None = None,
) -> None:
    import kfactory as kf

    if save_options is None:
        save_options = kf.save_layout_options()
    if library_save_options is None:
        library_save_options = kf.save_layout_options()
