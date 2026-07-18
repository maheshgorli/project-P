/**
 * Monitoring page — placeholder for live monitoring / logs view.
 * Future: real-time WebSocket feed, per-event image progress, AI pipeline status.
 */
import styles from "./Monitoring.module.css";

export default function Monitoring() {
  return (
    <main className={styles.page}>
      <h1 className={styles.title}>📡 Live Monitoring</h1>
      <p className={styles.sub}>
        Real-time monitoring feed — coming in a future phase.
      </p>
      <div className={styles.placeholder}>
        <span aria-hidden="true">🛰</span>
        <p>No active monitoring session.</p>
      </div>
    </main>
  );
}
