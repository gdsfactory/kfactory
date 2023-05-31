# Config

The config is managed by a pydantic [`SettingsModel`](https://docs.pydantic.dev/latest/usage/settings/). Entries can be set either through changing `kfactory.config`

The config can configure the logger and display type of the jupyter widget among other things.

Setting can be done through environment variables


## Logging

Logging is done through [`loguru`](https://github.com/Delgan/loguru). KFactory allows configuration of the log level.
The logger can be used to log message to the console.

```python
kfactory.config.logger.debug("message {}, {}", var1, var2)
kfactory.config.logger.info(f"f-string message {var}")
```

### Logging Options

Below are some basic configurations available in kfactory. loguru also supports various
advanced ways to log, e.g. lazy evaluation for expensive functions, this is explained excellently in the
[docs](https://loguru.readthedocs.io/en/stable/overview.html#take-the-tour)


#### Log Level

loguru can log in multiple levels. By default the following are available for kfactory

Available log levels are "TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL".

Log outputs can be filtered either by settings a minimum level or by regex. The minimum level is configured in `kfactory.config.logfilter.level`.
Instead of configuring it through python, it can also be configured from an environment variable. By default the log level is set to "INFO",
so anything below "INFO" is not output. This can be configured either by setting the level in python, through dotenv
([untested](https://docs.pydantic.dev/latest/usage/settings/#dotenv-env-support)), or through environment variables.

| Logging Function                  | Minimum `kfactory.config.logfilter.level` |
|-----------------------------------|-------------------------------------------|
| `kfactory.config.logger.trace`    | `TRACE`                                   |
| `kfactory.config.logger.debug`    | `DEBUG`                                   |
| `kfactory.config.logger.info`     | `INFO`                                    |
| `kfactory.config.logger.success`  | `SUCCESS`                                 |
| `kfactory.config.logger.warning`  | `WARNING`                                 |
| `kfactory.config.logger.error`    | `ERROR`                                   |
| `kfactory.config.logger.critical` | `CRITICAL`                                |

Alternatively `kfactory.config.logger.log(level: str | int, message: str)` can be used.

Setting the loglevel through environment:

##### Linux/MacOS

```bash
export KFACTORY_LOGFILTER_LEVEL="DEBUG"
```

This can of course also been set one time (under Linux/MacOS): `KFACTORY_LOGFILTER_LEVEL="DEBUG" python my_file.py`

##### Windows

```cmd
setx KFACTORY_LOGFILTER_LEVEL="DEBUG"
```

### Using loguru to give more comprehensive Traceback

loguru's logger offers a catch decorator to catch Exceptions and give a more conprehensive Traceback.

```python
import kfactory as kf


@kf.config.logger.catch
def test(x: int) -> None:
    if x != 42:
        raise ValueError(f"x is not 42, it's {x}")


def run_test(x: int) -> None:
    return test(x)


run_test(42)
run_test(20)
```

This will produce a traceback with infos about the values:

```
2023-05-31 17:56:45.816 | INFO     | kfactory.conf:__init__:105 - LogLevel: INFO
2023-05-31 17:56:45.890 | ERROR    | __main__:run_test:11 - An error has been caught in function 'run_test', process 'MainProcess' (28352), thread 'MainThread' (139734375601984):
Traceback (most recent call last):

  File "/home/sgoeldi/repos/kfactory/test.py", line 15, in <module>
    run_test(20)
    └ <function run_test at 0x7f15c421f100>

> File "/home/sgoeldi/repos/kfactory/test.py", line 11, in run_test
    return test(x)
           │    └ 20
           └ <function test at 0x7f16717d13a0>

  File "/home/sgoeldi/repos/kfactory/test.py", line 7, in test
    raise ValueError(f"x is not 42, it's {x}")
```

## Jupyter Widget

By default kfactory will provide an interactive Jupyter widget for notebooks. The widget is not very performant and might impact performance for larger
notebooks. Instead of the widget a simple `IPython.Image` may be used. It can be configured in `kfactory.config.display_type`. Available options are
`widget` or `image`. The docs for example use `image` as the interactive widget won't work in a standard html page.

Similar to the log level this may also be configured through dotenv or an env variable.
`export KFACTORY_DISPLAY_TYPE="image"` will set it to display as image by default.
