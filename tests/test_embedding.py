"""Check checkpoint reuse, input binding and failure recovery without model calls."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, call

import numpy as np

from rag_comparison.embedding import embed_with_checkpoint

ITEM_IDS = ["A", "B", "C", "D", "E"]
TEXTS = ["1", "2", "3", "4", "5"]
EXPECTED_VECTORS = [[1, -1], [2, -2], [3, -3], [4, -4], [5, -5]]


def synthetic_embeddings(texts):
    return [[float(text), -float(text)] for text in texts]


class EmbeddingCheckpointTests(unittest.TestCase):
    def test_failed_batch_resumes_remaining_inputs_in_order(self):
        with TemporaryDirectory() as directory:
            checkpoint_dir = Path(directory)
            interrupted = Mock(
                side_effect=[[[1, -1], [2, -2]], RuntimeError("Batch interrupted.")]
            )
            with self.assertRaises(RuntimeError):
                embed_with_checkpoint(
                    ITEM_IDS,
                    TEXTS,
                    interrupted,
                    checkpoint_dir,
                    model="synthetic-model",
                    dimension=2,
                    batch_size=2,
                )
            self.assertEqual(
                interrupted.call_args_list, [call(["1", "2"]), call(["3", "4"])]
            )
            saved = json.loads((checkpoint_dir / "checkpoint.json").read_text())
            self.assertEqual(saved["next_index"], 2)
            self.assertEqual(len(saved["batches"]), 1)

            resumed = Mock(side_effect=synthetic_embeddings)
            vectors = embed_with_checkpoint(
                ITEM_IDS,
                TEXTS,
                resumed,
                checkpoint_dir,
                model="synthetic-model",
                dimension=2,
                batch_size=2,
            )
            self.assertEqual(resumed.call_args_list, [call(["3", "4"]), call(["5"])])
            np.testing.assert_array_equal(vectors, EXPECTED_VECTORS)
            self.assertEqual(vectors.dtype, np.float32)

    def test_completed_checkpoint_needs_no_new_request(self):
        with TemporaryDirectory() as directory:
            checkpoint_dir = Path(directory)
            embed_with_checkpoint(
                ITEM_IDS,
                TEXTS,
                synthetic_embeddings,
                checkpoint_dir,
                model="synthetic-model",
                dimension=2,
                batch_size=2,
            )
            unexpected = Mock(side_effect=AssertionError("No request expected."))
            vectors = embed_with_checkpoint(
                ITEM_IDS,
                TEXTS,
                unexpected,
                checkpoint_dir,
                model="synthetic-model",
                dimension=2,
                batch_size=2,
            )
            unexpected.assert_not_called()
            np.testing.assert_array_equal(vectors, EXPECTED_VECTORS)

    def test_changed_inputs_or_settings_are_rejected_before_request(self):
        with TemporaryDirectory() as directory:
            checkpoint_dir = Path(directory)
            arguments = {
                "item_ids": ITEM_IDS,
                "texts": TEXTS,
                "model": "synthetic-model",
                "dimension": 2,
                "batch_size": 2,
            }
            embed_with_checkpoint(
                **arguments,
                embed_fn=synthetic_embeddings,
                checkpoint_dir=checkpoint_dir,
            )
            changes = {
                "text": {"texts": ["changed", "2", "3", "4", "5"]},
                "order": {"item_ids": ITEM_IDS[::-1], "texts": TEXTS[::-1]},
                "model": {"model": "different-model"},
                "dimension": {"dimension": 3},
                "batch_size": {"batch_size": 3},
            }
            unexpected = Mock(side_effect=AssertionError("No request expected."))
            for label, changed in changes.items():
                with self.subTest(change=label), self.assertRaises(ValueError):
                    embed_with_checkpoint(
                        **(arguments | changed),
                        embed_fn=unexpected,
                        checkpoint_dir=checkpoint_dir,
                    )
                unexpected.assert_not_called()

    def test_invalid_vector_batch_does_not_advance_saved_progress(self):
        invalid_batches = {
            "row_count": [[3, -3]],
            "dimension": [[3, -3, 1], [4, -4, 1]],
            "nan": [[float("nan"), -3], [4, -4]],
            "infinity": [[3, float("inf")], [4, -4]],
            "zero_vector": [[0, 0], [4, -4]],
        }
        for label, invalid in invalid_batches.items():
            with self.subTest(batch=label), TemporaryDirectory() as directory:
                checkpoint_dir = Path(directory)
                embed = Mock(side_effect=[[[1, -1], [2, -2]], invalid])
                with self.assertRaises(ValueError):
                    embed_with_checkpoint(
                        ITEM_IDS,
                        TEXTS,
                        embed,
                        checkpoint_dir,
                        model="synthetic-model",
                        dimension=2,
                        batch_size=2,
                    )
                saved = json.loads((checkpoint_dir / "checkpoint.json").read_text())
                self.assertEqual(saved["next_index"], 2)
                self.assertEqual(len(saved["batches"]), 1)
                self.assertEqual(len(list(checkpoint_dir.glob("*.npy"))), 1)

    def test_corrupted_saved_batch_is_rejected_before_request(self):
        with TemporaryDirectory() as directory:
            checkpoint_dir = Path(directory)
            embed_with_checkpoint(
                ITEM_IDS,
                TEXTS,
                synthetic_embeddings,
                checkpoint_dir,
                model="synthetic-model",
                dimension=2,
                batch_size=2,
            )
            saved = json.loads((checkpoint_dir / "checkpoint.json").read_text())
            batch_path = checkpoint_dir / saved["batches"][0]["path"]
            batch_path.write_bytes(batch_path.read_bytes() + b"changed")
            unexpected = Mock(side_effect=AssertionError("No request expected."))
            with self.assertRaisesRegex(ValueError, "checksum"):
                embed_with_checkpoint(
                    ITEM_IDS,
                    TEXTS,
                    unexpected,
                    checkpoint_dir,
                    model="synthetic-model",
                    dimension=2,
                    batch_size=2,
                )
            unexpected.assert_not_called()


if __name__ == "__main__":
    unittest.main()
