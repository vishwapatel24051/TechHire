SKIP_SOURCES = [
    "theladders", "teal", "remote.co", "remotejobs.org",
    "dailyremote", "jobgether", "showbizjobs", "itrecruiters",
    "jobright", "dice"
]

def is_good_url(url: str) -> bool:
    if not url or url == "N/A":
        return False
    url_lower = url.lower()
    if any(skip in url_lower for skip in SKIP_SOURCES):
        return False
    return True