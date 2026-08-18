"""Tests for the AEMET API client."""

from unittest.mock import Mock, patch

from rest_framework.test import APITestCase

from django.test import TestCase

from django.urls import reverse

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