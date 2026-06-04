from datetime import datetime
from scraper import indeed, glassdoor, handshake, lever
from scraper.utils import is_good_url

def run():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Starting scrape...\n")
    all_jobs = []

    # print("Fetching Indeed (JSearch)...")
    # try:
    #     jobs = indeed.fetch(query="software engineer", location="remote", pages=2)
    #     print(f"  → {len(jobs)} jobs")
    #     all_jobs.extend(jobs)
    # except Exception as e:
    #     print(f"  ✗ Indeed failed: {e}")

    # print("Fetching Glassdoor (JSearch)...")
    # try:
    #     jobs = glassdoor.fetch(query="software engineer", location="remote", pages=2)
    #     print(f"  → {len(jobs)} jobs")
    #     all_jobs.extend(jobs)
    # except Exception as e:
    #     print(f"  ✗ Glassdoor failed: {e}")

    # print("Fetching Handshake (JSearch)...")
    # try:
    #     jobs = handshake.fetch(query="software engineer", location="remote", pages=2)
    #     print(f"  → {len(jobs)} jobs")
    #     all_jobs.extend(jobs)
    # except Exception as e:
    #     print(f"  ✗ Handshake failed: {e}")

    print("Fetching Lever (JSearch)...")
    try:
        jobs = lever.fetch(query="software engineer", location="remote", pages=2)
        print(f"  → {len(jobs)} jobs")
        all_jobs.extend(jobs)
        print(all_jobs)
    except Exception as e:
        print(f"  ✗ Lever failed: {e}")

   
if __name__ == "__main__": 
    run()