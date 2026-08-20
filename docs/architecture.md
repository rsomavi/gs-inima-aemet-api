# Architecture

## Request flow

```
Frontend (Vue + TypeScript)
    │ QueryForm.vue emits params → api.ts builds URL → fetch()
    ▼
urls.py
    │ Routes to AntarcticaDataView
    ▼
views.py (AntarcticaDataView.get)
    │ 1. Validate station          (models.py → VALID_STATIONS)
    │ 2. Parse & validate fields   (serializers.py → parse_requested_fields)
    │ 3. Parse & validate aggregation (aggregation.py → VALID_AGGREGATIONS)
    │ 4. Resolve location          (timezones.py → resolve_input_timezone)
    │ 5. Parse dates, convert to UTC
    │ 6. Validate start <= end
    ▼
cache.py (get_observations)
    │ find_missing_ranges() checks SQLite (models.py → Measurement)
    │
    ├─ Gap found ──► _split_into_chunks() (≤30 days each)
    │                       │
    │                       ▼
    │               aemet_client.py (fetch_antarctica_observations)
    │                       │ Two-step AEMET request (URL → data)
    │                       ▼
    │               _store_observations() → SQLite upsert
    │
    ▼
aggregation.py (aggregate_measurements)
    │ If aggregation != none: group by hour / Madrid-day / Madrid-month, average
    ▼
serializers.py (serialize_measurement)
    │ Filter to requested fields, rename to spec format,
    │ convert Datetime to Europe/Madrid with offset
    ▼
JSON response
    ▼
Frontend: ResultsTable.vue + ResultsChart.vue render the data
```

Each module has a single responsibility and can be tested in isolation without spinning up the others — `aemet_client.py` doesn't know about caching, `cache.py` doesn't know about output formatting, `aggregation.py` doesn't know where the data came from. See [`testing.md`](testing.md) for how this pays off.

## Why this stack

The original brief suggested FastAPI/Flask for the backend and React for the frontend, but explicitly allowed deviating from this if justified (per the recruiter's guidance following the technical interview). The choices below were made with that freedom.

### Backend: Django + Django REST Framework (not FastAPI/Flask)

The hardest part of this challenge is data persistence and caching (Part 2), not routing. Django's built-in ORM and migration system (`makemigrations`/`migrate`) provide unique constraints, indexes, and schema versioning out of the box, avoiding the need to hand-roll or bolt on a separate ORM (e.g. SQLAlchemy + Alembic) as would be required with a micro-framework. This is a matter of fewer moving parts for this challenge's scope, not an objective claim that Django is superior for every use case — FastAPI with SQLModel is an equally valid combination.

Prior familiarity with Django also mattered for time efficiency, given the challenge's time constraints.

### Database: SQLite

Required explicitly by the challenge. It's also a good fit for the actual scope here: two fixed Antarctic stations, not the full AEMET network. If the scope grew to "all available stations" (as Part 2's trader scenario hints at), a managed database (e.g. Postgres) and a normalized `Station` table would become worth the added complexity — see [`known-limitations.md`](known-limitations.md).

### Frontend: Vue 3 + TypeScript (not React)

TypeScript is an explicit, named evaluation criterion in the brief's Part 3 ("checking concepts, code organization, and **the use of TypeScript**"). A lightly-typed approach was used — typing the API response shape and component props, while letting inference handle the rest — which satisfies the requirement without unnecessary complexity for an app of this size.

Vue was chosen over React purely on prior familiarity; the brief places no restriction on the frontend framework itself ("no restriction, just checking concepts, code organization, and the use of TypeScript").

**Not used:** Vue Router and Pinia were both skipped — this is a single-screen app with no routing needs and no state complex enough to warrant a dedicated state-management library. Adding either would be unjustified complexity for this scope.

### Charting: Chart.js

Lightweight, framework-agnostic, straightforward integration with Vue via a `<canvas>` ref. No steep learning curve given the time constraints.