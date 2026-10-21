# SPDX-FileCopyrightText: 2026-present IBPhoenix <www.ibphoenix.com>
#
# SPDX-License-Identifier: MIT

"""Build the six embedded runtimes from official Firebird release archives."""

from __future__ import annotations

import argparse
import ast
import io
import json
import re
import shutil
import string
import tarfile
import tempfile
import tomllib
import urllib.error
import urllib.request
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import BinaryIO

RELEASE_API = "https://api.github.com/repos/FirebirdSQL/firebird/releases"
RELEASE_DOWNLOAD = "https://github.com/FirebirdSQL/firebird/releases/download"
REQUEST_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "firebird-embedded-builder",
}


def archive_pattern(version: str, suffix: str) -> re.Pattern[str]:
    return re.compile(
        rf"Firebird-{re.escape(version)}\.[0-9]+-[0-9]+{re.escape(suffix)}\Z"
    )


def one_match(names: list[str], pattern: re.Pattern[str], description: str) -> str:
    matches = [name for name in names if pattern.fullmatch(name)]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one {description}, found {len(matches)}: {matches}"
        )
    return matches[0]


def release_assets(version: str) -> list[str]:
    """Find release filenames; the build and package revision are not known locally."""
    try:
        request = urllib.request.Request(
            f"{RELEASE_API}/tags/v{version}", headers=REQUEST_HEADERS
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            release = json.load(response)
        release_id = release["id"]
        names: list[str] = []
        page = 1
        while True:
            request = urllib.request.Request(
                f"{RELEASE_API}/{release_id}/assets?per_page=100&page={page}",
                headers=REQUEST_HEADERS,
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                assets = json.load(response)
            names.extend(asset["name"] for asset in assets)
            if len(assets) < 100:
                return names
            page += 1
    except (urllib.error.URLError, ValueError, KeyError) as exc:
        raise RuntimeError(
            f"Cannot list Firebird {version} release assets: {exc}"
        ) from exc


def download(version: str, filename: str, cache_dir: Path) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    destination = cache_dir / filename
    url = f"{RELEASE_DOWNLOAD}/v{version}/{filename}"
    temporary = destination.with_name(destination.name + ".download")
    try:
        request = urllib.request.Request(url, headers=REQUEST_HEADERS)
        with (
            urllib.request.urlopen(request, timeout=60) as response,
            temporary.open("wb") as output,
        ):
            shutil.copyfileobj(response, output)
        temporary.replace(destination)
    except (OSError, urllib.error.URLError) as exc:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"Cannot download {url}: {exc}") from exc
    return destination


def source_archives(
    version: str, assets_root: Path, targets: dict[str, dict]
) -> dict[str, Path]:
    found: dict[str, Path] = {}
    missing: list[str] = []
    for target, settings in targets.items():
        cache_dir = assets_root / target
        names = (
            [path.name for path in cache_dir.iterdir() if path.is_file()]
            if cache_dir.is_dir()
            else []
        )
        matches = [
            name
            for name in names
            if archive_pattern(version, settings["archive-suffix"]).fullmatch(name)
        ]
        if len(matches) > 1:
            raise RuntimeError(
                f"Multiple cached {target} archives for {version}: {matches}"
            )
        if matches:
            found[target] = cache_dir / matches[0]
        else:
            missing.append(target)

    if missing:
        names = release_assets(version)
        # Resolve every missing platform before downloading anything.
        filenames = {
            target: one_match(
                names,
                archive_pattern(version, targets[target]["archive-suffix"]),
                f"{target} release archive",
            )
            for target in missing
        }
        for target, filename in filenames.items():
            print(f"Downloading {filename}")
            found[target] = download(version, filename, assets_root / target)
    return found


def template_pattern(template: str) -> tuple[re.Pattern[str], int]:
    parts: list[str] = []
    seen: set[int] = set()
    for literal, field, spec, conversion in string.Formatter().parse(template):
        parts.append(re.escape(literal))
        if field is not None:
            if not field.isdecimal() or spec or conversion:
                raise ValueError(f"Invalid numeric placeholder in {template!r}")
            index = int(field)
            if index in seen:
                parts.append(f"(?P=n{index})")
            else:
                parts.append(f"(?P<n{index}>[0-9]+)")
                seen.add(index)
    if seen != set(range(len(seen))):
        raise ValueError(f"Placeholder indexes must start at zero: {template!r}")
    return re.compile("".join(parts) + r"\Z"), len(seen)


def relative_path(name: str) -> Path:
    path = PurePosixPath(name)
    if not name or name.startswith("/") or ".." in path.parts or "\\" in name:
        raise ValueError(f"Invalid manifest path: {name!r}")
    return Path(*path.parts)


@contextmanager
def archive_files(archive: Path) -> Iterator[tuple[dict[str, object], object]]:
    """Expose regular files from a Windows ZIP or Linux buildroot tarball."""
    if archive.name.endswith(".zip"):
        with zipfile.ZipFile(archive) as source:
            members = {
                info.filename: info for info in source.infolist() if not info.is_dir()
            }
            yield members, source
    else:
        with tarfile.open(archive, "r:gz") as outer:
            members = {
                member.name.removeprefix("./"): member
                for member in outer
                if member.isfile()
            }
            buildroots = [
                member
                for name, member in members.items()
                if name.endswith("/buildroot.tar.gz")
            ]
            if len(buildroots) > 1:
                raise RuntimeError(f"Multiple buildroot.tar.gz members in {archive}")
            if not buildroots:
                yield members, outer
            else:
                stream = outer.extractfile(buildroots[0])
                assert stream is not None
                with tarfile.open(
                    fileobj=io.BytesIO(stream.read()), mode="r:gz"
                ) as source:
                    nested = {
                        member.name.removeprefix("./"): member
                        for member in source
                        if member.isfile()
                    }
                    yield nested, source


def write_member(source: object, member: object, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(source, zipfile.ZipFile):
        with source.open(member) as input_file, destination.open("wb") as output:
            shutil.copyfileobj(input_file, output)
    else:
        assert isinstance(source, tarfile.TarFile)
        assert isinstance(member, tarfile.TarInfo)
        input_file: BinaryIO | None = source.extractfile(member)
        assert input_file is not None
        with input_file, destination.open("wb") as output:
            shutil.copyfileobj(input_file, output)
        destination.chmod(member.mode & 0o777)


def stage_target(
    target: str, archive: Path, assets_root: Path, destination: Path
) -> int:
    manifest = assets_root / "manifest" / f"{target}.txt"
    if not manifest.is_file():
        raise RuntimeError(f"Missing manifest: {manifest}")
    count = 0
    written: set[Path] = set()
    with archive_files(archive) as (members, source):
        names = list(members)
        for line_number, line in enumerate(
            manifest.read_text(encoding="utf-8").splitlines(), 1
        ):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if line.count("=") != 1:
                raise ValueError(
                    f"Invalid manifest entry {manifest}:{line_number}: {line!r}"
                )
            target_template, source_template = line.split("=", 1)
            pattern, count_values = template_pattern(source_template)
            source_name = one_match(
                names,
                pattern,
                f"source for {manifest}:{line_number} ({source_template})",
            )
            values = tuple(
                pattern.fullmatch(source_name).group(f"n{index}")
                for index in range(count_values)
            )
            target_name = target_template.format(*values)
            path = relative_path(target_name)
            if path in written:
                raise RuntimeError(f"Duplicate target {path} in {manifest}")
            write_member(source, members[source_name], destination / path)
            written.add(path)
            count += 1

    override_root = assets_root / "override"
    if override_root.is_dir():
        for override in override_root.rglob("*"):
            if override.is_file():
                path = override.relative_to(override_root)
                output = destination / path
                output.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(override, output)
    return count


def remove_entry(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def install_staged(
    binary_root: Path, stage: Path, backup: Path, targets: dict[str, dict]
) -> None:
    """Keep target directories and restore old contents if installation fails."""
    moved_old: dict[str, list[str]] = {target: [] for target in targets}
    moved_new: dict[str, list[str]] = {target: [] for target in targets}
    old_record = binary_root / ".prepared.json"
    saved_record = backup / ".prepared.json"
    record_installed = False
    try:
        for target in targets:
            destination = binary_root / target
            if destination.is_symlink():
                raise RuntimeError(
                    f"Runtime directory must not be a symlink: {destination}"
                )
            destination.mkdir(exist_ok=True)
            saved = backup / target
            saved.mkdir(parents=True)
            for child in list(destination.iterdir()):
                shutil.move(str(child), saved / child.name)
                moved_old[target].append(child.name)
            for child in list((stage / target).iterdir()):
                shutil.move(str(child), destination / child.name)
                moved_new[target].append(child.name)
        if old_record.exists():
            shutil.move(str(old_record), saved_record)
        shutil.move(str(stage / ".prepared.json"), old_record)
        record_installed = True
    except Exception:
        if record_installed:
            old_record.unlink()
        if saved_record.exists():
            shutil.move(str(saved_record), old_record)
        for target in targets:
            destination = binary_root / target
            saved = backup / target
            if saved.is_dir():
                for name in moved_new[target]:
                    remove_entry(destination / name)
                for name in moved_old[target]:
                    shutil.move(str(saved / name), destination / name)
        raise


def make_embedded(version: str | None = None, project_root: Path | None = None) -> None:
    if project_root is None:
        project_root = Path(__file__).resolve().parent
    with (project_root / "pyproject.toml").open("rb") as stream:
        config = tomllib.load(stream)["tool"]["firebird-embedded"]
    if not config.get("build-enabled", False):
        raise RuntimeError("Runtime preparation is disabled for this branch")
    configured_version = config["firebird-version"]
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", configured_version):
        raise ValueError(f"Invalid configured Firebird version: {configured_version!r}")
    if version is not None and version != configured_version:
        raise ValueError(
            f"Requested Firebird {version} differs from configured {configured_version}"
        )
    version = configured_version
    about = ast.parse((project_root / "src/firebird/embedded/__about__.py").read_text())
    package_version = next(
        node.value.value
        for node in about.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(name, ast.Name) and name.id == "__version__"
            for name in node.targets
        )
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )
    if ".".join(package_version.split(".")[:3]) != version:
        raise RuntimeError(
            f"Package version {package_version} does not match Firebird {version}"
        )
    targets = config["targets"]
    binary_root = project_root / "firebird-binaries"
    assets_root = binary_root / "assets"
    archives = source_archives(version, assets_root, targets)
    binary_root = binary_root / version
    binary_root.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix=".make-embedded-", dir=binary_root))
    cleanup = True
    try:
        stage = scratch / "stage"
        backup = scratch / "backup"
        for target, archive in archives.items():
            count = stage_target(target, archive, assets_root, stage / target)
            print(f"Prepared {target}: {count} files")
        (stage / ".prepared.json").write_text(
            json.dumps(
                {"firebird-version": version, "targets": list(targets)}, indent=2
            )
            + "\n"
        )
        try:
            install_staged(binary_root, stage, backup, targets)
        except Exception as exc:
            # Preserve the backup if a rollback itself fails.
            if backup.exists() and any(
                path.is_dir() and any(path.iterdir()) for path in backup.iterdir()
            ):
                cleanup = False
                raise RuntimeError(
                    f"Installation failed; backup retained at {backup}"
                ) from exc
            raise
    finally:
        if cleanup:
            shutil.rmtree(scratch)
    print(f"Built all {len(targets)} embedded runtimes for Firebird {version}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "version",
        nargs="?",
        help="Optional Firebird version; must match pyproject.toml",
    )
    arguments = parser.parse_args()
    try:
        make_embedded(arguments.version)
    except (
        OSError,
        RuntimeError,
        ValueError,
        tarfile.TarError,
        zipfile.BadZipFile,
    ) as exc:
        parser.exit(1, f"make_embedded: {exc}\n")


if __name__ == "__main__":
    main()
