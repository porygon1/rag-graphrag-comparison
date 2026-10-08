"""Build the two vector workflow guides; requires Inkscape, reportlab and pypdf."""

import argparse
import io
import json
import subprocess
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

from pypdf import PdfReader, PdfWriter, Transformation
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph

SOURCE = Path(__file__).resolve().parent
WIDTH = 160 * mm
LEFT = 25 * mm
INK = HexColor("#202830")
MUTED = HexColor("#52606b")


def paragraph(canvas, text, top, *, size=9.5, color=INK, bold=False):
    style = ParagraphStyle(
        "text",
        fontName="Helvetica-Bold" if bold else "Helvetica",
        fontSize=size,
        leading=size * 1.38,
        textColor=color,
    )
    block = Paragraph(escape(text), style)
    _, height = block.wrap(WIDTH, A4[1])
    if canvas is not None:
        block.drawOn(canvas, LEFT, top - height)
    return top - height


def page_header(canvas, document, number, count, title, part):
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 9)
    canvas.drawString(LEFT, 284 * mm, document["title"])
    canvas.drawRightString(185 * mm, 284 * mm, document["baseline"])
    canvas.setStrokeColor(HexColor("#c9cfd4"))
    canvas.setLineWidth(0.5)
    canvas.line(LEFT, 279 * mm, 185 * mm, 279 * mm)
    top = paragraph(canvas, title, 270 * mm, size=18, bold=True)
    top = paragraph(canvas, part, top - 2 * mm, size=9, color=MUTED)
    canvas.line(LEFT, 22 * mm, 185 * mm, 22 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(LEFT, 16 * mm, "rag-graphrag-comparison")
    canvas.drawRightString(185 * mm, 16 * mm, f"{number} / {count}")
    return top - 5 * mm


def build(document, config, inkscape, temporary):
    figures = {}
    for page in document["pages"]:
        for name in page["assets"]:
            svg = SOURCE / document["group"] / name
            target = temporary / f"{document['group']}-{svg.stem}.pdf"
            subprocess.run(
                [
                    inkscape,
                    str(svg),
                    "--export-type=pdf",
                    f"--export-filename={target}",
                ],
                check=True,
                capture_output=True,
            )
            figures[name] = PdfReader(target).pages[0]

    buffer = io.BytesIO()
    canvas = Canvas(buffer, pagesize=A4, invariant=1)
    placements = []
    count = len(document["pages"]) + 1
    for number, page in enumerate(document["pages"], 1):
        top = page_header(canvas, document, number, count, page["title"], page["part"])
        for text in page["intro"]:
            top = paragraph(canvas, text, top) - 2 * mm
        top -= 2 * mm
        caption = f"Figure {page['figure']}. {page['caption']}"
        reference = f"Thesis: {page['thesis']}."
        caption_height = -paragraph(None, caption, 0, size=9)
        caption_height += -paragraph(None, reference, 0, size=8.5) + 6 * mm
        available = top - 29 * mm - caption_height
        native_height = sum(
            WIDTH
            * float(figures[name].mediabox.height)
            / float(figures[name].mediabox.width)
            for name in page["assets"]
        )
        gaps = 3 * mm * (len(page["assets"]) - 1)
        width = WIDTH * min(1, (available - gaps) / native_height)
        assert width >= 145 * mm, "A workflow page needs a shorter caption or layout."
        placement = []
        for name in page["assets"]:
            figure = figures[name]
            scale = width / float(figure.mediabox.width)
            height = scale * float(figure.mediabox.height)
            placement.append((name, scale, LEFT + (WIDTH - width) / 2, top - height))
            top -= height + 3 * mm
        top = paragraph(canvas, caption, top - 1 * mm, size=9)
        top = paragraph(canvas, reference, top - 2 * mm, size=8.5, color=MUTED)
        assert top >= 28 * mm, "Caption overlaps the footer."
        placements.append(placement)
        canvas.showPage()

    top = page_header(
        canvas, document, count, count, "Scope and references", "Reading the figures"
    )
    for text in (
        "These figures explain the baseline workflow. Controlled variants and their configuration are documented in the repository notebooks and methods pages.",
        config["fiction"],
        "Notation: folded sheets and bordered tables show documents or retained records. Rounded rectangles show processing steps. Arrows show data flow. Vector components and two-dimensional geometry are schematic.",
        "Shared evaluation: qrel grade 2 indicates direct support for a required fact, grade 1 related content and grade 0 no answer evidence. Retrieval metrics and source traceability are separate from semantic answer assessment.",
        "Method details: docs/classical_rag_artifacts.md, docs/graphrag_artifacts.md and docs/evaluation_methods.md. The runnable public example uses RFC 2795; it is separate from these schematic figures.",
        "Figure and reference numbers match the thesis appendices. The full bibliography for the citations used here follows.",
    ):
        top = paragraph(canvas, text, top) - 4 * mm
    top = paragraph(canvas, "Master's thesis", top, size=10, bold=True) - 2 * mm
    top = paragraph(canvas, config["thesis"], top, size=9) - 5 * mm
    for key in document["references"]:
        top = (
            paragraph(canvas, f"[{key}] {config['references'][key]}", top, size=9)
            - 3 * mm
        )
    assert top >= 28 * mm, "References overlap the footer."
    canvas.save()

    reader = PdfReader(buffer)
    writer = PdfWriter()
    for page, items in zip(reader.pages, placements):
        for name, scale, x, y in items:
            page.merge_transformed_page(
                figures[name], Transformation().scale(scale).translate(x, y)
            )
        writer.add_page(page)
    writer.add_page(reader.pages[-1])
    writer.add_metadata(
        {
            "/Title": document["title"],
            "/Subject": f"Illustrated {document['baseline']} workflow and retrieval evaluation",
            "/Creator": "rag-graphrag-comparison",
        }
    )
    output = SOURCE.parent / document["filename"]
    writer.write(output)
    print(f"Built {output.name}: {count} pages")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inkscape", default="inkscape")
    args = parser.parse_args()
    config = json.loads((SOURCE / "workflows.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as folder:
        for document in config["documents"]:
            build(document, config, args.inkscape, Path(folder))


if __name__ == "__main__":
    main()
