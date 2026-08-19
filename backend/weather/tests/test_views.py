"""Tests for the /api/antartida/datos/... endpoint."""

import datetime
from unittest.mock import patch

from django.urls import reverse
from rest_framework.test import APITestCase

from ..aemet_client import AemetApiError
from ..models import Measurement


class AntarcticaDataViewTests(APITestCase):
    """Tests for the /api/antartida/datos/... endpoint."""

    def _build_url(self, fecha_ini="2026-01-15T00:00:00", fecha_fin="2026-01-15T01:00:00", estacion="89070"):
        return reverse(
            "antartida-datos",
            kwargs={
                "fecha_ini_str": fecha_ini,
                "fecha_fin_str": fecha_fin,
                "identificacion": estacion,
            },
        )

    @patch("weather.views.get_observations")
    def test_returns_200_with_observations_on_success(self, mock_get_observations):
        measurement = Measurement(
            station="89070",
            timestamp=datetime.datetime(2026, 1, 15, 0, 0, tzinfo=datetime.timezone.utc),
            temperature=2.2,
            pressure=983.3,
            speed=3.8,
        )
        mock_get_observations.return_value = [measurement]

        response = self.client.get(self._build_url())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["Temperature (ºC)"], 2.2)
        mock_get_observations.assert_called_once_with(
            "89070",
            datetime.datetime(2026, 1, 15, 0, 0, tzinfo=datetime.timezone.utc),
            datetime.datetime(2026, 1, 15, 1, 0, tzinfo=datetime.timezone.utc),
        )

    @patch("weather.views.get_observations")
    def test_returns_502_when_aemet_fails(self, mock_get_observations):
        mock_get_observations.side_effect = AemetApiError("No hay datos que satisfagan esos criterios")

        response = self.client.get(
            self._build_url(fecha_ini="2026-07-01T00:00:00", fecha_fin="2026-07-02T00:00:00")
        )

        self.assertEqual(response.status_code, 502)
        self.assertIn("error", response.data)

    def test_returns_400_for_malformed_date(self):
        response = self.client.get(self._build_url(fecha_ini="not-a-date"))

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

    def test_returns_400_for_invalid_station(self):
        response = self.client.get(self._build_url(estacion="99999"))

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

    @patch("weather.views.get_observations")
    def test_filters_response_to_requested_fields(self, mock_get_observations):
        measurement = Measurement(
            station="89070",
            timestamp=datetime.datetime(2026, 1, 15, 0, 0, tzinfo=datetime.timezone.utc),
            temperature=2.2,
            pressure=983.3,
            speed=3.8,
        )
        mock_get_observations.return_value = [measurement]

        response = self.client.get(self._build_url() + "?fields=temperature")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Temperature (ºC)", response.data[0])
        self.assertNotIn("Pressure (hpa)", response.data[0])

    def test_returns_400_for_invalid_field(self):
        response = self.client.get(self._build_url() + "?fields=humidity")

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)

    @patch("weather.views.get_observations")
    def test_returns_all_fields_when_no_fields_param(self, mock_get_observations):
        measurement = Measurement(
            station="89070",
            timestamp=datetime.datetime(2026, 1, 15, 0, 0, tzinfo=datetime.timezone.utc),
            temperature=2.2,
            pressure=983.3,
            speed=3.8,
        )
        mock_get_observations.return_value = [measurement]

        response = self.client.get(self._build_url())

        self.assertIn("Temperature (ºC)", response.data[0])
        self.assertIn("Pressure (hpa)", response.data[0])
        self.assertIn("Speed (m/s)", response.data[0])

    @patch("weather.views.get_observations")
    def test_aggregates_response_when_requested(self, mock_get_observations):
        base = datetime.datetime(2026, 1, 15, 0, 0, tzinfo=datetime.timezone.utc)
        mock_get_observations.return_value = [
            Measurement(
                station="89070",
                timestamp=base,
                temperature=2.0,
                pressure=983.0,
                speed=3.0,
            ),
            Measurement(
                station="89070",
                timestamp=base + datetime.timedelta(minutes=30),
                temperature=4.0,
                pressure=983.0,
                speed=3.0,
            ),
        ]

        response = self.client.get(self._build_url() + "?aggregation=hourly")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["Temperature (ºC)"], 3.0)

    def test_returns_400_for_invalid_aggregation(self):
        response = self.client.get(self._build_url() + "?aggregation=yearly")

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)