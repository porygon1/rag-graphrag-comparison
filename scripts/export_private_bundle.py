"""Export declared, field-selected scientific artefacts without model requests."""

import argparse
import hashlib
import json
import tomllib
import zipfile
from collections.abc import Iterable
from pathlib import Path, PureWindowsPath

REPO_ROOT = Path(__file__).resolve().parents[1]


def file_sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def bound_path(root: Path, filename: str) -> tuple[Path, str]:
    relative = Path(filename.replace("\\", "/"))
    if relative.is_absolute() or PureWindowsPath(filename).drive:
        raise ValueError("Use relative artifact paths inside the input folder.")
    if ".." in relative.parts:
        raise ValueError("Artifact paths must not contain parent segments.")
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Artifact paths must stay inside the input folder.")
    return path, relative.as_posix()


def select_fields(value, fields):
    """Keep explicitly allowed fields; apply a dictionary rule to list elements."""
    if fields is True or value is None:
        return value
    if not isinstance(fields, dict):
        raise ValueError("Field rules must be dictionaries or true.")
    if isinstance(value, list):
        return [select_fields(item, fields) for item in value]
    if not isinstance(value, dict):
        raise ValueError("A structured field rule needs an object or list.")
    return {
        key: select_fields(item, fields[key])
        for key, item in value.items()
        if key in fields
    }


def json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def selected_content(path: Path, rule: dict) -> Iterable[bytes]:
    if path.suffix.lower() in {".json", ".jsonl"}:
        fields = rule.get("fields")
        if not isinstance(fields, dict):
            raise ValueError("JSON files need an explicit positive field tree.")
        with path.open(encoding="utf-8") as handle:
            if path.suffix.lower() == ".json":
                yield json_bytes(select_fields(json.load(handle), fields))
            else:
                for line in handle:
                    if line.strip():
                        yield json_bytes(select_fields(json.loads(line), fields))
    else:
        if rule != {"copy": True}:
            raise ValueError("Non-JSON files need an explicit copy permission.")
        with path.open("rb") as handle:
            while block := handle.read(1024 * 1024):
                yield block


def write_member(archive: zipfile.ZipFile, name: str, blocks: Iterable[bytes]) -> dict:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    digest, size = hashlib.sha256(), 0
    with archive.open(info, "w") as handle:
        for block in blocks:
            handle.write(block)
            digest.update(block)
            size += len(block)
    return {"sha256": digest.hexdigest(), "size_bytes": size}


def code_binding() -> dict:
    files = [
        REPO_ROOT / name
        for name in (
            "README.md",
            "LICENSE",
            "CITATION.cff",
            "pyproject.toml",
            "uv.lock",
            ".python-version",
        )
    ]
    files += sorted((REPO_ROOT / "docs").rglob("*.md"))
    files += sorted(
        path
        for path in (REPO_ROOT / "docs/illustrations").rglob("*")
        if path.suffix in {".pdf", ".svg", ".json", ".py"}
    )
    files += sorted((REPO_ROOT / "src").rglob("*.py"))
    files += sorted((REPO_ROOT / "notebooks").glob("*.ipynb"))
    files.append(REPO_ROOT / "scripts/export_private_bundle.py")
    hashes = {
        path.relative_to(REPO_ROOT).as_posix(): file_sha256(path)
        for path in sorted(files)
    }
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        version = tomllib.load(handle)["project"]["version"]
    return {
        "version": version,
        "files": hashes,
        "sha256": hashlib.sha256(json_bytes(hashes)).hexdigest(),
    }


