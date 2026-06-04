import requests
from .base import Job

API_KEY = "b2fe1c1f92mshd13160c1bdf318ep124cf2jsn794ac316fe68"

CS_KEYWORDS = [
    "software engineer", "backend engineer", "frontend engineer",
    "full stack", "data engineer", "ml engineer", "devops",
    "data scientist", "python developer", "java developer",
    "android developer", "ios developer", "cloud engineer"
]

def fetch(query="software engineer", location="remote", pages=2):
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
                "date_posted":      "week",
                "employment_types": "FULLTIME,INTERN",  # handshake has lots of internships
                "remote_jobs_only": "true",
            },
            timeout=30
        )

        if res.status_code != 200:
            print(f"  ⚠ API error {res.status_code} on page {page}")
            continue

        jobs = res.json().get("data", [])
        print(f"  Page {page}: {len(jobs)} total jobs")

        for j in jobs:
            publisher = j.get("job_publisher", "NONE")

            title = j.get("job_title", "").lower()
            if not any(kw in title for kw in CS_KEYWORDS):
                continue

            if not j.get("job_apply_link"):
                continue

            all_jobs.append(Job(
                title    = j.get("job_title",                  "N/A"),
                company  = j.get("employer_name",              "N/A"),
                location = j.get("job_city",                   "N/A"),
                job_type = j.get("job_employment_type",        "N/A"),
                url      = j.get("job_apply_link",             "N/A"),
                source   = publisher,
                posted   = j.get("job_posted_at_datetime_utc", "N/A"),
            ))

    print(f"  → {len(all_jobs)} Handshake jobs after filter")
    return all_jobs