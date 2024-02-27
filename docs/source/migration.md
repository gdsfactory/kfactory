# Migration

## v0.12

### `KCLayout.cell`

Beginning with `kfactory>=0.12`, the [`@cell`][kfactory.kcell.KCLayout.cell] decorator is now part of a KCLayout. This has a minor impact on the [`KCLayout`][kfactory.kcell.KCLayout] as the function
[`kdb.Layout.cell`][klayout.dbcore.Layout.cell] gets shadowed as a consequence. Please use `KCLayout.layout.cell` to access the function.
