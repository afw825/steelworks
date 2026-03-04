"""Unit test stubs for defect drill-down acceptance criteria."""

from datetime import datetime
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from steelworks_defect.analysis import RecurringDefectAnalyzer
from steelworks_defect.models import InspectionEvent


def _event(defect_id: str, lot: str, year: int, month: int, day: int) -> InspectionEvent:
    return InspectionEvent(
        defect_id=defect_id,
        severity="Major",
        normalized_lot_id=lot,
        inspection_timestamp=datetime(year, month, day, 8, 0, 0),
        qty_checked=20,
        qty_defects=1,
        disposition="Rework",
        notes=None,
        inspector_name="A. Nguyen",
    )


def test_ac7_drilldown_detail_by_defect_code() -> None:
    analyzer = RecurringDefectAnalyzer()
    events = [
        _event("WELD", "LOT-20260101-001", 2026, 1, 1),
        _event("WELD", "LOT-20260108-001", 2026, 1, 8),
        _event("BURR", "LOT-20260101-001", 2026, 1, 1),
    ]

    drilldown = analyzer.build_defect_drilldown("WELD", events)

    assert drilldown.defect_id == "WELD"
    assert len(drilldown.events) == 2
    assert all(event.defect_id == "WELD" for event in drilldown.events)


def test_ac8_insufficient_data_message_with_missing_periods() -> None:
    analyzer = RecurringDefectAnalyzer()
    events = [
        _event("POR", "LOT-20260101-001", 2026, 1, 1),
        _event("POR", "LOT-20260115-001", 2026, 1, 15),
    ]

    drilldown = analyzer.build_defect_drilldown("POR", events)

    assert drilldown.insufficient_data_message is not None
    assert drilldown.missing_periods == ["2026-W02"]
