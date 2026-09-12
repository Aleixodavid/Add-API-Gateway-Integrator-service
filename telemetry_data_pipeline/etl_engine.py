"""ETL Engine — Motor de Extração, Transformação e Carga."""

import time
import uuid
import random
import logging

logger = logging.getLogger("ETLEngine")


class ETLEngine:
    """Motor ETL para processamento de eventos de telemetria."""

    def __init__(self, db_manager):
        self.db = db_manager

    def transform(self, raw_event: dict, event_id: str = None) -> dict:
        """
        Transforma um evento bruto em formato normalizado para carga.
        Aplica sanitização, normalização de campos e enriquecimento.
        """
        event_id = event_id or str(uuid.uuid4())
        return {
            "event_id": event_id,
            "source": str(raw_event.get("source", "unknown")).strip().lower(),
            "event_type": str(raw_event.get("event_type", "generic")).strip().lower(),
            "metric_name": str(raw_event.get("metric_name", "")).strip(),
            "metric_value": float(raw_event.get("metric_value", 0)),
            "unit": str(raw_event.get("unit", "count")).strip().lower(),
            "tags": raw_event.get("tags", {}),
            "timestamp": raw_event.get("timestamp", time.time()),
            "ingested_at": time.time(),
        }

    def load(self, transformed_event: dict):
        """Carrega evento transformado no banco de dados."""
        self.db.insert_event(transformed_event)
        logger.debug(f"[ETL] Evento carregado: {transformed_event['event_id']}")

    def generate_sample_events(self, count: int = 50) -> list:
        """Gera eventos simulados de telemetria para demonstração."""
        sources = ["sensor_alpha", "sensor_beta", "gateway_01", "monitor_central", "edge_node_03"]
        event_types = ["temperature", "cpu_usage", "memory_usage", "network_latency", "disk_io"]
        units = {"temperature": "celsius", "cpu_usage": "percent", "memory_usage": "percent",
                 "network_latency": "ms", "disk_io": "mbps"}

        events = []
        base_time = time.time() - (count * 60)

        for i in range(count):
            etype = random.choice(event_types)
            if etype == "temperature":
                value = round(random.uniform(20.0, 95.0), 2)
            elif etype in ("cpu_usage", "memory_usage"):
                value = round(random.uniform(5.0, 99.0), 2)
            elif etype == "network_latency":
                value = round(random.uniform(1.0, 500.0), 2)
            else:
                value = round(random.uniform(10.0, 1000.0), 2)

            event = {
                "source": random.choice(sources),
                "event_type": etype,
                "metric_name": f"{etype}_reading",
                "metric_value": value,
                "unit": units.get(etype, "count"),
                "tags": {"environment": random.choice(["production", "staging"]), "region": random.choice(["us-east", "eu-west", "br-south"])},
                "timestamp": base_time + (i * 60),
            }
            event_id = str(uuid.uuid4())
            transformed = self.transform(event, event_id)
            self.load(transformed)
            events.append(transformed)

        logger.info(f"[ETL] {count} eventos simulados gerados e carregados.")
        return events
