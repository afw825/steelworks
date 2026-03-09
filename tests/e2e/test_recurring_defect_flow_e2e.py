"""End-to-end browser tests for recurring defect workflow.

These tests intentionally exercise the user-facing flow through a rendered HTML UI
using Playwright, while sourcing data from the real domain/use-case logic and
the test database pointed to by `.env.test`.
"""

from __future__ import annotations

from dataclasses import asdict
import json
import os
from pathlib import Path
import sys

import pytest
from playwright.sync_api import Page, expect
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).resolve().parents[2] / "src"))

from steelworks_defect.analysis import RecurringDefectAnalyzer
from steelworks_defect.ingestion import SqlInspectionEventGateway
from steelworks_defect.models import DefectDrillDown, DefectTrendSummary
from steelworks_defect.use_cases import RecurringDefectAnalysisUseCase


def _project_root() -> Path:
  return Path(__file__).resolve().parents[2]


def _load_test_database_url() -> str:
  """Load DATABASE_URL specifically from .env.test for E2E execution."""
  env_test_path = _project_root() / ".env.test"
  load_dotenv(dotenv_path=env_test_path)
  database_url = os.getenv("DATABASE_URL")

  if not database_url:
    pytest.skip("DATABASE_URL not found in .env.test; skipping DB-backed E2E test.")

  return database_url


def _serialize_summaries(summaries: list[DefectTrendSummary]) -> list[dict[str, object]]:
    """Convert dataclass objects into JSON-safe payloads for browser rendering."""
    payload: list[dict[str, object]] = []
    for summary in summaries:
        summary_dict = asdict(summary)
        summary_dict["first_detected"] = summary.first_detected.isoformat()
        summary_dict["last_detected"] = summary.last_detected.isoformat()
        summary_dict["trend_classification"] = summary.trend_classification.value
        payload.append(summary_dict)
    return payload


def _serialize_drilldown(drilldown: DefectDrillDown) -> dict[str, object]:
    """Convert drilldown payload into JSON-safe structure for UI simulation."""
    return {
        "defect_id": drilldown.defect_id,
        "events": [
            {
                "lot": event.normalized_lot_id,
                "timestamp": event.inspection_timestamp.isoformat(),
                "qty_defects": event.qty_defects,
            }
            for event in drilldown.events
        ],
        "insufficient_data_message": drilldown.insufficient_data_message,
        "missing_periods": drilldown.missing_periods,
    }


