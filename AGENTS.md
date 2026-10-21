# AGENTS.md

## Project Overview

`firebird-embedded` packages Firebird embedded/client runtime binaries as platform-specific Python wheels.

The Python distribution name is:

```text
firebird-embedded
```

The import package is:

```text
firebird.embedded
```

The project follows the namespace-package convention used by the Firebird Python ecosystem:

```text
firebird.base
firebird.driver
firebird.lib
firebird.embedded
```

The top-level `firebird` package is an implicit namespace package. Do not add `src/firebird/__init__.py`.

The package contains a small amount of Python code plus prebuilt Firebird native binaries. It does not compile Firebird itself.

## Versioning

Package versions use four numeric components:

```text
<firebird-major>.<firebird-minor>.<firebird-release>.<package-revision>
```

Example:

```text
5.0.4.0
```

means Firebird 5.0.4, initial packaging revision.

A packaging-only correction increments the fourth component:

```text
5.0.4.1
```

On release branches, the first three components must identify the bundled
Firebird version. The disabled `main` branch uses `0.0.0.0` until a release is
configured.

The package version is stored in:

```text
src/firebird/embedded/__about__.py
```

and is read by Hatch.

Do not duplicate the package version elsewhere unless required by packaging metadata.

## Project Layout

Expected structure:

```text
.
├── AGENTS.md
├── README.md
├── hatch_build.py
├── make_embedded.py
├── pyproject.toml
├── firebird-binaries/
│   ├── assets/
│   │   ├── linux32/
│   │   ├── linux64/
│   │   ├── linux32-arm/
│   │   ├── linux64-arm/
│   │   ├── win32/
│   │   ├── win64/
│   │   ├── manifest/
│   │   │   └── <target>.txt
│   │   └── override/
│   │       └── <optional replacement files>
│   └── <version>/
│       ├── .prepared.json
│       └── <target>/
└── src/
    └── firebird/
        └── embedded/
            ├── __about__.py
            ├── __init__.py
            └── provider.py
```

The versioned platform directories under `firebird-binaries` contain the
prepared embedded runtimes used by the wheel build hook. They include the
selected client library, embedded engine and plugins, internationalization and
time zone data, and configuration files. They are generated from the release
archives in `assets`, not complete regular Firebird installations.

The asset directories named after platforms cache the original Firebird release
archives. `assets/manifest` contains one mapping file per configured
platform on the current branch, and `assets/override` optionally contains files
copied after manifest extraction. The root can also contain `embedded-*.tar.gz`,
`embedded-*.zip`, and `files*.chk` local artifacts; these are not inputs to
`make_embedded.py` or the wheel hook.

The prepared runtimes and downloaded archives are ignored by Git; the branch-local
manifest and override files are tracked.

Do not copy these binaries permanently into `src/firebird/embedded`.

The build hook injects the selected runtime into the generated wheel under:

```text
firebird/embedded/runtime/
```

## Build System

The project uses:

```text
Hatch
Hatchling
uv
```

Hatchling is the build backend.

Prepare or refresh the embedded runtime directories with:

```text
make_embedded.py
```

The Hatchling wheel build is controlled by:

```text
hatch_build.py
```

Platform-specific wheels are assembled from prebuilt Firebird distributions.

This is packaging, not cross-compilation. A Linux host may build Windows, Linux x86, or Linux ARM wheels because the native binaries already exist.

## Build Targets

Supported target names are:

```text
linux32
linux64
linux32-arm
linux64-arm
win32
win64
```

Firebird 3 and 4 branches configure four targets: Linux x86/amd64 and Windows
x86/x64. Their official ARM archives target Android. Firebird 5 configures all
six targets. Each release branch tracks only its own manifests and target
settings. `main` is a scaffold for Firebird 6 and must keep `build-enabled =
false` and no release targets until archives and manifests are available.

A target is selected using:

```text
FIREBIRD_EMBEDDED_TARGET
```

Example:

```bash
FIREBIRD_EMBEDDED_TARGET=linux64 hatch build -t wheel
```

The build hook must fail clearly if no target is specified or if the target is unknown.

Do not infer the target from `sys.platform`. The build host and wheel target may be different.

## Binary Source Location

By default, the prepared runtime directories used by the wheel build are under:

```text
firebird-binaries/<version>/<target>/
```

The root may be overridden using:

```text
FIREBIRD_EMBEDDED_BINARY_ROOT
```

Relative paths must be resolved against the project root, not against the current working directory.

`make_embedded.py` uses the project-local `firebird-binaries` tree. The
`FIREBIRD_EMBEDDED_BINARY_ROOT` override applies to the wheel build hook, not
to this preparation script.

## Preparing Embedded Distributions

Run from the project root:

```bash
python3 make_embedded.py
```

