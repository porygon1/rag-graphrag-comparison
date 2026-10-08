"""Check document structure, exact Unicode partitions and source projection."""

import copy
import importlib.util
import unittest
from unittest import mock


@unittest.skipUnless(
    importlib.util.find_spec("docling_core") and importlib.util.find_spec("spacy"),
    "Install the structure extra to run native CHUNK checks.",
)
class StructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import spacy
        from docling_core.transforms.chunker.hybrid_chunker import HybridChunker

        from rag_comparison import config, structure

        cls.structure = structure
        cls.policy = config.STRUCTURE_POLICY
        cls.tokenizer = structure.FrozenTokenizer()
        cls.sentences = spacy.blank("de")
        cls.sentences.add_pipe(
            "sentencizer", config={"punct_chars": cls.policy["SENTENCE_PUNCTUATION"]}
        )
        cls.chunker = HybridChunker(
            tokenizer=cls.tokenizer,
            max_tokens=cls.policy["CAP"],
            merge_peers=True,
            delim=" ",
            serializer_provider=structure.SourceSerializerProvider(),
        )

    @staticmethod
    def page(raw_text, number=1, document="DEMO-DOC"):
        page = {
            "chunk_id": f"{document}-P{number}",
            "document_id": document,
            "page_number": number,
            "corpus_snapshot_id": "DEMO-SNAPSHOT",
            "text": " ".join(raw_text.split()),
        }
        raw = {"document_id": document, "page_number": number, "text": raw_text}
        return page, raw

    def split(self, *pairs):
        pages, raw = zip(*pairs, strict=True)
        spans, details = self.structure.build_partitions(
            pages,
            raw,
            chunker=self.chunker,
            encode=self.tokenizer.encode,
            sentence_splitter=self.sentences,
        )
        for page in pages:
            ranges = spans[page["chunk_id"]]
            self.assertEqual(
                "".join(page["text"][a:b] for a, b in ranges), page["text"]
            )
            self.assertTrue(all(a[1] == b[0] for a, b in zip(ranges, ranges[1:])))
            self.assertTrue(
                all(
                    0
                    < len(self.tokenizer.encode(page["text"][a:b]))
                    <= self.policy["CAP"]
                    for a, b in ranges
                )
            )
        return spans, details

    def test_contents_confirms_headings_and_keeps_adjacent_parent_child(self):
        toc = self.page(
            "Inhaltsverzeichnis\n1 Parent .... 2\n1.1 Child .... 2\n1.2 Other .... 2"
        )
        body = self.page(
            "Vorspann.\n1 Parent\n1.1 Child\nErster Text.\n1.2 Other\nZweiter Text.", 2
        )
        spans, details = self.split(toc, body)
        text = body[0]["text"]
        self.assertEqual(spans[toc[0]["chunk_id"]], [(0, len(toc[0]["text"]))])
        self.assertEqual(
            [start for start, end in spans[body[0]["chunk_id"]]],
            [0, text.index("1 Parent"), text.index("1.2 Other")],
        )
        self.assertEqual(sum(detail["toc"] for detail in details.values()), 1)

    def test_siblings_confirm_only_within_the_same_document(self):
        first = self.page("Intro\n2.1 Alpha\nText.")
        sibling = self.page("Intro\n2.2 Beta\nText.", 2)
        spans, _ = self.split(first, sibling)
        self.assertEqual(len(spans[first[0]["chunk_id"]]), 2)
        other_document = self.page("Intro\n2.2 Beta\nText.", document="OTHER-DOC")
        spans, _ = self.split(first, other_document)
        self.assertEqual(len(spans[first[0]["chunk_id"]]), 1)

    def test_heading_exclusions_and_pdf_lines_do_not_create_sections(self):
        pair = self.page(
            "Intro\n1.1 Alpha.\nText\n1.2 Beta;\nText\n1.3 Gamma 12\nText\n1.4 "
            + "L" * 241
            + "\nEnde"
        )
        spans, _ = self.split(pair)
        self.assertEqual(len(spans[pair[0]["chunk_id"]]), 1)
        wrapped = self.page("Erste umgebrochene\nZeile und zweite\nZeile.")
        spans, _ = self.split(wrapped)
        self.assertEqual(len(spans[wrapped[0]["chunk_id"]]), 1)

    def test_short_sections_are_retained(self):
        pair = self.page("X\n3.1 Kurz\nA\n3.2 Weiter\nB")
        spans, _ = self.split(pair)
        self.assertEqual(len(spans[pair[0]["chunk_id"]]), 2)
        self.assertEqual(
            pair[0]["text"][slice(*spans[pair[0]["chunk_id"]][0])], "X 3.1 Kurz A "
        )

    def test_list_introduction_stays_with_first_item(self):
        pair = self.page(
            "Einleitung.\na) " + "Wort " * 430 + "\nb) " + "Wort " * 430 + "\nc) Ende."
        )
        spans, _ = self.split(pair)
        self.assertEqual(
            spans[pair[0]["chunk_id"]][0], (0, pair[0]["text"].index("b)"))
        )
        self.assertEqual(len(spans[pair[0]["chunk_id"]]), 2)

    def test_long_contents_list_and_technical_text_keep_exact_source(self):
        toc = self.page(
            "Inhaltsverzeichnis\n1 A .... 1\n2 B .... 2\n3 C .... 3\n"
            + "Wert " * 430
            + "\n"
            + "Wert " * 430
        )
        spans, _ = self.split(toc)
        self.assertGreater(len(spans[toc[0]["chunk_id"]]), 1)
        pair = self.page("Ä 😀 e\u0301 " + "🔬" * 1700 + " Ende. Zweiter Satz.")
        spans, _ = self.split(pair)
        self.assertGreater(len(spans[pair[0]["chunk_id"]]), 1)
        page = pair[0]
        origin = {
            "chunk_id": page["chunk_id"],
            "origin_evidence_unit_ids": ["DEMO-EU"],
            "projection_status": "projected",
        }
        segments, edges, graph_inputs = self.structure.segment_page_record(
            page,
            origin,
            self.tokenizer.encode,
            self.tokenizer.decode,
            character_spans=spans[page["chunk_id"]],
        )
        self.assertEqual("".join(row["text"] for row in segments), page["text"])
        self.assertEqual(
            [row["text"] for row in graph_inputs], [row["text"] for row in segments]
        )
        self.assertTrue(
            all(edge["source_evidence_unit_ids"] == ["DEMO-EU"] for edge in edges)
        )
        self.assertEqual(
            [edge["target_artifact_id"] for edge in edges],
            [row["segment_id"] for row in segments],
        )

    def test_normalisation_duplicate_raw_pages_and_version_drift_are_rejected(self):
        page, raw = self.page("Ä  Text\nweiter")
        changed_page = copy.deepcopy(page)
        changed_page["text"] += " "
        with self.assertRaisesRegex(ValueError, "normalization mismatch"):
            self.split((changed_page, raw))
        with self.assertRaisesRegex(ValueError, "ambiguous raw page"):
            self.structure.map_lines([page], [raw, raw])
        with mock.patch.object(self.structure.metadata, "version", return_value="0.0"):
            with self.assertRaisesRegex(ValueError, "version differs"):
                self.split((page, raw))

    def test_missing_partition_or_ambiguous_origin_is_rejected(self):
        page, _ = self.page("Alpha beta gamma")
        origin = {
            "chunk_id": page["chunk_id"],
            "origin_evidence_unit_ids": ["DEMO-EU"],
            "projection_status": "projected",
        }
        with self.assertRaisesRegex(ValueError, "document-confirmed partition"):
            self.structure.segment_page_record(
                page, origin, self.tokenizer.encode, self.tokenizer.decode
            )
        ambiguous = origin | {"origin_evidence_unit_ids": ["DEMO-EU", "OTHER-EU"]}
        with self.assertRaisesRegex(ValueError, "exactly one"):
            self.structure.segment_page_record(
                page,
                ambiguous,
                self.tokenizer.encode,
                self.tokenizer.decode,
                character_spans=[(0, len(page["text"]))],
            )

    def test_gap_overlap_or_incomplete_page_partition_is_rejected(self):
        page, _ = self.page("Alpha beta gamma")
        origin = {
            "chunk_id": page["chunk_id"],
            "origin_evidence_unit_ids": ["DEMO-EU"],
            "projection_status": "projected",
        }
        invalid_partitions = [
            [(0, 5), (4, len(page["text"]))],
            [(0, 4), (5, len(page["text"]))],
            [(1, len(page["text"]))],
            [(0, len(page["text"]) - 1)],
            [(0, len(page["text"]) + 1)],
        ]
        for spans in invalid_partitions:
            with self.subTest(spans=spans), self.assertRaises(ValueError):
                self.structure.segment_page_record(
                    page,
                    origin,
                    self.tokenizer.encode,
                    self.tokenizer.decode,
                    character_spans=spans,
                )


if __name__ == "__main__":
    unittest.main()
