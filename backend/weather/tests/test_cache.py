"""Tests for the local cache: gap detection and AEMET orchestration."""

import datetime
from unittest.mock import patch

from django.test import TestCase

from ..cache import find_missing_ranges, get_observations, _split_into_chunks

from ..models import Measurement


class FindMissingRangesTests(TestCase):
    """Tests for the gap-detection logic in the local cache."""

    def setUp(self):
        self.station = "89070"
        self.base = datetime.datetime(2026, 1, 15, 0, 0, tzinfo=datetime.timezone.utc)

    def _create_measurement(self, minutes_offset):
        Measurement.objects.create(
            station=self.station,
            timestamp=self.base + datetime.timedelta(minutes=minutes_offset),
            temperature=2.0,
            pressure=983.0,
            speed=3.0,
        )

    def test_returns_empty_list_when_fully_cached(self):
        """No gaps are returned when every timestamp in the range is cached."""
        for minutes in (0, 10, 20):
            self._create_measurement(minutes)

        gaps = find_missing_ranges(self.station, self.base, self.base + datetime.timedelta(minutes=20))

        self.assertEqual(gaps, [])

    def test_returns_single_gap_between_cached_edges(self):
        """A contiguous gap between two cached edges is detected as one range."""
        for minutes in (0, 10, 20, 60):
            self._create_measurement(minutes)

        gaps = find_missing_ranges(self.station, self.base, self.base + datetime.timedelta(minutes=60))

        expected_gap = (
            self.base + datetime.timedelta(minutes=30),
            self.base + datetime.timedelta(minutes=50),
        )
        self.assertEqual(gaps, [expected_gap])

    def test_returns_full_range_when_nothing_cached(self):
        """The whole range is one gap when nothing has been cached yet."""
        gaps = find_missing_ranges(self.station, self.base, self.base + datetime.timedelta(minutes=20))

        expected_gap = (self.base, self.base + datetime.timedelta(minutes=20))
        self.assertEqual(gaps, [expected_gap])

    def test_returns_two_separate_gaps(self):
        """Two non-adjacent gaps are returned as two separate ranges."""
        # Cached: 00:10 only. Missing: 00:00 and 00:20-00:30 (two separate gaps).
        self._create_measurement(10)

        gaps = find_missing_ranges(self.station, self.base, self.base + datetime.timedelta(minutes=30))

        expected_gaps = [
            (self.base, self.base),
            (self.base + datetime.timedelta(minutes=20), self.base + datetime.timedelta(minutes=30)),
        ]
        self.assertEqual(gaps, expected_gaps)


class GetObservationsTests(TestCase):
    """Tests for get_observations: the cache + AEMET orchestration."""

    def setUp(self):
        self.station = "89070"
        self.base = datetime.datetime(2026, 1, 15, 0, 0, tzinfo=datetime.timezone.utc)

    @patch("weather.cache.fetch_antarctica_observations")
    def test_does_not_call_aemet_when_fully_cached(self, mock_fetch):
        """No AEMET calls are made when the requested range is fully cached."""
        Measurement.objects.create(
            station=self.station, timestamp=self.base, temperature=1.0, pressure=1.0, speed=1.0
        )

        result = get_observations(self.station, self.base, self.base)

        mock_fetch.assert_not_called()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].temperature, 1.0)

    @patch("weather.cache.fetch_antarctica_observations")
    def test_fetches_and_stores_missing_gap(self, mock_fetch):
        """A missing gap is fetched from AEMET once and stored in the cache."""
        mock_fetch.return_value = [
            {
                "identificacion": self.station,
                "fhora": "2026-01-15T00:00:00Z",
                "temp": 2.2,
                "pres": 983.3,
                "vel": 3.8,
            },
        ]

        result = get_observations(self.station, self.base, self.base)

        mock_fetch.assert_called_once_with(
            fecha_ini="2026-01-15T00:00:00UTC",
            fecha_fin="2026-01-15T00:00:00UTC",
            estacion=self.station,
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].temperature, 2.2)
        self.assertEqual(Measurement.objects.count(), 1)

    @patch("weather.cache.fetch_antarctica_observations")
    def test_stores_nan_fields_as_none(self, mock_fetch):
        """Fields reported as the string "NaN" by AEMET are stored as None."""
        mock_fetch.return_value = [
            {
                "identificacion": self.station,
                "fhora": "2026-01-15T00:00:00Z",
                "temp": "NaN",
                "pres": 983.3,
                "vel": 3.8,
            },
        ]

        result = get_observations(self.station, self.base, self.base)

        self.assertIsNone(result[0].temperature)

class SplitIntoChunksTests(TestCase):
    """Tests for splitting large ranges into AEMET-sized sub-ranges."""

    def test_returns_single_chunk_when_range_within_limit(self):
        start = datetime.datetime(2026, 1, 15, 0, 0, tzinfo=datetime.timezone.utc)
        end = datetime.datetime(2026, 1, 15, 1, 0, tzinfo=datetime.timezone.utc)

        chunks = _split_into_chunks(start, end, max_days=30)

        self.assertEqual(chunks, [(start, end)])

    def test_splits_range_longer_than_max_days(self):
        start = datetime.datetime(2026, 1, 1, 0, 0, tzinfo=datetime.timezone.utc)
        end = datetime.datetime(2026, 2, 15, 0, 0, tzinfo=datetime.timezone.utc)  # 45 days

        chunks = _split_into_chunks(start, end, max_days=30)

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0], (start, start + datetime.timedelta(days=30)))
        self.assertEqual(chunks[1][1], end)

    def test_chunks_do_not_overlap(self):
        start = datetime.datetime(2026, 1, 1, 0, 0, tzinfo=datetime.timezone.utc)
        end = datetime.datetime(2026, 2, 15, 0, 0, tzinfo=datetime.timezone.utc)

        chunks = _split_into_chunks(start, end, max_days=30)

        for (_, first_end), (second_start, _) in zip(chunks, chunks[1:]):
            self.assertEqual(second_start - first_end, datetime.timedelta(minutes=10))

    def test_covers_the_entire_original_range(self):
        start = datetime.datetime(2026, 1, 1, 0, 0, tzinfo=datetime.timezone.utc)
        end = datetime.datetime(2026, 3, 10, 0, 0, tzinfo=datetime.timezone.utc)  # ~68 days

        chunks = _split_into_chunks(start, end, max_days=30)

        self.assertEqual(chunks[0][0], start)
        self.assertEqual(chunks[-1][1], end)