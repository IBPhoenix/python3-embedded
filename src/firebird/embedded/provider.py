# SPDX-FileCopyrightText: 2026-present IBPhoenix <www.ibphoenix.com>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import sys
from importlib.metadata import version as distribution_version
from pathlib import Path


class FirebirdProvider:
    """Provider for the Firebird runtime bundled with firebird-embedded."""

    DISTRIBUTION_NAME = "firebird-embedded"

    @property
    def name(self) -> str:
        """Provider identifier."""
        return "firebird"

    @property
    def package_version(self) -> str:
        """Version of the firebird-embedded distribution."""
        return distribution_version(self.DISTRIBUTION_NAME)

    @property
    def firebird_version(self) -> str:
        """Firebird version supplied by this provider.

        The first three components of the package version correspond to
        the Firebird version. For example::

            5.0.4.0 -> 5.0.4
            5.0.4.1 -> 5.0.4
        """
        parts = self.package_version.split(".")
        return ".".join(parts[:3])

    @property
    def root(self) -> Path:
        """Root directory of the bundled Firebird runtime."""
        return Path(__file__).resolve().parent / "runtime"

    @property
    def client_library(self) -> Path:
        """Path to the Firebird client library."""
        if sys.platform == "win32":
            path = self.root / "fbclient.dll"
        elif sys.platform.startswith("linux"):
            path = self.root / f"libfbclient.so.{self.firebird_version}"
        else:
            raise RuntimeError(
                f"Unsupported platform: {sys.platform}"
            )

        if not path.is_file():
            raise RuntimeError(
                f"Firebird client library not found: {path}"
            )

        return path

    @property
    def firebird_log(self) -> Path:
        """Path to the bundled Firebird log."""
        path = self.root / "firebird.log"
        if not path.is_file():
            raise RuntimeError(f"Firebird log not found: {path}")
        return path

    @property
    def capabilities(self) -> frozenset[str]:
        """Capabilities provided by this runtime."""
        return frozenset({
            "client",
            "embedded",
        })

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"name={self.name!r}, "
            f"package_version={self.package_version!r}, "
            f"firebird_version={self.firebird_version!r})"
        )
