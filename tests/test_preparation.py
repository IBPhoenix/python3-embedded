"""Regression checks for branch-local manifests and versioned runtimes."""

from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from make_embedded import install_staged, make_embedded, stage_target


class PreparationTests(unittest.TestCase):
    def test_requested_version_must_match_branch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "pyproject.toml").write_text(
                '[tool.firebird-embedded]\nfirebird-version = "4.0.7"\nbuild-enabled = true\n'
            )
            with self.assertRaisesRegex(ValueError, "differs from configured"):
                make_embedded("5.0.4", root)

    def test_manifest_must_match_exactly_one_archive_member(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = root / "manifest"
            manifest.mkdir(parents=True)
            (manifest / "win32.txt").write_text("client.dll=fbclient{0}.dll\n")
            archive = root / "kit.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("fbclient1.dll", b"one")
                output.writestr("fbclient2.dll", b"two")
            with self.assertRaisesRegex(RuntimeError, "Expected one source"):
                stage_target("win32", archive, root, root / "stage")

    def test_branch_local_manifest_and_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = root / "manifest"
            manifest.mkdir()
            (manifest / "win32.txt").write_text("plugin.dll=plugin.dll\n")
            override = root / "override"
            override.mkdir()
            (override / "plugin.dll").write_bytes(b"override")
            (override / "firebird.log").touch()
            archive = root / "kit.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("plugin.dll", b"upstream")
            stage = root / "stage"
            self.assertEqual(stage_target("win32", archive, root, stage), 1)
            self.assertEqual((stage / "plugin.dll").read_bytes(), b"override")
            self.assertEqual((stage / "firebird.log").read_bytes(), b"")

    def test_missing_branch_local_manifest_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / "kit.zip"
            with zipfile.ZipFile(archive, "w") as output:
                output.writestr("plugin.dll", b"upstream")
            with self.assertRaisesRegex(RuntimeError, "Missing manifest"):
                stage_target("win32", archive, root, root / "stage")

    def test_disabled_branch_needs_no_release_settings(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "pyproject.toml").write_text(
                "[tool.firebird-embedded]\nbuild-enabled = false\n"
            )
            with self.assertRaisesRegex(RuntimeError, "disabled for this branch"):
                make_embedded(project_root=root)

    def test_failed_install_restores_old_runtime_and_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runtime = root / "3.0.14"
            old = runtime / "linux64"
            old.mkdir(parents=True)
            (old / "client").write_text("old")
            old_record = {"firebird-version": "3.0.14", "targets": ["linux64"]}
            (runtime / ".prepared.json").write_text(json.dumps(old_record))
            stage = root / "stage"
            new = stage / "linux64"
            new.mkdir(parents=True)
            (new / "client").write_text("new")
            # A missing staged record forces failure after the new files move.
            with self.assertRaises(FileNotFoundError):
                install_staged(runtime, stage, root / "backup", {"linux64": {}})
            self.assertEqual((old / "client").read_text(), "old")
            self.assertEqual(
                json.loads((runtime / ".prepared.json").read_text()), old_record
            )


if __name__ == "__main__":
    unittest.main()
