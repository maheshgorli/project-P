# Tech Debt & PRD Gap Tracker

Tracks the delta between the PRD ("Project P – Automated Geo Satellite Platform")
and the current implementation. Update this file as items are resolved.

---

## 1. Declared but unused dependencies

The following packages appear in `Requirements.txt` but are not imported or
referenced anywhere in `backend/app/`:

| Package | PRD section requiring it | Status |
|---|---|---|
| `tensorflow` | §7 AI-Based Disaster Detection | Unused |
| `opencv-python` | §7 AI-Based Disaster Detection (image processing) | Unused |
| `pillow` | §7 AI-Based Disaster Detection (image I/O) | Unused |
| `scikit-learn` | §7 AI-Based Disaster Detection (classical ML fallback) | Unused |
| `motor` | §11 Technology Stack – async MongoDB driver | Unused |
| `pymongo` | §11 Technology Stack – MongoDB | Unused |

Installing these without using them increases environment setup time and attack
surface. They should stay in `Requirements.txt` as intent markers but be moved
to a clearly labelled `# --- future / not yet wired ---` section until the
relevant milestone is reached.

---

## 2. Missing PRD features

### AI / CV disaster detection (PRD §7)
- No model training, inference, or image-pipeline code exists yet.
- Current implementation is a pure pass-through of raw NASA EONET event data
  (`backend/app/routers/satellite.py` → `_fetch_events_by_category()`).
- No satellite imagery is fetched, preprocessed, or classified.

### MongoDB persistence layer (PRD FR-06 – "maintain historical records")
- No database connection, schema, or write path exists.
- Every request to `/wildfires` and `/storms` re-fetches live data from EONET
  with no caching, deduplication, or history stored.
- `motor` / `pymongo` are declared in `Requirements.txt` but never instantiated.

### Alert-threshold and risk-level logic (PRD FR-05)
- No risk score, severity tier, or threshold comparison is computed anywhere in
  `backend/app/`.
- Events are returned as raw EONET records with no prioritisation or alerting.

### Leaflet.js map (PRD – "High" priority frontend feature)
- `leaflet` is absent from `frontend/package.json`; no map component exists in
  `frontend/src/`.
- Current UI (`frontend/src/App.jsx`) renders events as plain card lists only.

---

## 3. Recommended next milestones

Work items ordered from lowest to highest complexity/risk:

- **(a) Leaflet map in frontend** — add `leaflet` + `react-leaflet` to
  `frontend/package.json`; replace the card lists in `frontend/src/App.jsx`
  with a map that plots wildfire and storm coordinates. No backend changes
  needed; unblocks the core visual deliverable.

- **(b) MongoDB event history** — add a `backend/app/services/db_service.py`
  using `motor` for async writes; wire `/wildfires` and `/storms` to persist
  each fetched event with a timestamp before returning. Satisfies FR-06 and
  enables deduplication.

- **(c) Risk-scoring function** — add a lightweight scoring function in
  `backend/app/services/` that assigns a severity tier based on event age,
  coordinate proximity, and category before any ML is introduced. Satisfies
  FR-05 without heavyweight dependencies.

- **(d) TensorFlow / OpenCV image detection** — only after (a)–(c) are stable.
  This is the highest-complexity, highest-risk item: requires a training
  dataset, model artefact storage, and a separate inference pipeline. Introduce
  it in an isolated `backend/app/services/detection_service.py` so the rest of
  the app stays unaffected during development.
