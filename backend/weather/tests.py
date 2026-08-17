"""Tests for the AEMET API client."""

from unittest.mock import Mock, patch

from django.test import TestCase

from .aemet_client import AemetApiError, fetch_antarctica_observations


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