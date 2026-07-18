import { useEffect } from "react";
import styles from "./Toast.module.css";

/**
 * Auto-dismissing toast notification.
 * Props:
 *   message   — string to display
 *   type      — "success" | "error" | "info"
 *   onClose   — called after duration expires or user dismisses
 *   duration  — ms before auto-close (default 4000)
 */
export default function Toast({ message, type = "info", onClose, duration = 4000 }) {
  useEffect(() => {
    if (!message) return;
    const t = setTimeout(onClose, duration);
    return () => clearTimeout(t);
  }, [message, duration, onClose]);

  if (!message) return null;

  return (
    <div
      className={`${styles.toast} ${styles[type]}`}
      role="alert"
      aria-live="assertive"
    >
      <span className={styles.icon} aria-hidden="true">
        {type === "success" ? "✅" : type === "error" ? "❌" : "ℹ️"}
      </span>
      <span className={styles.msg}>{message}</span>
      <button className={styles.close} onClick={onClose} aria-label="Dismiss">
        ×
      </button>
    </div>
  );
}
