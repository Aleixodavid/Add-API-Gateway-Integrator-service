"""
Telemetry Data Pipeline — Pipeline ETL Assíncrono
Arquitetura: Extração, Transformação e Carga (ETL) de eventos de telemetria
simulados em banco relacional SQLite com índices de alta performance.

Credenciais de demonstração: admin / admin
"""

import os
import json
import time
import uuid
import logging
import threading
from flask import Flask, request, jsonify

from etl_engine import ETLEngine
from schema_validator import SchemaValidator
from db_manager import TelemetryDBManager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

def load_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

config = load_config()

logging.basicConfig(level=logging.INFO, format="%(asctime)s — %(name)s — %(levelname)s — %(message)s")
logger = logging.getLogger("TelemetryPipeline")

app = Flask(__name__)
app.secret_key = config.get("secret_key", "telemetry_demo_secret")

db = TelemetryDBManager(os.path.join(BASE_DIR, "metrics.db"))
etl = ETLEngine(db)
validator = SchemaValidator()


def check_auth():
    auth = request.authorization
    if auth and auth.username == "admin" and auth.password == "admin":
        return True
    data = request.get_json(silent=True) or {}
    return data.get("username") == "admin" and data.get("password") == "admin"


@app.route("/api/health")
def health():
    return jsonify({
        "status": "online",
        "service": "Telemetry Data Pipeline",
        "version": "1.0.0",
        "db_path": db.db_path,
        "records_count": db.count_records(),
    })


@app.route("/api/ingest", methods=["POST"])
def ingest_event():
    """Ingere um evento de telemetria individual."""
    data = request.get_json(silent=True) or {}
    event_id = str(uuid.uuid4())

    validation = validator.validate_event(data)
    if not validation["valid"]:
        return jsonify({"error": "Schema validation failed", "details": validation["errors"]}), 400

    transformed = etl.transform(data, event_id)
    etl.load(transformed)

    return jsonify({"status": "ingested", "event_id": event_id})


@app.route("/api/ingest/batch", methods=["POST"])
def ingest_batch():
    """Ingere um lote de eventos de telemetria."""
    data = request.get_json(silent=True) or {}
    events = data.get("events", [])
    results = {"ingested": 0, "rejected": 0, "errors": []}

    for i, event in enumerate(events):
        validation = validator.validate_event(event)
        if not validation["valid"]:
            results["rejected"] += 1
            results["errors"].append({"index": i, "errors": validation["errors"]})
            continue
        event_id = str(uuid.uuid4())
        transformed = etl.transform(event, event_id)
        etl.load(transformed)
        results["ingested"] += 1

    return jsonify(results)


@app.route("/api/generate-sample", methods=["POST"])
def generate_sample():
    """Gera e ingere eventos de telemetria simulados para demonstração."""
    data = request.get_json(silent=True) or {}
    count = min(data.get("count", 50), 1000)
    events = etl.generate_sample_events(count)
    return jsonify({"status": "ok", "events_generated": len(events)})


@app.route("/api/reports/summary")
def report_summary():
    """Relatório agregado de métricas."""
    return jsonify(db.get_summary_report())


@app.route("/api/reports/by-source")
def report_by_source():
    """Relatório agrupado por fonte de dados."""
    return jsonify(db.get_report_by_source())


@app.route("/api/reports/by-period")
def report_by_period():
    """Relatório agrupado por período (hora/dia)."""
    granularity = request.args.get("granularity", "hour")
    return jsonify(db.get_report_by_period(granularity))


@app.route("/api/events")
def list_events():
    """Lista eventos com paginação."""
    limit = min(int(request.args.get("limit", 50)), 500)
    offset = int(request.args.get("offset", 0))
    return jsonify(db.list_events(limit, offset))


if __name__ == "__main__":
    print("=" * 60)
    print("  Telemetry Data Pipeline — ETL Assíncrono")
    print("  Credenciais: admin / admin")
    print("  Endpoint: http://127.0.0.1:5002")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5002, debug=False)
