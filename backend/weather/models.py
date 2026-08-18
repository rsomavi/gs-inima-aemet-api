"""Database models for cached AEMET observations."""

from django.db import models


class Measurement(models.Model):
    """A single 10-minute weather observation from an Antarctic station.

    Acts as a local cache of AEMET's data: once a (station, timestamp)
    observation is stored, it never changes and never needs to be
    re-fetched from AEMET.
    """

    station = models.CharField(max_length=10, help_text="AEMET station indicativo, e.g. '89070'.")
    timestamp = models.DateTimeField(help_text="Observation datetime, stored in UTC.")
    temperature = models.FloatField(null=True, blank=True, help_text="Temperature in °C.")
    pressure = models.FloatField(null=True, blank=True, help_text="Pressure in hPa.")
    speed = models.FloatField(null=True, blank=True, help_text="Wind speed in m/s.")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["station", "timestamp"], name="unique_station_timestamp"),
        ]
        indexes = [
            models.Index(fields=["station", "timestamp"]),
        ]
        ordering = ["timestamp"]

    def __str__(self):
        return f"{self.station} @ {self.timestamp.isoformat()}"