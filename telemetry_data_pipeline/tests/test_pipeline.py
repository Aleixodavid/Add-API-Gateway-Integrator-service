"""Testes unitários do Telemetry Data Pipeline."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import tempfile
from schema_validator import SchemaValidator
from db_manager import TelemetryDBManager
from etl_engine import ETLEngine


class TestSchemaValidator:
    def setup_method(self):
        self.v = SchemaValidator()

    def test_valid_event(self):
        event = {"source": "sensor_a", "event_type": "temperature", "metric_value": 42.5}
        result = self.v.validate_event(event)
        assert result["valid"] is True

    def test_missing_required_fields(self):
        result = self.v.validate_event({})
        assert result["valid"] is False
        assert len(result["errors"]) == 3

    def test_invalid_event_type(self):
        event = {"source": "s", "event_type": "invalid_type", "metric_value": 1.0}
        result = self.v.validate_event(event)
        assert result["valid"] is False

    def test_invalid_metric_value(self):
        event = {"source": "s", "event_type": "temperature", "metric_value": "not_a_number"}
        result = self.v.validate_event(event)
        assert result["valid"] is False

    def test_out_of_range_value(self):
        event = {"source": "s", "event_type": "temperature", "metric_value": 2_000_000}
        result = self.v.validate_event(event)
        assert result["valid"] is False


class TestDBManager:
    def setup_method(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.db = TelemetryDBManager(self.tmp.name)

    def teardown_method(self):
        os.unlink(self.tmp.name)

    def test_insert_and_count(self):
        import time
        event = {
            "event_id": "test-001", "source": "s", "event_type": "temperature",
            "metric_name": "temp", "metric_value": 42.0, "unit": "celsius",
            "tags": {}, "timestamp": time.time(), "ingested_at": time.time()
        }
        self.db.insert_event(event)
        assert self.db.count_records() == 1

    def test_summary_report(self):
        import time
        for i in range(5):
            self.db.insert_event({
                "event_id": f"test-{i}", "source": "sensor", "event_type": "cpu_usage",
                "metric_name": "cpu", "metric_value": 50.0 + i, "unit": "percent",
                "tags": {}, "timestamp": time.time(), "ingested_at": time.time()
            })
        report = self.db.get_summary_report()
        assert report["total_events"] == 5
        assert report["unique_sources"] == 1


class TestETLEngine:
    def setup_method(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.db = TelemetryDBManager(self.tmp.name)
        self.etl = ETLEngine(self.db)

    def teardown_method(self):
        os.unlink(self.tmp.name)

    def test_transform_normalizes(self):
        raw = {"source": "  Sensor_A  ", "event_type": "TEMPERATURE", "metric_value": "42.5"}
        result = self.etl.transform(raw, "eid-001")
        assert result["source"] == "sensor_a"
        assert result["event_type"] == "temperature"
        assert result["metric_value"] == 42.5

    def test_generate_sample_events(self):
        events = self.etl.generate_sample_events(10)
        assert len(events) == 10
        assert self.db.count_records() == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
