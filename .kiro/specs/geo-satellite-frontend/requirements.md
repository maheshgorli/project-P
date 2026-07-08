# Requirements Document

## Introduction

This document defines the requirements for the Geo Satellite Frontend — a full React-based mission-control UI that sits in front of an existing FastAPI backend. The frontend provides real-time wildfire and storm monitoring via NASA EONET data, Sentinel-2 true-color satellite imagery, mocked AI disaster-detection analysis, and historical analytics. The application uses a dark mission-control aesthetic with a persistent sidebar layout and five routed pages.

The backend is already live at `http://127.0.0.1:8000` and exposes the following real endpoints:
- `GET /` — health check
- `GET /wildfires` — `[{ title, event_id, category, coordinates: [lon, lat] }]`
- `GET /storms` — same shape, category = severe storms
- `GET /satellite-image?latitude=&longitude=` — Sentinel-2 PNG metadata + URL
- `GET /sentinel-test` — `{ authenticated, client_id }`
- `GET /satellite` — `{ status }`

The following backend features (AI/CV detection, MongoDB event history, risk scoring) are **not yet built** and must be mocked at the service layer.

---

## Glossary

- **App**: The complete React single-page application described in this document.
- **Sidebar**: The persistent left-side navigation component that lists all page routes.
- **Topbar**: The persistent top bar showing page title, UTC clock, and connection status.
- **Dashboard**: The `/` route providing a summary of platform health and live events.
- **LiveMonitoring**: The `/monitoring` route providing a split-map-and-satellite view with clickable coordinates.
- **SatelliteExplorer**: The `/explorer` route for manual coordinate input and satellite image retrieval.
- **AIDetection**: The `/detection` route showing mocked AI disaster analysis on a satellite image.
- **HistoryAnalytics**: The `/history` route showing time-series charts and before/after image comparisons.
- **Settings**: The `/settings` route for API status, theme, tile provider, and notification preferences.
- **MapComponent**: The `react-leaflet` map rendered inside LiveMonitoring using a CartoDB dark-matter tile layer.
- **RiskCard**: A card component displaying a disaster category (wildfire, flood, storm, thermal) with a HIGH/MEDIUM/LOW badge.
- **SatelliteImagePanel**: A reusable component that fetches and displays a Sentinel-2 image for a given coordinate pair.
- **AIDetectionService**: The mock service at `src/services/aiDetection.js` that simulates AI analysis of an image URL.
- **HistoryService**: The mock service at `src/services/history.js` that generates synthetic time-series event data.
- **DesignSystem**: The Tailwind CSS configuration defining the dark mission-control color palette and typography.
- **Marker**: A `react-leaflet` marker placed on the MapComponent at a wildfire or storm coordinate.
- **CoordinateState**: Shared React context that holds the most recently selected latitude/longitude from any map click or form input.

---

## Requirements

---

### Requirement 1: Foundation — Design System and App Shell

**User Story:** As a developer, I want a consistent dark mission-control design system and app shell, so that all pages share the same visual language and navigation structure.

#### Acceptance Criteria

