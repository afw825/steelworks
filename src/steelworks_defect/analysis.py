"""Analysis component scaffold for recurring defect behavior."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
import logging

from steelworks_defect.models import (
    DefectDrillDown,
    DefectTrendSummary,
    InspectionEvent,
    TrendClassification,
)


LOGGER = logging.getLogger(__name__)


class RecurringDefectAnalyzer:
    """Encapsulates classification logic required by AC1-AC4 and AC9."""

    def classify_defect_trends(
        self, events: list[InspectionEvent]
    ) -> list[DefectTrendSummary]:
        """Build summary rows for the recurring defects list view (AC5)."""
        LOGGER.info("Recurring defect analysis starts number_of_inspections=%s", len(events))
        grouped_events: dict[tuple[str, str], list[InspectionEvent]] = defaultdict(list)

        for event in events:
            if event.qty_defects <= 0:
                continue

            if event.qty_checked >= 0 and event.qty_defects > event.qty_checked:
                LOGGER.warning(
                    "Suspicious defect pattern defect_type=%s number_of_inspections=%s "
                    "number_of_defects_detected=%s",
                    event.defect_id if event.defect_id else "UNKNOWN_DEFECT",
                    1,
                    event.qty_defects,
                )

            defect_id = event.defect_id if event.defect_id else "UNKNOWN_DEFECT"
            severity = event.severity if event.severity else "Unknown"
            grouped_events[(defect_id, severity)].append(event)

        summaries: list[DefectTrendSummary] = []

        for (defect_id, severity), defect_events in grouped_events.items():
            timestamps = [event.inspection_timestamp for event in defect_events]
            lots = {event.normalized_lot_id for event in defect_events}
            weeks = {
                event.inspection_timestamp.isocalendar()[:2] for event in defect_events
            }

            first_detected = min(timestamps)
            last_detected = max(timestamps)
            days_span = (last_detected - first_detected).days
            total_defects = sum(event.qty_defects for event in defect_events)

            has_incomplete_fields = defect_id == "UNKNOWN_DEFECT" or severity == "Unknown"

            if has_incomplete_fields:
                LOGGER.warning("Missing inspection data defect_type=%s", defect_id)
                trend = TrendClassification.INSUFFICIENT_DATA
            elif len(lots) >= 2 and len(weeks) >= 2:
                trend = (
                    TrendClassification.RECURRING_CRITICAL
                    if severity == "Critical"
                    else TrendClassification.RECURRING_HIGH_FREQUENCY
                )
            elif len(lots) == 1:
                trend = TrendClassification.ISOLATED_INCIDENT
            else:
                trend = TrendClassification.INSUFFICIENT_DATA

            summaries.append(
                DefectTrendSummary(
                    defect_id=defect_id,
                    severity=severity,
                    impacted_lot_count=len(lots),
                    weeks_with_defects=len(weeks),
                    first_detected=first_detected,
                    last_detected=last_detected,
                    total_defects=total_defects,
                    days_span=days_span,
                    trend_classification=trend,
                )
            )

        recurring_count = sum(
            1
            for summary in summaries
            if summary.trend_classification
            in {
                TrendClassification.RECURRING_CRITICAL,
                TrendClassification.RECURRING_HIGH_FREQUENCY,
            }
        )
        LOGGER.info(
            "Recurring defect count calculated number_of_defects_detected=%s",
            recurring_count,
        )

        return summaries

    def filter_recurring_defects(
        self, summaries: list[DefectTrendSummary]
    ) -> list[DefectTrendSummary]:
        """Return only recurring rows for recurring-only filter behavior (AC6)."""
        recurring_classifications = {
            TrendClassification.RECURRING_CRITICAL,
            TrendClassification.RECURRING_HIGH_FREQUENCY,
        }
        return [
            summary
            for summary in summaries
            if summary.trend_classification in recurring_classifications
        ]

    def prioritize_defect_trends(
        self, summaries: list[DefectTrendSummary]
    ) -> list[DefectTrendSummary]:
        """Apply default sorting and prioritization required by AC9."""
        priority_rank = {
            TrendClassification.RECURRING_CRITICAL: 0,
            TrendClassification.RECURRING_HIGH_FREQUENCY: 1,
            TrendClassification.ISOLATED_INCIDENT: 2,
            TrendClassification.INSUFFICIENT_DATA: 3,
        }

        return sorted(
            summaries,
            key=lambda summary: (
                priority_rank[summary.trend_classification],
                -summary.impacted_lot_count,
                -summary.weeks_with_defects,
                -summary.total_defects,
                -summary.days_span,
                -summary.last_detected.timestamp(),
                summary.defect_id,
            ),
        )

    def build_defect_drilldown(
        self, defect_id: str, events: list[InspectionEvent]
    ) -> DefectDrillDown:
        """Build defect-code detail payload and missing-period messaging (AC7, AC8)."""
        defect_events = sorted(
            [
                event
                for event in events
                if event.defect_id == defect_id and event.qty_defects > 0
            ],
            key=lambda event: event.inspection_timestamp,
        )

        if not defect_events:
            LOGGER.warning("Missing inspection data for defect drilldown defect_type=%s", defect_id)
            return DefectDrillDown(
                defect_id=defect_id,
                events=[],
                insufficient_data_message=(
                    "Insufficient data: no defect events found for requested defect code."
                ),
                missing_periods=[],
            )

        observed_week_starts = {
            self._week_start(event.inspection_timestamp.date()) for event in defect_events
        }
        first_week = min(observed_week_starts)
        last_week = max(observed_week_starts)

        missing_periods: list[str] = []
        current_week = first_week
        while current_week <= last_week:
            if current_week not in observed_week_starts:
                iso_year, iso_week, _ = current_week.isocalendar()
                missing_periods.append(f"{iso_year}-W{iso_week:02d}")
            current_week += timedelta(days=7)

        insufficient_data_message = (
            "Insufficient data for continuous trend analysis. "
            f"Missing periods: {', '.join(missing_periods)}."
            if missing_periods
            else None
        )

        return DefectDrillDown(
            defect_id=defect_id,
            events=defect_events,
            insufficient_data_message=insufficient_data_message,
            missing_periods=missing_periods,
        )

    @staticmethod
    def _week_start(day: date) -> date:
        return day - timedelta(days=day.weekday())
