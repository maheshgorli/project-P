import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";
import StatsCards from "../components/StatsCards";
import EventCard from "../components/EventCard";
import StartMonitoringButton from "../components/StartMonitoringButton";
import Toast from "../components/Toast";
import LoadingSpinner from "../components/LoadingSpinner";
import styles from "./Dashboard.module.css";

export default function Dashboard() {
  const navigate = useNavigate();

  // Event data
  const [wildfires, setWildfires] = useState([]);
  const [storms, setStorms]       = useState([]);
  const [imageCount, setImageCount] = useState(0);

  // UI state
  const [eventsLoading, setEventsLoading] = useState(true);
  const [monitoring, setMonitoring]       = useState(false);
  const [toast, setToast] = useState({ message: "", type: "info" });

  // ── Data fetchers ────────────────────────────────────────────────────────

  const fetchEvents = useCallback(async () => {
    setEventsLoading(true);
    try {
      const [wfRes, stRes] = await Promise.all([
        api.get("/wildfires"),
        api.get("/storms"),
      ]);
      setWildfires(wfRes.data);
      setStorms(stRes.data);
    } catch (err) {
      console.error("Failed to fetch events:", err);
      setToast({ message: "Failed to load event data from NASA.", type: "error" });
    } finally {
      setEventsLoading(false);
    }
  }, []);

  const fetchImageCount = useCallback(async () => {
    try {
      const res = await api.get("/gallery");
      setImageCount(res.data.length);
    } catch {
      // non-critical — gallery may be empty
    }
  }, []);

  useEffect(() => {
    fetchEvents();
    fetchImageCount();
  }, [fetchEvents, fetchImageCount]);

  // ── Start Monitoring handler ─────────────────────────────────────────────

  async function handleMonitor() {
    setMonitoring(true);
    setToast({ message: "", type: "info" });
    try {
      const res = await api.get("/monitor");
      const d = res.data;
      const msg =
        `Monitoring complete — ${d.total_events} events found, ` +
        `${d.images_downloaded} image(s) saved.`;
      setToast({ message: msg, type: "success" });
      // Refresh all data
      await Promise.all([fetchEvents(), fetchImageCount()]);
    } catch (err) {
      const detail =
        err.response?.data?.detail || err.message || "Unknown error";
      setToast({ message: `Monitoring failed: ${detail}`, type: "error" });
    } finally {
      setMonitoring(false);
    }
  }

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <main className={styles.page}>
      {/* Page header */}
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>🌍 Satellite Dashboard</h1>
          <p className={styles.subtitle}>
            Real-time wildfire &amp; storm monitoring via NASA EONET
          </p>
        </div>
        <div className={styles.actions}>
          <StartMonitoringButton onClick={handleMonitor} loading={monitoring} />
          <button
            className={styles.galleryBtn}
            onClick={() => navigate("/gallery")}
            aria-label="Open image gallery"
          >
            🖼 Image Gallery
          </button>
        </div>
      </div>

      {/* Stats */}
      <StatsCards
        wildfires={wildfires.length}
        storms={storms.length}
        images={imageCount}
      />

      {/* Events grid */}
      {eventsLoading ? (
        <div className={styles.loadingRow}>
          <LoadingSpinner size="32px" color="var(--accent)" />
          <span>Loading events…</span>
        </div>
      ) : (
        <div className={styles.grid}>
          {/* Wildfires */}
          <section aria-labelledby="wf-heading">
            <h2 id="wf-heading" className={`${styles.colTitle} ${styles.fire}`}>
              🔥 Active Wildfires
              <span className={styles.count}>{wildfires.length}</span>
            </h2>
            {wildfires.length === 0 ? (
              <p className={styles.empty}>No active wildfires reported.</p>
            ) : (
              wildfires.map((fire) => (
                <EventCard key={fire.event_id} event={fire} type="wildfire" />
              ))
            )}
          </section>

          {/* Storms */}
          <section aria-labelledby="st-heading">
            <h2 id="st-heading" className={`${styles.colTitle} ${styles.storm}`}>
              🌪 Active Storms
              <span className={styles.count}>{storms.length}</span>
            </h2>
            {storms.length === 0 ? (
              <p className={styles.empty}>No active storms reported.</p>
            ) : (
              storms.map((storm) => (
                <EventCard key={storm.event_id} event={storm} type="storm" />
              ))
            )}
          </section>
        </div>
      )}

      {/* Toast */}
      <Toast
        message={toast.message}
        type={toast.type}
        onClose={() => setToast({ message: "", type: "info" })}
      />
    </main>
  );
}
