import os
import asyncio
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, or_, and_, func, text
from dotenv import load_dotenv
from db.session import init_db, SessionLocal
from db.models import JobListing
from scraper.runner import refresh as run_refresh

load_dotenv()

app = FastAPI(title="TechHire API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


def _job_to_dict(j: JobListing) -> dict:
    return {
        "id": j.id,
        "source_job_id": j.source_job_id,
        "title": j.title,
        "company": j.company,
        "source": j.source,
        "url": j.url,
        "posted_at": j.posted_at.isoformat() if j.posted_at else None,
        "expires_at": j.expires_at.isoformat() if j.expires_at else None,
        "city": j.city,
        "state": j.state,
        "country": j.country,
        "is_remote": j.is_remote,
        "work_mode": j.work_mode,
        "job_type": j.job_type,
        "experience_level": j.experience_level,
        "description": j.description,
        "responsibilities": j.responsibilities or [],
        "qualifications": j.qualifications or [],
        "benefits": j.benefits or [],
        "required_skills": j.required_skills or [],
        "salary_min": j.salary_min,
        "salary_max": j.salary_max,
        "salary_currency": j.salary_currency,
        "salary_period": j.salary_period,
        "visa_sponsorship": j.visa_sponsorship,
        "start_date_text": j.start_date_text,
    }


def _build_query(
    search, skills, visa_only, salary_min, salary_max,
    work_modes, experience_levels, date_posted, seasons
):
    stmt = select(JobListing)

    if search.strip():
        q = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(JobListing.title).like(q),
                func.lower(JobListing.company).like(q),
            )
        )

    if skills:
        for skill in skills:
            stmt = stmt.where(
                func.array_to_string(JobListing.required_skills, ",").ilike(
                    f"%{skill.lower()}%"
                )
            )

    if visa_only:
        stmt = stmt.where(JobListing.visa_sponsorship == True)

    if salary_min > 0:
        stmt = stmt.where(
            and_(
                JobListing.salary_min.isnot(None),
                JobListing.salary_min >= salary_min,
            )
        )

    if salary_max < 300000:
        stmt = stmt.where(
            or_(
                JobListing.salary_max.is_(None),
                JobListing.salary_max <= salary_max,
            )
        )

    if work_modes:
        stmt = stmt.where(JobListing.work_mode.in_(work_modes))

    if experience_levels:
        stmt = stmt.where(JobListing.experience_level.in_(experience_levels))

    if date_posted != "any":
        days = {"24h": 1, "7d": 7, "30d": 30}.get(date_posted, 30)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = stmt.where(JobListing.posted_at >= cutoff)

    if seasons:
        stmt = stmt.where(
            or_(*[func.lower(JobListing.start_date_text).contains(s.lower()) for s in seasons])
        )

    return stmt