The script reads the Firebird version and configured targets from
`pyproject.toml`. An optional three-component version argument must match the
configured version. It does not select a target from the host platform.

Source archive filenames have this form:

```text
Firebird-<MAJOR>.<MINOR>.<REVISION>.<BUILD>-<PKGVER><ARCHIVE-SUFFIX>
```

The script looks for matching archives in `firebird-binaries/assets/<target>`.
If any are missing, it discovers their full filenames from the Firebird GitHub
release tagged `v<MAJOR>.<MINOR>.<REVISION>` and downloads them from:

```text
https://github.com/FirebirdSQL/firebird/releases/download/v<MAJOR>.<MINOR>.<REVISION>/<FILENAME>
```

It rejects missing or ambiguous matches. Linux archives contain a nested
`buildroot.tar.gz`; manifest source paths refer to its `opt/firebird` tree.
Windows ZIP manifest source paths refer directly to members of the ZIP.

Each nonblank, noncomment manifest line has the form:

```text
<target-relative-path>=<source-relative-path>
```

Numeric filename components use positional placeholders. The source path
captures `{0}`, `{1}`, and so on; the target path uses those captured values.
For example:

```text
libfbclient.so.{0}.{1}.{2}=opt/firebird/lib/libfbclient.so.{0}.{1}.{2}
libtomcrypt.so.{0}=opt/firebird/lib/libtomcrypt.so.{0}.{1}.{2}
```

The second mapping uses the first number of the source filename for the
shorter target filename. Each source pattern must match exactly one regular
file in its archive. Keep overridden files in the manifests when they also
exist in the source archive; overrides are applied afterward.

The script stages all configured runtimes before replacing the contents of the
versioned platform directories. It preserves those directories, removes their
old contents, installs the staged files, and attempts to restore old contents
if installation fails. A `.prepared.json` record under the version directory
identifies the prepared version and targets; the wheel hook requires it.
Linux library aliases needed in wheels must be mapped
to real source files rather than relying on archive symlinks.

The script does not change package metadata. When preparing a new Firebird
version, update `src/firebird/embedded/__about__.py` and the
`tool.firebird-embedded.firebird-version` value in `pyproject.toml` before
building wheels so metadata matches the bundled runtime.

## Wheel Structure

The resulting wheel must contain:

```text
firebird/
    embedded/
        __about__.py
        __init__.py
        provider.py
        runtime/
            ...
```

Do not produce:

```text
embedded/
```

at the wheel root.

For Hatchling, the wheel package root should therefore preserve the `firebird` namespace, typically by configuring:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/firebird"]
```

The native runtime is added by the build hook using `force_include`.

## Wheel Tags

The package contains native binaries but no Python ABI-specific extension module.

Wheel tags should therefore normally use:

```text
py3-none-<platform>
```

Examples:

```text
py3-none-win32
py3-none-win_amd64
py3-none-linux_i686
py3-none-linux_x86_64
py3-none-linux_armv7l
py3-none-linux_aarch64
```

Do not generate CPython-specific tags such as:

```text
cp313-cp313-...
```

unless Python ABI-dependent native code is introduced in the future.

Linux wheels may later use appropriate `manylinux` tags, but only after the supplied Firebird binaries have been validated for the corresponding ABI level.

Do not claim a `manylinux` compatibility level without verification.

## Linux Shared Libraries

Official Firebird Linux distributions may contain symbolic links between shared-library names.

Wheel installation does not reliably preserve POSIX symlink semantics.

Do not depend on symlinks surviving wheel creation and installation.

If necessary, normalize the Firebird runtime during preparation so the wheel contains real files under every filename required at runtime.

When determining which names are necessary, inspect ELF metadata such as:

```text
DT_NEEDED
SONAME
RPATH
RUNPATH
```

and account for libraries loaded dynamically by Firebird.

Avoid modifying the installed package at runtime merely to create symlinks.

Installed `site-packages` should be treated as immutable.

## Provider Interface

The package exposes its runtime through a provider class:

```text
firebird.embedded.provider.FirebirdProvider
```

It is registered through the entry-point group:

```text
firebird.runtime.providers
```

with an entry point named:

```text
firebird
```

Example:

```toml
[project.entry-points."firebird.runtime.providers"]
firebird = "firebird.embedded.provider:FirebirdProvider"
```

The entry point advertises the provider class, not an instance and not individual functions.

Consumers load the class and instantiate it.

Example:

```python
from importlib.metadata import entry_points

for ep in entry_points(group="firebird.runtime.providers"):
    provider_class = ep.load()
    provider = provider_class()
