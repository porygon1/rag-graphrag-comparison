"""Keep the published percent bars and applicability notes on their correct bases."""

import copy
import unittest

import matplotlib.pyplot as plt

from rag_comparison.figure_layout import (
    correctness_change_figure,
    grade_distribution_figure,
)


class FigureLayoutTests(unittest.TestCase):
    def test_grade_shares_use_each_rows_valid_population_and_retain_na_note(self):
        rows = []
        for metric in ("answer_correctness", "faithfulness", "citation_correctness"):
            for condition in ("C0", "G0", "C-FINAL", "G-FINAL"):
                counts = [2, 1, 1, 0]
                if condition == "C0" and metric != "answer_correctness":
                    counts = [0, 1, 1, 0]
                rows.append(
                    {
                        "Condition": condition,
                        "Measure": metric,
                        "Grades 0 / 1 / 2 / 3": counts,
                        "Applicable valid k": sum(counts),
                    }
                )
        unchanged = copy.deepcopy(rows)
        fig = grade_distribution_figure(rows, illustrative=True)
        self.addCleanup(plt.close, fig)
        ax = fig.axes[0]
        bars = ax.patches[4:]
        for index, row in enumerate(rows):
            widths = [bar.get_width() for bar in bars[index * 4 : (index + 1) * 4]]
            for width, count in zip(widths, row["Grades 0 / 1 / 2 / 3"], strict=True):
                self.assertAlmostEqual(
                    width / 302 * 100, count / row["Applicable valid k"] * 100
                )
            self.assertAlmostEqual(sum(widths), 302)
        text = [item.get_text() for item in ax.texts]
        self.assertIn(
            "Faithfulness and citation correctness exclude 2 C0 abstentions.", text
        )
        self.assertIn("Share of valid cases (%)", text)
        self.assertEqual(rows, unchanged)

    def test_correctness_shares_keep_ties_and_separate_row_denominators(self):
        rows = [
            {
                "condition_id": f"V{index}",
                "losses": 1,
                "ties": index + 1,
                "wins": 2,
                "paired_k": index + 4,
            }
            for index in range(5)
        ]
        fig = correctness_change_figure(
            rows, {row["condition_id"]: row["condition_id"] for row in rows}
        )
        self.addCleanup(plt.close, fig)
        ax = fig.axes[0]
        bars = ax.patches[3:]
        for index, row in enumerate(rows):
            row_bars = bars[index * 3 : (index + 1) * 3]
            for bar, key in zip(row_bars, ("losses", "ties", "wins"), strict=True):
                self.assertAlmostEqual(
                    bar.get_width() / 302, row[key] / row["paired_k"]
                )
            self.assertAlmostEqual(sum(bar.get_width() for bar in row_bars), 302)
        self.assertIn(
            "Share of paired cases (%)", [item.get_text() for item in ax.texts]
        )


if __name__ == "__main__":
    unittest.main()
