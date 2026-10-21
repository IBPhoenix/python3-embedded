# Using firebird-embedded with firebird-driver

`firebird-embedded` supplies a client library and embedded engine; `firebird-driver` supplies
database APIs. Declare both as application dependencies when the application uses both.
The embedded wheel is platform-specific. Match its bundled Firebird release to the application's
required Firebird features; do not confuse `firebird-driver`'s Python package version with
the Firebird runtime version.

## Startup order

The driver's `driver_config.fb_client_library` is a configuration option. Set its `.value`
to the provider's `client_library` path **before** the first `connect()`, `create_database()`,
`connect_server()`, `load_api()`, or `get_api()` call in the process. The driver caches its
loaded client API. Importing `firebird.driver` is fine before this assignment; loading its
API is not. Configure this during application startup, before worker threads begin connecting.
If an application may use several providers, select one client library for the process before
any Firebird API load.

For a local embedded database, pass the local database path to `connect()` or `create_database()`
without a host prefix. A `localhost:` DSN selects a network connection and does not establish
that the embedded engine is being used. Keep database credentials and path in application configuration.

```python
from importlib.metadata import entry_points
from pathlib import Path

from firebird.driver import connect, driver_config


def select_embedded_provider():
    candidates = []
    for ep in entry_points(group="firebird.runtime.providers"):
        provider = ep.load()()
        if {"client", "embedded"} <= provider.capabilities:
            candidates.append(provider)
    if len(candidates) != 1:
        raise RuntimeError(
            f"Expected one embedded Firebird runtime provider, found {len(candidates)}; "
            "configure a provider explicitly if several are installed"
        )
    return candidates[0]


provider = select_embedded_provider()
driver_config.fb_client_library.value = str(provider.client_library)

database = Path("/absolute/path/to/application.fdb")  # supply from app configuration
with connect(database, user="SYSDBA", password="<configured password>") as connection:
    with connection.cursor() as cursor:
        cursor.execute("select current_timestamp from rdb$database")
        print(cursor.fetchone())
```

This example demonstrates discovery and configuration, not database creation or credential
storage. Adapt provider selection when the application config names one provider. Resolve
the database path to a suitable absolute path for the target OS. The provider's `root` is
the installed Firebird runtime directory; use it when other native resources are needed,
without copying files into the source tree or modifying installed `site-packages`.

## Verification

- Inspect the installed entry point, provider properties, and `client_library.is_file()` in
  the same environment as the application. Missing entry points usually mean the distribution
  is not installed there; missing runtime files can mean an editable installation or incomplete wheel.
- Test a real local database operation using the **installed wheel** on each supported target
  platform. File existence alone does not prove that the client library, embedded engine,
  plugins, and other native dependencies can load.
- If startup reports that a different client library was loaded, inspect the application's
  order of API initialization. Changing `fb_client_library.value` after the first API load
  will not replace the cached API.

For exact driver behavior, check the target version's [configuration guide](https://firebird-driver.rtfd.io/usage-guide/configuration/index.md), [database guide](https://firebird-driver.rtfd.io/usage-guide/databases/index.md), and installed `firebird.driver.fbapi` implementation.
