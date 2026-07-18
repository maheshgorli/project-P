import styles from "./LoadingSpinner.module.css";

/**
 * Inline loading spinner.
 * Props:
 *   size   — CSS size string, default "20px"
 *   color  — CSS color string, default "currentColor"
 */
export default function LoadingSpinner({ size = "20px", color = "currentColor" }) {
  return (
    <span
      className={styles.spinner}
      style={{ width: size, height: size, borderTopColor: color }}
      role="status"
      aria-label="Loading"
    />
  );
}
