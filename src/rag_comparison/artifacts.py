"""Check the relative file bindings of a stored scientific run."""

import hashlib
import json
from pathlib import Path


def read_jsonl(path: Path) -> list[dict]:
    """Read ordered UTF-8 records; malformed JSON remains a visible error."""
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def verify_artifacts(root: Path, manifest: dict) -> dict[str, Path]:
    """Return bound paths after checking containment and SHA256 for every file.

    Each artifacts entry has a relative path and a sha256 value. Missing files,
    changed bytes and references outside the run folder remain visible errors.
    """
    paths = {}
    for role, reference in manifest["artifacts"].items():
        relative_path = Path(reference["path"])
        if relative_path.is_absolute():
            raise ValueError("Artifact paths must be relative to their run folder.")
        path = (root / relative_path).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError("Artifact paths must stay inside their run folder.")
        if hashlib.sha256(path.read_bytes()).hexdigest() != reference["sha256"]:
            raise ValueError(f"Artifact checksum differs: {role}.")
        paths[role] = path
    return paths


def write_analysis_manifest(
    root: Path, input_manifest: Path, files: dict[str, str]
) -> dict:
    """Bind calculated output files to their exact input manifest with SHA256."""
    manifest = {
        "schema_version": "evaluation-outputs-v1",
        "input_manifest_sha256": hashlib.sha256(
            input_manifest.read_bytes()
        ).hexdigest(),
        "artifacts": {
            role: {
                "path": filename,
                "sha256": hashlib.sha256((root / filename).read_bytes()).hexdigest(),
            }
            for role, filename in files.items()
        },
    }
    verify_artifacts(root, manifest)
    (root / "analysis_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest
