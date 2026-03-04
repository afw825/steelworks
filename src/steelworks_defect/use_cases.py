"""Application use-case scaffolding for recurring defect workflows."""

from __future__ import annotations

from steelworks_defect.analysis import RecurringDefectAnalyzer
from steelworks_defect.ingestion import InspectionEventGateway
from steelworks_defect.models import DefectDrillDown, DefectTrendSummary


class RecurringDefectAnalysisUseCase:
    """Orchestrates recurring defect list and drill-down flows for the user story."""

    def __init__(
        self, gateway: InspectionEventGateway, analyzer: RecurringDefectAnalyzer
    ) -> None:
        self._gateway = gateway
        self._analyzer = analyzer

    def get_defect_trend_list(self, recurring_only: bool) -> list[DefectTrendSummary]:
        """Return list-view data including optional recurring-only filtering (AC5, AC6, AC9)."""
        events = self._gateway.fetch_inspection_events()
        summaries = self._analyzer.classify_defect_trends(events)

        if recurring_only:
            summaries = self._analyzer.filter_recurring_defects(summaries)

        return self._analyzer.prioritize_defect_trends(summaries)

    def get_defect_drilldown(self, defect_id: str) -> DefectDrillDown:
        """Return drill-down details and missing-period messaging for one defect (AC7, AC8)."""
        events = self._gateway.fetch_inspection_events()
        return self._analyzer.build_defect_drilldown(defect_id=defect_id, events=events)
