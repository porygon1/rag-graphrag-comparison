"""Document structure and exact page provenance for the CHUNK condition."""

import hashlib
import importlib.metadata as metadata
import math
import re
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from functools import lru_cache

import tiktoken
from docling_core.experimental.serializer.base import (
    BaseSerializerProvider,
    BaseTextSerializer,
)
from docling_core.experimental.serializer.common import create_ser_result
from docling_core.transforms.chunker.hierarchical_chunker import ChunkingDocSerializer
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from docling_core.types.doc import DocItemLabel, DoclingDocument
from pydantic import BaseModel
from spacy.language import Language
from transformers import PreTrainedTokenizerBase

from rag_comparison import config

POLICY: dict = config.STRUCTURE_POLICY


class FrozenTokenizer(PreTrainedTokenizerBase):
    """Use o200k_base through the tokenizer interface required by HybridChunker."""

    def __init__(self):
        super().__init__(model_max_length=POLICY["CAP"])
        self.encoding = tiktoken.get_encoding(POLICY["ENCODING"])

    # HybridChunker requires this small tiktoken adapter, not a full HF tokenizer.
    def tokenize(self, text, **kwargs):  # pyright: ignore[reportIncompatibleMethodOverride]
        return self.encoding.encode(text)

    def encode(self, text, add_special_tokens=False, **kwargs):  # pyright: ignore[reportIncompatibleMethodOverride]
        return self.encoding.encode(text)

    def decode(self, tokens, **kwargs):  # pyright: ignore[reportIncompatibleMethodOverride]
        return self.encoding.decode(tokens)

    def token_byte_values(self):
        return self.encoding.token_byte_values()


class SourceTextSerializer(BaseModel, BaseTextSerializer):
    def serialize(self, *, item, **kwargs):
        return create_ser_result(text=item.text, span_source=item)


class SourceSerializerProvider(BaseSerializerProvider):
    def get_serializer(self, doc):
        return ChunkingDocSerializer(doc=doc, text_serializer=SourceTextSerializer())


def comparison(text: str) -> str:
    """Normalise titles for comparison; never alter stored source text."""
    # Comparison only: case and wrapped-title hyphenation; never stored as source.
    return re.sub(r"-\s+", "", " ".join(text.split())).casefold()


def map_lines(pages: Sequence[dict], raw_pages: Sequence[dict]) -> dict:
    """Locate raw PDF lines in the same whitespace-normalised page text."""
    raw = {}
    for row in raw_pages:
        key = row["document_id"], row["page_number"]
        if key in raw:
            raise ValueError("ambiguous raw page")
        raw[key] = row
    mapped = {}
    for p in pages:
        text = p["text"]
        r = raw[p["document_id"], p["page_number"]]["text"]
        if " ".join(r.split()) != text:
            raise ValueError("raw-to-frozen normalization mismatch")
        lines, position = [], 0
        for i, line in enumerate(r.splitlines()):
            value = " ".join(line.split())
            if not value:
                continue
            assert text[position : position + len(value)] == value
            lines.append(
                {
                    "line": i,
                    "text": value,
                    "start": position,
                    "end": position + len(value),
                }
            )
            position += len(value) + 1
        assert position - 1 == len(text)
        if p["chunk_id"] in mapped:
            raise ValueError("duplicate source page")
        mapped[p["chunk_id"]] = lines
    return mapped


