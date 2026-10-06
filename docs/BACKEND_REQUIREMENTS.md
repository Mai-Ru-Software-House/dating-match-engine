# Match Engine: Backend Requirements & Prisma DAL Specification

**Project:** Online Dating System (SEN-201)    
**Target Service:** Elysia Backend (`api:3000`)  
**Consumer Service:** Match Engine (`match-engine:8000`)  

---

## 1. Executive Summary & Architectural Boundary

The **Match Engine** is a stateless, compute-only microservice built with FastAPI. It performs candidate ranking and mutual eligibility evaluations. It holds no persistent state and **does not connect directly to PostgreSQL**.

The **Elysia Backend** is the sole owner of application persistence, authentication, Prisma Data Access Layer (DAL), and domain business rules.

```text
┌─────────────────┐       ┌─────────────────┐
│  Mobile Client  │       │   PostgreSQL    │
└────────┬────────┘       └────────▲────────┘
         │                         │ Prisma ORM
         ▼                         ▼
┌───────────────────────────────────────────┐
│              Elysia Backend               │
│   (Auth, Profiles, Swipes, Blocks, DAL)   │
└────────┬─────────────────────────▲────────┘
         │                         │
         │ Internal HTTP API       │ Internal Prisma DAL REST API
         │ (/internal/v1/...)      │ (/internal/v1/...)
         ▼                         │
┌──────────────────────────────────┴────────┐
│               Match Engine                │
│    (Stateless Compatibility Scoring)      │
└───────────────────────────────────────────┘
```

---

## 2. Required Elysia Backend Internal Endpoints

The Match Engine communicates with the Elysia backend via HTTP to retrieve user profiles and candidate pools. The backend must expose the following internal routes.

### 2.1 Primary Endpoint: Unified Matching Pool (Recommended)

To minimize network latency and database round-trips, the backend provides an aggregated endpoint returning both the requesting user's profile and the pre-filtered candidate pool.

* **Method:** `GET`
* **Path:** `/internal/v1/matching-pool`
* **Query Parameters:**
  * `userId` (string, required): Unique identifier of the requesting user.

#### Request Example

```http
GET /internal/v1/matching-pool?userId=usr_7f8a9b HTTP/1.1
Host: api:3000
Accept: application/json
```

#### Response Example (`HTTP 200 OK`)

```json
{
  "user": {
    "userId": "usr_7f8a9b",
    "age": 25,
    "dateOfBirth": "2001-05-14",
    "gender": "female",
    "latitude": 13.7563,
    "longitude": 100.5018,
    "targetPreference": {
      "ageMin": 23,
      "ageMax": 30,
      "gender": ["male", "non_binary"],
      "radiusKm": 25.0
    }
  },
  "candidates": [
    {
      "userId": "usr_3c4d5e",
      "age": 27,
      "dateOfBirth": "1999-09-22",
      "gender": "male",
      "latitude": 13.7800,
      "longitude": 100.5200,
      "targetPreference": {
        "ageMin": 22,
        "ageMax": 28,
        "gender": ["female"],
        "radiusKm": 30.0
      }
    },
    {
      "userId": "usr_9a0b1c",
      "age": 26,
      "dateOfBirth": "2000-02-10",
      "gender": "non_binary",
      "latitude": 13.7650,
      "longitude": 100.5120,
      "targetPreference": {
        "ageMin": 24,
        "ageMax": 29,
        "gender": ["female", "male"],
        "radiusKm": 15.0
      }
    }
  ]
}
```

### 2.2 Candidate Pool for Specification Search

Returns active candidate profiles across the platform for specification-based candidate search filtering when candidates are not provided inline in the request payload.

* **Method:** `GET`
* **Path:** `/internal/v1/candidates`

#### Request Example

```http
GET /internal/v1/candidates HTTP/1.1
Host: api:3000
Accept: application/json
```

#### Response Example (`HTTP 200 OK`)

```json
{
  "candidates": [
    {
      "userId": "usr_3c4d5e",
      "age": 27,
      "gender": "male",
      "latitude": 13.7800,
      "longitude": 100.5200
    },
    {
      "userId": "usr_9a0b1c",
      "age": 26,
      "gender": "non_binary",
      "latitude": 13.7650,
      "longitude": 100.5120
    }
  ]
}
```

*(Note: An array `[...]` response is also supported.)*

---

## 3. Backend Pre-filtering Requirements (Prisma DAL Responsibility)

