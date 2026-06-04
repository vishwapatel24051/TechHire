import requests
from .base import Job

API_KEY = "b2fe1c1f92mshd13160c1bdf318ep124cf2jsn794ac316fe68"

CS_KEYWORDS = [
    "software engineer", "backend engineer", "frontend engineer",
    "full stack", "data engineer", "ml engineer", "devops",
    "data scientist", "python developer", "java developer"
]

def fetch(query, location, pages=2):
    all_jobs = []
    for page in range(1, pages + 1):
        res = requests.get(
            "https://jsearch.p.rapidapi.com/search",
            headers={
                "X-RapidAPI-Key":  API_KEY,
                "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
            },
            params={
                "query":            f"{query} in {location}",
                "page":             str(page),
                "num_results":      "10",
                "date_posted":      "week",       # only recent jobs
                "employment_types": "FULLTIME",   # full time only
                "remote_jobs_only": "true",       # remote only
            },
            timeout=30
        )
        jobs = res.json().get("data", [])
        print(f"  Page {page}: {len(jobs)} jobs before filter")

        for j in jobs:
            title = j.get("job_title", "").lower()

            # skip if title doesn't match any CS keyword
            if not any(kw in title for kw in CS_KEYWORDS):
                continue

            all_jobs.append(Job(
                title    = j.get("job_title",                  "N/A"),
                company  = j.get("employer_name",              "N/A"),
                location = j.get("job_city",                   "N/A"),
                job_type = j.get("job_employment_type",        "N/A"),
                url      = j.get("job_apply_link",             "N/A"),
                source   = "indeed",
                posted   = j.get("job_posted_at_datetime_utc", "N/A"),
            ))

    print(f"  → {len(all_jobs)} CS jobs after filter")
    return all_jobs