def detect_structure(pages: Sequence[dict], lines: Mapping[str, list[dict]]) -> dict:
    """Confirm headings within each document using its pages and contents list."""
    num_re = re.compile(POLICY["HEADING_PATTERN"])
    documents = defaultdict(list)
    for p in pages:
        documents[p["document_id"]].append(p)
    details = {}
    for doc, pp in documents.items():
        pp = sorted(pp, key=lambda p: p["page_number"])

        def edgekey(text):
            return re.sub(r"\d+", "#", comparison(text))

        head_counts, foot_counts = Counter(), Counter()
        for p in pp:
            ls = lines[p["chunk_id"]]
            head_counts.update(
                {edgekey(x["text"]) for x in ls[: POLICY["EDGE_HEADER_LINES"]]}
            )
            foot_counts.update(
                {edgekey(x["text"]) for x in ls[-POLICY["EDGE_FOOTER_LINES"] :]}
            )
        threshold = max(
            POLICY["EDGE_MIN_PAGES"], math.ceil(POLICY["EDGE_PAGE_FRACTION"] * len(pp))
        )
        toc, catalog = set(), {}
        for p in pp:
            pid = p["chunk_id"]
            ls = lines[pid]
            header_end = 0
            for x in ls[: POLICY["EDGE_HEADER_LINES"]]:
                if head_counts[edgekey(x["text"])] < threshold:
                    break
                header_end = min(x["end"] + 1, len(p["text"]))
            footer_start = len(p["text"])
            for x in reversed(ls[-POLICY["EDGE_FOOTER_LINES"] :]):
                if foot_counts[edgekey(x["text"])] < threshold:
                    break
                footer_start = x["start"]
            content = [x for x in ls if header_end <= x["start"] < footer_start]
            direct = (
                any(
                    re.search(POLICY["TOC_TITLE_PATTERN"], x["text"], re.I)
                    for x in ls[: POLICY["TOC_TITLE_LINES"]]
                )
                or sum(bool(re.search(r"\.{3,}", x["text"])) for x in ls)
                >= POLICY["TOC_DOTTED_MIN_LINES"]
            )
            numbered = sum(bool(num_re.match(x["text"])) for x in content)
            trailing = sum(bool(re.search(r"\s\d{1,4}$", x["text"])) for x in content)
            continuation = (
                len(toc) > 0
                and pp.index(p) > 0
                and pp[pp.index(p) - 1]["chunk_id"] in toc
                and numbered >= POLICY["TOC_MIN_ENTRIES"]
                and trailing / max(1, len(content)) >= POLICY["TOC_ENTRY_LINE_FRACTION"]
            )
            history_rows = [
                x["start"]
                for x in content
                if re.match(POLICY["HISTORY_ROW_PATTERN"], x["text"], re.I)
            ]
            if len(history_rows) < POLICY["HISTORY_MIN_ROWS"]:
                history_rows = []
            details[pid] = {
                "header_end": header_end,
                "footer_start": footer_start,
                "toc": direct or continuation,
                "history_rows": history_rows,
                "headings": [],
            }
            if direct or continuation:
                toc.add(pid)
                for i, x in enumerate(content):
                    m = num_re.match(x["text"])
                    if not m:
                        continue
                    value = x["text"]
                    for y in content[i + 1 : i + POLICY["WRAPPED_TITLE_LINES"]]:
                        if re.search(r"\s\d{1,4}$", value) or num_re.match(y["text"]):
                            break
                        value += " " + y["text"]
                    value = re.sub(r"\s*\.{2,}.*$", "", value)
                    value = re.sub(r"\s+\d{1,4}$", "", value).strip()
                    full = num_re.match(value)
                    if full:
                        catalog[tuple(int(n) for n in full[1].split("."))] = comparison(
                            full[2]
                        )
        possible = []
        for p in pp:
            pid = p["chunk_id"]
            d, ls = details[pid], lines[pid]
            if d["toc"]:
                continue
            for i, x in enumerate(ls):
                if not d["header_end"] <= x["start"] < d["footer_start"]:
                    continue
                if d["history_rows"] and x["start"] >= d["history_rows"][0]:
                    # Version/date records and their chapter references form a
                    # change ledger, not new numbered document sections.
                    continue
                m = num_re.match(x["text"])
                if (
                    not m
                    or re.search(r"\.{3,}|\s\d{1,4}$", m[2])
                    or m[2].endswith((".", ",", ";"))
                ):
                    continue
                if len(x["text"]) > POLICY["HEADING_MAX_CHARS"]:
                    continue
                number = tuple(int(n) for n in m[1].split("."))
                title, end, confirmed = m[2], x["end"], False
                for j in range(POLICY["WRAPPED_TITLE_LINES"]):
                    if catalog.get(number) == comparison(title):
                        confirmed = True
                        break
                    if i + j + 1 >= len(ls) or num_re.match(ls[i + j + 1]["text"]):
                        break
                    title += " " + ls[i + j + 1]["text"]
                    end = ls[i + j + 1]["end"]
                if not confirmed:
                    title, end = m[2], x["end"]
                possible.append((pid, i, number, title, end, confirmed))
        keys = {x[2] for x in possible}
        list_labels = set()
        for left, right in zip(possible, possible[1:]):
            if (
                left[0] == right[0]
                and right[1] == left[1] + 1
                and left[2][:-1] == right[2][:-1]
                and right[2][-1] == left[2][-1] + 1
                and not left[5]
                and not right[5]
            ):
                # Adjacent numbered labels with no intervening body are list
                # elements, not independent section starts.
                list_labels.update(((left[0], left[1]), (right[0], right[1])))
        for pid, i, number, title, end, confirmed in possible:
            if (pid, i) in list_labels:
                continue
            sibling = any(
                number[:-1] + (v,) in keys for v in (number[-1] - 1, number[-1] + 1)
            )
            # Numbered question headings are observable text structure, not benchmark questions.
            question = any(
                "?" in x["text"]
                for x in lines[pid][i : i + POLICY["WRAPPED_TITLE_LINES"]]
            )
            top_sequence = (
                len(number) == 1 and sibling and sum(len(k) == 1 for k in keys) >= 3
            )
            if (
                confirmed
                or (len(number) >= 2 and sibling)
                or (
                    top_sequence
                    and not catalog
                    and (
                        question or lines[pid][i]["text"].split(" ", 1)[0].endswith(".")
                    )
                )
            ):
                details[pid]["headings"].append(
                    {
                        "number": number,
                        "start": lines[pid][i]["start"],
                        "end": end,
                        "line_index": i,
                        "confirmed_by": "toc" if confirmed else "numbered_structure",
                    }
                )
    return details


