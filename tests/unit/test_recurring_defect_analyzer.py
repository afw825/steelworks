"""Unit test stubs for recurring defect analyzer acceptance criteria."""

from datetime import datetime
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from steelworks_defect.analysis import RecurringDefectAnalyzer
from steelworks_defect.models import DefectTrendSummary, InspectionEvent, TrendClassification


def _event(
    defect_id: str | None,
    severity: str | None,
    lot: str,
    year: int,
    month: int,
    day: int,
    qty_defects: int,
) -> InspectionEvent:
    return InspectionEvent(
        defect_id=defect_id,
        severity=severity,
        normalized_lot_id=lot,
        inspection_timestamp=datetime(year, month, day, 8, 0, 0),
        qty_checked=20,
        qty_defects=qty_defects,
        disposition="Rework",
        notes=None,
        inspector_name="M. Patel",
    )


def test_ac1_definition_of_recurring_multi_lot_multi_week() -> None:
    analyzer = RecurringDefectAnalyzer()

    events = [
        InspectionEvent(
            defect_id="WELD",
            severity="Critical",
            normalized_lot_id="LOT-20260101-001",
            inspection_timestamp=datetime(2026, 1, 1, 8, 0, 0),
            qty_checked=20,
            qty_defects=2,
            disposition="Rework",
            notes="Weld bead issue",
            inspector_name="M. Patel",
        ),
        InspectionEvent(
            defect_id="WELD",
            severity="Critical",
            normalized_lot_id="LOT-20260115-001",
            inspection_timestamp=datetime(2026, 1, 15, 9, 0, 0),
            qty_checked=25,
            qty_defects=1,
            disposition="Hold for MRB",
            notes="Repeat weld issue",
            inspector_name="M. Patel",
        ),
    ]

    summaries = analyzer.classify_defect_trends(events)

    assert len(summaries) == 1
    assert summaries[0].defect_id == "WELD"
    assert summaries[0].impacted_lot_count == 2
    assert summaries[0].weeks_with_defects >= 2
    assert summaries[0].trend_classification == TrendClassification.RECURRING_CRITICAL


def test_ac2_single_lot_not_recurring() -> None:
    analyzer = RecurringDefectAnalyzer()

    events = [
        _event("POR", "Major", "LOT-20260101-001", 2026, 1, 1, 3),
        _event("POR", "Major", "LOT-20260101-001", 2026, 1, 15, 2),
    ]

    summaries = analyzer.classify_defect_trends(events)

    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.defect_id == "POR"
    assert summary.impacted_lot_count == 1
    assert summary.trend_classification == TrendClassification.ISOLATED_INCIDENT


def test_ac3_exclude_zero_qty_defects() -> None:
    analyzer = RecurringDefectAnalyzer()

    events = [
        _event("BURR", "Minor", "LOT-20260101-001", 2026, 1, 1, 0),
        _event("BURR", "Minor", "LOT-20260108-001", 2026, 1, 8, 0),
        _event("BURR", "Minor", "LOT-20260115-001", 2026, 1, 15, 2),
    ]

    summaries = analyzer.classify_defect_trends(events)

    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.total_defects == 2
    assert summary.impacted_lot_count == 1
    assert summary.trend_classification == TrendClassification.ISOLATED_INCIDENT


def test_ac4_incomplete_data_marked_insufficient() -> None:
    analyzer = RecurringDefectAnalyzer()

    events = [
        _event(None, "Critical", "LOT-20260101-001", 2026, 1, 1, 1),
        _event("WELD", None, "LOT-20260108-001", 2026, 1, 8, 1),
    ]

    summaries = analyzer.classify_defect_trends(events)

    assert len(summaries) == 2
    assert all(
        summary.trend_classification == TrendClassification.INSUFFICIENT_DATA
        for summary in summaries
    )


def test_ac9_default_sorting_prioritization() -> None:
    analyzer = RecurringDefectAnalyzer()

    unordered_summaries = [
        DefectTrendSummary(
            defect_id="ISOLATED",
            severity="Minor",
            impacted_lot_count=1,
            weeks_with_defects=1,
            first_detected=datetime(2026, 1, 2, 8, 0, 0),
            last_detected=datetime(2026, 1, 2, 8, 0, 0),
            total_defects=1,
            days_span=0,
            trend_classification=TrendClassification.ISOLATED_INCIDENT,
        ),
        DefectTrendSummary(
            defect_id="HF",
            severity="Major",
            impacted_lot_count=2,
            weeks_with_defects=2,
            first_detected=datetime(2026, 1, 1, 8, 0, 0),
            last_detected=datetime(2026, 1, 8, 8, 0, 0),
            total_defects=4,
            days_span=7,
            trend_classification=TrendClassification.RECURRING_HIGH_FREQUENCY,
        ),
        DefectTrendSummary(
            defect_id="CRIT",
            severity="Critical",
            impacted_lot_count=2,
            weeks_with_defects=2,
            first_detected=datetime(2026, 1, 1, 8, 0, 0),
            last_detected=datetime(2026, 1, 9, 8, 0, 0),
            total_defects=4,
            days_span=8,
            trend_classification=TrendClassification.RECURRING_CRITICAL,
        ),
    ]

    prioritized = analyzer.prioritize_defect_trends(unordered_summaries)

    assert [summary.defect_id for summary in prioritized] == ["CRIT", "HF", "ISOLATED"]
