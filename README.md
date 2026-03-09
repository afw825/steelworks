# 🏭 SteelWorks - Recurring Defects Analysis Tool

Quality engineering tool for identifying and analyzing defects that appear across multiple manufacturing lots over time.

## Table of Contents

- [Project Description](#project-description)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Setup & Installation](#setup--installation)
- [How to Run / Build](#how-to-run--build)
- [Usage Examples](#usage-examples)
- [Running Tests](#running-tests)
- [Running E2E Tests (Playwright)](#running-e2e-tests-playwright)
- [Configuration](#configuration)
- [Key Design Decisions](#key-design-decisions)
- [What to Change for Production](#what-to-change-for-production)

---

## Project Description

### Problem Statement

As a quality engineer, you need to distinguish between:
- **Recurring Issues**: Defects that appear across multiple lots over time
- **One-off Incidents**: Defects that happen in only one lot/time window

This distinction helps prioritize systemic process improvements over isolated corrective actions.

### Solution Overview

This project provides an implemented recurring defect analysis flow for the steelworks quality engineering use case.

Current state:

1. **Layered Architecture Implemented**: Domain, ingestion, analysis, presentation, and use-case layers are wired end-to-end.
2. **Acceptance Coverage Implemented**: AC1–AC9 unit test coverage is present and runnable.
3. **Poetry-Managed Workflow**: Dependencies and test execution are standardized with Poetry commands.

### Key Features

✅ **Implemented Now**
- Recurring defect classification across lots and weeks.
- Single-lot isolation handling and zero-defect exclusion.
- Incomplete-data classification to insufficient-data trend state.
- Recurring-only filtering and prioritization logic.
- Defect drill-down details with missing-period messaging.
- Unit test suite covering AC1–AC9 (all passing).

---

## Architecture

### Layered Architecture

```
┌─────────────────────────────────────────────┐
│      Presentation Layer                     │
│  - List view and drill-down contracts       │
└─────────────────┬───────────────────────────┘
									│
┌─────────────────▼───────────────────────────┐
│      Analysis Layer                         │
│  - Recurring defect classification rules    │
└─────────────────┬───────────────────────────┘
									│
┌─────────────────▼───────────────────────────┐
│      Ingestion Layer                        │
│  - Inspection event gateway contract        │
└─────────────────┬───────────────────────────┘
									│
┌─────────────────▼───────────────────────────┐
│      Data Layer (Reference SQL)             │
│  - operations schema and seed scripts       │
└─────────────────────────────────────────────┘
```

### Directory Structure (Current)

```
src/
└── steelworks_defect/
		├── __init__.py
		├── models.py
		├── ingestion.py
		├── analysis.py
		├── presentation.py
		└── use_cases.py

tests/
└── unit/
		├── test_recurring_defect_analyzer.py
		├── test_recurring_defect_list_view.py
		└── test_defect_drilldown_view.py

db/
├── schema.sql
├── seed.sql
└── sample_queries.sql

docs/
├── architecture_decision_records.md
├── assumptions_scope.md
├── data_design.md
└── tech_stack_decision_records.md
```

---

## Tech Stack

| Component | Technology | Status |
|-----------|-----------|--------|
| Language | Python | Implemented recurring defect analysis workflow |
| Testing | pytest | AC1–AC9 unit tests implemented and passing |
| Data Model Reference | PostgreSQL schema (SQL) | Defined in `db/schema.sql` |
| Architecture Source | ADR + Data Design docs | In `docs/` |

> Note: This project currently focuses on domain logic and unit-tested analysis flows. Integration runtime (for production data adapters/UI) can be added on top of the existing contracts.

---

## Setup & Installation

### Prerequisites

- Python 3.10+
- Poetry installed

### Step 1: Open Project

```bash
cd steelworks
```

### Step 2: Ensure pytest is available

```bash
poetry install
```

---

## How to Run / Build

Current executable scope:
- Domain logic and unit tests for recurring defect analysis.
- Streamlit runtime for local interactive validation against your database.

### Run Streamlit App (Real DB via .env)

1. Set `DATABASE_URL` in `.env` (example: PostgreSQL URL).
2. Ensure your local database is running and includes the `operations` schema.
3. Launch the app:

```bash
poetry run streamlit run src/steelworks_defect/app.py
```

---

## Usage Examples

### Example 1: Validate Implemented AC1 Path

Run only AC1 test:

```bash
poetry run pytest tests/unit/test_recurring_defect_analyzer.py -k ac1 -q
```

Expected result:
- `1 passed` for AC1 test.

### Example 2: Run Full Unit Test Suite

```bash
poetry run pytest tests/unit -q
```

Expected result:
- All unit tests pass.

---

## Running Tests

### Run AC1 Test Only

```bash
poetry run pytest tests/unit/test_recurring_defect_analyzer.py::test_ac1_definition_of_recurring_multi_lot_multi_week -q
```

### Run Analyzer Test File

```bash
poetry run pytest tests/unit/test_recurring_defect_analyzer.py -q
```

### Acceptance Criteria Coverage

| AC | Status | Evidence |
|----|--------|----------|
| AC1 | ✅ Implemented | `RecurringDefectAnalyzer.classify_defect_trends` + analyzer unit test |
| AC2 | ✅ Implemented | Single-lot not-recurring analyzer unit test |
| AC3 | ✅ Implemented | Zero-defect exclusion analyzer unit test |
| AC4 | ✅ Implemented | Incomplete-data insufficient classification unit test |
| AC5 | ✅ Implemented | List view required fields presenter unit test |
| AC6 | ✅ Implemented | Recurring highlight + recurring-only filter unit test |
| AC7 | ✅ Implemented | Defect-code drill-down detail unit test |
| AC8 | ✅ Implemented | Missing-period insufficient-data message unit test |
| AC9 | ✅ Implemented | Prioritization and sorting analyzer unit test |

Current suite status:
- `poetry run pytest -q`
- `9 passed`

---

## Running E2E Tests (Playwright)

### Install Playwright test dependencies

```bash
poetry install
```

### Install browser binaries

```bash
poetry run playwright install
```

### Run E2E suite only

```bash
poetry run pytest tests/e2e -m e2e -q
```

E2E database source:
- `.env.test` must contain `DATABASE_URL` pointing to your local test DB.

### Run all tests (unit + e2e)

```bash
poetry run pytest -q
```

---

## Configuration

Current project does not require environment variables for unit-test validation.

For Streamlit runtime, expected environment variable in `.env`:
- `DATABASE_URL`: connection string for your local database.

For E2E runtime, expected environment variable in `.env.test`:
- `DATABASE_URL`: connection string for your local test database.

When runtime/data adapters are implemented later, configuration may include:
- Database connection URL
- Optional UI/runtime toggles

---

## Key Design Decisions

The implementation aligns to the project documents:

1. **Stateless Modular Monolith**
	 - Separation of ingestion, analysis, and presentation concerns.
2. **Fail-Soft Direction**
	 - Contracts are designed to support indeterminate/incomplete data handling.
3. **User-story-aligned Delivery**
	 - AC1–AC9 behavior is covered by matching unit tests.

Reference docs:
- `docs/architecture_decision_records.md`
- `docs/assumptions_scope.md`
- `docs/data_design.md`
- `docs/tech_stack_decision_records.md`

---

## What to Change for Production

When progressing from this implementation to production-ready deployment:

1. Add concrete ingestion adapters for live/external sources.
2. Add integration tests and CI checks.
3. Add deployment/runtime packaging and environment-specific config.
4. Add observability (logging/metrics) and operational hardening.
5. Add user-facing interface (if required) for list/drill-down workflows.

---

**Last Updated**: March 2026