1. THE DesignSystem SHALL define Tailwind CSS color tokens for `background` (#08111F), `surface` (#0F172A), `surface-alt` (#111827), `border` (#1E293B), `accent-cyan` (#22D3EE), `accent-green` (#10B981), `accent-orange` (#F97316), and `accent-red` (#EF4444) in `tailwind.config.js`.
2. THE DesignSystem SHALL configure `Space Grotesk` or `IBM Plex Sans` as the default body font and `JetBrains Mono` as the font for all coordinate and numeric readouts, applied via Tailwind's `fontFamily` theme extension.
3. THE App SHALL render a persistent Sidebar and Topbar on every route without re-mounting those components during page navigation.
4. THE Sidebar SHALL display navigation links for: Dashboard, Live Monitoring, Satellite Explorer, AI Detection, History & Analytics, and Settings.
5. WHEN a route is active, THE Sidebar SHALL highlight the corresponding navigation item with an accent-cyan left border and a tinted background distinct from the inactive state.
6. THE Sidebar SHALL support a collapsed state that hides link labels and shows only icons, toggled by a visible collapse button that remains visible in both states.
7. THE Topbar SHALL display the current page title, a live UTC clock updated every second, and connection status pills for Satellite (wired to `/sentinel-test`), AI (mocked, labeled "Mocked" in a code comment), and DB (mocked, labeled "Mocked" in a code comment).
8. WHEN the `/sentinel-test` endpoint returns `{ authenticated: true }`, THE Topbar SHALL render the Satellite status pill with accent-green color and the text "Connected".
9. IF the `/sentinel-test` endpoint returns a network error or `{ authenticated: false }`, THEN THE Topbar SHALL render the Satellite status pill with accent-red color and the text "Disconnected".
10. THE App SHALL include a commented-out route stub for a future `/auth` login page, with a code comment reading `// TODO: Uncomment when auth is implemented`.
11. THE App SHALL apply a `min-w-[1024px]` constraint so that content does not collapse below 1024px viewport width; a horizontal scrollbar is acceptable below that threshold.
12. THE App SHALL apply Framer Motion `AnimatePresence` page-transition animations (opacity fade + slight vertical slide) when navigating between routes.

---

### Requirement 2: Dependency Installation and Project Configuration

**User Story:** As a developer, I want all required libraries installed and configured, so that I can use routing, maps, charts, animations, and UI components without manual setup.

#### Acceptance Criteria

1. THE `frontend/package.json` SHALL list `react-router-dom`, `leaflet`, `react-leaflet`, `recharts`, `framer-motion`, `@tanstack/react-query`, and `lucide-react` as entries under `dependencies`.
2. THE `frontend/package.json` SHALL list `tailwindcss`, `postcss`, and `autoprefixer` as entries under `devDependencies`.
3. THE `frontend/tailwind.config.js` SHALL exist and its `content` array SHALL include glob patterns covering all files under `src/` (e.g., `./src/**/*.{js,jsx,ts,tsx}`).
4. THE `frontend/postcss.config.js` SHALL exist and SHALL include `tailwindcss` and `autoprefixer` as plugins.
5. THE shadcn/ui component files for `button`, `card`, `badge`, `tabs`, `dialog`, `select`, and `slider` SHALL be present under `src/components/ui/`.
6. THE `frontend/src/main.jsx` SHALL wrap the root `<App />` component in `<QueryClientProvider client={queryClient}>` where `queryClient` is an instance of `QueryClient`.
7. THE `frontend/src/main.jsx` SHALL contain a top-level import of `leaflet/dist/leaflet.css` before any component imports that render maps.

---

### Requirement 3: Dashboard Page

**User Story:** As an operator, I want a dashboard overview, so that I can quickly assess the current state of active disaster events and satellite connectivity.

#### Acceptance Criteria

1. THE Dashboard SHALL render a hero strip containing the platform name "Geo Satellite Tracking Platform", a one-line tagline, and a "Launch Monitoring" CTA button that navigates to `/monitoring` on click.
2. THE Dashboard SHALL display four RiskCards for the categories: Wildfire, Flood, Storm, and Thermal.
3. WHEN the `/wildfires` endpoint responds successfully, THE Dashboard SHALL derive the Wildfire RiskCard badge level as: 0 events → LOW, 1–5 events → MEDIUM, 6 or more events → HIGH.
4. THE Dashboard SHALL render the Flood RiskCard badge level from a mocked value (default MEDIUM) with a code comment reading `// TODO: Replace with real flood endpoint when available`.
5. THE Dashboard SHALL render the Thermal RiskCard badge level from a mocked value (default LOW) with a code comment reading `// TODO: Replace with real thermal endpoint when available`.
6. WHEN the `/storms` endpoint responds successfully, THE Dashboard SHALL derive the Storm RiskCard badge level as: 0 events → LOW, 1–3 events → MEDIUM, 4 or more events → HIGH.
7. THE Dashboard SHALL render a SatelliteImagePanel that issues a real `/satellite-image` call on mount with latitude=17.3850 and longitude=78.4867.
8. THE Dashboard SHALL render a "Latest AI Detection" card displaying the values from the mocked object `{ disaster: 'Wildfire', confidence: 94, area: 'California', time: '12:45 UTC' }` with a code comment reading `// TODO: Replace with real AI detection endpoint when available`.
9. THE Dashboard SHALL render an alerts strip with color-coded pills: wildfire alert pill count derived from `/wildfires` response length, storm alert pill count derived from `/storms` response length, and flood and thermal pills from mocked values with code comments indicating the future real source.
10. WHILE the `/wildfires` or `/storms` endpoint is loading, THE Dashboard SHALL render skeleton placeholder elements in place of the real data cards.
11. IF the `/wildfires` endpoint returns an error, THEN THE Dashboard SHALL display an inline error message within the Wildfire RiskCard and SHALL NOT unmount other page sections.
12. IF the `/storms` endpoint returns an error, THEN THE Dashboard SHALL display an inline error message within the Storm RiskCard and SHALL NOT unmount other page sections.
13. IF the `/satellite-image` call for the default Hyderabad coordinates fails, THEN THE SatelliteImagePanel on the Dashboard SHALL display an error state with the failure reason and SHALL NOT crash the page.

---

### Requirement 4: Live Monitoring Page

**User Story:** As an operator, I want a live map with real event markers and on-demand satellite imagery, so that I can visually monitor active disasters and inspect any geographic area in detail.

#### Acceptance Criteria

1. THE LiveMonitoring page SHALL render a two-column layout with the MapComponent occupying 60% of the content width on the left and the SatelliteImagePanel occupying 40% on the right, at viewport widths of 1024px and above; below 1024px the two panels SHALL stack vertically.
2. THE MapComponent SHALL use the CartoDB dark-matter tile layer URL `https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png`.
3. WHEN the `/wildfires` endpoint responds successfully, THE MapComponent SHALL render a visually distinct orange marker icon at position `[coordinates[1], coordinates[0]]` (latitude = index 1, longitude = index 0) for each event.
4. WHEN the `/storms` endpoint responds successfully, THE MapComponent SHALL render a visually distinct blue marker icon at position `[coordinates[1], coordinates[0]]` (latitude = index 1, longitude = index 0) for each event.
5. WHEN a user clicks on any Marker, THE MapComponent SHALL display a popup containing the event's `title`, `event_id`, and `category` fields.
6. WHEN a user clicks anywhere on the MapComponent, THE LiveMonitoring page SHALL update the CoordinateState context with the clicked `{ lat, lng }` values, where lat is in the range [-90, 90] and lng is in the range [-180, 180].
7. WHEN CoordinateState is updated by a map click, THE LiveMonitoring page SHALL display a coordinate readout showing the latitude and longitude values rounded to 4 decimal places.
8. THE SatelliteImagePanel SHALL initialize with latitude=17.3850 and longitude=78.4867 (Hyderabad) and SHALL display the image fetched for those coordinates until a different coordinate is explicitly fetched.
9. WHEN the user clicks "Fetch image for this point", THE LiveMonitoring page SHALL issue a real `/satellite-image?latitude=&longitude=` request using the current CoordinateState values, and the fetch button SHALL be disabled until the request completes.
10. WHEN the `/satellite-image` call is in progress, THE SatelliteImagePanel SHALL display a loading spinner and SHALL hide any previously displayed image.
11. IF the `/satellite-image` response contains `success: false`, THEN THE SatelliteImagePanel SHALL display the value of the `error` field from the response.
12. IF the `/satellite-image` network request fails (non-2xx HTTP status or network error), THEN THE SatelliteImagePanel SHALL display a generic error message and SHALL retain any previously displayed image.
13. THE LiveMonitoring page SHALL render an AI Prediction bar below the two-column section displaying mocked fields: event type, confidence value (0.0–1.0), and timestamp; with a code comment reading `// TODO: Replace with real AI detection endpoint when available`.
14. THE LiveMonitoring page SHALL apply staggered Framer Motion entrance animations to the MapComponent and SatelliteImagePanel on initial mount, with a stagger delay between 150ms and 500ms.

---

### Requirement 5: Satellite Explorer Page

**User Story:** As an analyst, I want to manually enter coordinates and fetch a satellite image with full metadata, so that I can inspect any specific geographic location.

#### Acceptance Criteria

1. THE SatelliteExplorer page SHALL render a form with two numeric input fields labeled "Latitude" and "Longitude" that accept floating-point values.
2. WHEN the SatelliteExplorer page mounts and CoordinateState holds a previously selected coordinate, THE latitude and longitude inputs SHALL be pre-populated with those CoordinateState values.
3. THE SatelliteExplorer page SHALL render a date-range input that is visually disabled (non-interactive) and SHALL display a tooltip with the text "Coming soon" when the user hovers over it.
4. THE SatelliteExplorer page SHALL render resolution and satellite-selector inputs that are visually disabled (non-interactive) and SHALL display a tooltip with the text "Coming soon" when the user hovers over each.
5. WHEN the user clicks "Fetch Satellite Image" and both inputs contain valid values, THE SatelliteExplorer SHALL issue a real `/satellite-image?latitude=&longitude=` request.
6. IF the latitude input is empty or contains a non-numeric value or a value outside [-90, 90] at the time the user clicks "Fetch Satellite Image", THEN THE SatelliteExplorer SHALL display an inline validation error adjacent to the latitude input and SHALL NOT issue the request.
7. IF the longitude input is empty or contains a non-numeric value or a value outside [-180, 180] at the time the user clicks "Fetch Satellite Image", THEN THE SatelliteExplorer SHALL display an inline validation error adjacent to the longitude input and SHALL NOT issue the request.
8. WHEN the `/satellite-image` endpoint responds with `success: true`, THE SatelliteExplorer SHALL display the image at the URL given by the `image_url` field.
9. WHEN the `/satellite-image` endpoint responds with `success: true`, THE SatelliteExplorer SHALL display a metadata panel in JetBrains Mono font showing: `bbox` (array of 4 values), `resolution_meters`, `image_size_pixels.width` and `image_size_pixels.height`, `file_size_bytes`, `time_interval` (start and end dates), `data_collection`, `latitude`, and `longitude`.
10. WHILE the `/satellite-image` request is in progress, THE "Fetch Satellite Image" button SHALL show a loading indicator and SHALL be disabled to prevent duplicate submissions.
11. IF the `/satellite-image` response contains `success: false` or the network request fails, THEN THE SatelliteExplorer SHALL display the error message from the response (or a generic fallback) and SHALL retain any previously displayed image and metadata.

---

### Requirement 6: AI Detection Page

**User Story:** As an analyst, I want to run AI-based disaster analysis on a satellite image, so that I can identify potential threats with confidence scores.

#### Acceptance Criteria

1. THE AIDetection page SHALL accept a satellite image via file upload input OR by receiving an image URL passed through CoordinateState from the SatelliteImagePanel flow.
2. WHEN a satellite image source is available but detection has not yet been triggered, THE AIDetection page SHALL display the original image on the left panel and a placeholder graphic on the right panel labeled "Processed image will appear here".
3. WHEN the user clicks the "Run Detection" button, THE AIDetection page SHALL call `runDetection(imageUrl)` from AIDetectionService, and the button SHALL be disabled until the call resolves.
4. WHEN `runDetection` is called, THE AIDetectionService SHALL wait between 1500ms and 3000ms before resolving, and SHALL return an object shaped as `{ disaster: string, confidence: number (integer 0–100), area: string, smokeDetected: boolean, thermalHotspot: boolean, riskLevel: 'HIGH' | 'MEDIUM' | 'LOW' }` with a code comment reading `// TODO: Replace with real CV/AI endpoint when available`.
5. WHEN AIDetectionService resolves successfully, THE AIDetection page SHALL render a confidence meter bar whose filled width corresponds to the `confidence` value on a 0–100 scale, with the percentage value displayed as text.
6. WHEN AIDetectionService resolves successfully, THE AIDetection page SHALL render a risk badge displaying the `riskLevel` text, colored accent-red for HIGH, accent-orange for MEDIUM, and accent-green for LOW.
7. WHEN AIDetectionService resolves successfully, THE AIDetection page SHALL render a "Smoke detected" chip showing a filled/active state when `smokeDetected` is true and an outlined/inactive state when false, and a "Thermal hotspot detected" chip with the same active/inactive states for `thermalHotspot`.
8. WHILE `runDetection` is processing, THE AIDetection page SHALL display an animated progress indicator and the "Run Detection" button SHALL remain disabled.
9. THE `src/services/aiDetection.js` file SHALL contain a file-level comment block explaining that the module is a mock implementation pending a real CV/AI backend endpoint.
10. IF `runDetection` throws or rejects, THEN THE AIDetection page SHALL display an error message within the results panel and SHALL re-enable the "Run Detection" button.

---

### Requirement 7: History & Analytics Page

**User Story:** As an analyst, I want to review historical event trends and compare satellite images over time, so that I can identify long-term patterns and assess change.

#### Acceptance Criteria

1. THE HistoryAnalytics page SHALL render two tabs labeled "Timeline" and "Analytics", with "Timeline" active by default.
2. THE HistoryAnalytics page SHALL render four timeline filter controls: "Yesterday", "Last Week", "Last Month", and a custom date picker accepting a start date and an end date, each within the range 2000-01-01 to the current date.
3. WHEN a timeline filter or date range is selected, THE HistoryAnalytics page SHALL call `getHistory(range)` from HistoryService where `range` encodes the selected period.
4. THE HistoryService `getHistory(range)` function SHALL return a synchronous or Promise-resolved array of between 7 and 30 objects shaped as `{ date: string (ISO 8601 date, e.g. "2024-03-15"), wildfires: number (0–50), floods: number (0–50), storms: number (0–50) }`, with a file-level comment reading `// TODO: Replace with real /history endpoint when available`.
5. THE "Timeline" tab SHALL render a before/after satellite image comparison slider; dragging the slider handle SHALL reveal more of the "after" image and less of the "before" image in a continuous motion.
6. THE "Analytics" tab SHALL render a Recharts `LineChart` with three lines (wildfires, floods, storms) plotted over the dates returned by HistoryService.
7. THE "Analytics" tab SHALL render a Recharts `BarChart` displaying the total event count per category (wildfire, flood, storm) as separate bars.
8. THE "Analytics" tab SHALL render a Recharts `PieChart` showing the relative proportion of wildfire, flood, and storm events as slices.
9. THE "Analytics" tab SHALL render summary stat cards displaying: total event count (sum of all wildfires + floods + storms across all dates), peak single-day wildfire count, and peak single-day storm count — all derived from HistoryService data.
10. WHILE HistoryService data is loading (or the Promise is pending), THE HistoryAnalytics page SHALL render skeleton placeholder elements in place of all charts and stat cards.
11. IF `getHistory` throws or rejects, THEN THE HistoryAnalytics page SHALL display an error message and SHALL NOT render blank or partially-rendered charts.
12. IF the before/after image sources fail to load in the Timeline tab, THEN THE comparison slider SHALL display an error placeholder for the failing image without crashing the tab.

---

### Requirement 8: Settings Page

**User Story:** As an operator, I want to view API connection status and configure application preferences, so that I can monitor system health and customize the interface.

#### Acceptance Criteria

1. THE Settings page SHALL display an API status section listing three entries: "NASA EONET", "Sentinel Hub", and "AI Service".
2. WHEN the `/satellite` endpoint returns `{ status: 200 }`, THE Settings page SHALL display the NASA EONET entry with an accent-green badge labeled "Online".
3. IF the `/satellite` endpoint returns a network error or a response where `status` is not 200, THEN THE Settings page SHALL display the NASA EONET entry with an accent-red badge labeled "Offline".
4. WHEN the `/sentinel-test` endpoint returns `{ authenticated: true }`, THE Settings page SHALL display the Sentinel Hub entry with an accent-green badge labeled "Online".
5. IF the `/sentinel-test` endpoint returns a network error or `{ authenticated: false }`, THEN THE Settings page SHALL display the Sentinel Hub entry with an accent-red badge labeled "Offline".
6. THE Settings page SHALL display the AI Service entry with an accent-orange badge labeled "Mocked" at all times.
7. THE Settings page SHALL render a theme section with a "Dark" toggle in the active/on state and a "Light" toggle in a visually disabled state; WHEN the user hovers over the "Light" toggle, a tooltip SHALL appear indicating the feature is not yet available.
8. THE Settings page SHALL render a map tile provider selector offering at least three options: "CartoDB Dark Matter", "OpenStreetMap Standard", and "Esri Satellite"; WHEN the user selects a provider, THE MapComponent on the LiveMonitoring page SHALL use the corresponding tile URL immediately without requiring page navigation or reload.
9. THE Settings page SHALL render three notification preference toggles labeled "Wildfire alerts", "Storm alerts", and "AI detection alerts", stored in local component state; WHEN the page is reloaded, all toggles SHALL reset to their default-on values.

---

### Requirement 9: Shared State and Service Layer Architecture

**User Story:** As a developer, I want a clean shared-state and service-layer architecture, so that coordinate selection, tile provider preference, and mock services are consistently accessible across all pages.

#### Acceptance Criteria

1. THE App SHALL expose CoordinateState via a React Context provider wrapping the entire router, so that any page can read and update the selected latitude and longitude without prop-drilling.
2. WHEN a user clicks on the MapComponent in LiveMonitoring, THE CoordinateState context SHALL be updated with the clicked `{ lat, lng }` values, where lat is validated to be within [-90, 90] and lng within [-180, 180] before being stored.
3. WHEN a user submits coordinates in SatelliteExplorer, THE CoordinateState context SHALL be updated with the submitted `{ lat, lng }` values after client-side validation confirms both are within their respective valid ranges.
4. IF a map click or form submission produces coordinate values outside the valid ranges, THEN THE CoordinateState context SHALL NOT be updated and an error indicator SHALL be shown to the user.
5. THE App SHALL expose a tile provider preference via a React Context provider, with a default value of the CartoDB Dark Matter URL (`https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png`), so that MapComponent reads the active tile URL from context on each render.
6. THE `src/services/aiDetection.js` file SHALL return static or algorithmically-generated in-memory data structures and SHALL NOT call `fetch`, `axios`, `XMLHttpRequest`, or any equivalent network API.
7. THE `src/services/history.js` file SHALL return static or algorithmically-generated in-memory data structures and SHALL NOT call `fetch`, `axios`, `XMLHttpRequest`, or any equivalent network API.
8. THE App SHALL use `@tanstack/react-query` `useQuery` hooks for all real API calls to `/wildfires`, `/storms`, `/satellite-image`, `/satellite`, and `/sentinel-test`, with a default `staleTime` of at least 30 seconds to prevent unnecessary refetches.
9. IF a `useQuery` call to any real endpoint fails, THEN THE component consuming that query SHALL receive the error via the query's `error` field and SHALL display it without crashing the page.

---

### Requirement 10: Visual Polish and Animation

**User Story:** As a user, I want smooth animations and polished visual feedback, so that the interface feels responsive and conveys the real-time nature of the platform.

#### Acceptance Criteria

1. THE App SHALL apply Framer Motion staggered card entrance animations to all card grids on initial page load; each card SHALL animate from `opacity: 0, translateY: 16px` to `opacity: 1, translateY: 0px` with a delay of `0.1s × card index`.
2. WHILE a badge or indicator is in a "LIVE" or "HIGH" risk state, THE App SHALL apply a Framer Motion animation that cycles the element's opacity between 0.4 and 1.0 on a 2-second repeat loop.
3. ALL card components SHALL apply the Tailwind classes `border border-white/10 rounded-xl` for baseline card styling.
4. WHEN a user hovers over a card component, THE card SHALL transition to a box-shadow glow using accent-cyan at 20% opacity within 150ms to 300ms.
5. THE App SHALL NOT include inline `style={{}}` props except on elements where the style value is a runtime-computed percentage (progress meter fill widths and before/after slider positions).
6. THE App SHALL use Tailwind utility classes for all static styling, including colors, spacing, typography, borders, and shadows; no hardcoded hex values or pixel values SHALL appear in JSX className strings.
7. WHEN a RiskCard badge level is HIGH, THE badge SHALL apply a class that resolves to the `accent-red` (#EF4444) color token.
8. WHEN a RiskCard badge level is MEDIUM, THE badge SHALL apply a class that resolves to the `accent-orange` (#F97316) color token.
9. WHEN a RiskCard badge level is LOW, THE badge SHALL apply a class that resolves to the `accent-green` (#10B981) color token.
