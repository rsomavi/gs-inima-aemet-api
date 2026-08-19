"""Adversarial smoke tests against the local server's validation logic.

Run with the dev server already running (python manage.py runserver),
then: python scripts/smoke_test_validation.py

These tests hit the endpoint directly and check for the correct HTTP
status code. They intentionally try to break the API, not just
confirm the happy path.
"""

import sys
import urllib.parse

import requests

BASE_URL = "http://127.0.0.1:8000/api/antartida/datos"

# A range known to already be cached from earlier manual testing,
# to keep most of these tests from touching AEMET at all.
CACHED_STATION = "89070"
CACHED_START = "2026-01-15T00:00:00"
CACHED_END = "2026-01-15T01:00:00"


def build_url(fecha_ini=CACHED_START, fecha_fin=CACHED_END, estacion=CACHED_STATION, query=None):
    path = f"{BASE_URL}/fechaini/{fecha_ini}/fechafin/{fecha_fin}/estacion/{estacion}"
    if query:
        path += "?" + urllib.parse.urlencode(query)
    return path


CASES = [
    # --- Dates: limits and edge cases ---
    ("reversed date range (end before start)", build_url(fecha_ini="2026-01-15T01:00:00", fecha_fin="2026-01-15T00:00:00"), 400),
    ("same start and end (single instant)", build_url(fecha_ini=CACHED_START, fecha_fin=CACHED_START), 200),
    ("range not aligned to 10-minute grid", build_url(fecha_ini="2026-01-15T00:03:00", fecha_fin="2026-01-15T00:07:00"), 502),
    ("non-existent date (Feb 30)", build_url(fecha_ini="2026-02-30T00:00:00", fecha_fin="2026-02-30T01:00:00"), 400),
    ("hour 24 instead of next-day 00", build_url(fecha_ini="2026-01-15T24:00:00", fecha_fin="2026-01-15T01:00:00"), 400),
    ("date without zero-padding", build_url(fecha_ini="2026-1-15T00:00:00", fecha_fin=CACHED_END), 200),
    ("space instead of T separator", build_url(fecha_ini="2026-01-15 00:00:00", fecha_fin=CACHED_END), 400),
    ("completely malformed date", build_url(fecha_ini="not-a-date", fecha_fin=CACHED_END), 400),

    # --- Station ---
    ("invalid station code", build_url(estacion="99999"), 400),
    ("empty station code", build_url(estacion=""), 404),  # likely a URL-routing 404, not a 400

    # --- fields ---
    ("duplicate fields", build_url(query={"fields": "temperature,temperature"}), 200),
    ("mix of valid and invalid fields", build_url(query={"fields": "temperature,foo"}), 400),
    ("field name with wrong case", build_url(query={"fields": "Temperature"}), 400),
    ("fields with stray spaces", build_url(query={"fields": " temperature , speed "}), 200),

    # --- aggregation ---
    ("aggregation in uppercase", build_url(query={"aggregation": "HOURLY"}), 200),
    ("unknown aggregation value", build_url(query={"aggregation": "yearly"}), 400),

    # --- location ---
    ("location as zero offset", build_url(query={"location": "+00:00"}), 200),
    ("location as lowercase IANA name (should fail, case-sensitive)", build_url(query={"location": "europe/berlin"}), 400),
    ("location with non-standard minute offset", build_url(query={"location": "+05:45"}), 200),
    ("unknown IANA location", build_url(query={"location": "Europe/Atlantida"}), 400),
    ("malformed offset", build_url(query={"location": "+2"}), 400),

    # --- Cross-parameter combinations ---
    ("invalid station AND malformed date together", build_url(fecha_ini="not-a-date", estacion="99999"), 400),
    ("all optional params valid together", build_url(query={"fields": "temperature", "aggregation": "hourly", "location": "+01:00"}), 200),

    # --- Injection / hostile input ---
    ("SQL-injection-like station value", build_url(estacion="89070' OR '1'='1"), 400),
    # Known gap: no length limit enforced on query params. Low priority
    # (doesn't produce incorrect results, only wasted processing).
    # Documented here and in the README as an accepted limitation.
    ("very long fields value", build_url(query={"fields": "temperature," * 200}), 200),
]


def run():
    passed = 0
    failed = 0
    for name, url, expected_status in CASES:
        try:
            response = requests.get(url, timeout=10)
        except requests.RequestException as exc:
            print(f"ERROR   {name}: request failed ({exc})")
            failed += 1
            continue

        if response.status_code == expected_status:
            print(f"PASS    {name} -> {response.status_code}")
            passed += 1
        else:
            print(
                f"FAIL    {name} -> got {response.status_code}, expected {expected_status} "
                f"(body: {response.text[:150]})"
            )
            failed += 1

    print(f"\n{passed} passed, {failed} failed, {len(CASES)} total")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    run()