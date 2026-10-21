# Changelog

All notable changes to `firebird-embedded` are recorded here. Package versions
use the Firebird release as their first three components and a packaging revision
as the fourth.

## [4.0.7.2] - 2026-10-15

### Added

- Bundle an empty `firebird.log` in every target wheel and expose its path through
  `FirebirdProvider.firebird_log`.

### Fixed

- Reject a prepared runtime that lacks its bundled log before building a wheel.

## [4.0.7.1] - 2026-10-15

### Added

- Include UDR and trace plugins in the Firebird 4 wheels.

### Changed

- Keep only Firebird 4 build inputs on this branch and use branch-local manifests
  and overrides.
- Use upstream Firebird configuration files instead of custom overrides.

## [4.0.7.0] - 2026-10-13

### Added

- Package Firebird 4.0.7 client and embedded runtimes for Linux x86 and x64,
  and Windows x86 and x64.
- Provide versioned runtime preparation, platform-specific wheels, and a
  discoverable `FirebirdProvider`.
- Add a wheel smoke test and integration guidance for `firebird-driver`.

### Changed

- Select build inputs from the configured Firebird release and keep prepared
  runtimes outside the Python source package.
