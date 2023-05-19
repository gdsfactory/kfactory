.. python(code):
   language: python

Config
------

The config is managed by a pydantic `SettingsModel <https://docs.pydantic.dev/latest/usage/settings/>`_. Entries can be set either through changing :py:attr:`kfactory.config`

The config can configure the logger and display type of the jupyter widget among other things.

Setting can be done through environment variables


Logging
=======

Logging is done through `loguru <https://github.com/Delgan/loguru>`_. KFactory allows configuration of the log level.
The logger can be used to log message to the console.

.. code::

   kfactory.config.logger.debug("message {}, {}", var1, var2)
   kfactory.config.logger.info(f"f-string message {var}")

Log Level
+++++++++

The logger's level can be set with :py:attr:`kfactory.config.logfilter.level` or through environment variables, under linux for example

.. code::

   export KFACTORY_LOGFILTER__LEVEL="DEBUG"

Available levels are "TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"
