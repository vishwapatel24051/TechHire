from dataclasses import dataclass

@dataclass
class Job:
    title:    str
    company:  str
    location: str
    job_type: str
    url:      str
    source:   str  # "indeed", "simplyhired", etc.
    posted:   str