def build_partitions(
    pages: Sequence[dict],
    raw_pages: Sequence[dict],
    *,
    chunker: HybridChunker,
    encode: Callable[[str], Sequence[int]],
    sentence_splitter: Language,
) -> tuple[dict, dict]:
    """Build disjoint page partitions from document-confirmed structure.

    The caller creates the native HybridChunker and German sentencizer with
    STRUCTURE_POLICY. Returned offsets are half-open Unicode codepoint intervals.
    Every source character belongs to exactly one segment on its original page.
    Docling packs the structural units; its output is rebound to exact source text.
    Oversized units use the same technical split and whitespace reattachment.
    """
    for package, version in POLICY["VERSIONS"].items():
        if metadata.version(package) != version:
            raise ValueError("Structure package version differs: " + package)
    nlp = sentence_splitter
    nt = lru_cache(maxsize=20000)(lambda text: len(encode(text)))
    lines = map_lines(pages, raw_pages)
    details = detect_structure(pages, lines)
    markers = re.compile(POLICY["LIST_PATTERN"])
    result = {}
    for p in pages:
        text, pid = p["text"], p["chunk_id"]
        d, ls = details[pid], lines[pid]
        hh = d["headings"]
        starts = {0}
        for i, h in enumerate(hh):
            # Adjacent headings have no intervening body. Keep their source
            # sequence together even in ambiguous, interleaved source columns.
            previous = hh[i - 1] if i else None
            chain = previous and not text[previous["end"] : h["start"]].strip()
            if not chain:
                starts.add(h["start"])
        # Repeated running head stays in first content unit. Also attach a source
        # unnumbered chapter label immediately preceding the first numbered child.
        if hh:
            first = hh[0]["start"]
            prefix = text[d["header_end"] : first].strip()
            if first > 0 and (
                first == d["header_end"]
                or (
                    len(prefix.split()) <= POLICY["UNNUMBERED_LABEL_MAX_WORDS"]
                    and prefix.isupper()
                )
            ):
                starts.discard(first)
        # A colon-ended parent introduces its numbered descendant list. Its whole
        # subtree is one semantic envelope; HybridChunker splits it only if needed.
        for i, h in enumerate(hh[:-1]):
            nxt = hh[i + 1]
            intro = text[h["end"] : nxt["start"]].strip()
            if intro.endswith(":") and nxt["number"][: len(h["number"])] == h["number"]:
                for child in hh[i + 1 :]:
                    if child["number"][: len(h["number"])] != h["number"]:
                        break
                    starts.discard(child["start"])
        cuts = sorted(starts | {len(text)})
        groups = list(zip(cuts, cuts[1:]))
        out, fallback = [], []
        for a, b in groups:
            atom_starts = {a}
            if nt(text[a:b]) > POLICY["CAP"]:
                if d["toc"]:
                    atom_starts |= {
                        x["start"]
                        for x in ls
                        if a < x["start"] < b
                        and re.match(POLICY["HEADING_PATTERN"], x["text"])
                    }
                elif d["history_rows"] and a <= d["history_rows"][0] < b:
                    atom_starts |= {s for s in d["history_rows"][1:] if a < s < b}
                else:
                    # First build genuine sentences (not PDF line breaks).
                    body = max([h["end"] for h in hh if h["start"] == a] or [a])
                    while body < b and text[body].isspace():
                        body += 1
                    sents = []
                    for sentence in nlp(text[body:b]).sents:
                        s = body + sentence.start_char
                        # spaCy can attach an opening bracket to the previous
                        # sentence. Move it back to its own content; Docling's
                        # delimiter must replace actual source whitespace only.
                        while s > body and text[s - 1] in '(\u005b\u007b“"':
                            s -= 1
                        if sentence.text.strip() and (
                            s == body or text[s - 1].isspace()
                        ):
                            sents.append(s)
                    atom_starts |= set(sents[1:])
                    mm = [
                        x["start"]
                        for x in ls
                        if a < x["start"] < b
                        and markers.match(x["text"])
                        and x["start"] not in {h["start"] for h in hh}
                    ]
                    if mm:
                        intro_start = max([s for s in sents if s < mm[0]] or [a])
                        if nt(text[intro_start:b]) <= POLICY["CAP"]:
                            atom_starts = {
                                s for s in atom_starts if s < intro_start
                            } | {intro_start}
                        else:
                            atom_starts = {
                                s for s in atom_starts if s < intro_start
                            } | {intro_start, *mm[1:]}
                    # Numbered children of an introduced subtree are atomic units.
                    child_starts = [h["start"] for h in hh if a < h["start"] < b]
                    if child_starts:
                        atom_starts = {a, *child_starts[1:]}
                # Never create a footer-only atom, or separate a heading from body.
                atom_starts = {
                    s for s in atom_starts if s < d["footer_start"] or s == a
                }
                atom_starts = {
                    s
                    for s in atom_starts
                    if not any(h["start"] < s <= h["end"] + 1 for h in hh)
                }
            acuts = sorted(atom_starts | {b})
            dl = DoclingDocument(name="frozen-source-envelope")
            for x, y in zip(acuts, acuts[1:]):
                # Exact source is reattached below; stripping here only exposes
                # Docling's structural unit boundary, never experiment text.
                dl.add_text(label=DocItemLabel.TEXT, text=text[x:y].strip())
                if nt(text[x:y].strip()) > POLICY["CAP"]:
                    fallback.append([x, y])
            native = list(chunker.chunk(dl))
            positions, cursor = [], a
            for c in native:
                pos = text.find(c.text, cursor, b)
                if pos < 0 or text[cursor:pos].strip():
                    raise ValueError(
                        f"non-exact Docling serialization: {pid} [{a},{b})"
                    )
                positions.append(pos)
                cursor = pos + len(c.text)
            if not positions or text[cursor:b].strip():
                raise ValueError("Docling omitted source content")
            # Inter-unit whitespace is assigned to the preceding slice; leading
            # and trailing source bytes are retained exactly once.
            rcuts = [a, *positions[1:], b]
            for x, y in zip(rcuts, rcuts[1:]):
                if nt(text[x:y]) > POLICY["CAP"]:
                    # Whitespace reattachment can add a BPE token. Prefer a prior
                    # whole-word boundary; no arbitrary UTF-8 byte slicing.
                    end = y
                    while nt(text[x:end]) > POLICY["CAP"]:
                        prior = text.rfind(" ", x + 1, end - 1)
                        end = prior + 1 if prior >= 0 else end - 1
                    if end <= x:
                        raise ValueError("one source character exceeds cap")
                    out.append((x, end))
                    x = end
                out.append((x, y))
        # Reattach a pure running footer after a technical long-atom split by
        # moving the final content sentence/line with it. No minimum-size rule.
        while len(out) > 1 and out[-1][0] >= d["footer_start"]:
            x, y = out[-2][0], out[-1][1]
            if nt(text[x:y]) <= POLICY["CAP"]:
                out[-2:] = [(x, y)]
                continue
            sentence_cuts = [
                x + s.start_char
                for s in nlp(text[x : d["footer_start"]]).sents
                if s.text.strip()
            ]
            line_cuts = [
                line["start"] for line in ls if x < line["start"] < d["footer_start"]
            ]
            valid = [
                s
                for s in sentence_cuts
                if x < s < d["footer_start"] and nt(text[s:y]) <= POLICY["CAP"]
            ]
            if not valid:
                valid = [s for s in line_cuts if nt(text[s:y]) <= POLICY["CAP"]]
            if not valid:
                raise ValueError("no content-bearing footer attachment within cap")
            split = valid[-1]
            out[-2:] = [(x, split), (split, y)]
        assert out[0][0] == 0 and out[-1][1] == len(text)
        assert all(x[1] == y[0] for x, y in zip(out, out[1:]))
        assert all(0 < nt(text[a:b]) <= POLICY["CAP"] for a, b in out)
        result[pid] = out
        d["groups"] = groups
        d["long_atom_fallbacks"] = fallback
    return result, details