```

The design intentionally allows multiple runtime providers to coexist, for example:

```text
firebird
phoenixvault
```

Do not hard-code `firebird-embedded` into consumer packages when provider discovery can be used instead.

## FirebirdProvider Responsibilities

`FirebirdProvider` should remain lightweight and should not depend on `firebird-driver`.

It describes the installed runtime.

Expected public information includes:

```text
name
package_version
firebird_version
root
client_library
capabilities
```

Typical capabilities for the standard Firebird package are:

```text
client
embedded
```

The provider should return filesystem paths to installed native resources.

The runtime root is:

```text
firebird/embedded/runtime
```

The provider should validate important paths such as the client library and raise a clear error if the installed package is incomplete.

Do not put `firebird-driver` configuration logic into the provider unless there is a strong reason to do so.

The provider supplies runtime information; consumers decide how to use it.

## Specialized Runtime Providers

The provider mechanism is intentionally generic.

Specialized distributions such as PhoenixVault should implement their own provider and register it in the same entry-point group.

For example:

```toml
[project.entry-points."firebird.runtime.providers"]
phoenixvault = "firebird.phoenixvault.provider:PhoenixVaultProvider"
```

Consumers should prefer capability inspection over provider-name-specific branching where possible.

Example:

```python
if "embedded" in provider.capabilities:
    ...
```

rather than:

```python
if provider.name == "firebird":
    ...
```

## Dependencies

Keep runtime Python dependencies minimal.

`firebird-embedded` should not depend on `firebird-driver` merely to expose a bundled Firebird client.

If a shared provider protocol is later added to `firebird-base`, depending on `firebird-base` may be appropriate.

Until then, structural compatibility is preferred over unnecessary package dependencies.

## Development Environment

Normal Hatch development environments install the project in editable mode.

Editable installs do not contain the build-hook-generated Firebird runtime under:

```text
firebird/embedded/runtime
```

This is expected.

Do not assume that `hatch shell` represents the contents of a built wheel.

Python-only code can be developed and tested in editable mode, but tests involving the bundled Firebird runtime must use a non-editable installation.

## Smoke Testing

Runtime smoke tests must exercise the actual built package rather than the editable source tree.

A dedicated Hatch environment may use:

```toml
[tool.hatch.envs.smoke]
dev-mode = false
```

The target must be defined when Hatch installs the project:

```bash
FIREBIRD_EMBEDDED_TARGET=linux64 hatch env remove smoke
FIREBIRD_EMBEDDED_TARGET=linux64 hatch -e smoke run python smoke_test.py
```

Recreate the environment when testing a newly built package version or changed runtime contents.

The smoke test should discover providers through the registered entry-point group rather than importing `FirebirdProvider` directly.

It should at minimum verify:

```text
entry-point discovery
provider loading
provider instantiation
package version
Firebird version
runtime root
client library path
capabilities
```

Tests that actually load or use embedded Firebird are stronger than tests that merely check file existence.

## Package Registry

Hatch is configured to use `uv` as its installer.

Private package registry behavior should be configured through Hatch configuration, not by modifying global pip configuration.

Do not assume pip is used internally.

Do not add project-specific instructions that require changing the developer's global pip or uv configuration unless explicitly requested.

## manylinux Validation

A Linux wheel may be tagged `manylinux` only after validation of all bundled ELF binaries.

Use `auditwheel show` as an initial compatibility check.

Also inspect all shipped ELF binaries, including:

```text
libfbclient
embedded engine
plugins
intl modules
bundled ICU libraries
other native helpers
```

Pay particular attention to required versions of:

```text
GLIBC
GLIBCXX
CXXABI
```

A successful `auditwheel show` result is useful but not sufficient for Firebird because some components may be loaded dynamically.

Validate the runtime on a system or container matching the claimed minimum glibc level and perform a real embedded database operation.

Do not use `auditwheel repair` blindly. It may relocate libraries or rewrite runtime paths in ways that conflict with Firebird's expected directory layout.

## General Coding Rules

Use modern Python supported by the project's declared minimum version.

Prefer:

```python
from __future__ import annotations
```

where appropriate.

Use `pathlib.Path` for filesystem paths.

Use clear exceptions with actionable messages for build and installation failures.

Do not silently fall back to a different target or binary distribution.

Do not infer release-critical information when it can be explicitly configured.

Keep wheel assembly logic in `hatch_build.py` and runtime preparation logic in
`make_embedded.py`.

Keep runtime-discovery logic in `firebird.embedded.provider`.

Avoid platform-specific behavior in unrelated modules.

Do not modify bundled Firebird binaries unnecessarily.

Preserve the upstream Firebird runtime layout unless there is a packaging-specific reason to normalize it.

## Changes to Packaging

When changing packaging logic, verify the generated wheel rather than reasoning only from the source tree.

Inspect at least:

```text
wheel filename
wheel platform tag
wheel RECORD
installed package layout
entry-point metadata
runtime directory contents
client library resolution
```

The expected Python package path inside the wheel is always:

```text
firebird/embedded/
```

and the bundled Firebird distribution belongs under:

```text
firebird/embedded/runtime/
```
