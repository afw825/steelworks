"""Unit test stubs for recurring defects list view acceptance criteria."""

from datetime import datetime
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from steelworks_defect.models import DefectTrendSummary, TrendClassification
from steelworks_defect.presentation import RecurringDefectListPresenter


def _summary(defect_id: str, classification: TrendClassification) -> DefectTrendSummary:
    return DefectTrendSummary(
        defect_id=defect_id,
        severity="Major",
        impacted_lot_count=2,
        weeks_with_defects=2,
        first_detected=datetime(2026, 1, 1, 8, 0, 0),
        last_detected=datetime(2026, 1, 8, 8, 0, 0),
        total_defects=3,
        days_span=7,
        trend_classification=classification,
    )


def test_ac5_list_view_required_fields() -> None:
    presenter = RecurringDefectListPresenter()
    summaries = [_summary("WELD", TrendClassification.RECURRING_CRITICAL)]

    presenter.render_list_view(summaries)

    assert len(presenter.last_rendered_rows) == 1
    row = presenter.last_rendered_rows[0]
    assert set(row.keys()) == {
        "defect_id",
        "severity",
        "impacted_lot_count",
        "weeks_with_defects",
        "first_detected",
        "last_detected",
        "total_defects",
        "days_span",
        "trend_classification",
    }
    assert row["defect_id"] == "WELD"


def test_ac6_visual_highlight_and_filter_for_recurring() -> None:
    presenter = RecurringDefectListPresenter()
    recurring = _summary("WELD", TrendClassification.RECURRING_CRITICAL)
    isolated = _summary("BURR", TrendClassification.ISOLATED_INCIDENT)
    summaries = [recurring, isolated]

    presenter.apply_recurring_highlight(summaries)
    filtered = presenter.apply_recurring_filter(summaries, recurring_only=True)

    assert presenter.highlighted_defect_ids == {"WELD"}
    assert [summary.defect_id for summary in filtered] == ["WELD"]
