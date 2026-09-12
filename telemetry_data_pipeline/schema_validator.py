"""Schema Validator — Validação de schema de eventos de telemetria."""


class SchemaValidator:
    """Validador de schema para eventos de telemetria."""

    REQUIRED_FIELDS = ["source", "event_type", "metric_value"]
    VALID_EVENT_TYPES = {"temperature", "cpu_usage", "memory_usage", "network_latency",
                         "disk_io", "error_rate", "request_count", "generic"}
    MAX_METRIC_VALUE = 1_000_000
    MIN_METRIC_VALUE = -1_000_000

    def validate_event(self, event: dict) -> dict:
        """
        Valida um evento de telemetria contra o schema esperado.

        Returns:
            {"valid": True/False, "errors": [...]}
        """
        errors = []

        if not isinstance(event, dict):
            return {"valid": False, "errors": ["Event must be a JSON object"]}

        for field in self.REQUIRED_FIELDS:
            if field not in event or event[field] is None:
                errors.append(f"Missing required field: '{field}'")

        if "source" in event:
            source = str(event["source"]).strip()
            if len(source) < 1 or len(source) > 100:
                errors.append("Field 'source' must be 1-100 characters")

        if "event_type" in event:
            etype = str(event["event_type"]).strip().lower()
            if etype not in self.VALID_EVENT_TYPES:
                errors.append(f"Invalid event_type: '{etype}'. Valid: {self.VALID_EVENT_TYPES}")

        if "metric_value" in event:
            try:
                val = float(event["metric_value"])
                if val < self.MIN_METRIC_VALUE or val > self.MAX_METRIC_VALUE:
                    errors.append(f"metric_value out of range [{self.MIN_METRIC_VALUE}, {self.MAX_METRIC_VALUE}]")
            except (ValueError, TypeError):
                errors.append("metric_value must be numeric")

        if "tags" in event and not isinstance(event.get("tags"), dict):
            errors.append("Field 'tags' must be a JSON object")

        return {"valid": len(errors) == 0, "errors": errors}
