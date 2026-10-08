"""Persist embedding batches and resume with the same ordered inputs and model."""

import hashlib
import json
from collections.abc import Callable, Sequence
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from rag_comparison.config import (
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_DIMENSION,
    EMBEDDING_MODEL,
)


def embed_with_checkpoint(
    item_ids: Sequence[str],
    texts: Sequence[str],
    embed_fn: Callable[[list[str]], Sequence[Sequence[float]]],
    checkpoint_dir: Path,
    *,
    model: str = EMBEDDING_MODEL,
    dimension: int = EMBEDDING_DIMENSION,
    batch_size: int = EMBEDDING_BATCH_SIZE,
) -> NDArray[np.float32]:
    """Return raw Float32 vectors in input order, reusing committed batches.

    The callback supplies one embedding per text in the same order. A checkpoint
    binds ordered IDs and exact text hashes, model, dimension and batch size.
    Changed inputs or damaged batches raise ValueError before another request.
    Callback errors propagate; only fully written batches advance the checkpoint.
    """
    if not texts or len(item_ids) != len(texts) or len(set(item_ids)) != len(item_ids):
        raise ValueError("Provide nonempty texts with one unique ID per text.")
    if batch_size < 1 or dimension < 1:
        raise ValueError("Batch size and dimension must be positive.")
    ordered_inputs = [
        [item_id, hashlib.sha256(text.encode("utf-8")).hexdigest()]
        for item_id, text in zip(item_ids, texts, strict=True)
    ]
    identity = {
        "ordered_input_sha256": hashlib.sha256(
            json.dumps(ordered_inputs, ensure_ascii=False).encode("utf-8")
        ).hexdigest(),
        "embedding_model": model,
        "dimension": dimension,
        "batch_size": batch_size,
    }
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = checkpoint_dir / "checkpoint.json"
    checkpoint = {"identity": identity, "next_index": 0, "batches": []}
    if checkpoint_path.exists():
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        if checkpoint["identity"] != identity:
            raise ValueError("Checkpoint inputs, model or batch settings differ.")

    matrices = []
    next_index = 0
    for batch in checkpoint["batches"]:
        path = checkpoint_dir / batch["path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != batch["sha256"]:
            raise ValueError("Checkpoint batch checksum differs.")
        matrix = np.load(path, allow_pickle=False)
        if (
            batch["start"] != next_index
            or batch["stop"] > len(texts)
            or matrix.shape != (batch["stop"] - batch["start"], dimension)
            or matrix.dtype != np.float32
        ):
            raise ValueError("Checkpoint batches do not form the saved input prefix.")
        matrices.append(matrix)
        next_index = batch["stop"]
    if next_index != checkpoint["next_index"]:
        raise ValueError("Checkpoint progress differs from its saved batches.")

    for start in range(next_index, len(texts), batch_size):
        stop = min(start + batch_size, len(texts))
        matrix = np.asarray(embed_fn(list(texts[start:stop])), dtype=np.float32)
        if (
            matrix.shape != (stop - start, dimension)
            or not np.isfinite(matrix).all()
            or not np.all(np.linalg.norm(matrix, axis=1) > 0)
        ):
            raise ValueError("Embedding batch has invalid shape or vector values.")
        path = checkpoint_dir / f"batch_{start:05d}_{stop:05d}.npy"
        temporary = path.with_suffix(".npy.tmp")
        with temporary.open("wb") as handle:
            np.save(handle, matrix, allow_pickle=False)
        temporary.replace(path)
        checkpoint["batches"].append(
            {
                "path": path.name,
                "start": start,
                "stop": stop,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
        checkpoint["next_index"] = stop
        temporary = checkpoint_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(checkpoint, indent=2) + "\n", encoding="utf-8")
        temporary.replace(checkpoint_path)
        matrices.append(matrix)

    return np.vstack(matrices)
