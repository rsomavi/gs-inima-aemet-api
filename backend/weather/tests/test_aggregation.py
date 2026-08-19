"""Tests for measurement aggregation (hourly, daily, monthly)."""

import datetime

from django.test import TestCase

from ..aggregation import AggregatedMeasurement, aggregate_measurements
from ..models import Measurement


def _measurement(hour_offset_minutes, temperature=2.0, pressure=983.0, speed=3.0, station="89070"):
    """Build a Measurement at a fixed base time plus an offset, for test brevity."""
    base = datetime.datetime(2026, 1, 15, 0, 0, tzinfo=datetime.timezone.utc)
    return Measurement(
        station=station,
        timestamp=base + datetime.timedelta(minutes=hour_offset_minutes),
        temperature=temperature,
        pressure=pressure,
        speed=speed,
    )


class AggregateMeasurementsNoneTests(TestCase):
    """Tests for aggregation="none" (no-op)."""

    def test_returns_measurements_unchanged(self):
        measurements = [_measurement(0), _measurement(10)]

        result = aggregate_measurements(measurements, "none")

        self.assertEqual(result, measurements)


class AggregateMeasurementsHourlyTests(TestCase):
    """Tests for aggregation="hourly"."""

    def test_groups_measurements_within_the_same_hour(self):
        measurements = [_measurement(0, temperature=2.0), _measurement(30, temperature=4.0)]

        result = aggregate_measurements(measurements, "hourly")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].temperature, 3.0)

    def test_separates_measurements_in_different_hours(self):
        measurements = [_measurement(0), _measurement(70)]  # 00:00 and 01:10

        result = aggregate_measurements(measurements, "hourly")

        self.assertEqual(len(result), 2)

    def test_bucket_timestamp_is_the_start_of_the_hour(self):
        measurements = [_measurement(45)]  # 00:45

        result = aggregate_measurements(measurements, "hourly")

        self.assertEqual(
            result[0].timestamp, datetime.datetime(2026, 1, 15, 0, 0, tzinfo=datetime.timezone.utc)
        )

    def test_results_are_sorted_chronologically(self):
        measurements = [_measurement(130), _measurement(0)]  # 02:10 and 00:00, given out of order

        result = aggregate_measurements(measurements, "hourly")

        self.assertTrue(result[0].timestamp < result[1].timestamp)


class AggregateMeasurementsAverageTests(TestCase):
    """Tests for how None values are handled when averaging."""

    def test_ignores_none_values_when_averaging(self):
        m1 = _measurement(0, temperature=10.0)
        m2 = _measurement(10, temperature=None)
        m3 = _measurement(20, temperature=20.0)

        result = aggregate_measurements([m1, m2, m3], "hourly")

        self.assertEqual(result[0].temperature, 15.0)  # average of 10.0 and 20.0 only

    def test_returns_none_when_all_values_are_missing(self):
        m1 = _measurement(0, temperature=None)
        m2 = _measurement(10, temperature=None)

        result = aggregate_measurements([m1, m2], "hourly")

        self.assertIsNone(result[0].temperature)


class AggregateMeasurementsDailyTimezoneTests(TestCase):
    """Confirms daily aggregation groups by the Madrid calendar day, not the UTC day."""

    def test_late_utc_measurement_joins_the_next_madrid_day(self):
        # 23:30 UTC on Jan 14 is already 00:30 on Jan 15 in Madrid (CET, +1h).
        late_previous_day_utc = Measurement(
            station="89070",
            timestamp=datetime.datetime(2026, 1, 14, 23, 30, tzinfo=datetime.timezone.utc),
            temperature=10.0,
            pressure=1000.0,
            speed=1.0,
        )
        # 10:00 UTC on Jan 15 is clearly within Jan 15 in Madrid too.
        mid_day_utc = Measurement(
            station="89070",
            timestamp=datetime.datetime(2026, 1, 15, 10, 0, tzinfo=datetime.timezone.utc),
            temperature=20.0,
            pressure=1000.0,
            speed=1.0,
        )

        result = aggregate_measurements([late_previous_day_utc, mid_day_utc], "daily")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].temperature, 15.0)

    def test_daily_bucket_timestamp_is_midnight_madrid_in_utc(self):
        # Jan 15 00:00 in Madrid (CET, +1h) is Jan 14 23:00 in UTC.
        measurement = Measurement(
            station="89070",
            timestamp=datetime.datetime(2026, 1, 15, 10, 0, tzinfo=datetime.timezone.utc),
            temperature=2.0,
            pressure=983.0,
            speed=3.0,
        )

        result = aggregate_measurements([measurement], "daily")

        self.assertEqual(
            result[0].timestamp,
            datetime.datetime(2026, 1, 14, 23, 0, tzinfo=datetime.timezone.utc),
        )


class AggregateMeasurementsMonthlyTests(TestCase):
    """Tests for aggregation="monthly"."""

    def test_groups_measurements_within_the_same_madrid_month(self):
        m1 = Measurement(
            station="89070",
            timestamp=datetime.datetime(2026, 1, 5, 10, 0, tzinfo=datetime.timezone.utc),
            temperature=10.0, pressure=1000.0, speed=1.0,
        )
        m2 = Measurement(
            station="89070",
            timestamp=datetime.datetime(2026, 1, 25, 10, 0, tzinfo=datetime.timezone.utc),
            temperature=20.0, pressure=1000.0, speed=1.0,
        )

        result = aggregate_measurements([m1, m2], "monthly")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].temperature, 15.0)

    def test_separates_measurements_in_different_months(self):
        m1 = Measurement(
            station="89070",
            timestamp=datetime.datetime(2026, 1, 25, 10, 0, tzinfo=datetime.timezone.utc),
            temperature=10.0, pressure=1000.0, speed=1.0,
        )
        m2 = Measurement(
            station="89070",
            timestamp=datetime.datetime(2026, 2, 5, 10, 0, tzinfo=datetime.timezone.utc),
            temperature=20.0, pressure=1000.0, speed=1.0,
        )

        result = aggregate_measurements([m1, m2], "monthly")

        self.assertEqual(len(result), 2)


class AggregateMeasurementsDstTests(TestCase):
    """Confirms daily aggregation still works across DST-affected days (23h/25h days)."""

    def test_spring_forward_day_aggregates_correctly(self):
        """March 29, 2026 has 23 hours in Madrid; measurements should still group as one day."""
        m1 = Measurement(
            station="89070",
            timestamp=datetime.datetime(2026, 3, 28, 23, 30, tzinfo=datetime.timezone.utc),  # 00:30 Madrid (CET)
            temperature=10.0, pressure=1000.0, speed=1.0,
        )
        m2 = Measurement(
            station="89070",
            timestamp=datetime.datetime(2026, 3, 29, 20, 0, tzinfo=datetime.timezone.utc),  # 22:00 Madrid (CEST)
            temperature=20.0, pressure=1000.0, speed=1.0,
        )

        result = aggregate_measurements([m1, m2], "daily")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].temperature, 15.0)