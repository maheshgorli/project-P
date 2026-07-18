import LoadingSpinner from "./LoadingSpinner";
import styles from "./StartMonitoringButton.module.css";

/**
 * "Start Monitoring" primary action button.
 * Props:
 *   onClick    — async handler called on click
 *   loading    — bool, shows spinner and disables button while true
 */
export default function StartMonitoringButton({ onClick, loading }) {
  return (
    <button
      className={styles.btn}
      onClick={onClick}
      disabled={loading}
      aria-busy={loading}
      aria-label={loading ? "Monitoring in progress…" : "Start monitoring"}
    >
      {loading ? (
        <>
          <LoadingSpinner size="16px" color="#fff" />
          <span>Monitoring…</span>
        </>
      ) : (
        <>
          <span className={styles.dot} aria-hidden="true" />
          <span>Start Monitoring</span>
        </>
      )}
    </button>
  );
}