@app.get("/jobs")
def get_jobs(
    search: str = Query(default=""),
    skills: list[str] = Query(default=[]),
    visa_only: bool = Query(default=False),
    salary_min: int = Query(default=0),
    salary_max: int = Query(default=300000),
    work_modes: list[str] = Query(default=[]),
    experience_levels: list[str] = Query(default=[]),
    date_posted: str = Query(default="any"),
    seasons: list[str] = Query(default=[]),
    sort: str = Query(default="newest"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    with SessionLocal() as session:
        stmt = _build_query(
            search, skills, visa_only, salary_min, salary_max,
            work_modes, experience_levels, date_posted, seasons,
        )

        # Count total matching rows
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = session.scalar(count_stmt)

        # Apply sort
        if sort == "salary":
            stmt = stmt.order_by(
                JobListing.salary_max.desc().nullslast(),
                JobListing.salary_min.desc().nullslast(),
                JobListing.id.desc(),
            )
        else:
            stmt = stmt.order_by(
                JobListing.posted_at.desc().nullslast(),
                JobListing.id.desc(),
            )

        # Apply pagination
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        jobs = session.scalars(stmt).all()

        return {
            "jobs": [_job_to_dict(j) for j in jobs],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, -(-total // page_size)),  # ceiling division
        }


@app.get("/jobs/{job_id}")
def get_job(job_id: int):
    with SessionLocal() as session:
        j = session.get(JobListing, job_id)
        if not j:
            raise HTTPException(status_code=404, detail="Job not found")
        return _job_to_dict(j)


# ── Refresh (incremental scrape) ────────────────────────────────────────────

_scrape_state = {
    "status": "idle",  # idle | running | done | error
    "started_at": None,
    "finished_at": None,
    "result": None,
    "error": None,
}
_scrape_lock = asyncio.Lock()


async def _run_scrape_job():
    _scrape_state.update(
        status="running",
        started_at=datetime.now(timezone.utc).isoformat(),
        finished_at=None,
        error=None,
    )
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, run_refresh)
        _scrape_state.update(
            status="done",
            result=result,
            finished_at=datetime.now(timezone.utc).isoformat(),
        )
    except Exception as e:
        _scrape_state.update(
            status="error",
            error=str(e),
            finished_at=datetime.now(timezone.utc).isoformat(),
        )
    finally:
        if _scrape_lock.locked():
            _scrape_lock.release()


@app.post("/scrape/refresh")
async def trigger_refresh():
    if _scrape_lock.locked():
        return {"status": "already_running"}
    await _scrape_lock.acquire()
    asyncio.create_task(_run_scrape_job())
    return {"status": "started"}


@app.get("/scrape/status")
def scrape_status():
    return _scrape_state


# ── AI summary ────────────────────────────────────────────────────────────────

def _build_job_context(j: JobListing) -> str:
    parts = [
        f"Job Title: {j.title}",
        f"Company: {j.company}",
        f"Work Mode: {j.work_mode or 'remote'}",
        f"Experience Level: {j.experience_level or 'not specified'}",
        f"Job Type: {j.job_type or 'Full-time'}",
    ]
    if j.salary_min or j.salary_max:
        lo = f"${int(j.salary_min):,}" if j.salary_min else "?"
        hi = f"${int(j.salary_max):,}" if j.salary_max else "?"
        parts.append(f"Salary: {lo} – {hi} / {j.salary_period or 'yr'}")
    if j.visa_sponsorship is True:
        parts.append("Visa Sponsorship: Yes")
    elif j.visa_sponsorship is False:
        parts.append("Visa Sponsorship: No")
    if j.required_skills:
        parts.append(f"Key Skills: {', '.join(j.required_skills[:12])}")
    if j.city or j.state:
        loc = ", ".join(x for x in [j.city, j.state] if x)
        parts.append(f"Location: {loc}")
    parts.append(f"\nFull Job Description:\n{(j.description or '')[:3000]}")
    return "\n".join(parts)


_SYSTEM = (
    "You are a concise career advisor helping CS Masters students and new grad "
    "engineers quickly evaluate job postings. Write clearly, avoid filler phrases "
    "like 'this is a great opportunity', and always include concrete details "
    "(tech stack, salary, experience requirements if mentioned). "
    "Output only the requested paragraphs — no headers, no bullet points, no preamble."
)

# Three different models (all free on Groq) covering different angles
_VARIANTS = [
    (
        "llama-3.3-70b-versatile",  # best quality — role & day-to-day
        "Summarize this job in exactly 3 short paragraphs for a CS Masters student:\n"
        "Paragraph 1: What the company does and what this role is about.\n"
        "Paragraph 2: What you will actually build or do day-to-day, and the tech stack.\n"
        "Paragraph 3: What they require — years of experience and must-have skills.\n"
        "Be specific. No filler.",
    ),
    (
        "qwen/qwen3-32b",           # different model — fit & growth angle
        "Summarize this job in exactly 3 short paragraphs:\n"
        "Paragraph 1: What makes this company and role interesting — product, scale, or mission.\n"
        "Paragraph 2: What a typical week looks like — responsibilities and tech used.\n"
        "Paragraph 3: Who is the ideal candidate — skills, background, experience level. "
        "Mention salary and visa if available.\n"
        "Keep it tight.",
    ),
    (
        "llama-3.1-8b-instant",     # fastest — practical / student-focused
        "Summarize this job posting in exactly 3 short paragraphs for someone deciding whether to apply:\n"
        "Paragraph 1: One-sentence pitch — role + company + why it matters.\n"
        "Paragraph 2: The core technical work and stack they will use.\n"
        "Paragraph 3: Requirements and what you get — salary, remote/hybrid, visa, perks.\n"
        "Be direct. Students want facts, not marketing.",
    ),
]

_SYNTHESIS_PROMPT = (
    "Three different AI models each summarized the same job posting from a different angle. "
    "Read all three summaries, then write the single best 3-paragraph summary that combines "
    "the strongest, most specific information from each:\n\n"
    "Paragraph 1: Company context and what this role is (2-3 sentences).\n"
    "Paragraph 2: Day-to-day work, tech stack, and what you will build.\n"
    "Paragraph 3: Requirements (skills, experience level) and compensation "
    "(salary, visa sponsorship, work mode).\n\n"
    "Rules: include actual numbers and tech names from the originals. No filler. "
    "Output only the 3 paragraphs separated by blank lines — nothing else."
)


async def _call_groq(client, model: str, prompt: str, context: str) -> str:
    loop = asyncio.get_event_loop()
    def _sync():
        resp = client.chat.completions.create(
            model=model,
            max_tokens=350,
            temperature=0.4,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": f"{prompt}\n\n---JOB---\n{context}"},
            ],
        )
        return resp.choices[0].message.content.strip()
    return await loop.run_in_executor(None, _sync)


async def _synthesize_groq(client, summaries: list[str], context: str) -> str:
    numbered = "\n\n".join(
        f"[Model {i+1} — {name}]\n{s}"
        for i, ((name, _), s) in enumerate(zip(_VARIANTS, summaries))
    )
    loop = asyncio.get_event_loop()
    def _sync():
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=500,
            temperature=0.3,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"{_SYNTHESIS_PROMPT}\n\n"
                        f"--- THREE MODEL SUMMARIES ---\n{numbered}\n\n"
                        f"--- ORIGINAL JOB (reference) ---\n{context[:1500]}"
                    ),
                },
            ],
        )
        return resp.choices[0].message.content.strip()
    return await loop.run_in_executor(None, _sync)


