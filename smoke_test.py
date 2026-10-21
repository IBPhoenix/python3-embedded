from importlib.metadata import entry_points


GROUP = "firebird.runtime.providers"


def main() -> None:
    providers = entry_points(group=GROUP)

    if not providers:
        raise SystemExit(f"No providers registered in {GROUP!r}")

    for entry_point in providers:
        print(f"Entry point: {entry_point.name}")
        print(f"  target: {entry_point.value}")

        provider_class = entry_point.load()
        provider = provider_class()

        print(f"  class: {provider_class.__module__}.{provider_class.__qualname__}")
        print(f"  name: {provider.name}")
        print(f"  package_version: {provider.package_version}")
        print(f"  firebird_version: {provider.firebird_version}")
        print(f"  root: {provider.root}")
        print(f"  client_library: {provider.client_library}")
        print(f"  firebird_log: {provider.firebird_log}")
        print(f"  capabilities: {sorted(provider.capabilities)}")
        print(f"  repr: {provider!r}")
        print()


if __name__ == "__main__":
    main()
