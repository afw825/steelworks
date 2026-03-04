"""Ingestion component scaffold for loading inspection data."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Protocol

from sqlalchemy import create_engine, text

from steelworks_defect.models import InspectionEvent


class InspectionEventGateway(Protocol):
    """Protocol for reading inspection events from a data source."""

    def fetch_inspection_events(self) -> list[InspectionEvent]:
        """Return inspection events required for recurring defect analysis."""
        ...


class SqlInspectionEventGateway:
    """SQL-backed gateway for loading inspection events from the operations schema."""

    _REQUIRED_TABLES = (
        "inspection_event",
        "lot",
        "inspector",
        "defect_type",
    )

    def __init__(self, database_url: str) -> None:
        self._engine = create_engine(self._normalize_database_url(database_url))

    @staticmethod
    def _normalize_database_url(database_url: str) -> str:
        """Ensure PostgreSQL URLs use the installed psycopg (v3) driver.

        This avoids runtime failures when DATABASE_URL points to psycopg2 by default,
        while the project intentionally depends on `psycopg[binary]`.
        """
        if database_url.startswith("postgres://"):
            return database_url.replace("postgres://", "postgresql+psycopg://", 1)

        if database_url.startswith("postgresql://"):
            return database_url.replace("postgresql://", "postgresql+psycopg://", 1)

        if database_url.startswith("postgresql+psycopg2://"):
            return database_url.replace(
                "postgresql+psycopg2://", "postgresql+psycopg://", 1
            )

        return database_url

    def fetch_inspection_events(self) -> list[InspectionEvent]:
        query = text(
            """
            SELECT
                dt.defect_id,
                dt.severity,
                l.normalized_lot_id,
                ie.inspection_timestamp,
                ie.qty_checked,
                ie.qty_defects,
                ie.disposition,
                ie.notes,
                i.inspector_name
            FROM operations.inspection_event ie
            JOIN operations.lot l
                ON l.id = ie.lot_id
            JOIN operations.inspector i
                ON i.id = ie.inspector_id
            LEFT JOIN operations.defect_type dt
                ON dt.id = ie.defect_type_id
            ORDER BY ie.inspection_timestamp
            """
        )

        with self._engine.connect() as connection:
            rows = connection.execute(query).mappings().all()

        events: list[InspectionEvent] = []
        for row in rows:
            inspection_timestamp = row["inspection_timestamp"]
            if not isinstance(inspection_timestamp, datetime):
                raise ValueError("Expected inspection_timestamp to be a datetime value")

            events.append(
                InspectionEvent(
                    defect_id=row["defect_id"],
                    severity=row["severity"],
                    normalized_lot_id=row["normalized_lot_id"],
                    inspection_timestamp=inspection_timestamp,
                    qty_checked=int(row["qty_checked"]),
                    qty_defects=int(row["qty_defects"]),
                    disposition=row["disposition"],
                    notes=row["notes"],
                    inspector_name=row["inspector_name"],
                )
            )

        return events

    def has_required_schema_objects(self) -> bool:
        """Return whether required operations schema tables exist."""
        table_check_query = text(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'operations'
              AND table_name = ANY(:required_tables)
            """
        )

        with self._engine.connect() as connection:
            count = connection.execute(
                table_check_query,
                {"required_tables": list(self._REQUIRED_TABLES)},
            ).scalar_one()

        return int(count) == len(self._REQUIRED_TABLES)

    def initialize_database(self, schema_sql_path: Path, seed_sql_path: Path) -> None:
        """Initialize local database schema and seed data from SQL files."""
        if not self.has_required_schema_objects():
            self._execute_sql_script(schema_sql_path)
        self._execute_sql_script(seed_sql_path)

    def _execute_sql_script(self, script_path: Path) -> None:
        sql_script = script_path.read_text(encoding="utf-8")
        statements = [stmt.strip() for stmt in sql_script.split(";") if stmt.strip()]

        with self._engine.begin() as connection:
            for statement in statements:
                connection.exec_driver_sql(statement)
