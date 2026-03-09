"""Application use-case scaffolding for recurring defect workflows."""

from __future__ import annotations

import logging

from steelworks_defect.analysis import RecurringDefectAnalyzer
from steelworks_defect.ingestion import InspectionEventGateway
from steelworks_defect.models import (
    DefectDrillDown,
    DefectTrendSummary,
    TrendClassification,
)


LOGGER = logging.getLogger(__name__)


class RecurringDefectAnalysisUseCase:
    """Orchestrates recurring defect list and drill-down flows for the user story."""

    def __init__(
        self, gateway: InspectionEventGateway, analyzer: RecurringDefectAnalyzer
    ) -> None:
        self._gateway = gateway
        self._analyzer = analyzer

    def get_defect_trend_list(self, recurring_only: bool) -> list[DefectTrendSummary]:
        """Return list-view data including optional recurring-only filtering (AC5, AC6, AC9)."""
        LOGGER.info("Running recurring defect analysis recurring_only=%s", recurring_only)
        events = self._gateway.fetch_inspection_events()
        LOGGER.info("Inspection events loaded number_of_inspections=%s", len(events))

        summaries = self._analyzer.classify_defect_trends(events)
        recurring_defect_count = sum(
            1
            for summary in summaries
            if summary.trend_classification
            in {
                TrendClassification.RECURRING_CRITICAL,
                TrendClassification.RECURRING_HIGH_FREQUENCY,
            }
        )

        LOGGER.info(
            "Recurring defect analysis completed number_of_inspections=%s "
            "number_of_defects_detected=%s",
            len(events),
            recurring_defect_count,
        )

        if recurring_only:
            summaries = self._analyzer.filter_recurring_defects(summaries)
            LOGGER.info("Recurring-only filter applied filtered_rows=%s", len(summaries))

        return self._analyzer.prioritize_defect_trends(summaries)

    def get_defect_drilldown(self, defect_id: str) -> DefectDrillDown:
        """Return drill-down details and missing-period messaging for one defect (AC7, AC8)."""
        LOGGER.info("Loading defect drilldown defect_type=%s", defect_id)
        events = self._gateway.fetch_inspection_events()
        LOGGER.info(
            "Inspection events loaded for drilldown defect_type=%s number_of_inspections=%s",
            defect_id,
            len(events),
        )
        return self._analyzer.build_defect_drilldown(defect_id=defect_id, events=events)
