# Dating Match Engine

> **SEN-201 Online Dating System**  
> Standalone FastAPI microservice responsible for candidate recommendation and specification search.

---

## 1. Service Purpose & Architecture Boundary

The **Match Engine** is a dedicated compute-only microservice for the Online Dating System:

* **Computation Only**: Evaluates mutual eligibility and calculates mathematical compatibility scores.
* **No Database Ownership**: Does **not** own or connect directly to PostgreSQL.
* **No Authentication / State**: Does not store user passwords, credentials, swipes, likes, passes, or seen history.
* **Integration Boundary**: The **Elysia Backend** remains the sole authority for persistent application data and calls the Match Engine via internal HTTP API endpoints.

```text
PostgreSQL
    ^
    |
Elysia Backend (Prisma DAL)
    ^
    | Internal HTTP API (/internal/v1/...)
    v
Match Engine (FastAPI :8000)
```

> [!NOTE]
> For complete specifications on what the Match Engine requires from the Elysia Backend (Prisma DAL), including schemas, pre-filtering rules, and endpoint contracts, refer to [BACKEND_REQUIREMENTS.md](docs/BACKEND_REQUIREMENTS.md).

---

## 2. API Endpoints

All matching endpoints reside under versioned internal routes (`/internal/v{version}/...`). Unversioned endpoints are not exposed:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service health status check |
| `GET` | `/internal/v1/recommendations?user_id={id}&limit={n}` | Generates ranked candidate recommendations |
| `POST` | `/internal/v1/recommendations` | Computes recommendations with optional direct payload |
| `POST` | `/internal/v1/candidates/search` | Filters candidates by explicit search criteria |

> [!NOTE]
> Currently supported API version is `v1`. Unsupported versions (e.g. `/internal/v2/...`) return `HTTP 400 Bad Request`.

---

## 3. Request & Response Examples

### Feature 1: Candidate Recommendations

#### Request (GET)

```http
GET /internal/v1/recommendations?user_id=usr_001&limit=20 HTTP/1.1
Host: localhost:8000
```

#### Request (POST - Direct Payload Mode)

```http
POST /internal/v1/recommendations HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "user_id": "usr_001",
  "limit": 20,
  "user": {
    "user_id": "usr_001",
    "age": 25,
    "gender": "female",
    "latitude": 13.7563,
    "longitude": 100.5018,
    "target_preference": {
      "age_min": 24,
      "age_max": 30,
      "gender": ["male", "non_binary"],
      "radius_km": 15.0
    }
  },
  "candidates": [
    {
      "user_id": "usr_002",
      "age": 27,
      "gender": "male",
      "latitude": 13.7800,
      "longitude": 100.5200,
      "target_preference": {
        "age_min": 22,
        "age_max": 28,
        "gender": ["female"],
        "radius_km": 20.0
      }
    }
  ]
}
```

#### Response

```json
{
  "candidates": [
    {
      "user_id": "usr_002",
      "match_score": 96.4,
      "distance_km": 3.42
    }
  ]
}
```

---

### Feature 2: Candidate Search by Specification

#### Request (POST)

```http
POST /internal/v1/candidates/search HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "age_min": 20,
  "age_max": 25,
  "gender": ["G1", "G3"],
  "radius_km": 10.0,
  "location": {
    "lat": 13.7563,
    "lng": 100.5018
  },
  "limit": 20
}
```

#### Response

```json
{
  "candidates": [
    {
      "user_id": "usr_101",
      "distance_km": 3.42
    },
    {
      "user_id": "usr_102",
      "distance_km": 7.15
    }
  ]
}
```

---

## 4. Mutual Eligibility Rules

A candidate pair $(A, B)$ must satisfy all three criteria mutually:

1. **Gender**:
   $$
   \operatorname{gender}(B) \in \operatorname{targetGenders}(A) \quad \land \quad \operatorname{gender}(A) \in \operatorname{targetGenders}(B)
   $$
   *(Genders are configurable string tokens and never hardcoded).*