def export_bundle(
    input_dir: Path,
    output_zip: Path,
    selection: dict,
    result_dirs: Iterable[Path] = (),
) -> dict:
    """Verify every declared input, then export only explicitly selected roles.

    selection contains manifest_fields and roles. JSON/JSONL roles have a fields
    tree; non-JSON roles have copy=true. Optional record fields may be absent.
    Every selected role is required. Optional result_dirs contain the output
    manifests of notebooks 06, 06a and 06b. Input files remain unchanged.
    """
    if output_zip.resolve().is_relative_to(input_dir.resolve()):
        raise ValueError("Write the delivery archive outside the input folder.")
    manifest_path = input_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bound = {}
    for role, reference in manifest["artifacts"].items():
        path, name = bound_path(input_dir, reference["path"])
        if file_sha256(path) != reference["sha256"]:
            raise ValueError(f"Artifact checksum differs: {role}.")
        bound[role] = (path, name)
    roles = selection["roles"]
    if not roles or set(roles) - set(bound):
        raise ValueError("Every selected artifact role must be present.")
    fields = selection["manifest_fields"]
    if not isinstance(fields, dict) or "artifacts" in fields:
        raise ValueError("Select manifest fields separately from artifact references.")
    exported = select_fields(manifest, fields)
    exported["artifacts"] = {}
    entries = {}
    for role, rule in roles.items():
        path, name = bound[role]
        if name in {"manifest.json", "package_manifest.json"}:
            raise ValueError("Selected files must not replace the package manifests.")
        if name in entries and entries[name][1] != rule:
            raise ValueError("A shared file must have the same field selection.")
        entries[name] = (path, rule)
    package = {
        "schema_version": "private-companion-package-v1",
        "source_manifest_sha256": file_sha256(manifest_path),
        "selection_sha256": hashlib.sha256(json_bytes(selection)).hexdigest(),
        "code": code_binding(),
        "files": {},
    }
    for name, (path, rule) in sorted(entries.items()):
        digest, size = hashlib.sha256(), 0
        for block in selected_content(path, rule):
            digest.update(block)
            size += len(block)
        package["files"][name] = {
            "sha256": digest.hexdigest(),
            "size_bytes": size,
            "source_sha256": file_sha256(path),
        }
    for role in sorted(roles):
        path, name = bound[role]
        exported["artifacts"][role] = {
            "path": name,
            "sha256": package["files"][name]["sha256"],
        }
    manifest_content = json_bytes(exported)
    package["files"]["manifest.json"] = {
        "sha256": hashlib.sha256(manifest_content).hexdigest(),
        "size_bytes": len(manifest_content),
    }
    generated = {
        "manifest.json": manifest_content,
        "package_manifest.json": json_bytes(package),
    }
    result_sources = {}
    if result_dirs:
        result_roles = selection["result_roles"]
        input_sha = hashlib.sha256(manifest_content).hexdigest()
        for folder in result_dirs:
            result_manifest = json.loads(
                (folder / "analysis_manifest.json").read_text(encoding="utf-8")
            )
            if result_manifest["input_manifest_sha256"] != input_sha:
                raise ValueError("Calculate results from the exported input manifest.")
            for role, reference in result_manifest["artifacts"].items():
                path, _ = bound_path(folder, reference["path"])
                if file_sha256(path) != reference["sha256"]:
                    raise ValueError(f"Result checksum differs: {role}.")
                if role in result_roles:
                    if role in result_sources:
                        raise ValueError(f"Result role is declared twice: {role}.")
                    result_sources[role] = (path, reference["sha256"])
        if set(result_sources) != set(result_roles):
            raise ValueError("Every selected result role must be present.")
        result_binding = {
            "schema_version": "evaluation-outputs-v1",
            "input_manifest_sha256": input_sha,
            "artifacts": {},
        }
        for role, (path, source_sha) in sorted(result_sources.items()):
            name = "results/" + path.name
            rule = result_roles[role]
            if name in entries:
                raise ValueError("Result filenames must be unique.")
            entries[name] = (path, rule)
            content = b"".join(selected_content(path, rule))
            digest = hashlib.sha256(content).hexdigest()
            package["files"][name] = {
                "sha256": digest,
                "size_bytes": len(content),
                "source_sha256": source_sha,
            }
            result_binding["artifacts"][role] = {
                "path": path.name,
                "sha256": digest,
            }
        result_content = json_bytes(result_binding)
        generated["results/manifest.json"] = result_content
        package["files"]["results/manifest.json"] = {
            "sha256": hashlib.sha256(result_content).hexdigest(),
            "size_bytes": len(result_content),
        }
        generated["package_manifest.json"] = json_bytes(package)
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_zip.with_suffix(output_zip.suffix + ".tmp")
    with zipfile.ZipFile(temporary, "w") as archive:
        for name in sorted(set(entries) | set(generated)):
            blocks = (
                [generated[name]]
                if name in generated
                else selected_content(*entries[name])
            )
            observed = write_member(archive, name, blocks)
            if name in package["files"]:
                assert observed == {
                    key: package["files"][name][key] for key in ("sha256", "size_bytes")
                }, "Selected content changed while exporting."
    for role in roles:
        if file_sha256(bound[role][0]) != manifest["artifacts"][role]["sha256"]:
            raise ValueError(f"Input changed while exporting: {role}.")
    for role, (path, expected) in result_sources.items():
        if file_sha256(path) != expected:
            raise ValueError(f"Result changed while exporting: {role}.")
    temporary.replace(output_zip)
    return package


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument(
        "--results",
        nargs=3,
        type=Path,
        help="Output folders of notebooks 06, 06a and 06b, in that order.",
    )
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to((REPO_ROOT / "local").resolve()):
        parser.error(
            "Write delivery archives under the ignored repository local folder."
        )
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    package = export_bundle(args.input, args.output, selection, args.results or ())
    print(f"Exported {len(package['files'])} bound files to {args.output}.")


if __name__ == "__main__":
    main()
