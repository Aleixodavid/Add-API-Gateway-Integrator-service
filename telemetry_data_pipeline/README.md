# 📊 Telemetry Data Pipeline

> **Pipeline Assíncrono de Extração, Transformação e Carga (ETL) & Observabilidade**  
> Microsserviço de alta performance para ingestão, sanitização, estruturação e análise agregada de dados de telemetria.

---

## 🎯 Objetivo do Subprograma

O **Telemetry Data Pipeline** é responsável pela coleta volumétrica de métricas de telemetria (temperatura, uso de CPU, memória, latência de rede, I/O de disco) originadas de nós periféricos e microsserviços. Ele executa a validação rigorosa dos esquemas de dados, normalização de tipos e persistência otimizada para consultas analíticas de baixa latência.

---

## 🏛️ Arquitetura & Padrões de Projeto (*Design Patterns*)

### 1. **Motor ETL (Extract, Transform, Load)**
- **Arquivo:** `etl_engine.py`
- **Etapas:**
  - **Extração:** Recepção de dados via requisições HTTP RESTful em lote (*batch*) ou eventos individuais.
  - **Transformação:** Higienização de strings, conversão de unidades, timestamping UNIX e enriquecimento de metadados/tags.
  - **Carga:** Inserção otimizada no banco SQLite relacional.

### 2. **Validador de Schema (Schema Validator)**
- **Arquivo:** `schema_validator.py`
- **Validações:**
  - Verificação de campos obrigatórios (`source`, `event_type`, `metric_value`).
  - Restrição de domínio para tipos de evento (`cpu_usage`, `memory_usage`, `temperature`, `network_latency`, `disk_io`).
  - Checagem de limites numéricos sanitizados ($[-1.000.000, 1.000.000]$).

### 3. **SQLite com WAL Mode & Índices Compostos**
- **Arquivo:** `db_manager.py`
- **Otimizações de Banco:**
  - `PRAGMA journal_mode=WAL`: Permite leituras simultâneas sem bloquear gravações.
  - `PRAGMA synchronous=NORMAL` + `cache_size=-4000`: Máxima eficiência em operações de I/O em disco no Windows.
  - **Índices Compostos:** `(source, event_type)` e `(event_timestamp DESC)` para responder a consultas agregadas em tempo **< 150ms**.

---

## 🔒 Sanitização & Segurança

- **Chaves de Acesso:** Configuradas com o placeholder estático `TEST_TOKEN_API_KEY_001`.
- **Identificadores:** Utilizam identificadores neutros de teste corporativo (`TEST_CLIENT_SAMPLE_ID`).
- **Autenticação:** Protegida por autenticação HTTP Basic (`admin` / `admin`).

---

## 📡 Endpoints da API (Porta `5002`)

### `POST /api/ingest`
Ingere um evento individual de telemetria.
- **Body Exemplo:**
  ```json
  {
    "source": "sensor_alpha",
    "event_type": "cpu_usage",
    "metric_value": 45.2,
    "unit": "percent",
    "tags": { "env": "production" }
  }
  ```

### `POST /api/ingest/batch`
Ingere múltiplos eventos em uma única requisição com validação individual.

### `POST /api/generate-sample`
Gera e ingere eventos sintéticos para simulação de carga (entre 50 e 1000 registros).

### `GET /api/reports/summary`
Retorna estatísticas consolidadas (total de eventos, fontes únicas, médias, mínimos e máximos).

### `GET /api/reports/by-source`
Agrupa o volume e a média das métricas por fonte de origem.

### `GET /api/reports/by-period?granularity=hour`
Agrupa métricas agregadas por intervalos de hora ou dia.

---

## 🧪 Testes Unitários

Para executar os testes do Pipeline de Telemetria:

```bash
cd D:\Pessoal\portifolio\telemetry_data_pipeline
python -m pytest tests/ -v
```
