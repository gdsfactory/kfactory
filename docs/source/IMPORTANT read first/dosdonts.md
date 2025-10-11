# Dos and Don'ts


## Dos

## Don'ts

* "function_name" as a function parameter when using `@kf.cell` decorator,
  it will be overwritten by the function name used to create the cell
* "self", "cls" in `@cell` functions, they will be dropped.
