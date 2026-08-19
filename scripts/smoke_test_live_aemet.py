"""Adversarial smoke tests against the local server, backed by the real AEMET API.

Run with the dev server running (python manage.py runserver), then:
    python scripts/smoke_test_live_aemet.py

Unlike smoke_test_validation.py, these tests intentionally trigger
real calls to AEMET on first run (they consume API quota). Re-running
this script later should be fast, since the ranges used here get
cached after the first run.
"""

import sys
import time
import urllib.parse

import requests

BASE_URL = "http://127.0.0.1:8000/api/antartida/datos"

GABRIEL_DE_CASTILLA = "89070"
JUAN_CARLOS_I = "89064"

# Known to have real data (Antarctic summer campaign).
SUMMER_START = "2026-01-10T00:00:00"
SUMMER_END = "2026-01-10T06:00:00"

# Known to have no data (Antarctic winter, stations offline).
WINTER_START = "2026-07-01T00:00:00"
WINTER_END = "2026-07-02T00:00:00"


def build_url(fecha_ini, fecha_fin, estacion, query=None):
    path = f"{BASE_URL}/fechaini/{fecha_ini}/fechafin/{fecha_fin}/estacion/{estacion}"
    if query:
        path += "?" + urllib.parse.urlencode(query)
    return path


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"{status}    {name}" + (f" ({detail})" if detail else ""))
    return condition


def test_cache_idempotency():
    url = build_url(SUMMER_START, SUMMER_END, GABRIEL_DE_CASTILLA)

    start = time.monotonic()
    first_response = requests.get(url, timeout=30)
    first_duration = time.monotonic() - start

    start = time.monotonic()
    second_response = requests.get(url, timeout=30)
    second_duration = time.monotonic() - start

    results = []
    results.append(
        check(
            "first request succeeds",
            first_response.status_code == 200,
            f"status={first_response.status_code}",
        )
    )
    results.append(
        check(
            "second request succeeds",
            second_response.status_code == 200,
            f"status={second_response.status_code}",
        )
    )
    results.append(
        check(
            "second request is faster than the first (cache hit)",
            second_duration < first_duration,
            f"first={first_duration:.3f}s, second={second_duration:.3f}s",
        )
    )
    results.append(
        check(
            "both responses return the same data",
            first_response.json() == second_response.json(),
        )
    )
    return results


def test_partial_overlap():
    # First half of the range, then the full range (new second half).
    half_url = build_url(SUMMER_START, "2026-01-10T03:00:00", GABRIEL_DE_CASTILLA)
    requests.get(half_url, timeout=30)  # warm the first half into cache

    full_url = build_url(SUMMER_START, SUMMER_END, GABRIEL_DE_CASTILLA)
    start = time.monotonic()
    response = requests.get(full_url, timeout=30)
    duration = time.monotonic() - start

    return [
        check("partial overlap request succeeds", response.status_code == 200),
        check(
            "partial overlap completes reasonably fast (only fetched the gap)",
            duration < 15,
            f"duration={duration:.3f}s",
        ),
    ]


def test_large_realistic_range():
    url = build_url(SUMMER_START, "2026-01-12T00:00:00", GABRIEL_DE_CASTILLA)
    response = requests.get(url, timeout=60)

    results = [check("multi-day range succeeds", response.status_code == 200)]
    if response.status_code == 200:
        count = len(response.json())
        # ~6 points/hour * 48 hours = ~288, allow some slack.
        results.append(
            check(
                "returns a plausible number of points",
                200 <= count <= 350,
                f"count={count}",
            )
        )
    return results


def test_winter_no_data_propagates_correctly():
    url = build_url(WINTER_START, WINTER_END, GABRIEL_DE_CASTILLA)
    response = requests.get(url, timeout=30)

    return [
        check(
            "winter range with no data returns 502",
            response.status_code == 502,
            f"status={response.status_code}",
        )
    ]


def test_both_stations_have_data():
    results = []
    for name, station in [("Gabriel de Castilla", GABRIEL_DE_CASTILLA), ("Juan Carlos I", JUAN_CARLOS_I)]:
        url = build_url(SUMMER_START, SUMMER_END, station)
        response = requests.get(url, timeout=30)
        results.append(
            check(f"{name} ({station}) returns data", response.status_code == 200)
        )
    return results


def run():
    all_results = []
    all_results += test_cache_idempotency()
    all_results += test_partial_overlap()
    all_results += test_large_realistic_range()
    all_results += test_winter_no_data_propagates_correctly()
    all_results += test_both_stations_have_data()

    passed = sum(1 for r in all_results if r)
    failed = len(all_results) - passed
    print(f"\n{passed} passed, {failed} failed, {len(all_results)} total")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    run()