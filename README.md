# AIAA UH Summer 2027 Internship Finder

Checks configured Greenhouse and Lever career boards daily for Summer 2027 engineering internships and generates an Excel tracker.

## Run locally
1. Install Python 3.11+.
2. `pip install -r requirements.txt`
3. `python internship_finder.py`

The script creates `data/jobs.csv` and `AIAA_UH_Summer_2027_Internships.xlsx`.

## Add companies
Edit `companies.json`. For Greenhouse, the token is the part after `job-boards.greenhouse.io/`. For Lever, it is the part after `jobs.lever.co/`.

## Automatic daily scan
Push this folder to a GitHub repository. The included GitHub Actions workflow runs every day at 9:00 AM America/Chicago and commits changes back to the repository. You can also run it manually from the Actions tab.

## Matching logic
A posting must contain an internship/student term, a Summer 2027 term, and an engineering-relevant term. Adjust the regexes near the top of `internship_finder.py` to broaden or narrow results.

## Current limitation
The scanner supports four source types:

- `greenhouse` — Greenhouse public job-board API
- `lever` — Lever public Postings API
- `workday` — Workday public CXS endpoint
- `careers_page` — conservative parsing of official server-rendered career search pages

**Important:** `careers_page` sources are best-effort checks of official employer pages. JavaScript-heavy sites may return zero results even when jobs exist; the script prints a warning on request failures. API-backed Greenhouse/Lever/Workday integrations are generally more reliable.

## Automatically generated AIAA UH views
Every daily scan rebuilds the Excel workbook from the master job history. It now contains:

- **DASHBOARD** — live counts and the date of the latest run.
- **ALL INTERNSHIPS** — complete history, including postings that later close.
- **NEW TODAY** — live internships first discovered on the current run.
- **NEW THIS WEEK** — live internships first discovered during the last 7 calendar days.
- **TEXAS - HOUSTON** — live postings whose returned location matches Texas or major Texas aerospace hubs; Houston sorts first.
- **CLOSING SOON** — live postings with an explicitly stated deadline in the next 14 days.

The deadline parser is intentionally conservative. If a career site does not expose a trustworthy deadline in the posting text, the scanner leaves the deadline blank rather than guessing. Change `CLOSING_SOON_DAYS` in `internship_finder.py` if the chapter wants a different warning window.
