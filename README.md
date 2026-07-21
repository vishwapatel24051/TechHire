# TechHire

TechHire is a full-stack job board built for CS students and new-grad engineers. It continuously scrapes remote software engineering and internship listings from multiple job sources, normalizes and enriches them, and serves them through a filterable React UI — complete with AI-generated job summaries and an AI resume compatibility checker.

```
JSearch API (RapidAPI)
       ↓
  Scraper Layer      →  Python (scraper/)
       ↓
  PostgreSQL          →  SQLAlchemy ORM (db/)
       ↓
  FastAPI Backend     →  api.py
       ↓
  React Frontend      →  frontend/src/
```

## Features

- **Multi-source scraping** — Indeed, Glassdoor, Handshake, and Lever, aggregated via the JSearch API, with 20+ query/source combinations covering full-time and internship roles.
- **Incremental scraping** — tracks already-seen job IDs and stops paging early once it reaches known listings, so refreshes stay fast.
- **Dead-link filtering** — every apply URL is validated concurrently (HEAD/GET requests) before being saved; 404s and known spam domains are dropped.
- **Rich parsing** — extracts location, salary (range/period), responsibilities, qualifications, benefits, required skills (~70 tech keywords), visa sponsorship, work mode, experience level, and start date from raw postings.
- **AI job summaries** — three Groq models (`llama-3.3-70b`, `qwen3-32b`, `llama-3.1-8b-instant`) each summarize a listing from a different angle, then a synthesis pass combines them into one cached 3-paragraph summary.
- **AI resume checker** — upload a PDF/TXT resume, match it against a job description, and get a 0–100 score, matched/missing skills, section-by-section feedback, and suggested bullet rewrites.
- **Filterable job board** — search, skills, salary range, work mode, experience level, visa sponsorship, date posted, and start season, with pagination and sorting (newest / salary).

## Tech Stack

| Layer      | Technology |
|------------|------------|
| Frontend   | React 18, Vite, Tailwind CSS, TanStack React Query |
| Backend    | FastAPI, Uvicorn |
| Database   | PostgreSQL, SQLAlchemy ORM |
| Scraping   | `requests`, JSearch API (RapidAPI) |
| AI         | Groq (Llama 3.3/3.1, Qwen3) |
| PDF parsing| pdfplumber |

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker Desktop (for PostgreSQL)
- A free [Groq API key](https://console.groq.com) for AI summaries and resume analysis

## Getting Started

The included `setup.sh` script automates environment setup, dependency installation, and running the app.

```bash
# 1. First-time setup — creates .env, installs deps, starts Postgres, initializes tables
bash setup.sh setup

# 2. Add your GROQ_API_KEY to .env, then fetch initial job listings
bash setup.sh scrape

# 3. Start the API and frontend
bash setup.sh start
```

- Frontend → http://localhost:5173
- API → http://localhost:8000

Stop everything with:

```bash
bash setup.sh stop
```

### Manual setup

```bash
# Python deps
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Frontend deps
npm --prefix frontend install

# Postgres
docker compose up -d ddb

# Run the API
.venv/bin/uvicorn api:app --reload --port 8000

# Run the frontend (separate terminal)
npm --prefix frontend run dev

# Run a full scrape
.venv/bin/python3 main.py
```

## Environment Variables

Create a `.env` file in the project root:

```
DATABASE_URL=postgresql://techhire:localdev@localhost:5433/techhire_db
GROQ_API_KEY=your_groq_api_key_here
```

> **Note:** The JSearch/RapidAPI key used by the scraper is currently hardcoded in `scraper/indeed.py`, `scraper/glassdoor.py`, `scraper/handshake.py`, and `scraper/lever.py` rather than read from `.env`. This key is committed to git history — treat it as compromised, rotate it in RapidAPI, and move it to an environment variable before any public use of this repo.

## Project Structure

```
TechHire/
├── main.py                # CLI entry point — runs a full scrape
├── api.py                 # FastAPI app: job listing, AI summary, resume analysis endpoints
├── scraper/
│   ├── runner.py           # Orchestrates all scrape configs (run / refresh)
│   ├── utils.py             # JSearch pagination, CS-title filtering, URL liveness checks
│   ├── parse.py             # Raw API dict → normalized Job dataclass
│   ├── base.py               # Job dataclass definition
│   └── indeed.py / glassdoor.py / handshake.py / lever.py   # Per-source fetch wrappers
├── db/
│   ├── models.py            # SQLAlchemy JobListing ORM model
│   ├── save.py                # Deduplicated bulk insert
│   ├── session.py             # DB engine/session setup
│   └── reparse.py            # Re-applies the parser to existing rows
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # Root component, filter state, layout
│   │   ├── components/         # Sidebar, JobCard, SlideOver, ResumeChecker, etc.
│   │   ├── hooks/useJobs.js    # React Query wrapper around GET /jobs
│   │   └── utils/format.js
│   └── vite.config.js
├── docker-compose.yml       # Postgres (+ Redis) for local development
├── setup.sh                 # One-command setup / start / scrape / stop
├── requirements.txt
└── CODEBASE_WALKTHROUGH.md  # Detailed step-by-step architecture walkthrough
```

For a deeper dive into how data flows through each layer (parsing rules, salary/skill extraction, the AI summary pipeline, etc.), see [CODEBASE_WALKTHROUGH.md](CODEBASE_WALKTHROUGH.md).

## API Overview

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET  | `/jobs` | Paginated, filtered job list |
| GET  | `/jobs/{id}` | Single job detail |
| GET  | `/jobs/{id}/summary` | AI-generated summary (cached in DB) |
| POST | `/scrape/refresh` | Trigger an incremental background scrape |
| GET  | `/scrape/status` | Poll scrape state (idle/running/done/error) |
| POST | `/resume/extract-text` | Upload a PDF/TXT resume → plain text |
| POST | `/resume/analyze` | Resume + job description → AI match analysis |
| GET  | `/health` | Liveness check |

## How It Works

1. **Scrape** — `scraper/runner.py` fetches listings from Indeed, Glassdoor, Handshake, and Lever via the JSearch API, filtering to CS-relevant titles and skipping jobs already in the database.
2. **Parse** — `scraper/parse.py` normalizes each raw posting into a `Job` dataclass, extracting salary, location, skills, sections, visa sponsorship, and more.
3. **Validate** — `scraper/utils.py` concurrently checks that every apply link is still live before saving.
4. **Save** — `db/save.py` deduplicates by `source_job_id` and bulk-inserts new listings into PostgreSQL.
5. **Serve** — `api.py` exposes filtered/paginated job queries, on-demand AI summaries, and resume analysis.
6. **Browse** — the React frontend lets users filter, page through, and inspect listings, with AI summaries and resume matching available per job.

## License

No license file is currently included in this repository.
