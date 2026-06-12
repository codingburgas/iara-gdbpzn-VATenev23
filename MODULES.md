# Feature Modules — Pick One, I'll Build It

Each module below is self-contained. Tell me the number and I'll implement it fully.
Sorted roughly easiest → hardest. All fit inside the existing Flask/SQLite stack.

---

## Already done
- **[DONE]** Firefighter "Available / On Break" buttons — wired to real backend (was fake `alert()`)
- **[DONE]** Module 2-ish — auto On-Scene on arrival with timestamps + status history entry
- **[DONE]** Module 13 — Real-Time GPS tracker, upgraded far beyond spec: real OSRM road routes, live ETA, animated units (`/staff/map`)
- **[DONE]** Module 14 — Incident timeline / audit log on detail page (with response metrics)
- **[DONE]** Module 17 — Firefighter Performance Score: scoring engine in `app/routes/firefighters.py` (`compute_performance`), commander leaderboard at `/staff/performance` with podium + full breakdown table + 30/90/365-day switcher
- **[DONE]** Module 18 — Major Incident mode: `is_major` + `parent_incident_id` on Incident, declare/link/unlink flows (commander), command card on detail page, MAJOR badges on list + Operations Board
- **[BONUS]** Operations Board command wall (`/staff/operations`)
- **[BONUS]** Public live operations map (`/live`) with privacy-filtered API
- **[BONUS]** Interactive map picker + closest-unit suggestion on incident report
- **[BONUS]** Crew status auto-sync on dispatch/close

---

## 🟢 Easy (30–60 min each)

### 1. Incident Priority Color-Coding + Auto-Sort
Right now incidents show up in whatever order. Add a `priority` field (critical / high / normal / low),
color the entire table row red/orange/yellow/green, and auto-sort so critical ones always float to the top.
Affects: incident model, incident list template, dispatcher dashboard.

### 2. Firefighter "On Scene" Check-In Timer
When a firefighter clicks "On Scene" on an incident, record the exact timestamp.
Show a live ticking clock on their dashboard ("Time on scene: 01:23:45") in red.
Pure JS + one new DB column. Impressive in a demo.

### 3. "My Shift History" Page for Firefighters
Currently firefighters have no way to see their past shifts.
Add a simple page: table of all their shifts (start, end, duration, incidents during that shift).
Clean, useful, and shows DB relationships working correctly.

### 4. Equipment Low-Stock Warning Banner
If any equipment item has quantity < 5, show a red banner at the top of the equipment page
and a small badge on the navbar. Commander/dispatcher can click it to jump straight to that item.
No new model needed — just query logic + template tweaks.

### 5. Incident Search with Filters (date range, type, status)
The current incident list has no real search. Add a proper filter bar:
date from/to, incident type dropdown, status dropdown, free-text search on title/location.
All done server-side with SQLAlchemy filters. Very demo-friendly.

### 6. "Assign Me" Button on Incidents
Firefighters can see open incidents and click "Assign Me" to request assignment to one.
Dispatcher gets a notification. Simple request model — no complex logic.

---

## 🟡 Medium (1–2 hours each)

### 7. Live Incident Feed (SSE-powered ticker)
A scrolling ticker strip at the top of the dispatcher dashboard showing new incidents as they come in,
like a news ticker. Uses the existing SSE notification stream — no new backend needed.
Pure frontend work. Looks extremely impressive in a demo.

### 8. Firefighter Duty Roster Calendar
A weekly calendar view (Mon–Sun grid) showing which firefighters are on shift each day.
Commanders can click a day to see who's scheduled. Built with a plain HTML/CSS grid — no JS calendar library.

### 9. Incident "Hot Spot" Heatmap on the Map
Aggregate all incident coordinates and overlay a heatmap on the Leaflet map.
Leaflet.heat plugin (free, tiny). Shows commanders where incidents cluster in the city.
Very visual, very impressive for a presentation.

### 10. One-Click Incident Report PDF
The PDF generation exists but is probably bare-bones. Make it proper:
header with fire dept logo placeholder, incident details table, assigned units, task list, weather at time of incident, status history timeline. ReportLab is already installed.

### 11. Radio Log with Timestamps + Export
The radio log page likely exists but might be thin. Enhance it:
auto-timestamp every entry, show sender's rank and name, add a "Copy to clipboard" button,
and an "Export as .txt" button for the full log of an incident. No new model needed.

### 12. Dispatcher "Command Board" — Drag-to-Assign
Visual board: left column = open incidents, right column = available vehicles.
Drag a vehicle card onto an incident to assign it. Uses HTML5 drag-and-drop API.
One fetch call on drop. Replaces the current form-based assignment. Looks amazing live.

