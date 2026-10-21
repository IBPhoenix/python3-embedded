# Changelog

## Development

### Added

- Prepare the `FirebirdProvider` interface to expose a bundled `firebird.log`
  when a future runtime release is configured.
- Add versioned runtime preparation, branch-local manifest support, a wheel
  smoke test, and integration guidance for `firebird-driver`.

### Changed

- Keep `main` as a release-neutral scaffold with builds disabled until a
  Firebird 6 release and its manifests are available.
- Use upstream Firebird configuration files instead of custom overrides.