@app.get("/jobs/{job_id}/summary")
async def get_job_summary(job_id: int, refresh: bool = False):
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key or api_key == "your_key_here":
        raise HTTPException(
            status_code=503,
            detail="GROQ_API_KEY not configured. Add it to your .env file. Get a free key at console.groq.com"
        )

    with SessionLocal() as session:
        j = session.get(JobListing, job_id)
        if not j:
            raise HTTPException(status_code=404, detail="Job not found")

        if j.ai_summary and not refresh:
            return {"summary": j.ai_summary, "cached": True}

        if not j.description:
            raise HTTPException(status_code=422, detail="No description to summarize")

        from groq import Groq
        client = Groq(api_key=api_key)
        context = _build_job_context(j)

        # Run 3 different models concurrently
        summaries = await asyncio.gather(*[
            _call_groq(client, model, prompt, context)
            for model, prompt in _VARIANTS
        ])

        # Synthesize with the best model
        final = await _synthesize_groq(client, list(summaries), context)

        # Cache in DB
        session.execute(
            text("UPDATE job_listings SET ai_summary = :s WHERE id = :id"),
            {"s": final, "id": job_id}
        )
        session.commit()

        return {"summary": final, "cached": False}


@app.get("/health")
def health():
    return {"status": "ok"}
