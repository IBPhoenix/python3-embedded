# Changelog

All notable changes to `firebird-embedded` are recorded here. Package versions
use the Firebird release as their first three components and a packaging revision
as the fourth.

## [5.0.4.2] - 2026-10-15

### Added

- Bundle an empty `firebird.log` in every target wheel and expose its path through
  `FirebirdProvider.firebird_log`.

### Fixed

- Reject a prepared runtime that lacks its bundled log before building a wheel.

## [5.0.4.1] - 2026-10-15

### Added

- Include UDR, trace, and profiler plugins in the Firebird 5 wheels.

### Changed

- Keep only Firebird 5 build inputs on this branch and use branch-local manifests
  and overrides.
- Use upstream Firebird configuration files instead of custom overrides.

## [5.0.4.0] - 2026-10-13

### Added

- Package Firebird 5.0.4 client and embedded runtimes for Linux x86, x64, ARM32,
  and ARM64, and Windows x86 and x64.
- Provide versioned runtime preparation, platform-specific wheels, and a
  discoverable `FirebirdProvider`.
- Add older Windows runtime support DLLs, a wheel smoke test, and integration
  guidance for `firebird-driver`.

### Changed

- Select build inputs from the configured Firebird release and keep prepared
  runtimes outside the Python source package.
