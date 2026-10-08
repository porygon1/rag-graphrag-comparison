"""Assessment figures. See thesis Figures 5 and 6 for details."""

from collections.abc import Mapping, Sequence

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import RendererAgg
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Rectangle


_WIDTH = 160 / 25.4 * 72
_GRADE_COLOURS = ("#DDDDDD", "#AAAAAA", "#707070", "#333333")
_CHANGE_COLOURS = ("#A74C26", "#DDDDDD", "#1B6389")
_COUNT_FONT = FontProperties(family="Arial", size=9.5)
_RENDERER = RendererAgg(round(_WIDTH), 570, 72)


def _text(
    ax: Axes,
    x: float,
    y: float,
    value: object,
    size: float = 10,
    colour: str = "#222222",
    anchor: str = "left",
    bold: bool = False,
) -> None:
    ax.text(
        x,
        y,
        str(value),
        fontsize=size,
        color=colour,
        ha=anchor,
        va="baseline",
        fontfamily="Arial",
        fontweight="bold" if bold else "normal",
    )


def _canvas(
    height: int,
    title: str,
    subtitle: str,
    labels: Sequence[str],
    colours: Sequence[str],
    positions: Sequence[float],
) -> tuple[Figure, Axes]:
    fig = plt.figure(figsize=(_WIDTH / 72, height / 72), facecolor="white")
    ax = fig.add_axes((0, 0, 1, 1), xlim=(0, _WIDTH), ylim=(height, 0))
    ax.set_axis_off()
    _text(ax, 10, 20, title, 14, bold=True)
    _text(ax, 10, 40, subtitle, colour="#555555")
    for label, colour, x in zip(labels, colours, positions, strict=True):
        ax.add_patch(
            Rectangle((x - 15, 54), 10, 10, facecolor=colour, edgecolor="none")
        )
        _text(ax, x, 62.5, label, 9.5)
    return fig, ax


def _grid(ax: Axes, top: float, bottom: float) -> None:
    for percentage in (0, 25, 50, 75, 100):
        x = 82 + 302 * percentage / 100
        ax.plot((x, x), (top, bottom), color="#DDDDDD", linewidth=0.5, zorder=0)
        _text(ax, x, bottom + 14, percentage, 9.5, "#555555", "center")
    ax.plot((82, 384), (bottom, bottom), color="#555555", linewidth=0.7)


def _bar(
    ax: Axes,
    y: float,
    condition: str,
    counts: Sequence[int],
    total: int,
    colours: Sequence[str],
) -> None:
    assert total > 0 and sum(counts) == total and all(count >= 0 for count in counts)
    _text(ax, 74, y + 3.5, condition, anchor="right")
    _text(ax, 394, y + 3.5, f"n = {total}", 9.5, "#555555")
    x = 82.0
    for count, colour in zip(counts, colours, strict=True):
        width = 302 * count / total
        ax.add_patch(
            Rectangle(
                (x, y - 6.8),
                width,
                13.6,
                facecolor=colour,
                edgecolor="white",
                linewidth=0.6,
            )
        )
        label_width, _, _ = _RENDERER.get_text_width_height_descent(
            str(count), _COUNT_FONT, ismath=False
        )
        centre = x + width / 2
        if width >= label_width + 2.4:
            ink = "#222222" if colour in ("#DDDDDD", "#AAAAAA") else "white"
            _text(ax, centre, y + 3.3, count, 9.5, ink, "center")
        elif count:
            ax.plot((centre, centre), (y - 6.8, y - 12), color="#555555", linewidth=0.5)
            _text(ax, centre, y - 14, count, 9.5, anchor="center")
        x += width


def grade_distribution_figure(
    grade_rows: Sequence[Mapping], illustrative: bool = False
) -> Figure:
    """Plot valid grade counts and shares for C0, G0, C-FINAL and G-FINAL."""
    title = (
        "Illustrative: " if illustrative else ""
    ) + "Assessment grade distributions"
    fig, ax = _canvas(
        570,
        title,
        "Primary benchmark: baseline and FINAL configurations",
        [f"Grade {grade}" for grade in range(4)],
        _GRADE_COLOURS,
        (25, 96.326172, 167.652344, 238.978516),
    )
    conditions = ("C0", "G0", "C-FINAL", "G-FINAL")
    rows = {(row["Condition"], row["Measure"]): row for row in grade_rows}
    assert len(rows) == len(grade_rows)
    for metric, label, header in (
        ("answer_correctness", "(a) Answer correctness", 86),
        ("faithfulness", "(b) Faithfulness", 226),
        ("citation_correctness", "(c) Citation correctness", 366),
    ):
        _text(ax, 10, header, label, 11, bold=True)
        _grid(ax, header + 9, header + 105)
        for condition, offset in zip(conditions, (18, 39, 68, 89), strict=True):
            row = rows[condition, metric]
            _bar(
                ax,
                header + offset,
                condition,
                row["Grades 0 / 1 / 2 / 3"],
                row["Applicable valid k"],
                _GRADE_COLOURS,
            )
    exclusions = []
    for condition in conditions:
        correctness = rows[condition, "answer_correctness"]["Applicable valid k"]
        faithfulness = rows[condition, "faithfulness"]["Applicable valid k"]
        citation = rows[condition, "citation_correctness"]["Applicable valid k"]
        assert faithfulness == citation <= correctness
        if correctness > faithfulness:
            exclusions.append(f"{correctness - faithfulness} {condition}")
    exclusion_note = (
        "Faithfulness and citation correctness exclude "
        + " and ".join(exclusions)
        + " abstentions."
        if exclusions
        else "Faithfulness and citation correctness use all answer correctness cases."
    )
    _text(ax, 233, 507, "Share of valid cases (%)", anchor="center")
    for y, note in zip(
        (527, 541, 555),
        (
            "Numbers show case counts. Bar lengths show shares of valid cases.",
            exclusion_note,
            "Distributions describe applicable cases, not paired transitions.",
        ),
        strict=True,
    ):
        _text(ax, 10, y, note, 9.5, "#555555")
    return fig


def correctness_change_figure(
    balances: Sequence[Mapping], labels: Mapping[str, str], illustrative: bool = False
) -> Figure:
    """Plot lower, equal and higher paired correctness counts and shares."""
    title = ("Illustrative: " if illustrative else "") + "Changes in answer correctness"
    fig, ax = _canvas(
        320,
        title,
        "Paired changes relative to each variant's own baseline",
        ("Lower grade", "Equal grade", "Higher grade"),
        _CHANGE_COLOURS,
        (25, 114.811279, 203.045410),
    )
    assert len(balances) == 5
    _grid(ax, 81, 234)
    for row, y in zip(balances, (91, 122, 153, 184, 215), strict=True):
        _bar(
            ax,
            y,
            labels[row["condition_id"]],
            [row[key] for key in ("losses", "ties", "wins")],
            row["paired_k"],
            _CHANGE_COLOURS,
        )
    totals = {row["paired_k"] for row in balances}
    denominator = (
        f"{next(iter(totals))} paired answerable questions per row."
        if len(totals) == 1
        else "Paired answerable question counts are shown per row."
    )
    _text(ax, 233, 272, "Share of paired cases (%)", anchor="center")
    _text(
        ax,
        10,
        293,
        "Numbers show case counts. C variants vs C0. G variants vs G0.",
        9.5,
        "#555555",
    )
    _text(ax, 10, 307, denominator + " Ties remain in the denominator.", 9.5, "#555555")
    return fig
