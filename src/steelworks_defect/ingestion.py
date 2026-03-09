"""Ingestion component scaffold for loading inspection data."""

from __future__ import annotations

from datetime import datetime
import logging
from pathlib import Path
from typing import Protocol

from sqlalchemy import create_engine, text

from steelworks_defect.models import InspectionEvent


LOGGER = logging.getLogger(__name__)


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
        LOGGER.info("SQL inspection event gateway initialized")

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

        try:
            with self._engine.connect() as connection:
                rows = connection.execute(query).mappings().all()
        except Exception:
            LOGGER.exception("Database query failure while fetching inspection events")
            raise

        row_count = len(rows)
        LOGGER.info("Database query completed number_of_inspections=%s", row_count)
        if row_count > 5000:
            LOGGER.warning(
                "Very large query result number_of_inspections=%s",
                row_count,
            )

        events: list[InspectionEvent] = []
        for row in rows:
            defect_type = row["defect_id"]
            if not defect_type or not row["normalized_lot_id"]:
                LOGGER.warning(
                    "Missing inspection data defect_type=%s",
                    defect_type if defect_type else "UNKNOWN_DEFECT",
                )

            inspection_timestamp = row["inspection_timestamp"]
            try:
                if not isinstance(inspection_timestamp, datetime):
                    raise ValueError("Expected inspection_timestamp to be a datetime value")

                events.append(
                    InspectionEvent(
                        defect_id=defect_type,
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
            except Exception:
                LOGGER.exception(
                    "Data parsing error defect_type=%s number_of_defects_detected=%s",
                    defect_type if defect_type else "UNKNOWN_DEFECT",
                    row.get("qty_defects"),
                )
                raise

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

        try:
            with self._engine.connect() as connection:
                count = connection.execute(
                    table_check_query,
                    {"required_tables": list(self._REQUIRED_TABLES)},
                ).scalar_one()
        except Exception:
            LOGGER.exception("Database query failure while checking schema objects")
            raise

        return int(count) == len(self._REQUIRED_TABLES)

    def initialize_database(self, schema_sql_path: Path, seed_sql_path: Path) -> None:
        """Initialize local database schema and seed data from SQL files."""
        LOGGER.info("Initializing database from SQL scripts")
        if not self.has_required_schema_objects():
            self._execute_sql_script(schema_sql_path)
        self._execute_sql_script(seed_sql_path)
        LOGGER.info("Database initialization scripts completed")

    def _execute_sql_script(self, script_path: Path) -> None:
        sql_script = script_path.read_text(encoding="utf-8")
        statements = [stmt.strip() for stmt in sql_script.split(";") if stmt.strip()]
        LOGGER.info("Executing SQL script path=%s statement_count=%s", script_path, len(statements))

        try:
            with self._engine.begin() as connection:
                for statement in statements:
                    normalized_statement = statement.lstrip().lower()
                    if normalized_statement.startswith(
                        "insert into operations.inspection_event"
                    ):
                        LOGGER.info(
                            "Creating or updating inspection records operation=insert"
                        )
                    elif normalized_statement.startswith(
                        "update operations.inspection_event"
                    ):
                        LOGGER.info(
                            "Creating or updating inspection records operation=update"
                        )
                    connection.exec_driver_sql(statement)
        except Exception:
            LOGGER.exception("Database query failure while executing SQL script path=%s", script_path)
            raise
