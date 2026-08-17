# 📬 AI Email Task Extractor

> An intelligent, privacy-focused email task extraction engine. Connects to email accounts, automatically extracts deadlines & action items using the Gemini API, and aggregates them into a secure task dashboard.

---

## 🚀 Architecture Overview

```
User → React Frontend → FastAPI Backend → PostgreSQL (users, linked_accounts, tasks)
                               ↓
                   OAuth (Gmail/Outlook/Yahoo)
                               ↓
                     Hourly Polling Worker
                               ↓
                    Gemini API Task Extractor
                               ↓
                    Tasks Scoped by user_id & RLS
```

---

## ✨ Key Features

- **Multi-Account Aggregation**: Monitor multiple linked email accounts in one dashboard.
- **AI Task Extraction**: Automatically parses action items, due dates, and infers ambiguous deadlines.
- **Zero Raw Data Retention**: Discards raw email content immediately after task extraction.
- **DB-Enforced Data Isolation**: Enforces PostgreSQL **Row-Level Security (RLS)** at the database level—preventing cross-user data leaks even if application code bugs occur.
- **Encrypted Token Storage**: Encrypts OAuth access and refresh tokens at rest using Fernet (AES-128-CBC) symmetric encryption.
- **Hardened Authentication**: bcrypt password hashing, JWT with revocation support, password strength policies, and rate-limited auth endpoints.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.14+, FastAPI, SQLAlchemy 2.0, Alembic
- **Database**: PostgreSQL 16 (running via Podman)
- **Database Driver**: `psycopg3` / `psycopg2-binary`
- **Authentication**: bcrypt, PyJWT (HS256), OAuth2 Bearer flow
- **Encryption**: `cryptography` (Fernet) for OAuth token storage
- **Rate Limiting**: `slowapi` (IP-based)
- **AI Engine**: Google Gemini API
- **Containerization**: Podman

---

## 📊 Database Schema (ERD)

```mermaid
erDiagram
  USERS ||--o{ LINKED_ACCOUNTS : owns
  USERS ||--o{ TASKS : owns
  LINKED_ACCOUNTS ||--o{ TASKS : sources

  USERS {
    uuid id PK
    string email
    string password_hash
    boolean email_verified
    timestamp created_at
  }
  LINKED_ACCOUNTS {
    uuid id PK
    uuid user_id FK
    string provider
    string encrypted_token
    string encrypted_refresh_token
    timestamp connected_at
  }
  TASKS {
    uuid id PK
    uuid user_id FK
    uuid account_id FK
    string description
    date due_date
    boolean date_is_inferred
    string status
    timestamp created_at
  }
```

---

## 📡 API Endpoints

### Auth

| Method | Endpoint | Description | Rate Limit |
|--------|----------|-------------|------------|
| `POST` | `/auth/signup` | Register a new user | 5/min per IP |
| `POST` | `/auth/login` | Authenticate & receive JWT | 10/min per IP |
| `POST` | `/auth/refresh` | Rotate access token (revokes old) | — |
| `POST` | `/auth/logout` | Revoke current token | — |
| `GET` | `/auth/me` | Get current user profile | — |

### Tasks

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/tasks` | List tasks (filterable by `status`, sortable by `due_date`) |
| `PATCH` | `/tasks/{task_id}` | Update task status (`pending` / `completed` / `dismissed`) |

### Linked Accounts

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/accounts` | List linked email accounts |
| `DELETE` | `/accounts/{account_id}` | Unlink an email account |

---

## ⚙️ Quickstart & Local Setup

### 1. Prerequisites

- Python 3.10+ installed
- [Podman](https://podman.io/) installed

### 2. Start Database Container (Podman)

```bash
podman run -d \
  --name email-tasks-db \
  -p 5432:5432 \
  -e POSTGRES_USER=dev \
  -e POSTGRES_PASSWORD=devpass \
  -e POSTGRES_DB=email_tasks \
  postgres:16
```

Confirm the container is running:
```bash
podman ps
```

### 3. Virtual Environment Setup

```bash
# Clone the repository
git clone https://github.com/zynssam/ai-email-task-extractor.git
cd ai-email-task-extractor

# Create & activate venv
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Environment Variables (`.env`)

Create a `.env` file in the root directory (**all are required** — the app crashes on startup if any are missing):

```env
DATABASE_URL=postgresql+psycopg://app_worker:app_secure_pass_123@localhost:5432/email_tasks
SECRET_KEY=<generate-a-strong-random-key>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
ENCRYPTION_KEY=<generate-with-command-below>
ALLOWED_ORIGINS=http://localhost:3000
```

Generate the `ENCRYPTION_KEY`:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Generate a strong `SECRET_KEY`:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 5. Run Database Migrations

Apply Alembic migrations to create tables and Row-Level Security policies:

```bash
alembic upgrade head
```

### 6. Start the Server

```bash
uvicorn main:app --reload
```

API docs available at: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🛡️ Security

### Row-Level Security (RLS)

Every user-scoped table (`linked_accounts`, `tasks`) has Row-Level Security enabled with PostgreSQL policies enforcing isolation:

```sql
ALTER TABLE linked_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE linked_accounts FORCE ROW LEVEL SECURITY;

ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks FORCE ROW LEVEL SECURITY;

CREATE POLICY user_isolation_tasks ON tasks
  FOR ALL
  USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid);
```

### Authentication & API Hardening

| Layer | Implementation |
|-------|----------------|
| **Password Hashing** | bcrypt with auto-generated salts |
| **Password Policy** | Min 8 chars, requires uppercase, lowercase, and digit |
| **JWT Tokens** | HS256 with `jti` claim for per-token revocation |
| **Token Lifecycle** | 30-min expiry, refresh rotation, logout revocation |
| **Rate Limiting** | slowapi — 5/min signup, 10/min login (per IP) |
| **CORS** | Explicit allowed origins (configurable via `ALLOWED_ORIGINS`) |
| **Security Headers** | `X-Content-Type-Options`, `X-Frame-Options`, `HSTS`, `Referrer-Policy`, `Permissions-Policy` |
| **Token Encryption** | Fernet (AES-128-CBC) for OAuth tokens at rest |
| **No Fallback Defaults** | App crashes on startup if `SECRET_KEY`, `DATABASE_URL`, or `ENCRYPTION_KEY` are missing |

To verify RLS status in PostgreSQL:
```bash
podman exec -it email-tasks-db psql -U dev -d email_tasks -c "SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';"
```

For full details on all security fixes applied, see [`docs/security-flaws-fixed.md`](docs/security-flaws-fixed.md).

---

## 🗺️ Roadmap & Project Phases

- [x] **Phase 1: Database Schema & RLS Setup**
- [x] **Phase 2: Core Backend API (Auth & Task CRUD)**
- [ ] **Phase 3: Gmail OAuth Integration**
- [ ] **Phase 4: AI Extraction Worker (Gemini API Integration)**
- [ ] **Phase 5: Task Dashboard UI**
- [ ] **Phase 6: Provider Expansion (Outlook & Yahoo)**
- [ ] **Phase 7: Mobile App (React Native)**
- [ ] **Phase 8: Production Deployment & Container Polish**

---

## 📄 License

MIT License.