def segment_page_record(
    page: Mapping[str, object],
    origin: dict,
    encode: Callable[[str], Sequence[int]],
    decode: Callable[[list[int]], str],
    *,
    character_spans: Sequence[tuple[int, int]] | None = None,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Bind exact segments and GraphRAG inputs to the page's unique evidence unit.

    character_spans must partition the complete normalised page in source order.
    Identity binds policy, source page, Unicode offsets and the full page text hash.
    Returns segment records, source-evidence projection edges and GraphRAG inputs.
    """

    if page.get("chunk_id") != origin.get("chunk_id"):
        raise ValueError("Page and origin records must identify the same source page.")
    evidence_units = list(origin.get("origin_evidence_unit_ids") or [])
    if len(evidence_units) != 1 or origin.get("projection_status") != "projected":
        raise ValueError(
            "The page requires exactly one projected source-native evidence unit."
        )
    text = str(page.get("text") or "")
    input_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    segments: list[dict] = []
    ledger: list[dict] = []
    graph_inputs: list[dict] = []
    if character_spans is None:
        raise ValueError(
            "A document-confirmed partition is required; isolated page splitting is invalid."
        )
    position = 0
    for segment_index, (character_start, character_end) in enumerate(
        character_spans, start=1
    ):
        if character_start != position or not character_start < character_end <= len(
            text
        ):
            raise ValueError("Segment offsets must be ordered, nonempty and gap-free.")
        position = character_end
        segment_text = text[character_start:character_end]
        stored_token_ids = list(encode(segment_text))
        if (
            not segment_text
            or len(stored_token_ids) > POLICY["CAP"]
            or str(decode(stored_token_ids)) != segment_text
        ):
            raise ValueError("Segment text violates the Unicode or token contract.")
        identity_payload = "\0".join(
            (
                POLICY["POLICY_ID"],
                str(page["chunk_id"]),
                str(character_start),
                str(character_end),
                input_sha256,
            )
        )
        identity = hashlib.sha256(identity_payload.encode("utf-8")).hexdigest()
        segment_id = f"seg::{identity}"
        segment = {
            "schema_version": "opt-search-segment-local-v1",
            "segment_id": segment_id,
            "segment_index_on_page": segment_index,
            "chunking_config_ref": POLICY["POLICY_ID"],
            "encoding_model": POLICY["ENCODING"],
            "corpus_snapshot_id": page["corpus_snapshot_id"],
            "source_page_chunk_id": page["chunk_id"],
            "document_id": page["document_id"],
            "page_number": page["page_number"],
            "offset_unit": "zero_based_half_open_unicode_codepoints",
            "token_count": len(stored_token_ids),
            "character_start": character_start,
            "character_end": character_end,
            "source_text_character_count": len(text),
            "input_text_sha256": input_sha256,
            "text": segment_text,
        }
        edge = {
            "schema_version": "opt-search-segment-projection-local-v1",
            "projection_edge_id": f"edge::{identity}",
            "projection_route": "prepared_segment_to_source_native_page",
            "character_start": character_start,
            "character_end": character_end,
            "segment_id": segment_id,
            "source_page_chunk_id": page["chunk_id"],
            "source_artifact_id": evidence_units[0],
            "source_artifact_kind": "source_native_evidence_unit",
            "source_evidence_unit_ids": evidence_units,
            "target_artifact_id": segment_id,
            "target_artifact_kind": "graphrag_input_record",
            "projection_status": "projected",
            "support_status": "direct_source_support",
        }
        graph_input = {
            "schema_version": "graphrag-input-record-local-v2-opt-search",
            "input_record_id": segment_id,
            "source_chunk_id": segment_id,
            "source_document_id": page["document_id"],
            "source_page_number": page["page_number"],
            "corpus_snapshot_id": page["corpus_snapshot_id"],
            "chunking_config_ref": POLICY["POLICY_ID"],
            "text": segment_text,
        }
        segments.append(segment)
        ledger.append(edge)
        graph_inputs.append(graph_input)
    if position != len(text):
        raise ValueError("The partition must cover the complete source page.")
    return segments, ledger, graph_inputs