def _render_dashboard_html(
    summaries: list[DefectTrendSummary],
    drilldowns_by_defect: dict[str, DefectDrillDown],
) -> str:
    """Create a lightweight browser UI used by Playwright to validate the user flow.

    Why this approach:
    - The repository currently contains domain/use-case logic, not a full web app.
    - This test page allows true browser interaction checks (filter toggle, row click,
      drilldown messaging) while still validating real project behavior.
    """
    summaries_json = json.dumps(_serialize_summaries(summaries))
    drilldowns_json = json.dumps(
        {
            defect_id: _serialize_drilldown(drilldown)
            for defect_id, drilldown in drilldowns_by_defect.items()
        }
    )

    return f"""
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>SteelWorks Defect Dashboard</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 16px; }}
      table {{ border-collapse: collapse; width: 100%; margin-top: 12px; }}
      th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
      tr.recurring {{ background: #eef6ff; }}
      tr[data-defect-id] {{ cursor: pointer; }}
      #drilldown {{ margin-top: 16px; border: 1px solid #ddd; padding: 12px; }}
      .hidden {{ display: none; }}
      .insufficient {{ color: #a94442; font-weight: 600; }}
    </style>
  </head>
  <body>
    <h1>Recurring Defects</h1>
    <label>
      <input id="recurring-only" type="checkbox" />
      Show recurring defects only
    </label>

    <table aria-label="defect-trend-table">
      <thead>
        <tr>
          <th>Defect</th>
          <th>Severity</th>
          <th>Lots</th>
          <th>Weeks</th>
          <th>Total Defects</th>
          <th>Trend</th>
        </tr>
      </thead>
      <tbody id="defect-rows"></tbody>
    </table>

    <section id="drilldown" class="hidden" aria-label="defect-drilldown">
      <h2 id="drilldown-title"></h2>
      <p id="drilldown-insufficient" class="insufficient"></p>
      <ul id="drilldown-events"></ul>
    </section>

    <script>
      // Browser-side state seeded directly from Python domain/use-case output.
      const summaries = {summaries_json};
      const drilldowns = {drilldowns_json};

      const recurringOnlyCheckbox = document.getElementById("recurring-only");
      const rowsElement = document.getElementById("defect-rows");

      function isRecurring(summary) {{
        return (
          summary.trend_classification === "Recurring - Critical" ||
          summary.trend_classification === "Recurring - High Frequency"
        );
      }}

      function renderRows() {{
        rowsElement.innerHTML = "";
        const filtered = recurringOnlyCheckbox.checked
          ? summaries.filter(isRecurring)
          : summaries;

        for (const summary of filtered) {{
          const row = document.createElement("tr");
          row.setAttribute("data-defect-id", summary.defect_id);
          if (isRecurring(summary)) {{
            row.classList.add("recurring");
          }}

          row.innerHTML = `
            <td>${{summary.defect_id}}</td>
            <td>${{summary.severity}}</td>
            <td>${{summary.impacted_lot_count}}</td>
            <td>${{summary.weeks_with_defects}}</td>
            <td>${{summary.total_defects}}</td>
            <td>${{summary.trend_classification}}</td>
          `;

          // Clicking a row simulates user drilldown behavior from AC7/AC8.
          row.addEventListener("click", () => renderDrilldown(summary.defect_id));
          rowsElement.appendChild(row);
        }}
      }}

      function renderDrilldown(defectId) {{
        const payload = drilldowns[defectId];
        const section = document.getElementById("drilldown");
        const title = document.getElementById("drilldown-title");
        const insufficient = document.getElementById("drilldown-insufficient");
        const events = document.getElementById("drilldown-events");

        title.textContent = `Defect: ${{defectId}}`;
        insufficient.textContent = payload.insufficient_data_message || "";
        events.innerHTML = "";
        for (const event of payload.events) {{
          const item = document.createElement("li");
          item.textContent = `${{event.lot}} | defects=${{event.qty_defects}}`;
          events.appendChild(item);
        }}

        section.classList.remove("hidden");
      }}

      recurringOnlyCheckbox.addEventListener("change", renderRows);
      renderRows();
    </script>
  </body>
</html>
"""


@pytest.mark.e2e
def test_e2e_list_filter_and_drilldown_flow(page: Page) -> None:
    """Validate list rendering, recurring filter, and drilldown interactions.

    End-to-end scope covered here:
    1. Use-case computes summaries/drilldowns from source inspection events.
    2. Browser renders list rows and interactive controls.
    3. User toggles recurring-only filter and opens drilldown detail.
    """
    database_url = _load_test_database_url()
    gateway = SqlInspectionEventGateway(database_url)

    # Keep the test DB deterministic by applying project schema/seed scripts before
    # running browser assertions. This ensures the E2E contract is stable.
    project_root = _project_root()
    gateway.initialize_database(
      schema_sql_path=project_root / "db" / "schema.sql",
      seed_sql_path=project_root / "db" / "seed.sql",
    )

    use_case = RecurringDefectAnalysisUseCase(gateway=gateway, analyzer=RecurringDefectAnalyzer())

    summaries = use_case.get_defect_trend_list(recurring_only=False)
    assert len(summaries) > 0

    drilldowns = {
        defect_id: use_case.get_defect_drilldown(defect_id)
        for defect_id in {summary.defect_id for summary in summaries}
    }

    page.set_content(_render_dashboard_html(summaries, drilldowns))

    # Initial state: all classified defects from the seeded DB are visible.
    total_rows = len(summaries)
    expect(page.locator("tbody#defect-rows tr")).to_have_count(total_rows)

    # Toggle recurring-only filter and verify table shrinks to recurring subset.
    page.locator("#recurring-only").check()
    recurring_count = len(
      [
        summary
        for summary in summaries
        if summary.trend_classification.value
        in {"Recurring - Critical", "Recurring - High Frequency"}
      ]
    )
    expect(page.locator("tbody#defect-rows tr")).to_have_count(recurring_count)

    # Disable filter, click first row, and verify drilldown section renders.
    page.locator("#recurring-only").uncheck()
    first_defect_id = summaries[0].defect_id
    page.locator(f'tbody#defect-rows tr[data-defect-id="{first_defect_id}"]').click()
    expect(page.locator("#drilldown-title")).to_have_text(f"Defect: {first_defect_id}")
    expect(page.locator("#drilldown-events li")).to_have_count(
      len(drilldowns[first_defect_id].events)
    )