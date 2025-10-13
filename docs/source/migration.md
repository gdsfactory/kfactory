# Migration

## v0.13

### `KCLayout.cell`

Beginning with `kfactory>=0.12`, the [`@cell`][kfactory.layout.KCLayout.cell] decorator is now part of a KCLayout.
This has a minor impact on the [`KCLayout`][kfactory.layout.KCLayout] as the function `kdb.Layout.cell` gets shadowed as a consequence. Please use `KCLayout.layout.cell` to access the function.


# Deprecation

## v 0.11.2

- `@kf.cell` is depracted due to the integration into `kf.kcl`, use `@kf.kcl.cell` instead
