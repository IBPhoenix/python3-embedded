# SPDX-FileCopyrightText: 2026-present IBPhoenix <www.ibphoenix.com>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import os
import re
import tomllib
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    """Build hook for platform-specific firebird-embedded wheels."""

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        if self.target_name != "wheel":
            return

        project_root = Path(self.root)
        pyproject_path = project_root / "pyproject.toml"

        with pyproject_path.open("rb") as f:
            pyproject = tomllib.load(f)

        config = pyproject["tool"]["firebird-embedded"]
        if not config.get("build-enabled", False):
            raise RuntimeError("Wheel builds are disabled for this branch")
        firebird_version = config["firebird-version"]
        if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", firebird_version):
            raise RuntimeError(
                f"Invalid configured Firebird version: {firebird_version!r}"
            )
        package_version = self.metadata.version
        if ".".join(package_version.split(".")[:3]) != firebird_version:
            raise RuntimeError(
                f"Package version {package_version} does not match Firebird {firebird_version}"
            )

        target_name = os.environ.get("FIREBIRD_EMBEDDED_TARGET")
        if not target_name:
            raise RuntimeError(
                "FIREBIRD_EMBEDDED_TARGET must be specified when building "
                "a firebird-embedded wheel"
            )

        targets = config["targets"]

        try:
            target = targets[target_name]
        except KeyError:
            valid = ", ".join(sorted(targets))
            raise RuntimeError(
                f"Unknown FIREBIRD_EMBEDDED_TARGET {target_name!r}. "
                f"Valid targets: {valid}"
            ) from None

        binary_root = Path(
            os.environ.get(
                "FIREBIRD_EMBEDDED_BINARY_ROOT",
                config["binary-root"],
            )
        ).expanduser()

        if not binary_root.is_absolute():
            binary_root = project_root / binary_root

        version_root = binary_root / firebird_version
        source_dir = version_root / target["directory"]

        if not source_dir.is_dir():
            raise RuntimeError(
                f"Firebird runtime directory does not exist: {source_dir}"
            )
        record_path = version_root / ".prepared.json"
        try:
            record = json.loads(record_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise RuntimeError(
                f"Missing or invalid preparation record: {record_path}"
            ) from exc
        if record.get(
            "firebird-version"
        ) != firebird_version or target_name not in record.get("targets", []):
            raise RuntimeError(
                f"Preparation record does not match Firebird {firebird_version} target {target_name}: {record_path}"
            )
        client = (
            "fbclient.dll"
            if target_name.startswith("win")
            else f"libfbclient.so.{firebird_version}"
        )
        if not (source_dir / client).is_file():
            raise RuntimeError(f"Client library is missing: {source_dir / client}")
        if not (source_dir / "firebird.log").is_file():
            raise RuntimeError(f"Firebird log is missing: {source_dir / 'firebird.log'}")

        wheel_tag = target["wheel-tag"]

        # Add the complete pre-built Firebird runtime tree to the wheel.
        #
        # A directory supplied through force_include has its contents
        # recursively mapped below the destination path.
        build_data["force_include"][str(source_dir)] = "firebird/embedded/runtime"

        # Although the Python code is pure Python, this distribution contains
        # platform-specific native libraries.
        build_data["pure_python"] = False

        # The native binaries do not depend on a particular CPython ABI.
        build_data["tag"] = wheel_tag
