# firebird-embedded

`firebird-embedded` packages prebuilt Firebird client and embedded-engine files
as platform-specific Python wheels. It does not compile Firebird. The Python
distribution is `firebird-embedded`; its import package is
`firebird.embedded` within the implicit `firebird` namespace package.

The [agent skill](skills/firebird-embedded/SKILL.md) describes provider discovery
and integration with `firebird-driver` for applications using the installed wheel.

## Architecture

The small Python package exposes `firebird.embedded.provider.FirebirdProvider`
through the `firebird.runtime.providers` entry-point group. Consumers discover
the provider class, instantiate it, and obtain the installed runtime root,
client-library and log paths, versions, and capabilities. The provider does not depend
on `firebird-driver` or configure it.

Each wheel contains the Python package at `firebird/embedded/` and one
prepared native runtime at `firebird/embedded/runtime/`. `hatch_build.py`
selects that runtime using `FIREBIRD_EMBEDDED_TARGET` and adds it to the wheel.
The runtime includes an initially empty `firebird.log` at its root.
The wheels have `py3-none-<platform>` tags because the native files do not
depend on a particular Python ABI. A build host can assemble wheels for other
platforms from their prebuilt Firebird archives.

## Native runtime requirements

The Linux wheels use these tags so PyPI accepts them and installers select
the matching architecture and glibc version:

| Target | Platform tag |
| --- | --- |
| `linux32` | `manylinux_2_26_i686` |
| `linux64` | `manylinux_2_17_x86_64` |
| `linux32-arm` | `manylinux_2_17_armv7l` |
| `linux64-arm` | `manylinux_2_17_aarch64` |

Firebird 5 also requires the target system to provide `libtommath.so.1` and
its dependencies. This library is not bundled in the wheels. Install the
distribution package supplying it before using the embedded runtime; a
matching `manylinux` tag alone does not establish that it is present.

The Windows wheels include the Visual C++ runtime DLLs used by the supplied
Firebird binaries, along with the required ICU DLLs. The Windows installation
must provide the Universal CRT components those binaries import.

The package version has four components:
`<Firebird major>.<minor>.<revision>.<packaging revision>`. The first three
components must match the bundled Firebird release. The version is stored in
`src/firebird/embedded/__about__.py`.

## Repository layout

```text
.
├── make_embedded.py              # prepare configured local runtimes
├── hatch_build.py                # select one runtime for a wheel
├── pyproject.toml                # metadata, targets, and Hatch scripts
├── src/firebird/embedded/        # provider and package metadata
└── firebird-binaries/
    ├── assets/
    │   ├── linux32/             # cached Firebird release archives
    │   ├── linux64/
    │   ├── linux32-arm/
    │   ├── linux64-arm/
    │   ├── win32/
    │   ├── win64/
    │   ├── manifest/             # this branch's <target>.txt mappings
    │   └── override/             # optional branch-local replacements
    └── <version>/<target>/       # prepared runtime directories
```

The cached archives and prepared runtimes are local build assets and are
ignored by Git. Only this branch's flat manifests and overrides are tracked.
Each manifest selects only the files needed for its embedded runtime, including files later
replaced by an override. A preparation record at `<version>/.prepared.json`
lets the wheel hook reject incomplete or mismatched runtimes.

The `fb-3.0` and `fb-4.0` branches build Linux x86/amd64 and Windows x86/x64
wheels. Their published ARM kits target Android, not Linux. `fb-5.0` builds all
six targets. `main` is a build-disabled scaffold for Firebird 6, with no
release manifests or target settings.

## Prepare local runtimes

Run these commands from the repository root. Use Python 3.11 or newer:

```bash
python3.11 make_embedded.py
```

The script reads `firebird-version` and target settings from `pyproject.toml`.
An optional version argument must match that configuration. It checks
`firebird-binaries/assets/<target>/` for matching archives, downloads missing
ones from the corresponding Firebird GitHub release, and prepares the versioned
runtime trees from the branch-local manifests and optional overrides. It
installs all configured targets together, with rollback on failure.

For a new Firebird release, update the first three components of
`src/firebird/embedded/__about__.py` and the
`tool.firebird-embedded.firebird-version` setting in `pyproject.toml` before
building wheels. Also update `tool.hatch.build.directory` with new Firebird version so
produced wheels are stored in separate directory. Update archive suffixes and branch-local
manifests if an upstream kit changes. `make_embedded.py` does not edit package metadata.

## Build wheels

From the repository root, run one Hatch script per target:

```bash
hatch run linux32
hatch run linux64
hatch run linux32-arm
hatch run linux64-arm
hatch run win32
hatch run win64
```

The scripts are defined in the `default` Hatch environment. Each runs a wheel
build with its own `FIREBIRD_EMBEDDED_TARGET`; the wheels are written to
`dist/<Firebird-version>/`. A target's versioned prepared directory and
preparation record must exist before its wheel is built. Run only the scripts
configured on the branch.
