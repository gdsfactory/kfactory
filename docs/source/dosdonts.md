# Dos and Don'ts

This describes generally what are best practices for kfactory. This should be used in addition to good general python practices.

## Dos

* Make parameters restricted types whenever possible. This avoids collisions within caches if they do not get matched exactly

## Don'ts

* "function_name" as a function parameter when using `@kf.cell` (or any of its friends in other KCLayout) decorator,
  it will be overwritten by the function name used to create the cell
* "self", "cls" in `@cell` functions, they will be dropped.
