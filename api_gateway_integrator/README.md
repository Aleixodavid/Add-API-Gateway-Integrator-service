# 🛡️ API Gateway Integrator

> **Microsserviço de Roteamento, Resiliência e Controle de Trafego**  
> Componente central da suíte de integração para roteamento seguro de requisições, controle de taxa e tolerância a falhas em sistemas distribuídos.

---

## 🎯 Objetivo do Subprograma

O **API Gateway Integrator** atua como uma fachada (*Facade*) unificada para a suíte de microsserviços. Ele gerencia o fluxo de entrada de requisições, protegendo os serviços downstream contra sobrecarga, falhas em cascata e degradação de performance por meio de padrões resilientes de engenharia de software.

---

## 🏛️ Arquitetura & Padrões de Projeto (*Design Patterns*)

### 1. **Circuit Breaker (Máquina de Estados)**
- **Arquivo:** `circuit_breaker.py`
- **Estados:**
  - `CLOSED`: Operação normal. As requisições são encaminhadas com sucesso.
  - `OPEN`: O serviço downstream apresentou taxa de erro superior ao limite (`failure_threshold = 5`). As requisições são imediatamente bloqueadas para evitar contaminação.
  - `HALF_OPEN`: Após o tempo de recuperação (`recovery_timeout = 30s`), uma requisição de teste é permitida para avaliar se o serviço recuperou a estabilidade.
- **Benefício:** Evita sobrecarga em serviços instáveis e previne falhas em cascata.

### 2. **Token Bucket Rate Limiter**
- **Arquivo:** `rate_limiter.py`
- **Algoritmo:** Balde de Tokens (*Token Bucket*) com janela deslizante e reposição contínua.
- **Configuração Padrão:** Capacidade de 60 tokens, com taxa de reposição de 10 tokens/segundo por IP/Cliente.
- **Benefício:** Mitiga ataques de negação de serviço (DoS) e garante *fair usage* dos recursos da API.

### 3. **Exponential Backoff com Jitter**
- **Arquivo:** `retry_handler.py`
- **Mecanismo:** Retentativa automática de requisições com tempo de espera exponencial que dobra a cada falha ($0.5s, 1s, 2s, \dots$), acrescido de um *jitter* aleatório.
- **Benefício:** Resolve problemas de indisponibilidade temporária sem causar o fenômeno de *thundering herd*.

---

## 🔒 Sanitização & Segurança

- **Chaves de API:** Substituídas por placeholders de demonstração corporativa (`TEST_TOKEN_API_KEY_001`).
- **Identificadores de Cliente:** Formatados como `TEST_CLIENT_SAMPLE_ID`.
- **Autenticação HTTP Basic:** Protegida sob a credencial sanitizada `admin` / `admin`.

---

## 📡 Endpoints da API (Porta `5001`)

### `GET /api/health`
Verifica o status de saúde do gateway.
- **Resposta:**
  ```json
  {
    "service": "API Gateway Integrator",
    "status": "online",
    "version": "1.0.0"
  }
  ```

### `POST /api/proxy`
Encaminha requisições aplicando filtros de Rate Limit e Circuit Breaker.
- **Body Exemplo:**
  ```json
  {
    "target": "telemetry_service",
    "payload": { "event": "ping" }
  }
  ```

### `GET /api/circuit-breaker/status`
Retorna o estado atual da máquina de estados do Circuit Breaker.
- **Resposta Exemplo:**
  ```json
  {
    "failure_count": 0,
    "failure_threshold": 5,
    "name": "gateway_circuit",
    "state": "CLOSED",
    "total_requests": 14
  }
  ```

### `POST /api/circuit-breaker/reset`
Força a reinicialização manual do circuito para o estado `CLOSED`.

### `GET /api/rate-limit/stats`
Estatísticas em tempo real do limitador de taxa Token Bucket.

---

## 🧪 Testes Unitários

Para executar a suíte de testes do Gateway:

```bash
cd D:\Pessoal\portifolio\api_gateway_integrator
python -m pytest tests/ -v
```