Before delivering candidate profiles to the Match Engine, the Elysia Backend Prisma DAL **must apply the following SQL / Prisma filters**:

1. **Self Exclusion**
2. **Location & Preference Completeness**: Only return profiles having valid coordinates and populated preferences:

---

## 4. End-to-End Interaction Flows

### 4.1 Recommendations Pull Flow (Standard)

```mermaid
sequenceDiagram
    autonumber
    actor Client as Mobile Client
    participant Backend as Elysia Backend (:3000)
    participant DB as PostgreSQL (Prisma)
    participant Engine as Match Engine (:8000)

    Client->>Backend: GET /api/v1/recommendations?limit=20
    Note over Backend: Authenticates user session (JWT)
    Backend->>Engine: GET /internal/v1/recommendations?userId=A&limit=20
    Engine->>Backend: GET /internal/v1/matching-pool?userId=A
    Backend->>DB: Prisma query: fetch User A & pre-filtered candidate pool
    DB-->>Backend: Returns User A + Candidates
    Backend-->>Engine: 200 OK (UserMatchingProfile + Candidates)
    Note over Engine: 1. Verify mutual eligibility<br/>2. Compute Gaussian age scores<br/>3. Compute exponential distance scores<br/>4. Geometric mean mutual score<br/>5. Sort descending by score
    Engine-->>Backend: 200 OK { candidates: [{ userId, matchScore, distanceKm }, ...] }
    Note over Backend: Decorates candidate IDs with photos, names, bios from DB
    Backend-->>Client: 200 OK { candidates: [...] }
```

### 4.2 Recommendations Push Flow (Direct Payload)

The Elysia backend can also pre-fetch user and candidates, avoiding the secondary HTTP callback:

```mermaid
sequenceDiagram
    autonumber
    actor Client as Mobile Client
    participant Backend as Elysia Backend (:3000)
    participant DB as PostgreSQL (Prisma)
    participant Engine as Match Engine (:8000)

    Client->>Backend: GET /api/v1/recommendations?limit=20
    Backend->>DB: Fetch User A + Pre-filtered Candidate Pool
    DB-->>Backend: Records
    Backend->>Engine: POST /internal/v1/recommendations<br/>{ userId: "A", limit: 20, user: {...}, candidates: [...] }
    Note over Engine: Executes mutual matching & ranking
    Engine-->>Backend: 200 OK { candidates: [{ userId, matchScore, distanceKm }, ...] }
    Backend-->>Client: 200 OK { candidates: decorated with profile data }
```

### 4.3 Specification Candidate Search Flow

```mermaid
sequenceDiagram
    autonumber
    actor Client as Mobile Client
    participant Backend as Elysia Backend (:3000)
    participant Engine as Match Engine (:8000)
    participant DB as PostgreSQL (Prisma)

    Client->>Backend: POST /api/v1/candidates/search { ageMin, ageMax, gender, radiusKm, location, limit }
    Backend->>Engine: POST /internal/v1/candidates/search<br/>{ ageMin: 20, ageMax: 25, gender: ["G1"], radiusKm: 10, location: {...}, limit: 20 }
    alt Candidates not included in body
        Engine->>Backend: GET /internal/v1/candidates
        Backend->>DB: Fetch candidate pool
        DB-->>Backend: Candidates
        Backend-->>Engine: 200 OK [Candidates]
    end
    Note over Engine: Filters candidates strictly meeting specifications
    Engine-->>Backend: 200 OK { candidates: [{ userId, distanceKm }, ...] }
    Backend-->>Client: 200 OK { candidates: decorated }
```

---

## 5. Error Handling & Edge Cases

| Scenario | HTTP Status | Response Error Envelope | Action Expected by Backend |
|---|:---:|---|---|
| Requesting user not found in database | `404 Not Found` | `{"error": {"code": "USER_NOT_FOUND", "message": "User not found"}}` | Elysia returns `404` to client. |
| Incomplete candidate profile (missing location / DOB) | `400 Bad Request` | `{"error": {"code": "INVALID_INPUT", "message": "Validation error: ..."}}` | Check Prisma query select fields. |
| Candidate pool is empty | `200 OK` | `{"candidates": []}` | Return empty recommendations array to client. |
| Match Engine unreachable / timeout | `502 Bad Gateway` | `{"error": {"code": "BACKEND_ERROR", "message": "Failed to connect..."}}` | Log error and return `503` to client. |
