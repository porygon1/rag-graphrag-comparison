"""Check portable delivery, explicit field selection and preserved scientific values."""

import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from rag_comparison.artifacts import verify_artifacts
from rag_comparison.metrics import ndcg_at_k

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/export_private_bundle.py"
SPEC = importlib.util.spec_from_file_location("export_private_bundle", SCRIPT)
assert SPEC and SPEC.loader
EXPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXPORT)


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.input = self.root / "source"
        self.input.mkdir()
        self.output = self.root / "delivery.zip"
        self.rows = [
            {
                "question_id": "Q1",
                "hits": [
                    {"rank": 1, "evidence_id": "A", "score": 0.9, "debug": "discard"},
                    {"rank": 2, "evidence_id": "A", "score": None},
                    {"rank": 3, "evidence_id": None, "score": 0.0},
                ],
                "qrels": {"A": 2, "B": 0},
                "accepted": {"grade": 0, "reason": None, "internal_note": "discard"},
                "change_log": "discard",
            },
            {"question_id": "Q2", "hits": [], "qrels": {}, "optional": "discard"},
        ]
        (self.input / "ranking.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in self.rows), encoding="utf-8"
        )
        (self.input / "reference.json").write_text(
            json.dumps(
                {
                    "ranking": ["A", "B", "C", "D", "E"],
                    "qrels": {"A": 2, "B": 0, "C": 1, "D": 2, "E": 0, "F": 1},
                    "proposal": "discard",
                }
            ),
            encoding="utf-8",
        )
        (self.input / "vectors.npy").write_bytes(b"\x93NUMPY\x00\x00\xff\x01")
        (self.input / "unselected.txt").write_text("discard", encoding="utf-8")
        self.manifest = {
            "schema_version": "evaluation-inputs-v1",
            "metadata": {"dataset_kind": "private", "debug_id": "discard"},
            "absolute_source": "discard",
            "artifacts": {
                role: {"path": name, "sha256": EXPORT.file_sha256(self.input / name)}
                for role, name in {
                    "retrieval": "ranking.jsonl",
                    "reference": "reference.json",
                    "vectors": "vectors.npy",
                    "unselected": "unselected.txt",
                }.items()
            },
        }
        self.write_manifest()
        self.selection = {
            "manifest_fields": {
                "schema_version": True,
                "metadata": {"dataset_kind": True},
            },
            "roles": {
                "retrieval": {
                    "fields": {
                        "question_id": True,
                        "hits": {"rank": True, "evidence_id": True, "score": True},
                        "qrels": True,
                        "accepted": {"grade": True, "reason": True},
                    }
                },
                "reference": {"fields": {"ranking": True, "qrels": True}},
                "vectors": {"copy": True},
            },
        }

    def write_manifest(self):
        (self.input / "manifest.json").write_text(
            json.dumps(self.manifest), encoding="utf-8"
        )

    def export(self):
        return EXPORT.export_bundle(self.input, self.output, self.selection)

    def test_positive_nested_selection_preserves_order_nulls_and_binary_bytes(self):
        source_hashes = {p.name: EXPORT.file_sha256(p) for p in self.input.iterdir()}
        package = self.export()
        with zipfile.ZipFile(self.output) as archive:
            self.assertEqual(archive.namelist(), sorted(archive.namelist()))
            self.assertNotIn("unselected.txt", archive.namelist())
            data = [
                json.loads(line) for line in archive.read("ranking.jsonl").splitlines()
            ]
            self.assertEqual([row["question_id"] for row in data], ["Q1", "Q2"])
            self.assertEqual([row["rank"] for row in data[0]["hits"]], [1, 2, 3])
            self.assertEqual(
                [row["evidence_id"] for row in data[0]["hits"]], ["A", "A", None]
            )
            self.assertEqual(data[0]["hits"][1]["score"], None)
            self.assertIs(type(data[0]["hits"][2]["score"]), float)
            self.assertEqual(data[0]["accepted"], {"grade": 0, "reason": None})
            self.assertEqual(data[0]["qrels"], self.rows[0]["qrels"])
            self.assertEqual(
                archive.read("vectors.npy"), (self.input / "vectors.npy").read_bytes()
            )
            for name in archive.namelist():
                if name.endswith((".json", ".jsonl")):
                    self.assertNotIn(b"discard", archive.read(name))
            self.assertEqual(json.loads(archive.read("package_manifest.json")), package)
        self.assertEqual(
            source_hashes, {p.name: EXPORT.file_sha256(p) for p in self.input.iterdir()}
        )

    def test_repeat_zip_is_identical_and_moved_extraction_recalculates_metric(self):
        self.export()
        first = self.output.read_bytes()
        self.export()
        self.assertEqual(first, self.output.read_bytes())
        extracted = self.root / "extracted"
        with zipfile.ZipFile(self.output) as archive:
            archive.extractall(extracted)
        moved = extracted.rename(self.root / "another_location")
        manifest = json.loads((moved / "manifest.json").read_text(encoding="utf-8"))
        paths = verify_artifacts(moved, manifest)
        reference = json.loads(paths["reference"].read_text(encoding="utf-8"))
        self.assertEqual(ndcg_at_k(reference["ranking"], reference["qrels"]), 0.801747)
        package = json.loads(
            (moved / "package_manifest.json").read_text(encoding="utf-8")
        )
        for name, record in package["files"].items():
            self.assertEqual(EXPORT.file_sha256(moved / name), record["sha256"])
            self.assertEqual((moved / name).stat().st_size, record["size_bytes"])
        self.assertEqual(
            package["code"]["files"]["scripts/export_private_bundle.py"],
            EXPORT.file_sha256(SCRIPT),
        )
        for name in ("LICENSE", "CITATION.cff"):
            self.assertEqual(
                package["code"]["files"][name],
                EXPORT.file_sha256(SCRIPT.parent.parent / name),
            )
        self.assertEqual(
            package["source_manifest_sha256"],
            EXPORT.file_sha256(self.input / "manifest.json"),
        )

    def test_workflow_documents_and_sources_change_the_code_binding(self):
        code = self.root / "code"
        code.mkdir()
        for name in (
            "README.md",
            "LICENSE",
            "CITATION.cff",
            "uv.lock",
            ".python-version",
            "scripts/export_private_bundle.py",
        ):
            path = code / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"code")
        (code / "pyproject.toml").write_text(
            '[project]\nversion = "0.1.0"\n', encoding="utf-8"
        )
        documents = code / "docs/illustrations"
        documents.mkdir(parents=True)
        selected = (
            "workflow.pdf",
            "workflow.svg",
            "guide.json",
            "build.py",
            "README.md",
        )
        for name in (*selected, "render-cache.png"):
            (documents / name).write_bytes(b"first")
        with patch.object(EXPORT, "REPO_ROOT", code):
            first = EXPORT.code_binding()
            for name in selected:
                relative = "docs/illustrations/" + name
                self.assertEqual(
                    first["files"][relative], EXPORT.file_sha256(documents / name)
                )
            self.assertNotIn("docs/illustrations/render-cache.png", first["files"])
            (documents / "workflow.pdf").write_bytes(b"changed")
            second = EXPORT.code_binding()
        self.assertNotEqual(first["sha256"], second["sha256"])
        self.assertNotEqual(
            first["files"]["docs/illustrations/workflow.pdf"],
            second["files"]["docs/illustrations/workflow.pdf"],
        )

    def test_corrupted_unselected_file_is_not_a_valid_input(self):
        (self.input / "unselected.txt").write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "checksum differs"):
            self.export()
        self.assertFalse(self.output.exists())

    def test_missing_selected_role_and_missing_declared_file_fail(self):
        self.selection["roles"]["missing"] = {"copy": True}
        with self.assertRaisesRegex(ValueError, "selected artifact role"):
            self.export()
        del self.selection["roles"]["missing"]
        (self.input / "reference.json").unlink()
        with self.assertRaises(FileNotFoundError):
            self.export()

    def test_absolute_and_escaping_paths_are_rejected(self):
        for name in [
            str(self.root / "outside.json"),
            "../outside.json",
            "C:\\outside.json",
        ]:
            with self.subTest(name=name):
                self.manifest["artifacts"]["reference"]["path"] = name
                self.write_manifest()
                with self.assertRaisesRegex(ValueError, "paths"):
                    self.export()

    def test_json_requires_explicit_fields_and_unknown_top_fields_are_removed(self):
        self.selection["roles"]["retrieval"] = {"copy": True}
        with self.assertRaisesRegex(ValueError, "positive field tree"):
            self.export()
        self.selection["roles"]["retrieval"] = {"fields": {"question_id": True}}
        self.export()
        with zipfile.ZipFile(self.output) as archive:
            data = [
                json.loads(line) for line in archive.read("ranking.jsonl").splitlines()
            ]
            self.assertEqual(data, [{"question_id": "Q1"}, {"question_id": "Q2"}])

    def test_export_cannot_overwrite_an_input(self):
        with self.assertRaisesRegex(ValueError, "outside the input folder"):
            EXPORT.export_bundle(
                self.input, self.input / "ranking.jsonl", self.selection
            )

    def result_fixture(self):
        self.export()
        with zipfile.ZipFile(self.output) as archive:
            input_sha = EXPORT.hashlib.sha256(archive.read("manifest.json")).hexdigest()
        folder = self.root / "results"
        folder.mkdir()
        result = folder / "reported_tables.json"
        result.write_text(
            json.dumps(
                {
                    "tables": [{"grade": 0, "score": None, "debug": "discard"}],
                    "history": "discard",
                }
            ),
            encoding="utf-8",
        )
        manifest = {
            "input_manifest_sha256": input_sha,
            "artifacts": {
                "reported_tables": {
                    "path": result.name,
                    "sha256": EXPORT.file_sha256(result),
                }
            },
        }
        self.selection["result_roles"] = {
            "reported_tables": {"fields": {"tables": {"grade": True, "score": True}}},
        }
        (folder / "analysis_manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        return folder, manifest

    def test_results_preserve_zero_na_and_bind_exact_selected_inputs(self):
        folder, _ = self.result_fixture()
        package = EXPORT.export_bundle(
            self.input, self.output, self.selection, [folder]
        )
        first = self.output.read_bytes()
        EXPORT.export_bundle(self.input, self.output, self.selection, [folder])
        self.assertEqual(first, self.output.read_bytes())
        with zipfile.ZipFile(self.output) as archive:
            data = json.loads(archive.read("results/reported_tables.json"))
            self.assertEqual(data, {"tables": [{"grade": 0, "score": None}]})
            result_binding = json.loads(archive.read("results/manifest.json"))
            self.assertEqual(
                result_binding["input_manifest_sha256"],
                EXPORT.hashlib.sha256(archive.read("manifest.json")).hexdigest(),
            )
            self.assertEqual(
                result_binding["artifacts"]["reported_tables"]["sha256"],
                package["files"]["results/reported_tables.json"]["sha256"],
            )

    def test_stale_result_binding_and_changed_result_are_rejected(self):
        folder, manifest = self.result_fixture()
        manifest["input_manifest_sha256"] = "0" * 64
        (folder / "analysis_manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "exported input manifest"):
            EXPORT.export_bundle(self.input, self.output, self.selection, [folder])
        with zipfile.ZipFile(self.output) as archive:
            manifest["input_manifest_sha256"] = EXPORT.hashlib.sha256(
                archive.read("manifest.json")
            ).hexdigest()
        (folder / "analysis_manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        (folder / "reported_tables.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Result checksum"):
            EXPORT.export_bundle(self.input, self.output, self.selection, [folder])


if __name__ == "__main__":
    unittest.main()
