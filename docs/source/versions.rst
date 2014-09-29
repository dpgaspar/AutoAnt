Versions
========

Improvements and Bug fixes on 0.3.0
-----------------------------------

- New, Processor echo, writes to stdout or file the produced items.
- New, DirMon property mtime, files modified before or after X minutes.
- Fix, JSON load log's critical error, but does not raise python exception.
- New, Processors and Providers inherit from same class BaseProvider.
- New, all properties are declared on providers and automatically assigned with decorator @register_property.
- New, required property verification, if missing will log's critical error.
- New, type property verification, if missing will log's critical error.
- Fix, unicode support.
