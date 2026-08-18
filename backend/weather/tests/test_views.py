"""Tests for the /api/antartida/datos/... endpoint."""

from unittest.mock import patch

from django.urls import reverse
from rest_framework.test import APITestCase

from ..aemet_client import AemetApiError


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

        response = self.client.get(
            self._build_url(fecha_ini="2026-07-01T00:00:00UTC", fecha_fin="2026-07-02T00:00:00UTC")
        )

        self.assertEqual(response.status_code, 502)
        self.assertIn("error", response.data)