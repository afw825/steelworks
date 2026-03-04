"""Presentation component scaffold for recurring defect user interactions."""

from __future__ import annotations

from steelworks_defect.models import DefectDrillDown, DefectTrendSummary, TrendClassification


class RecurringDefectListPresenter:
    """List/table presentation contract for AC5, AC6, and AC9."""

    def __init__(self) -> None:
        self.last_rendered_rows: list[dict[str, object]] = []
        self.highlighted_defect_ids: set[str] = set()

    def render_list_view(self, summaries: list[DefectTrendSummary]) -> None:
        """Render required list/table fields for defect trends (AC5)."""
        self.last_rendered_rows = [
            {
                "defect_id": summary.defect_id,
                "severity": summary.severity,
                "impacted_lot_count": summary.impacted_lot_count,
                "weeks_with_defects": summary.weeks_with_defects,
                "first_detected": summary.first_detected,
                "last_detected": summary.last_detected,
                "total_defects": summary.total_defects,
                "days_span": summary.days_span,
                "trend_classification": summary.trend_classification.value,
            }
            for summary in summaries
        ]

    def apply_recurring_highlight(self, summaries: list[DefectTrendSummary]) -> None:
        """Apply visual highlighting for recurring defects (AC6)."""
        recurring_classifications = {
            TrendClassification.RECURRING_CRITICAL,
            TrendClassification.RECURRING_HIGH_FREQUENCY,
        }
        self.highlighted_defect_ids = {
            summary.defect_id
            for summary in summaries
            if summary.trend_classification in recurring_classifications
        }

    def apply_recurring_filter(
        self,
        summaries: list[DefectTrendSummary],
        recurring_only: bool,
    ) -> list[DefectTrendSummary]:
        """Filter list view to recurring-only rows when requested (AC6)."""
        if not recurring_only:
            return list(summaries)

        recurring_classifications = {
            TrendClassification.RECURRING_CRITICAL,
            TrendClassification.RECURRING_HIGH_FREQUENCY,
        }
        return [
            summary
            for summary in summaries
            if summary.trend_classification in recurring_classifications
        ]


class DefectDrillDownPresenter:
    """Drill-down presentation contract for AC7 and AC8."""

    def __init__(self) -> None:
        self.last_rendered_drilldown: DefectDrillDown | None = None

    def render_drilldown_view(self, drilldown: DefectDrillDown) -> None:
        """Render defect-specific detail rows and explainability messaging."""
        self.last_rendered_drilldown = drilldown
