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
This first version supports Greenhouse and Lever. Workday and custom career sites need separate adapters; they should not be scraped with the same logic.


## Expanded company coverage
The starter automatic scanner now includes SpaceX, Astranis, Anduril, Stoke Space, K2 Space, BETA Technologies, Shield AI, Hermeus, CesiumAstro, E-Space, Rocket Lab, Star Catcher, and Varda Space Industries. Add more Greenhouse/Lever companies in `companies.json` as their board identifiers are verified.


## Expanded coverage

This version contains **23 automated company feeds** across Greenhouse, Lever, and Workday, plus a `watchlist.json` registry of **100+ aerospace/aviation/space employers** to migrate into automated feeds as their career systems are verified.

The Workday adapter is intentionally configuration-driven (`host`, `tenant`, `site`). Boeing and GE Aerospace are included first. Workday tenants differ, so additional employers should only be enabled after their public CXS endpoint is verified. A failed company check prints a `WARNING` rather than silently counting the company as successfully scanned.

### Coverage strategy
- **Automated now:** Greenhouse, Lever, selected Workday employers.
- **Watch registry:** primes, NewSpace, aircraft/eVTOL, suppliers, labs, and NASA contractors.
- **Next adapters:** additional Workday tenants and custom career platforms used by RTX, Northrop Grumman, Lockheed Martin, Textron/Bell, Gulfstream, Honeywell, L3Harris, etc.

## Expanded official-careers integrations

The scanner now supports four source types:

- `greenhouse` — Greenhouse public job-board API
- `lever` — Lever public Postings API
- `workday` — Workday public CXS endpoint
- `careers_page` — conservative parsing of official server-rendered career search pages

The expanded configuration includes automated checks for RTX/Raytheon/Collins/Pratt & Whitney, Lockheed Martin, Northrop Grumman, L3Harris, Honeywell, Gulfstream Aerospace, Bell/Textron, Firefly Aerospace, Intuitive Machines, and Axiom Space.

`careers_page` sources are intentionally conservative and may return fewer results than the employer's UI when the site loads listings only with JavaScript. A warning is printed if a source cannot be reached; the program does not silently count a failed source as a successful zero-result scan.
## Expanded source coverage

This build contains **89 automated/checkable company configurations** plus the broader 119-company watch registry. Sources include Greenhouse, Lever, Workday CXS, and conservative official-careers-page scans.

Priority additions include ULA, Amentum, Barrios Technology, KBR, Leidos, CACI, Oceaneering, AeroVironment, Sierra Nevada Corporation, Sierra Space, Redwire, Ursa Major, Lunar Outpost, Astrolab, Joby, Archer, Wisk, Moog, Safran, General Atomics, Blue Origin, The Aerospace Corporation, Parsons, Peraton, SAIC, Kratos, General Dynamics Mission Systems, JHU APL, MIT Lincoln Laboratory, Southwest Research Institute, NASA/JPL, Scaled Composites, Stratolaunch, Virgin Galactic, Maxar, Terran Orbital, York Space Systems, Planet, BlackSky, Capella, Muon Space, Embraer, Honda Aircraft, Bombardier, Airbus, Parker, Eaton, Curtiss-Wright, Woodward, Howmet, GKN, Crane, and StandardAero.

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

## Source health and safe failure behavior

The generated workbook includes a **SOURCE HEALTH** sheet. Each configured company is classified as:

- **OK** — the source was successfully checked; zero is trusted only for API-backed or explicitly trusted sources.
- **UNKNOWN** — the page loaded but the scanner could not reliably verify its job inventory (common with JavaScript-heavy career sites).
- **BLOCKED** — the site rejected automated access (for example HTTP 403/429).
- **ERROR** — invalid endpoint, server error, DNS failure, or another fetch/parser failure.

A failed/unknown source no longer causes previously known jobs to be marked CLOSED. Jobs are closed only after that company's source completes a trustworthy check and the job is absent.

The Dashboard summarizes source health so chapter officers can see coverage quality without reading GitHub Actions logs.
