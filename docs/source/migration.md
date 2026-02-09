# Migration

## kfactory 3.0

With kfactory 3.0, some modules and types have changed:

- `kfactory.factories.virtual.utils` was moved to unify it with other factory utils into `kfactory.factories.utils`
- Old routing functions removed: `routing.electrical`'s `route_L` and `route_elec`, `routing.optical.route`.
  - Use `routing.[...].route_bundle` instead
- Routing interface for schematics:
  - In order to enable
