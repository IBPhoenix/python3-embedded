---
name: firebird-embedded
description: Integrate a Python application with the firebird-embedded runtime provider, especially when selecting its client library for firebird-driver. Use for provider discovery, runtime paths, packaging, and embedded connection setup; not for building Firebird binaries.
---

# Integrate firebird-embedded

Use the installed `firebird-embedded` wheel as a source of native runtime files. It provides
no database connection API and has no dependency on `firebird-driver`. Applications own provider
selection, driver configuration, database credentials, and connection lifetime.

## Provider contract

Discover classes through `importlib.metadata.entry_points(group="firebird.runtime.providers")`
and instantiate the chosen class. The standard provider is registered under entry-point name
`firebird` as `firebird.embedded.provider:FirebirdProvider`; other distributions can register
other names. Inspect `provider.capabilities` when choosing by function, and use explicit
application configuration if multiple providers qualify. Do not assume the first entry point
is the desired runtime.

The standard provider exposes `name`, `package_version`, `firebird_version`, `root`, `client_library`,
and `capabilities`. `root` and `client_library` are `pathlib.Path` values. Accessing `client_library`
checks that the expected file exists and raises `RuntimeError` if it does not. The usual capabilities
are `client` and `embedded`. The first three components of the four-component package version
identify the bundled Firebird release; the fourth is the packaging revision.

Use the provider's paths instead of constructing paths into `site-packages` or guessing
the client library filename. Keep the top-level `firebird` package an implicit namespace
package so `firebird.base`, `firebird.driver`, and `firebird.embedded` can coexist.

## Integration workflow

1. Check the target application's Python, OS, and CPU architecture against the available wheel.
   Install `firebird-embedded` for the running platform; a wheel assembled on a different host
   still runs only on its tagged target platform.
2. Discover and select a provider. Report a missing provider, missing capability, or invalid
   `client_library` clearly rather than silently using a different runtime.
3. If using `firebird-driver`, read [driver integration](references/firebird-driver.md) for
   startup order, a concrete example, and verification.
4. Verify from an installed wheel when runtime behavior matters. An editable checkout lacks
   the build-hook-injected `firebird/embedded/runtime/` directory, so it cannot prove
   the installed runtime works.

For the current provider implementation and entry-point metadata, consult `src/firebird/embedded/provider.py`
and `pyproject.toml` in this project. Verify exact behavior against the installed package
version when integrating another checkout or release.
