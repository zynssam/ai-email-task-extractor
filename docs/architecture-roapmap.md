# AI Email Task Extractor — Architecture & Roadmap

## What it does

Connects to multiple email accounts (Gmail, Outlook, Yahoo) per user, uses an AI API to extract deadlines/tasks from emails, and shows them on a unified dashboard. Starts as a web app, later expands to iOS/Android via React Native.

---

## Tech Stack

| Layer | Choice | Notes |

|---|---|---|

| Backend | Python + FastAPI | Pairs well with AI API calls, fast to build |

| Database | PostgreSQL | Relational data: users, linked accounts, tasks |

| Frontend (web) | React | + anime.js used sparingly, for purposeful motion only |

| Frontend (mobile) | React Native | Talks to same backend, built later |

| AI extraction | Gemini API | Most generous free tier of the major providers |

| Containers | Podman + Podman Compose | Daemon-less, good fit for Fedora |

| Backend/DB hosting | Render or Railway | Usable free tiers |

| Frontend hosting | Vercel or Netlify | Free for personal projects |

| Version control | Git, pinned dependency versions | `requirements.txt` (exact versions) + Node lock file |

---

## Architecture Overview

```

User → React Frontend → FastAPI Backend → PostgreSQL (users, linked accounts, tasks)

                              ↓

                    OAuth (Gmail/Outlook/Yahoo)

                              ↓

                    Polling job pulls new emails

                              ↓

                    Gemini API extracts tasks/deadlines

                              ↓

                    Tasks stored, scoped to user_id

                              ↓

                    Dashboard aggregates across all linked accounts

```

Core security rules baked in throughout:

- Parameterized queries only (no raw SQL string building) → prevents SQL injection

- Every query filtered by `user_id` → no cross-user data leakage

- OAuth tokens encrypted at rest in the DB (not just hashed — you need to decrypt to use them)

- AI API keys live only on the backend, never shipped to the frontend

---

## Phases

### Phase 1 — Database Schema

- `users` table

- `linked_accounts` table (one user → many email accounts; provider type, encrypted OAuth token)

- `tasks` table (linked to user_id, source account, due date, description)

### Phase 2 — Core Backend API

- User signup/login (authentication)

- CRUD endpoints for tasks

- Enforce user-scoped access on every endpoint

### Phase 3 — Gmail Integration (single provider first)

- OAuth flow to link a Gmail account

- Store encrypted token in `linked_accounts`

- Polling job to fetch new emails periodically (e.g. every hour, or once daily)

### Phase 4 — AI Extraction

- Send fetched email content to Gemini API

- Prompt it to identify tasks/deadlines and extract structured data (date, description)

- Store results in `tasks`, linked to the right user and account

### Phase 5 — Frontend Dashboard

- React app: login, view aggregated tasks across accounts, sort by due date

- Subtle anime.js touches (fade-in on load, staggered list reveal) — nothing decorative for its own sake

### Phase 6 — Expand Providers

- Add Outlook and Yahoo OAuth + polling, reusing the same extraction pipeline

### Phase 7 — Mobile

- React Native app (iOS + Android) hitting the same backend API — no backend changes needed

### Phase 8 — Deployment

- Containerize backend + DB with Podman

- Deploy backend/DB to Render/Railway, frontend to Vercel/Netlify

---

## Habits worth stealing from professional workflows

- Write down what each feature needs to do before coding it (even a one-line user story)

- Sketch the DB schema before writing backend code

- Build in small, testable chunks rather than everything-then-test-at-end

- Write basic tests as you go

- Use meaningful Git commits and pull requests, even solo
