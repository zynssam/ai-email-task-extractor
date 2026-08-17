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
- **Encrypted Token Storage**: Encrypts OAuth access and refresh tokens at rest in the database.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.14+, FastAPI, SQLAlchemy 2.0, Alembic
- **Database**: PostgreSQL 16 (running via Podman)
- **Database Driver**: `psycopg3` / `psycopg2-binary`
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

Create a `.env` file in the root directory:

```env
DATABASE_URL=postgresql+psycopg://dev:devpass@localhost:5432/email_tasks
```

### 5. Run Database Migrations

Apply Alembic migrations to create tables and Row-Level Security policies:

```bash
alembic upgrade head
```

---

## 🛡️ Security & Row-Level Security (RLS)

Every user-scoped table (`linked_accounts`, `tasks`) has Row-Level Security enabled with PostgreSQL policies enforcing isolation:

```sql
ALTER TABLE linked_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_isolation_tasks ON tasks
  FOR ALL
  USING (user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid);
```

To verify RLS status in PostgreSQL:
```bash
podman exec -it email-tasks-db psql -U dev -d email_tasks -c "SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';"
```

---

## 🗺️ Roadmap & Project Phases

- [x] **Phase 1: Database Schema & RLS Setup**
- [ ] **Phase 2: Core Backend API (Auth & Task CRUD)**
- [ ] **Phase 3: Gmail OAuth Integration**
- [ ] **Phase 4: AI Extraction Worker (Gemini API Integration)**
- [ ] **Phase 5: Task Dashboard UI**
- [ ] **Phase 6: Provider Expansion (Outlook & Yahoo)**
- [ ] **Phase 7: Mobile App (React Native)**
- [ ] **Phase 8: Production Deployment & Container Polish**

---

## 📄 License

MIT License.
