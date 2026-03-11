"""Streamlit app for recurring defect analysis using database data.

Primary source: `.env` (real/local runtime DB)
Fallback source: `.env.test`
"""

from __future__ import annotations

from dataclasses import asdict
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import os
import sys

from dotenv import load_dotenv
import pandas as pd
import streamlit as st

SRC_PATH = Path(__file__).resolve().parents[1]
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from steelworks_defect.analysis import RecurringDefectAnalyzer
from steelworks_defect.ingestion import SqlInspectionEventGateway
from steelworks_defect.use_cases import RecurringDefectAnalysisUseCase


LOGGER = logging.getLogger(__name__)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_env_file() -> None:
    project_root = _project_root()
    env_path = project_root / ".env"
    fallback_env_path = project_root / ".env.test"

    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    elif fallback_env_path.exists():
        load_dotenv(dotenv_path=fallback_env_path)


def _configure_logging() -> None:
    project_root = _project_root()
    log_dir = project_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    root_logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(module)s | %(message)s"
    )
    file_handler = RotatingFileHandler(
        log_dir / "steelworks.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)


def _summary_to_row(summary: object) -> dict[str, object]:
    summary_dict = asdict(summary)
    summary_dict["trend_classification"] = summary_dict["trend_classification"].value
    return summary_dict


def main() -> None:
    _configure_logging()
    LOGGER.info("Application startup")

    st.set_page_config(page_title="SteelWorks Defect Dashboard", layout="wide")
    st.title("🏭 SteelWorks Defect Dashboard")
    LOGGER.info('User opened the "Recurring Defects" page')

    _load_env_file()
    database_url = os.getenv("DATABASE_URL")

    import sentry_sdk
    sentry_sdk.init(
        dsn = os.getenv("SENTRY_DSN"),
        send_default_pii=False,
        traces_sample_rate=0.0,
        enable_logs=False,
    )
    divide_by_zero = 1/0

    if not database_url:
        LOGGER.error("Missing DATABASE_URL configuration")
        st.error(
            "DATABASE_URL not found. Add DATABASE_URL to .env "
            "(or .env.test as fallback) and retry."
        )
        st.stop()

    analyzer = RecurringDefectAnalyzer()
    gateway = SqlInspectionEventGateway(database_url)
    use_case = RecurringDefectAnalysisUseCase(gateway=gateway, analyzer=analyzer)

    if not gateway.has_required_schema_objects():
        LOGGER.warning("Missing required database schema objects")
        st.error(
            "Required database objects were not found. "
            "The app expects tables under the operations schema (for example: "
            "operations.inspection_event)."
        )
        st.info(
            "Use the button below to initialize your local database using "
            "db/schema.sql and db/seed.sql from this repository."
        )

        if st.button("Initialize Local Database"):
            try:
                LOGGER.info("Initializing local database")
                project_root = _project_root()
                gateway.initialize_database(
                    schema_sql_path=project_root / "db" / "schema.sql",
                    seed_sql_path=project_root / "db" / "seed.sql",
                )
            except Exception as error:
                LOGGER.exception("Unexpected exception during database initialization")
                st.error("Database initialization failed.")
                st.exception(error)
                st.stop()

            LOGGER.info("Local database initialized successfully")
            st.success("Database initialized successfully. Re-running app...")
            st.rerun()

        st.stop()

    try:
        recurring_only = st.checkbox("Show recurring defects only", value=False)
        summaries = use_case.get_defect_trend_list(recurring_only=recurring_only)
    except Exception as error:
        LOGGER.exception("Unexpected exception while loading recurring defects list")
        st.error("Failed to load inspection data from your local database.")
        st.exception(error)
        st.stop()

    st.subheader("Defect Trend List")

    if not summaries:
        LOGGER.info("No defect trends found for current dataset")
        st.info("No defect trends were found with the current data.")
        st.stop()

    LOGGER.info("Defect trend list loaded total_rows=%s", len(summaries))

    summary_rows = [_summary_to_row(summary) for summary in summaries]
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)

    st.subheader("Defect Drilldown")
    selected_defect_id = st.selectbox(
        "Select defect code",
        options=[summary.defect_id for summary in summaries],
        index=0,
    )

    try:
        drilldown = use_case.get_defect_drilldown(selected_defect_id)
    except Exception as error:
        LOGGER.exception(
            "Unexpected exception while loading defect drilldown defect_type=%s",
            selected_defect_id,
        )
        st.error("Failed to load drilldown details from your local database.")
        st.exception(error)
        st.stop()

    if drilldown.insufficient_data_message:
        LOGGER.warning(
            "Missing inspection data for drilldown defect_type=%s",
            selected_defect_id,
        )
        st.warning(drilldown.insufficient_data_message)

    if drilldown.events:
        event_rows = [
            {
                "normalized_lot_id": event.normalized_lot_id,
                "inspection_timestamp": event.inspection_timestamp,
                "severity": event.severity,
                "qty_checked": event.qty_checked,
                "qty_defects": event.qty_defects,
                "disposition": event.disposition,
                "inspector_name": event.inspector_name,
                "notes": event.notes,
            }
            for event in drilldown.events
        ]
        st.dataframe(pd.DataFrame(event_rows), use_container_width=True)
    else:
        st.info("No drilldown events found for the selected defect.")


if __name__ == "__main__":
    main()