---

## 🔴 Hard / Impressive (2–4 hours each)

### 13. Real-Time GPS Tracker on Map (Auto-Refresh)
Vehicles already have lat/lng in the DB. Add a `/api/vehicles/locations` JSON endpoint,
then on the map page poll it every 3 seconds and move the vehicle markers smoothly.
No WebSockets — just setInterval + fetch. Looks like a real dispatch system.

### 14. Incident Timeline / Audit Log
Every status change on an incident (Reported → Dispatched → On Scene → Closed) gets logged
with who did it and when. Show it as a vertical timeline on the incident detail page.
New `IncidentLog` model + timeline CSS. Extremely useful for demo — shows the full lifecycle.

### 15. Commander "Situation Report" Auto-Generator
Button on commander dashboard: "Generate SitRep". Pulls all active incidents, assigned units,
weather, and resource status and formats it as a downloadable PDF briefing document.
Two-page PDF: summary stats + incident-by-incident breakdown. Uses ReportLab.

### 16. Photo Upload in Incident Chat
Already listed as Issue #50 — the most requested missing feature.
Firefighters can attach a photo to a chat message. Stored in `app/static/uploads/`.
Shown as a thumbnail in the chat. Proper file type validation, size limit, secure filename.

### 17. Firefighter Performance Score
Each firefighter gets a score based on: incidents responded to, tasks completed on time,
shift hours this month, SOS alerts (negative). Shown as a badge on their profile.
Commander sees a leaderboard. No new model — calculated from existing data.

### 18. Multi-Incident "Major Incident" Mode
Commander can declare a "Major Incident" which merges multiple related incidents
into one command structure. All assigned units report under one incident ID.
Adds a `parent_incident_id` field and changes how the dispatcher dashboard groups things.

---

## 💡 Quick Polish (under 20 min, do multiple in one session)

- **P1** — Add `requirements.txt` (literally 1 command: `pip freeze > requirements.txt`)
- **P2** — Replace all `print()` debug statements in routes with proper `app.logger.debug()`
- **P3** — Pagination on incidents list (currently loads ALL incidents — bad for demo with lots of data)
- **P4** — 404 and 500 custom error pages with fire department theming
- **P5** — Flash message auto-dismiss (currently they stay until clicked — add a 4-second JS fade-out)
- **P6** — Confirm dialog before closing/deleting anything (currently some deletes have no confirmation)
- **P7** — "Last seen" timestamp on firefighter profiles (updated on every login)
- **P8** — Add a favicon (fire emoji or 🚒) so the browser tab looks right during a demo

---

## 🆕 New ideas (added June 2026)

### 19. Incident Replay Mode
Time-scrubber on a closed incident's map: replay the dispatch as it happened —
unit leaves station, drives the stored route, arrives, status flips — all from
`StatusUpdate` timestamps + the saved route polyline. Like a sports replay for
post-incident review. Pure frontend over existing data. **~3 h, demo gold.**

### 20. Hydrant Map Layer
Seed ~20 hydrant locations around Burgas (new tiny model or static JSON).
Toggleable layer on the Live Map + "nearest hydrant: 140 m NE" hint on the
incident detail map. Real fire-service workflow. **~2 h.**

### 21. Shift Handover Report
When a firefighter ends a shift, auto-generate a handover summary: incidents
during the shift, tasks completed, equipment still checked out. Shown on screen
+ downloadable PDF (ReportLab already installed). **~2 h.**

### 22. Risk Clock (hour × weekday heat matrix)
Analytics widget: a 24×7 grid showing when incidents cluster (e.g. Friday
18:00 hotspot). Plain CSS grid colored by count — no chart library needed.
Commanders use this for staffing arguments. **~1.5 h.**

### 23. Equipment Inspection Alerts
`next_inspection` already exists on Equipment but nothing reads it. Add an
"Inspections due" card on the equipment page + a count badge in the sidebar,
and block checkout of overdue items until re-inspected. **~1 h.**

### 24. Station Coverage Rings
On the Live Map, draw 5/10-minute response-time rings around each station
(circles sized from average urban driving speed, or true OSRM isochrones if
ambitious). Instantly shows coverage gaps in the city. **~2 h.**

---

## How to use this file

Open a new session with Opus 4.8 and say:
> "Do module 13" or "Do modules 7 and 8" or "Do all the P modules"

The module descriptions above are self-contained enough that a fresh Claude can build them
without needing the full conversation history.