2. **Age**:
   $$
   \operatorname{age}_{\min}(A) \le \operatorname{age}(B) \le \operatorname{age}_{\max}(A) \quad \land \quad \operatorname{age}_{\min}(B) \le \operatorname{age}(A) \le \operatorname{age}_{\max}(B)
   $$
3. **Distance**:
   $$
   \operatorname{distance}(A, B) \le \operatorname{radius}(A) \quad \land \quad \operatorname{distance}(A, B) \le \operatorname{radius}(B)
   $$
   *(Computed using the great-circle Haversine formula).*

---

## 5. Match Score Algorithm

The scoring model is bidirectional, explainable, and tunable:

### 1. Age Compatibility ($A \to B$)

$$
\mu_A = \frac{\operatorname{age}_{\min}(A) + \operatorname{age}_{\max}(A)}{2}
$$

$$
S_{\text{age}}(A, B) = \exp\left( -\frac{(\operatorname{age}(B) - \mu_A)^2}{2 \sigma_A^2} \right)
$$

where $\sigma_A = \frac{\operatorname{age}_{\max}(A) - \operatorname{age}_{\min}(A)}{2}$ (or fallback `DEFAULT_AGE_SIGMA`).

### 2. Distance Compatibility ($A \to B$)

$$
S_{\text{distance}}(A, B) = \exp\left( -\left(\frac{\operatorname{distance}(A, B)}{\operatorname{radius}(A)}\right)^2 \right)
$$

### 3. Directional Compatibility

$$
C_{A \to B} = w_{\text{age}} \cdot S_{\text{age}}(A, B) + w_{\text{distance}} \cdot S_{\text{distance}}(A, B)
$$

with default weights:
* $w_{\text{age}} = 0.7$
* $w_{\text{distance}} = 0.3$

The same symmetric calculation is performed for $C_{B \to A}$.

### 4. Mutual Match Score

$$
S_{\text{match}}(A, B) = 100 \times \sqrt{C_{A \to B} \cdot C_{B \to A}}
$$

Bounded within $[0, 100]$. The geometric mean ensures that strong compatibility on one side cannot mask poor compatibility on the other.

---

## 6. Environment Variables

| Variable | Type | Default | Description |
|---|---|---|---|
| `ENVIRONMENT` | string | `development` | Runtime environment (`development`, `production`, `test`) |
| `HOST` | string | `0.0.0.0` | Host interface to bind server |
| `PORT` | integer | `8000` | Port for Match Engine service |
| `BACKEND_URL` | string | `http://api:3000` | Elysia Backend service base URL |
| `BACKEND_TIMEOUT_SECONDS` | float | `10.0` | HTTP request timeout for backend requests |
| `WEIGHT_AGE` | float | `0.7` | Weight $w_{\text{age}}$ for age compatibility |
| `WEIGHT_DISTANCE` | float | `0.3` | Weight $w_{\text{distance}}$ for distance compatibility |
| `DEFAULT_AGE_SIGMA` | float | `2.0` | Fallback $\sigma$ when user age range width is zero |
| `SCORE_DECIMALS` | integer | `1` | Decimal places to round match score |

---

## 7. How to Run Locally

### Prerequisites

* Python 3.12+
* `uv` or `pip`

### Using `uv` (Recommended)

```bash
# 1. Navigate to service directory
cd dating-match-engine

# 2. Create virtual environment and install dependencies
uv venv --python python3.12 .venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# 3. Copy environment template
cp .env.example .env

# 4. Run tests
pytest -v

# 5. Start the development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Using Docker

```bash
docker build -t dating-match-engine:dev .
docker run -p 8000:8000 --env-file .env.example dating-match-engine:dev
```

### Standalone Testing with Mock Backend

When the Elysia backend is not yet available, run the bundled mock backend to test end-to-end matching:

```bash
# Terminal 1: Start mock Elysia backend (port 3000)
python scripts/mock_backend.py

# Terminal 2: Start Match Engine (port 8000)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 3: Query recommendations end-to-end
curl -s "http://localhost:8000/internal/v1/recommendations?userId=usr_001&limit=5" | jq
```
