# 🚀 AIAA UH — Aerospace Internships & New Grad Roles

A community-maintained, automated tracker for **aerospace, aviation, space, defense, robotics, manufacturing, and research opportunities** for University of Houston students.

> ⭐ Texas and Houston opportunities are a priority, but the tracker covers roles across the United States.

## 🎓 New Grad / Early Career

> **Coming next:** the scanner is being expanded to include genuine entry-level and new-graduate engineering roles. A title such as *Engineer I* will not automatically qualify; the posting must show evidence that it is appropriate for a first post-bachelor's role.

<!-- NEW_GRAD_JOBS_START -->
| Company | Role | Location | Posted | Apply |
|---|---|---|---|---|
| _Scanner expansion in progress_ | — | — | — | — |
<!-- NEW_GRAD_JOBS_END -->

## 🛠️ Internships

The existing automated scanner checks configured employer career boards for Summer 2027 engineering internships. Generated results are stored in `data/jobs.csv` and the Excel tracker.

<!-- INTERNSHIP_JOBS_START -->
_Run the scanner to refresh the current internship dataset. The README generator will populate this section from the normalized job data._
<!-- INTERNSHIP_JOBS_END -->

## What belongs here

The tracker covers opportunities across these AIAA UH interest areas:

- 🚀 **Spaceflight** — rockets, propulsion, launch
- 🛰️ **Space Systems** — spacecraft, satellites, stations
- 🌙 **Exploration** — rovers, landers, habitats, spacesuits
- ✈️ **Aviation** — commercial, general, electric and advanced aircraft
- 🛡️ **Defense & High-Speed Flight** — military aircraft, missiles, hypersonics
- 🤖 **Robotics & Autonomous Systems** — UAS, drones, autonomy
- 🏭 **Manufacturing & Suppliers** — materials, components, production
- 🔬 **Government & Research** — NASA, national labs, R&D

Relevant disciplines include aerospace, mechanical, electrical/electronics, computer, embedded, software, systems, GNC/controls, manufacturing/industrial, materials, test/integration, propulsion, structures, quality/reliability, and other technical engineering roles.

## Automation

The current scanner runs automatically and safely preserves previously known roles when an employer source is blocked or cannot be verified.

### Current source adapters

- `greenhouse` — Greenhouse public job-board API
- `lever` — Lever public Postings API
- `workday` — Workday public CXS endpoint
- `careers_page` — conservative parsing of official server-rendered career pages

API-backed Greenhouse, Lever, and verified Workday integrations are preferred. JavaScript-heavy career pages may not expose their inventory reliably.

## Data and generated views

The scanner currently produces:

- `data/jobs.csv` — master internship job data
- `AIAA_UH_Summer_2027_Internships.xlsx` — chapter-friendly workbook
- **NEW TODAY**
- **NEW THIS WEEK**
- **TEXAS - HOUSTON**
- **CLOSING SOON**
- **SOURCE HEALTH**

The deadline parser is intentionally conservative. If an employer does not expose a trustworthy deadline, the tracker leaves it blank instead of guessing.

## Source health

Each configured employer is classified as:

- **OK** — source successfully checked
- **UNKNOWN** — source loaded but inventory could not be reliably verified
- **BLOCKED** — automated access was rejected
- **ERROR** — endpoint or request failed

A failed or unknown source does **not** automatically close previously known jobs.

## Run locally

1. Install Python 3.11+.
2. Run `pip install -r requirements.txt`.
3. Run `python internship_finder.py`.

## Add companies

Edit `companies.json` for verified automated feeds. `watchlist.json` contains the broader aerospace/aviation/space employer registry being migrated into verified sources.

---

### Goal

Build an aerospace-focused equivalent of the large community internship trackers: simple GitHub tables for students, structured data underneath, automated discovery and closure checking, and strict eligibility rules so the board stays useful instead of becoming a dump of unrelated job postings.
