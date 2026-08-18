"""Tests for the AEMET API client."""

import datetime

from unittest.mock import Mock, patch

from rest_framework.test import APITestCase

from django.test import TestCase

from django.urls import reverse

from .aemet_client import AemetApiError, fetch_antarctica_observations

from .cache import find_missing_ranges

from .models import Measurement




class FetchAntarcticaObservationsTests(TestCase):
    """Tests for fetch_antarctica_observations."""

    @patch("weather.aemet_client.requests.get")
    def test_returns_observations_on_success(self, mock_get):
        """When AEMET returns status 200 twice, the raw observations are returned."""
        first_response = Mock()
        first_response.json.return_value = {
            "descripcion": "exito",
            "estado": 200,
            "datos": "https://opendata.aemet.es/opendata/sh/fake-data-url",
        }

        second_response = Mock()
        second_response.json.return_value = [
            {"identificacion": "89070", "fhora": "2026-01-15T00:00:00Z", "temp": 2.2},
        ]

        mock_get.side_effect = [first_response, second_response]

        result = fetch_antarctica_observations(
            "2026-01-15T00:00:00UTC", "2026-01-15T01:00:00UTC", "89070"
        )

        self.assertEqual(result, second_response.json.return_value)
        self.assertEqual(mock_get.call_count, 2)

    @patch("weather.aemet_client.requests.get")
    def test_raises_aemet_api_error_when_no_data(self, mock_get):
        """When AEMET returns a non-200 estado, AemetApiError is raised."""
        first_response = Mock()
        first_response.json.return_value = {
            "descripcion": "No hay datos que satisfagan esos criterios",
            "estado": 404,
        }
        mock_get.return_value = first_response

        with self.assertRaises(AemetApiError):
            fetch_antarctica_observations(
                "2026-07-01T00:00:00UTC", "2026-07-02T00:00:00UTC", "89070"
            )

class AntarcticaDataViewTests(APITestCase):
    """Tests for the /api/antartida/datos/... endpoint."""

    def _build_url(self, fecha_ini="2026-01-15T00:00:00UTC", fecha_fin="2026-01-15T01:00:00UTC", estacion="89070"):
        return reverse(
            "antartida-datos",
            kwargs={
                "fecha_ini_str": fecha_ini,
                "fecha_fin_str": fecha_fin,
                "identificacion": estacion,
            },
        )

    @patch("weather.views.fetch_antarctica_observations")
    def test_returns_200_with_observations_on_success(self, mock_fetch):
        mock_fetch.return_value = [
            {"identificacion": "89070", "fhora": "2026-01-15T00:00:00Z", "temp": 2.2},
        ]

        response = self.client.get(self._build_url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, mock_fetch.return_value)
        mock_fetch.assert_called_once_with(
            fecha_ini="2026-01-15T00:00:00UTC",
            fecha_fin="2026-01-15T01:00:00UTC",
            estacion="89070",
        )

    @patch("weather.views.fetch_antarctica_observations")
    def test_returns_502_when_aemet_fails(self, mock_fetch):
        mock_fetch.side_effect = AemetApiError("No hay datos que satisfagan esos criterios")

        response = self.client.get(self._build_url(fecha_ini="2026-07-01T00:00:00UTC", fecha_fin="2026-07-02T00:00:00UTC"))

        self.assertEqual(response.status_code, 502)
        self.assertIn("error", response.data)

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

from .cache import get_observations


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