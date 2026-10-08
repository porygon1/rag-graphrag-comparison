"""Integrity and portability of stored-run artifact bindings."""

import hashlib
import tempfile
import unittest
from pathlib import Path

from rag_comparison.artifacts import verify_artifacts


class ArtifactTests(unittest.TestCase):
    def test_relative_binding_survives_run_folder_move(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            root.mkdir()
            (root / "data.txt").write_bytes(b"recorded source")
            manifest = {
                "artifacts": {
                    "source": {
                        "path": "data.txt",
                        "sha256": hashlib.sha256(b"recorded source").hexdigest(),
                    }
                }
            }
            moved = root.rename(Path(directory) / "delivered")
            paths = verify_artifacts(moved, manifest)
            self.assertEqual(paths["source"].read_bytes(), b"recorded source")

    def test_changed_bytes_cannot_reuse_a_saved_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data.txt").write_bytes(b"changed")
            manifest = {
                "artifacts": {
                    "source": {
                        "path": "data.txt",
                        "sha256": hashlib.sha256(b"original").hexdigest(),
                    }
                }
            }
            with self.assertRaisesRegex(ValueError, "checksum differs"):
                verify_artifacts(root, manifest)

    def test_absolute_and_parent_paths_are_not_portable_bindings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "run"
            root.mkdir()
            for path in (str(root / "data.txt"), "../data.txt"):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    verify_artifacts(
                        root, {"artifacts": {"source": {"path": path, "sha256": ""}}}
                    )


if __name__ == "__main__":
    unittest.main()
